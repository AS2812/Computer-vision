"""Tests for honest calibration, the class-index mapping guard, and the
Target-Spot confusion-group rescue.

These are the tests the task specifically asks for: catch a wrong class-index
ordering, prove a low-confidence-but-correct Target Spot becomes a *medium*
("probable") verdict instead of being dropped, and prove nothing inflates the
displayed confidence.
"""

import json

import numpy as np
from PIL import Image

from app.analysis import analyze_image
from app.calibration import (
    TARGET_SPOT_INDEX,
    TARGET_SPOT_KEY,
    TARGET_SPOT_LABEL,
    TOMATO_MODEL_LABELS,
    Calibration,
    apply_temperature,
    assess_confusion_group,
    class_high_threshold,
    confusion_group,
    fit_temperature,
    is_confusable,
    softmax,
    uncertainty_from_state,
)
from app.config import settings
from app.diagnosis_evidence import assess_visual_prediction, fuse_diagnosis
from app.diseases import disease_info
from app.model_runtime import DiseasePrediction
from app.schemas import ValidationLevel

GREEN = Image.new("RGB", (128, 128), (30, 160, 40))


# --- Class-index mapping guard (catches a wrong ordering) --------------------

EXPECTED_TOMATO_KEYS = {
    "Tomato___Bacterial_spot": "tomato_bacterial_spot",
    "Tomato___Early_blight": "tomato_early_blight",
    "Tomato___Late_blight": "tomato_late_blight",
    "Tomato___Leaf_Mold": "tomato_leaf_mold",
    "Tomato___Septoria_leaf_spot": "septoria_leaf_spot_tomato",
    "Tomato___Spider_mites Two-spotted_spider_mite": "tomato_spider_mites",
    "Tomato___Target_Spot": "tomato_target_spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "tomato_yellow_leaf_curl_virus",
    "Tomato___Tomato_mosaic_virus": "tomato_mosaic_virus",
    "Tomato___healthy": "healthy",
}


def _manifest_labels() -> list[str]:
    return json.loads(settings.model_manifest_path.read_text(encoding="utf-8"))["models"]["disease"]["labels"]


def _labels_json() -> list[str]:
    path = settings.disease_model_path.with_name("plant_disease_mobilenetv2.labels.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_labels_file_and_manifest_agree():
    assert _labels_json() == _manifest_labels()


def test_target_spot_is_at_the_expected_class_index():
    labels = _manifest_labels()
    assert labels[TARGET_SPOT_INDEX] == TARGET_SPOT_LABEL == "Tomato___Target_Spot"
    # If anyone re-orders the labels, this fails loudly.
    assert labels.index("Tomato___Target_Spot") == TARGET_SPOT_INDEX


def test_tomato_model_labels_match_manifest_order():
    tomato_in_manifest = tuple(l for l in _manifest_labels() if l.startswith("Tomato___"))
    assert TOMATO_MODEL_LABELS == tomato_in_manifest


def test_every_tomato_label_maps_to_the_right_knowledge_base_key():
    # Catches alias drift: a re-ordered or mistyped alias would map Target Spot to
    # the wrong disease entry and this asserts the exact expected mapping.
    for label, expected_key in EXPECTED_TOMATO_KEYS.items():
        assert disease_info(label).key == expected_key, label
    assert disease_info(TARGET_SPOT_LABEL).key == TARGET_SPOT_KEY


# --- Confusion groups + per-class thresholds ---------------------------------

def test_target_spot_confusion_group_contains_its_lookalikes():
    group = confusion_group(TARGET_SPOT_KEY)
    assert {"tomato_target_spot", "tomato_early_blight", "tomato_bacterial_spot"} <= group
    assert is_confusable(TARGET_SPOT_KEY) is True
    # A virus is not part of the brown-spot complex.
    assert is_confusable("tomato_yellow_leaf_curl_virus") is False


def test_class_threshold_defaults_to_global_without_a_sidecar():
    assert class_high_threshold(TARGET_SPOT_KEY) == settings.disease_confidence_threshold


def test_uncertainty_levels_map_from_state():
    assert uncertainty_from_state("confident") == "high"
    assert uncertainty_from_state("screening") == "medium"
    assert uncertainty_from_state("not_sure") == "low"


# --- Temperature scaling (honest calibration maths) --------------------------

def test_apply_temperature_identity_and_flattening():
    logits = np.array([2.0, 1.0, 0.0])
    assert np.allclose(apply_temperature(logits, 1.0), softmax(logits))
    peaked = apply_temperature(logits, 1.0).max()
    flatter = apply_temperature(logits, 5.0).max()
    assert flatter < peaked  # higher temperature => less peaked, never changes argmax
    assert np.argmax(apply_temperature(logits, 5.0)) == np.argmax(logits)


def test_fit_temperature_reduces_overconfident_nll():
    rng = np.random.default_rng(0)
    n, k = 400, 5
    # Overconfident-and-sometimes-wrong: the model confidently predicts `pred`, but
    # the true label only matches it ~65% of the time. That is exactly the case a
    # temperature > 1 should calibrate (flatten the over-sharp probabilities).
    pred = rng.integers(0, k, size=n)
    logits = rng.normal(0, 0.5, size=(n, k))
    logits[np.arange(n), pred] += 6.0
    labels = pred.copy()
    flip = rng.random(n) < 0.35
    labels[flip] = rng.integers(0, k, size=int(flip.sum()))

    def nll(temp):
        z = logits / temp
        z -= z.max(axis=1, keepdims=True)
        logp = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        return -logp[np.arange(n), labels].mean()

    temperature = fit_temperature(logits, labels)
    assert temperature > 1.0
    assert nll(temperature) < nll(1.0)


def test_calibration_default_is_honestly_labelled_uncalibrated():
    cal = Calibration()
    assert cal.is_calibrated is False
    assert "uncalibrated" in cal.describe().lower()
    fitted = Calibration(temperature=1.4, n_samples=120, method="temperature scaling")
    assert fitted.is_calibrated is True
    assert "1.4" in fitted.describe()


# --- The Target Spot rescue (the core behavioural fix) -----------------------

def _assessment_from(scores):
    pred = DiseasePrediction(scores[0][0], scores[0][1], "test", ValidationLevel.EXPERIMENTAL, scores, scores)
    return assess_visual_prediction(pred, "tomato", leaf_coverage=0.5)


TARGET_SPOT_SPLIT = [
    ("Tomato___Target_Spot", 0.40),
    ("Tomato___Early_blight", 0.28),
    ("Tomato___Bacterial_spot", 0.14),
    ("Tomato___healthy", 0.10),
    ("Tomato___Late_blight", 0.08),
]


def test_assess_confusion_group_promotes_split_target_spot():
    probs = {
        "tomato_target_spot": 0.40,
        "tomato_early_blight": 0.28,
        "tomato_bacterial_spot": 0.14,
        "healthy": 0.10,
        "tomato_late_blight": 0.08,
    }
    promoted = assess_confusion_group(probs, crop_probability_mass=1.0)
    assert promoted.promote is True
    assert promoted.leader == "tomato_target_spot"
    assert promoted.group_mass >= settings.disease_group_mass_threshold
    assert promoted.note_en and promoted.note_ar


def test_assess_confusion_group_refuses_when_host_unsupported():
    probs = {"tomato_target_spot": 0.40, "tomato_early_blight": 0.28, "healthy": 0.32}
    # Low crop mass => the model is not even sure it is tomato => no promotion.
    assert assess_confusion_group(probs, crop_probability_mass=0.4).promote is False


def test_assess_confusion_group_refuses_non_confusable_leader():
    probs = {"tomato_yellow_leaf_curl_virus": 0.45, "healthy": 0.30, "tomato_mosaic_virus": 0.25}
    assert assess_confusion_group(probs, crop_probability_mass=1.0).promote is False


def test_low_confidence_target_spot_becomes_medium_not_silence():
    fused = fuse_diagnosis(_assessment_from(TARGET_SPOT_SPLIT), None, "tomato")
    assert fused.state == "screening"
    assert fused.group_promoted is True
    assert fused.top_key == TARGET_SPOT_KEY
    assert fused.uncertainty_level == "medium"


def test_rescue_never_inflates_confidence():
    fused = fuse_diagnosis(_assessment_from(TARGET_SPOT_SPLIT), None, "tomato")
    # Displayed confidence stays the honest raw value (and never exceeds it),
    # capped by the screening cap — never invented upward.
    assert fused.confidence <= fused.raw_confidence + 1e-9
    assert fused.confidence <= 0.62
    assert abs(fused.raw_confidence - 0.40) < 1e-6  # raw == calibrated at T=1


def test_calibration_method_is_reported_and_honest():
    fused = fuse_diagnosis(_assessment_from(TARGET_SPOT_SPLIT), None, "tomato")
    assert "uncalibrated" in fused.calibration_method.lower()


def test_analyze_image_reports_probable_target_spot_with_evidence():
    class Scripted:
        provider = "scripted"

        def predict(self, image):
            return DiseasePrediction(
                TARGET_SPOT_SPLIT[0][0], TARGET_SPOT_SPLIT[0][1], self.provider,
                ValidationLevel.EXPERIMENTAL, TARGET_SPOT_SPLIT, TARGET_SPOT_SPLIT,
            )

    result = analyze_image(GREEN, "leaf.png", Scripted(), crop="tomato")
    disease = next(item for item in result.results if item.feature == "disease")
    assert disease.value.startswith("Probable Target spot")
    assert "medium confidence" in disease.value
    assert result.uncertainty_level == "medium"
    assert result.raw_confidence == result.calibrated_confidence  # T=1
    assert "uncalibrated" in result.calibration_method.lower()
    # Top-3 candidates carried for the dashboard.
    assert len(result.diagnosis_candidates) >= 1
    assert result.diagnosis_candidates[0].disease == "Target spot (tomato)"


def test_genuinely_ambiguous_non_group_case_stays_low():
    scores = [
        ("Tomato___Spider_mites Two-spotted_spider_mite", 0.40),
        ("Tomato___healthy", 0.33),
        ("Tomato___Late_blight", 0.27),
    ]
    fused = fuse_diagnosis(_assessment_from(scores), None, "tomato")
    assert fused.state == "not_sure"
    assert fused.group_promoted is False
