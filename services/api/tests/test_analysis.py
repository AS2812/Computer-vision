import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.analysis import analyze_image, infection_extent, plant_count, vegetation_indices
from app.main import app
from app.model_runtime import DiseasePrediction
from app.schemas import ValidationLevel
from app.weather import WeatherObservation


class FakeRuntime:
    provider = "test-runtime"

    def predict(self, image):
        return DiseasePrediction("healthy", 0.92, self.provider, ValidationLevel.VALIDATED)


def image_bytes(color=(40, 150, 55), size=(128, 128)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def test_vegetation_indices_detect_green():
    indices = vegetation_indices(Image.new("RGB", (100, 100), (30, 170, 40)))
    assert indices["coverage"] > 0.9
    assert indices["exg"] > 0


def test_large_image_is_processed_in_bounded_tiles():
    indices = vegetation_indices(Image.new("RGB", (1200, 900), (30, 170, 40)))
    assert indices["coverage"] > 0.9


def test_plant_count_finds_separate_clusters():
    array = np.zeros((100, 100, 3), dtype=np.uint8)
    array[10:30, 10:30] = [20, 200, 20]
    array[60:85, 60:85] = [20, 200, 20]
    assert plant_count(Image.fromarray(array)) == 2


def test_infection_extent_is_low_for_clean_green_leaf():
    assert infection_extent(Image.new("RGB", (100, 100), (30, 170, 40))) < 0.05


def test_analysis_exposes_current_evidence_focused_features():
    result = analyze_image(Image.new("RGB", (128, 128), (30, 160, 35)), "test.png", FakeRuntime())
    assert len(result.results) == 4
    assert result.processing_ms < 15_000
    assert result.peak_memory_mb < 4096
    levels = {item.feature: item.level for item in result.results}
    assert levels == {
        "disease": ValidationLevel.EXPERIMENTAL,
        "infection_extent": ValidationLevel.EXPERIMENTAL,
        "resistant_varieties": ValidationLevel.SAMPLE_DATA,
        "weather": ValidationLevel.SAMPLE_DATA,
    }
    assert result.crop == "tomato"
    assert result.assistant_questions


def test_health_demo_and_upload_flow():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    demo = client.get("/api/demo")
    assert demo.status_code == 200
    upload = client.post("/api/analyze", files={"file": ("leaf.png", image_bytes(), "image/png")})
    assert upload.status_code == 200
    analysis_id = upload.json()["analysis_id"]
    assert client.get(f"/api/analyses/{analysis_id}").status_code == 200
    assert any(item["analysis_id"] == analysis_id for item in client.get("/api/analyses").json())
    assert client.get(f"/api/reports/{analysis_id}.csv").status_code == 200
    assert client.get(f"/api/reports/{analysis_id}.pdf").content.startswith(b"%PDF")
    weather = next(item for item in upload.json()["results"] if item["feature"] == "weather")
    assert weather["value"] == "24°C, partly cloudy, wind 9 km/h"


def test_invalid_upload_and_missing_analysis():
    client = TestClient(app)
    response = client.post("/api/analyze", files={"file": ("bad.txt", b"not image", "text/plain")})
    assert response.status_code == 422
    bad_crop = client.post(
        "/api/analyze",
        data={"crop": "potato"},
        files={"file": ("leaf.png", image_bytes(), "image/png")},
    )
    assert bad_crop.status_code == 422
    assert client.get("/api/analyses/missing").status_code == 404


def test_tomato_knowledge_endpoint_is_available_without_analysis():
    response = TestClient(app).get("/api/knowledge/tomato?language=en")

    assert response.status_code == 200
    assert any(item["name"] == "Iron Lady" for item in response.json()["varieties"])
    assert response.json()["sources"]


def test_assistant_is_grounded_and_has_sources(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "external_llm_api_key", None)
    client = TestClient(app)
    response = client.post("/api/assistant", json={"question": "ماذا أفعل مع الري؟"})
    assert response.status_code == 200
    assert response.json()["mode"] == "grounded-case-answer"
    assert response.json()["sources"]


def test_yield_indicator_is_transparent_and_deterministic():
    from app.yield_model import predict_yield_potential

    assert predict_yield_potential(1.0, 1.0) == 1.0
    assert predict_yield_potential(0.0, 0.0) == 0.0
    assert abs(predict_yield_potential(0.5, 0.5) - 0.5) < 1e-9
    # Same inputs always give the same output (no random-trained model).
    assert predict_yield_potential(0.7, 0.3) == predict_yield_potential(0.7, 0.3)


def test_numbers_are_honest_no_fabricated_values():
    # A pure-green canopy has no yellowing, no dark spots, and full coverage.
    result = analyze_image(Image.new("RGB", (96, 96), (30, 160, 40)), "green.png", FakeRuntime())
    by_feature = {item.feature: item for item in result.results}

    # Weather must not invent a reading.
    weather = by_feature["weather"]
    assert "No live weather" in weather.value
    assert weather.score == 0

    # The visible infection extent stays low on a clean green image.
    assert by_feature["infection_extent"].score < 0.05


def test_live_weather_is_shown_and_adds_weather_aware_guidance():
    weather = WeatherObservation(
        temperature_c=37,
        wind_kph=8,
        precipitation_mm=1.2,
        condition="rain",
        condition_ar="أمطار",
    )
    result = analyze_image(
        Image.new("RGB", (96, 96), (30, 160, 40)),
        "green.png",
        FakeRuntime(),
        weather=weather,
    )
    by_feature = {item.feature: item for item in result.results}

    assert by_feature["weather"].level == ValidationLevel.VALIDATED
    assert "37°C" in by_feature["weather"].value
    assert any("High temperature now" in alert.en for alert in result.alerts)
    assert any("Rain is reported now" in item.en for item in result.recommendations)
