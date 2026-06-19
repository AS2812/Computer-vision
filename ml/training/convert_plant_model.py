"""One-time conversion of the PlantVillage MobileNetV2 classifier to ONNX.

Downloads ozair23/mobilenet_v2_1.0_224-finetuned-plantdisease (38 PlantVillage
classes, 97.8% lab test accuracy), exports it to ONNX for the onnxruntime-based
serving app, saves the authoritative id2label map, and runs a verification
inference on a real photo so we can SEE the labels are wired correctly before
trusting it.

Preprocessing is done manually (no torchvision) and mirrors the HF MobileNetV2
image processor: resize shortest edge to 256, center-crop 224, rescale 1/255,
normalize with mean/std 0.5 -> range [-1, 1], NCHW. The serving runtime must use
the SAME steps.

Run inside the throwaway conversion env (torch + transformers + onnx). The
serving venv only needs onnxruntime.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from PIL import Image
from transformers import AutoModelForImageClassification

MODEL_ID = "ozair23/mobilenet_v2_1.0_224-finetuned-plantdisease"
OUT_DIR = Path(__file__).resolve().parents[1] / "models"
ONNX_PATH = OUT_DIR / "plant_disease_mobilenetv2.onnx"
LABELS_PATH = OUT_DIR / "plant_disease_mobilenetv2.labels.json"


def preprocess(img: Image.Image) -> np.ndarray:
    """Match the HF MobileNetV2 image processor without torchvision."""
    img = img.convert("RGB")
    w, h = img.size
    short = 256
    if w <= h:
        nw, nh = short, round(h * short / w)
    else:
        nw, nh = round(w * short / h), short
    img = img.resize((nw, nh), Image.BILINEAR)
    left = (nw - 224) // 2
    top = (nh - 224) // 2
    img = img.crop((left, top, left + 224, top + 224))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = (arr - 0.5) / 0.5
    arr = np.transpose(arr, (2, 0, 1))[None, ...]
    return np.ascontiguousarray(arr, dtype=np.float32)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading {MODEL_ID} ...")
    model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
    model.eval()
    id2label = {int(k): v for k, v in model.config.id2label.items()}
    labels = [id2label[i] for i in range(len(id2label))]
    print(f"{len(labels)} classes")

    dummy = torch.randn(1, 3, 224, 224)
    print(f"Exporting ONNX -> {ONNX_PATH}")
    torch.onnx.export(
        model,
        dummy,
        str(ONNX_PATH),
        input_names=["pixel_values"],
        output_names=["logits"],
        dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=18,
        do_constant_folding=True,
        verbose=False,
    )

    LABELS_PATH.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    sha = hashlib.sha256(ONNX_PATH.read_bytes()).hexdigest()
    size = ONNX_PATH.stat().st_size
    print(f"ONNX written: {size} bytes  sha256={sha}")

    test_image = sys.argv[1] if len(sys.argv) > 1 else None
    if test_image and Path(test_image).exists():
        x = preprocess(Image.open(test_image))
        with torch.no_grad():
            torch_logits = model(torch.from_numpy(x)).logits.numpy()[0]
        sess = ort.InferenceSession(str(ONNX_PATH), providers=["CPUExecutionProvider"])
        onnx_logits = sess.run(None, {"pixel_values": x})[0][0]
        max_diff = float(np.max(np.abs(torch_logits - onnx_logits)))
        probs = np.exp(onnx_logits - onnx_logits.max())
        probs /= probs.sum()
        order = np.argsort(probs)[::-1][:5]
        print(f"\nVerification image: {test_image}")
        print(f"Max |torch-onnx| logit diff: {max_diff:.6f} (should be ~0)")
        print("Top-5 (ONNX):")
        for i in order:
            print(f"  {probs[i] * 100:5.1f}%  [{i:2d}] {labels[i]}")
    else:
        print("No test image given (or not found) — skipping verification inference.")


if __name__ == "__main__":
    main()
