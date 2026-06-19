import time
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.model_runtime import DiseaseRuntime, banana_disease_runtime
from app.schemas import ValidationLevel


@pytest.mark.skipif(
    not settings.disease_model_path.exists(),
    reason="Run after the PlantVillage ONNX model has been converted into ml/models/.",
)
def test_real_plant_model_loads_and_ranks_all_labels():
    runtime = DiseaseRuntime()
    assert runtime.session is not None
    assert len(runtime.labels) == 38

    started = time.perf_counter()
    prediction = runtime.predict(Image.new("RGB", (256, 256), (60, 140, 60)))
    elapsed = time.perf_counter() - started

    assert prediction.level == ValidationLevel.EXPERIMENTAL
    assert prediction.provider == "CPUExecutionProvider"
    assert prediction.label in runtime.labels
    # The runtime returns the full ranked score list (used for crop-conditioning).
    assert len(prediction.scores) == len(runtime.labels)
    assert prediction.scores[0][0] == prediction.label
    assert 0.0 <= prediction.confidence <= 1.0
    assert elapsed < 15


@pytest.mark.skipif(
    not settings.banana_disease_model_path.exists(),
    reason="Run after the banana ONNX model is installed.",
)
def test_real_banana_model_identifies_cordana_smoke_photo():
    assert banana_disease_runtime.session is not None
    fixture = Path(__file__).resolve().parents[3] / "tests/fixtures/banana_cordana_public_domain.jpg"
    image = Image.open(fixture).convert("RGB")
    prediction = banana_disease_runtime.predict(image)

    assert len(prediction.scores) == 4
    assert prediction.label == "cordana_leaf_spot"
    assert prediction.confidence > 0.9
