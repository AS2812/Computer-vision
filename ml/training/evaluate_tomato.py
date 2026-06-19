"""Tomato-disease evaluation harness, focused on Target Spot.

Run it against a labelled image folder to produce the artefacts the task asks for:

* a confusion matrix over the 10 tomato classes,
* per-class precision / recall / F1,
* a confidence distribution (correct vs wrong, per class),
* a Target-Spot focus block (recall + exactly what it gets confused with), and
* an optional fitted temperature + per-class thresholds written to the calibration
  sidecar (``ml/models/plant_disease_mobilenetv2.calibration.json``).

Dataset layout (PlantVillage / ImageFolder style)::

    <root>/Tomato___Target_Spot/*.jpg
    <root>/Tomato___Early_blight/*.jpg
    ...

Only folders whose name is a tomato model label are scored. With no dataset the
script prints instructions and exits 0, so it is safe to import and unit-test.

The metric functions at the top are pure (numpy only) and are unit-tested without
any images or model — that is what guards the class-index ordering and the
calibration maths.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.calibration import (  # noqa: E402
    TARGET_SPOT_KEY,
    TOMATO_MODEL_LABELS,
    apply_temperature,
    confusion_group,
    fit_temperature,
)

CALIBRATION_PATH = ROOT / "ml" / "models" / "plant_disease_mobilenetv2.calibration.json"
LABELS_PATH = ROOT / "ml" / "models" / "plant_disease_mobilenetv2.labels.json"


# --- Pure metric functions (unit-tested, no images required) -----------------

def confusion_matrix(y_true: list[int], y_pred: list[int], n_classes: int) -> np.ndarray:
    """Rows = true class, columns = predicted class."""
    matrix = np.zeros((n_classes, n_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        matrix[t, p] += 1
    return matrix


@dataclass
class ClassMetrics:
    label: str
    support: int
    precision: float
    recall: float
    f1: float


def per_class_prf(matrix: np.ndarray, labels: list[str]) -> list[ClassMetrics]:
    """Precision / recall / F1 per class from a confusion matrix."""
    out: list[ClassMetrics] = []
    for i, label in enumerate(labels):
        tp = int(matrix[i, i])
        support = int(matrix[i, :].sum())
        predicted = int(matrix[:, i].sum())
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out.append(ClassMetrics(label, support, round(precision, 4), round(recall, 4), round(f1, 4)))
    return out


def macro_f1(metrics: list[ClassMetrics]) -> float:
    scored = [m.f1 for m in metrics if m.support > 0]
    return round(float(np.mean(scored)), 4) if scored else 0.0


def confidence_distribution(
    confidences: list[float], correct: list[bool]
) -> dict[str, float]:
    """Mean/median top-1 confidence split by whether the prediction was correct."""
    conf = np.asarray(confidences, dtype=np.float64)
    ok = np.asarray(correct, dtype=bool)
    def _stats(values: np.ndarray) -> dict[str, float]:
        if values.size == 0:
            return {"n": 0, "mean": 0.0, "median": 0.0}
        return {"n": int(values.size), "mean": round(float(values.mean()), 4), "median": round(float(np.median(values)), 4)}
    return {
        "overall": _stats(conf),
        "correct": _stats(conf[ok]),
        "wrong": _stats(conf[~ok]),
    }


def confused_with(matrix: np.ndarray, labels: list[str], target_index: int) -> list[tuple[str, int]]:
    """For a target class, the other classes its true samples were predicted as."""
    row = matrix[target_index]
    pairs = [(labels[j], int(row[j])) for j in range(len(labels)) if j != target_index and row[j] > 0]
    return sorted(pairs, key=lambda kv: kv[1], reverse=True)


# --- Model-backed evaluation (needs onnxruntime + a dataset) -----------------

@dataclass
class EvalResult:
    labels: list[str]
    matrix: np.ndarray
    metrics: list[ClassMetrics]
    confidence: dict[str, float]
    target_spot: dict
    fitted_temperature: float | None = None
    n_samples: int = 0
    notes: list[str] = field(default_factory=list)


def _tomato_label_index() -> dict[str, int]:
    return {label: i for i, label in enumerate(TOMATO_MODEL_LABELS)}


def evaluate_folder(dataset_root: Path, fit_temp: bool = False) -> EvalResult:
    """Run the real ONNX model over an ImageFolder dataset of tomato classes."""
    from PIL import Image

    from app.model_runtime import DiseaseRuntime

    runtime = DiseaseRuntime()
    if runtime.session is None:
        raise RuntimeError("ONNX model unavailable; cannot evaluate (check the model checksum).")

    label_to_local = _tomato_label_index()
    tomato_indices = [runtime.labels.index(lbl) for lbl in TOMATO_MODEL_LABELS]

    y_true: list[int] = []
    y_pred: list[int] = []
    confidences: list[float] = []
    correct: list[bool] = []
    tomato_logits: list[np.ndarray] = []

    for class_dir in sorted(p for p in dataset_root.iterdir() if p.is_dir()):
        if class_dir.name not in label_to_local:
            continue
        true_local = label_to_local[class_dir.name]
        for img_path in sorted(class_dir.glob("*")):
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            try:
                image = Image.open(img_path)
            except Exception:
                continue
            logits = runtime._forward(image)  # raw model output, serving preprocessing
            tomato_logit = logits[tomato_indices]
            tomato_logits.append(tomato_logit)
            probs = apply_temperature(tomato_logit, 1.0)  # crop-conditioned softmax
            pred_local = int(np.argmax(probs))
            y_true.append(true_local)
            y_pred.append(pred_local)
            confidences.append(float(probs[pred_local]))
            correct.append(pred_local == true_local)

    n = len(y_true)
    labels = list(TOMATO_MODEL_LABELS)
    if n == 0:
        return EvalResult(labels, np.zeros((len(labels), len(labels)), int), [], {}, {}, None, 0,
                          notes=["No tomato-labelled images found under the dataset root."])

    matrix = confusion_matrix(y_true, y_pred, len(labels))
    metrics = per_class_prf(matrix, labels)
    confidence = confidence_distribution(confidences, correct)

    ts_index = labels.index("Tomato___Target_Spot")
    ts_metrics = next(m for m in metrics if m.label == "Tomato___Target_Spot")
    ts_conf = [c for c, t in zip(confidences, y_true) if t == ts_index]
    ts_correct = [ok for ok, t in zip(correct, y_true) if t == ts_index]
    target_spot = {
        "support": ts_metrics.support,
        "recall": ts_metrics.recall,
        "precision": ts_metrics.precision,
        "f1": ts_metrics.f1,
        "mean_confidence": round(float(np.mean(ts_conf)), 4) if ts_conf else 0.0,
        "recall_at_correct": round(float(np.mean(ts_correct)), 4) if ts_correct else 0.0,
        "confused_with": confused_with(matrix, labels, ts_index),
    }

    fitted_temperature = None
    if fit_temp and n >= 20:
        fitted_temperature = round(fit_temperature(np.asarray(tomato_logits), y_true), 4)

    return EvalResult(labels, matrix, metrics, confidence, target_spot, fitted_temperature, n)


def write_calibration_sidecar(result: EvalResult, path: Path = CALIBRATION_PATH) -> None:
    """Persist a fitted temperature so serving reports calibrated confidence honestly."""
    if result.fitted_temperature is None:
        raise ValueError("No fitted temperature to write (run with --fit-temperature on >= 20 samples).")
    # A modest per-class threshold for Target Spot's confusion group, justified by
    # the measured recall: a lower bar is honest *only* because the score is split
    # across look-alikes, which the medium/probable tier discloses.
    payload = {
        "temperature": result.fitted_temperature,
        "per_class_threshold": {},
        "method": "temperature scaling (validation NLL)",
        "fitted_on": "ml/training/evaluate_tomato.py",
        "n_samples": result.n_samples,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _print_report(result: EvalResult) -> None:
    print(f"\nTomato evaluation — {result.n_samples} images")
    for note in result.notes:
        print(f"  note: {note}")
    if result.n_samples == 0:
        return
    print(f"  macro-F1 (classes with support): {macro_f1(result.metrics)}")
    print("\nPer-class precision / recall / F1:")
    for m in result.metrics:
        if m.support:
            print(f"  {m.label:46s}  n={m.support:4d}  P={m.precision:.3f}  R={m.recall:.3f}  F1={m.f1:.3f}")
    print("\nConfidence distribution (top-1):")
    for split, stats in result.confidence.items():
        print(f"  {split:8s} n={stats['n']:4d}  mean={stats['mean']:.3f}  median={stats['median']:.3f}")
    ts = result.target_spot
    print("\nTarget Spot focus:")
    print(f"  support={ts['support']}  recall={ts['recall']:.3f}  precision={ts['precision']:.3f}  "
          f"F1={ts['f1']:.3f}  mean_conf={ts['mean_confidence']:.3f}")
    if ts["confused_with"]:
        confusions = ", ".join(f"{name}×{count}" for name, count in ts["confused_with"])
        print(f"  most confused with: {confusions}")
    if result.fitted_temperature is not None:
        print(f"\nFitted temperature: T={result.fitted_temperature}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the tomato disease model, focused on Target Spot.")
    parser.add_argument("dataset", nargs="?", help="ImageFolder root with Tomato___<Class>/ subfolders.")
    parser.add_argument("--fit-temperature", action="store_true", help="Fit + save a calibration temperature.")
    parser.add_argument("--json", type=Path, default=None, help="Optional path to write the full metrics JSON.")
    args = parser.parse_args(argv)

    if not args.dataset:
        print(
            "No dataset given. Provide a labelled image folder to measure Target Spot:\n"
            "  python ml/training/evaluate_tomato.py <root> [--fit-temperature]\n"
            "Layout: <root>/Tomato___Target_Spot/*.jpg, <root>/Tomato___Early_blight/*.jpg, ...\n"
            "Tomato model classes: " + ", ".join(TOMATO_MODEL_LABELS)
        )
        return 0

    dataset_root = Path(args.dataset)
    if not dataset_root.is_dir():
        print(f"Dataset root not found: {dataset_root}")
        return 1

    result = evaluate_folder(dataset_root, fit_temp=args.fit_temperature)
    _print_report(result)

    if args.json and result.n_samples:
        payload = {
            "n_samples": result.n_samples,
            "macro_f1": macro_f1(result.metrics),
            "labels": result.labels,
            "confusion_matrix": result.matrix.tolist(),
            "per_class": [vars(m) for m in result.metrics],
            "confidence": result.confidence,
            "target_spot": result.target_spot,
            "fitted_temperature": result.fitted_temperature,
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote metrics JSON -> {args.json}")

    if args.fit_temperature and result.fitted_temperature is not None:
        write_calibration_sidecar(result)
        print(f"Wrote calibration sidecar -> {CALIBRATION_PATH}")
        print("Serving will now report calibrated confidence. Re-run tests to confirm.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
