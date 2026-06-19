import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from .calibration import apply_temperature, load_calibration, softmax
from .config import settings
from .schemas import ValidationLevel


@dataclass
class DiseasePrediction:
    label: str
    confidence: float
    provider: str
    level: ValidationLevel
    # All labels ranked by probability (desc). Used for crop-conditioning and
    # showing the top possibilities instead of one over-confident answer.
    # ``scores`` are the *calibrated* probabilities (== raw when temperature is 1);
    # ``raw_scores`` keep the uncalibrated softmax so both can be reported honestly.
    scores: list[tuple[str, float]] = field(default_factory=list)
    raw_scores: list[tuple[str, float]] = field(default_factory=list)

    def raw_confidence(self) -> float:
        """The uncalibrated top-1 probability (falls back to ``confidence``)."""
        return self.raw_scores[0][1] if self.raw_scores else self.confidence


class DiseaseRuntime:
    def __init__(self, model_path: Path | None = None, manifest_key: str = "disease"):
        self.model_path = model_path or settings.disease_model_path
        self.manifest_key = manifest_key
        self.session = None
        self.labels = ["healthy", "possible_leaf_disease"]
        self.input_size = (224, 224)
        self.resize_short = 256
        self.input_layout = "NCHW"
        self.preprocessing = "scale_0_1"
        self.output_type = "logits"
        self.level = ValidationLevel.SAMPLE_DATA
        self.expected_sha256: str | None = None
        self.provider = "deterministic-fallback"
        # Honest calibration: temperature from a fitted sidecar (or 1.0 identity).
        # The explicit setting overrides only when it has been moved off 1.0.
        self.calibration = load_calibration()
        self.temperature = (
            settings.disease_temperature
            if abs(settings.disease_temperature - 1.0) > 1e-6
            else self.calibration.temperature
        )
        self._load_optional_model()

    def _load_optional_model(self) -> None:
        if settings.model_manifest_path.exists():
            manifest = json.loads(settings.model_manifest_path.read_text(encoding="utf-8"))
            metadata = manifest["models"][self.manifest_key]
            self.labels = metadata["labels"]
            self.input_size = tuple(metadata.get("input_size", self.input_size))
            self.resize_short = int(metadata.get("resize_short", self.resize_short))
            self.input_layout = metadata.get("input_layout", self.input_layout)
            self.preprocessing = metadata.get("preprocessing", self.preprocessing)
            self.output_type = metadata.get("output_type", self.output_type)
            self.level = ValidationLevel(metadata.get("validation_level", ValidationLevel.EXPERIMENTAL))
            self.expected_sha256 = metadata.get("sha256")
        if not self.model_path.exists():
            return
        try:
            if self.expected_sha256 and self.expected_sha256 != "pending":
                digest = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
                if digest != self.expected_sha256:
                    return
            import onnxruntime as ort

            available = ort.get_available_providers()
            preferred = [
                p
                for p in ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]
                if p in available
            ]
            options = ort.SessionOptions()
            options.intra_op_num_threads = settings.max_tile_workers
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(str(self.model_path), sess_options=options, providers=preferred)
            self.provider = self.session.get_providers()[0]
        except Exception:
            self.session = None

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        sample = image.convert("RGB")
        if self.preprocessing == "mobilenet_pv":
            # Resize shortest edge to resize_short, center-crop to input_size,
            # rescale 1/255, normalize with mean/std 0.5 -> [-1, 1] (HF MobileNetV2).
            w, h = sample.size
            short = self.resize_short
            if w <= h:
                nw, nh = short, max(short, round(h * short / w))
            else:
                nw, nh = max(short, round(w * short / h)), short
            sample = sample.resize((nw, nh), Image.BILINEAR)
            cw, ch = self.input_size
            left, top = (nw - cw) // 2, (nh - ch) // 2
            sample = sample.crop((left, top, left + cw, top + ch))
            array = np.asarray(sample, dtype=np.float32) / 255.0
            array = (array - 0.5) / 0.5
            array = np.transpose(array, (2, 0, 1))
            return np.ascontiguousarray(array[None, ...], dtype=np.float32)

        sample = sample.resize(self.input_size)
        array = np.asarray(sample, dtype=np.float32)
        if self.preprocessing == "vgg19":
            array = array[..., ::-1].copy()
            array -= np.asarray([103.939, 116.779, 123.68], dtype=np.float32)
        else:
            array /= 255.0
        if self.input_layout == "NCHW":
            array = np.transpose(array, (2, 0, 1))
        return array[None, ...]

    def _forward(self, image: Image.Image) -> np.ndarray:
        """One forward pass returning the raw model output vector (logits/probs)."""
        input_name = self.session.get_inputs()[0].name
        return np.asarray(self.session.run(None, {input_name: self._preprocess(image)})[0])[0]

    def _raw_probs(self, output: np.ndarray) -> np.ndarray:
        """Uncalibrated probabilities from the raw model output."""
        if self.output_type == "probabilities":
            probs = np.clip(output, 0, None).astype(np.float64)
            total = float(probs.sum())
            if not 0.95 <= total <= 1.05:
                probs /= max(total, 1e-8)
            return probs
        return softmax(output.astype(np.float64))

    def _calibrated_probs(self, output: np.ndarray) -> np.ndarray:
        """Temperature-scaled probabilities (identity when temperature is 1.0).

        A pre-softmaxed probability output cannot be honestly temperature-scaled,
        so it is returned unchanged.
        """
        if self.output_type == "probabilities":
            return self._raw_probs(output)
        return apply_temperature(output.astype(np.float64), self.temperature)

    def _probs_for(self, image: Image.Image) -> np.ndarray:
        """One forward pass returning a calibrated probability vector."""
        return self._calibrated_probs(self._forward(image))

    def _tta_views(self, image: Image.Image) -> list[Image.Image]:
        """A few deterministic views averaged to steady real-field-photo predictions."""
        sample = image.convert("RGB")
        views = [sample, sample.transpose(Image.FLIP_LEFT_RIGHT)]
        # A tighter center crop emphasises the lesion area over background clutter.
        w, h = sample.size
        cw, ch = int(w * 0.8), int(h * 0.8)
        if cw > 0 and ch > 0:
            left, top = (w - cw) // 2, (h - ch) // 2
            views.append(sample.crop((left, top, left + cw, top + ch)))
        return views

    def predict(self, image: Image.Image) -> DiseasePrediction:
        if self.session:
            views = self._tta_views(image) if settings.disease_tta else [image]
            outputs = [self._forward(view) for view in views]
            raw = np.mean([self._raw_probs(o) for o in outputs], axis=0)
            calibrated = np.mean([self._calibrated_probs(o) for o in outputs], axis=0)
            # Temperature scaling is monotonic, so calibrated and raw share an order.
            order = np.argsort(calibrated)[::-1]
            scores = [(self.labels[i], float(calibrated[i])) for i in order]
            raw_scores = [(self.labels[i], float(raw[i])) for i in order]
            top_label, top_conf = scores[0]
            return DiseasePrediction(top_label, top_conf, self.provider, self.level, scores, raw_scores)

        array = np.asarray(image.convert("RGB").resize((224, 224)), dtype=np.float32) / 255.0
        green = array[..., 1]
        red = array[..., 0]
        brown_signal = float(np.mean((red > green * 1.15) & (green < 0.55)))
        confidence = min(0.59, 0.45 + brown_signal)
        label = "possible_leaf_disease" if brown_signal > 0.08 else "healthy"
        scored = [(label, confidence)]
        return DiseasePrediction(label, confidence, self.provider, ValidationLevel.SAMPLE_DATA, scored, scored)


disease_runtime = DiseaseRuntime()
banana_disease_runtime = DiseaseRuntime(settings.banana_disease_model_path, "banana_disease")


def runtime_for_crop(crop: str | None) -> DiseaseRuntime:
    return banana_disease_runtime if crop == "banana" else disease_runtime
