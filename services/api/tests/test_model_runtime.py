import numpy as np
from PIL import Image

from app.model_runtime import DiseaseRuntime
from app.schemas import ValidationLevel


def test_missing_model_uses_labeled_fallback(tmp_path):
    runtime = DiseaseRuntime(tmp_path / "missing.onnx")
    prediction = runtime.predict(Image.new("RGB", (64, 64), (40, 160, 40)))
    assert prediction.level == ValidationLevel.SAMPLE_DATA
    assert prediction.provider == "deterministic-fallback"
    assert 0 <= prediction.confidence < 0.62


def test_checksum_mismatch_rejects_model(tmp_path):
    bad_model = tmp_path / "bad.onnx"
    bad_model.write_bytes(b"not approved weights")
    runtime = DiseaseRuntime(bad_model)
    prediction = runtime.predict(Image.new("RGB", (64, 64), (40, 160, 40)))
    assert runtime.session is None
    assert prediction.level == ValidationLevel.SAMPLE_DATA


def test_manifest_drives_mobilenet_preprocessing(tmp_path):
    # Even with a missing model file, the manifest drives the preprocessing config.
    runtime = DiseaseRuntime(tmp_path / "missing.onnx")
    assert runtime.preprocessing == "mobilenet_pv"
    sample = runtime._preprocess(Image.new("RGB", (300, 200), (10, 20, 30)))
    # MobileNetV2: shortest edge -> 256, center-crop 224, NCHW, normalized to [-1, 1].
    assert sample.shape == (1, 3, 224, 224)
    assert sample.min() >= -1.001 and sample.max() <= 1.001
