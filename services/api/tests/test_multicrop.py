"""Tests for the multi-crop (PlantVillage) model wiring and honest presentation."""

import numpy as np
from PIL import Image

from app.analysis import analyze_image
from app.config import settings
from app.diagnosis_evidence import assess_visual_prediction
from app.diseases import disease_info, labels_for_crop
from app.model_runtime import DiseasePrediction, DiseaseRuntime
from app.schemas import ValidationLevel
from app.treatments import has_chemical_cure, treatments_for

GREEN = Image.new("RGB", (128, 128), (30, 160, 40))


class ScriptedRuntime:
    """A runtime that returns a fixed ranked score list, like the real model."""

    provider = "scripted"

    def __init__(self, scores):
        self._scores = scores

    def predict(self, image):
        top_label, top_prob = self._scores[0]
        return DiseasePrediction(top_label, top_prob, self.provider, ValidationLevel.EXPERIMENTAL, self._scores)


def test_disease_info_resolves_plantvillage_labels():
    assert disease_info("Tomato___Septoria_leaf_spot").key == "septoria_leaf_spot_tomato"
    assert disease_info("Potato___Late_blight").key == "tomato_late_blight"
    assert disease_info("Tomato___healthy").key == "healthy"
    assert disease_info("Corn_(maize)___healthy").key == "healthy"
    assert disease_info("Apple___Apple_scab").key == "other_crop_disease"
    # Tomato/foliar diseases carry a ranked treatment program.
    assert disease_info("Tomato___Septoria_leaf_spot").treatments
    assert disease_info("Tomato___Bacterial_spot").treatments


def test_labels_for_crop_filters_to_the_chosen_crop():
    labels = [
        "Tomato___Early_blight", "Tomato___Septoria_leaf_spot",
        "Potato___Late_blight", "Strawberry___Leaf_scorch",
    ]
    assert labels_for_crop("tomato", labels) == ["Tomato___Early_blight", "Tomato___Septoria_leaf_spot"]
    assert labels_for_crop(None, labels) == []
    assert labels_for_crop("unknown-crop", labels) == []
    assert labels_for_crop("banana", ["cordana_leaf_spot", "Tomato___Early_blight"]) == ["cordana_leaf_spot"]


def test_crop_conditioning_ignores_other_crops():
    scores = [
        ("Strawberry___Leaf_scorch", 0.40),
        ("Tomato___Early_blight", 0.25),
        ("Tomato___Septoria_leaf_spot", 0.15),
        ("Tomato___Late_blight", 0.10),
        ("Potato___Late_blight", 0.10),
    ]
    result = analyze_image(GREEN, "leaf.png", ScriptedRuntime(scores), crop="tomato")
    disease = next(item for item in result.results if item.feature == "disease")
    # Strawberry must not survive the tomato filter.
    assert "Strawberry" not in (disease.disease_info.name_en if disease.disease_info else "")
    assert disease.value == "No reliable tomato diagnosis from this photo"
    assert disease.level == ValidationLevel.SAMPLE_DATA
    assert "only 50% of its score to tomato labels" in (disease.limitation or "")
    assert any("Do not choose a treatment" in alert.en for alert in result.alerts)
    assert not any("spray program" in item.en for item in result.recommendations)


def test_confident_in_crop_match_reads_as_strong_visual_match():
    scores = [
        ("Tomato___Early_blight", 0.80),
        ("Tomato___Septoria_leaf_spot", 0.15),
        ("Tomato___Late_blight", 0.05),
    ]
    result = analyze_image(GREEN, "leaf.png", ScriptedRuntime(scores), crop="tomato")
    disease = next(item for item in result.results if item.feature == "disease")
    assert disease.value.startswith("Strong visual match:")
    assert disease.level == ValidationLevel.EXPERIMENTAL
    assert any("Strong visual match only" in alert.en for alert in result.alerts)


def test_healthy_prediction_is_shown_plainly():
    result = analyze_image(GREEN, "leaf.png", ScriptedRuntime([("Tomato___healthy", 0.95)]), crop="tomato")
    disease = next(item for item in result.results if item.feature == "disease")
    assert "healthy" in disease.value.lower()


def test_treatments_have_required_fields_and_no_cure_is_honest():
    blight = treatments_for("tomato_late_blight")
    assert blight and all(t.dose_en and t.frac and t.price_en for t in blight)
    assert has_chemical_cure("tomato_late_blight") is True
    assert has_chemical_cure("panama_disease") is False
    assert has_chemical_cure("tomato_yellow_leaf_curl_virus") is False


def test_real_model_runs_when_present_and_conditions_on_crop():
    if not settings.disease_model_path.exists():
        return
    runtime = DiseaseRuntime()
    if runtime.session is None:
        return
    pred = runtime.predict(Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)))
    assert len(pred.scores) == 38
    result = analyze_image(GREEN, "leaf.png", runtime, crop="tomato")
    assert len(result.results) == 4
    disease = next(item for item in result.results if item.feature == "disease")
    assert disease.feature == "disease"


def test_visual_assessment_rejects_tied_low_quality_and_missing_model_results():
    tied = DiseasePrediction(
        "Tomato___Early_blight",
        0.45,
        "test",
        ValidationLevel.EXPERIMENTAL,
        [("Tomato___Early_blight", 0.45), ("Tomato___Late_blight", 0.40), ("Tomato___healthy", 0.15)],
    )
    tied_result = assess_visual_prediction(tied, "tomato", leaf_coverage=0.5)
    assert tied_result.accepted is False
    assert any("top two" in reason for reason in tied_result.rejection_reasons)

    no_leaf = assess_visual_prediction(tied, "tomato", leaf_coverage=0.01)
    assert any("Too little" in reason for reason in no_leaf.rejection_reasons)

    fallback = DiseasePrediction("possible_leaf_disease", 0.5, "fallback", ValidationLevel.SAMPLE_DATA)
    fallback_result = assess_visual_prediction(fallback, "tomato", leaf_coverage=0.5)
    assert fallback_result.accepted is False
    assert any("not available" in reason for reason in fallback_result.rejection_reasons)


def test_banana_assessment_discloses_missing_healthy_and_host_detection():
    prediction = DiseasePrediction(
        "cordana_leaf_spot",
        0.95,
        "test",
        ValidationLevel.EXPERIMENTAL,
        [("cordana_leaf_spot", 0.95), ("sigatoka_leaf_spot", 0.05)],
    )
    result = assess_visual_prediction(prediction, "banana", leaf_coverage=0.5)

    assert result.accepted is True
    assert any("no healthy or out-of-domain class" in limitation for limitation in result.limitations)
    assert any("does not independently confirm the host crop" in limitation for limitation in result.limitations)
