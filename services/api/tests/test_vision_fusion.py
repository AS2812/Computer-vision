"""Tests for the hosted vision second opinion and the honest local+vision fusion.

The network is always mocked here — no real calls — and the conftest keeps vision
disabled by default, so these tests deterministically exercise parsing, mapping,
the fusion state machine, and the screening result on the real Septoria pattern.
"""

import numpy as np
from PIL import Image

from app.analysis import analyze_image
from app.config import settings
from app.diagnosis_evidence import (
    VisualDiagnosisAssessment,
    fuse_diagnosis,
    fused_named_candidates,
)
from app.model_runtime import DiseasePrediction
from app.schemas import ValidationLevel
from app import vision_llm
from app.vision_llm import (
    VisionDiagnosis,
    VisionRanked,
    _extract_json,
    _image_data_url,
    parse_vision_payload,
    resolve_disease_key,
    vision_diagnose,
    vision_enabled,
)


GREEN = Image.new("RGB", (128, 128), (30, 160, 40))


def _assessment(candidates, *, accepted, crop_mass, reasons=None, limitations=None):
    return VisualDiagnosisAssessment(
        crop="tomato",
        candidates=candidates,
        crop_probability_mass=crop_mass,
        top_score=candidates[0][1] if candidates else 0.0,
        margin=0.0,
        accepted=accepted,
        rejection_reasons=reasons or [],
        limitations=limitations or ["host disclosure"],
    )


def _vision(ranked, *, is_tomato=True, not_sure=False, signs="small dark spots"):
    return VisionDiagnosis(
        is_tomato_leaf=is_tomato,
        not_sure=not_sure,
        ranked=[VisionRanked(key=k, name=n, confidence=c) for k, n, c in ranked],
        visible_signs=signs,
        model="mimo-v2.5-free",
    )


# --- name resolution + JSON parsing -----------------------------------------

def test_resolve_disease_key_handles_exact_and_alias_and_unknown():
    assert resolve_disease_key("Septoria leaf spot") == "septoria_leaf_spot_tomato"
    assert resolve_disease_key("bacterial leaf spot") == "tomato_bacterial_spot"
    assert resolve_disease_key("Alternaria early blight") == "tomato_early_blight"
    assert resolve_disease_key("TYLCV") == "tomato_yellow_leaf_curl_virus"
    assert resolve_disease_key("dragon fruit rot") is None
    assert resolve_disease_key("") is None


def test_extract_json_tolerates_fences_and_prose():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('Here it is: {"a": 2} done') == {"a": 2}
    assert _extract_json("no json here") is None
    assert _extract_json("[1,2,3]") is None  # not an object


def test_parse_vision_payload_maps_and_normalizes():
    content = (
        '{"is_tomato_leaf": true, "not_sure": false, '
        '"top": [{"disease": "Septoria leaf spot", "confidence": 65}, '
        '{"disease": "Bacterial spot", "confidence": 0.4}, '
        '{"disease": "made up", "confidence": 90}], '
        '"visible_signs": "small dark spots"}'
    )
    result = parse_vision_payload(content, model="mimo", provider="external-vision", latency_ms=10)
    assert result is not None
    assert result.is_tomato_leaf is True and result.not_sure is False
    assert [r.key for r in result.ranked] == ["septoria_leaf_spot_tomato", "tomato_bacterial_spot"]
    assert result.ranked[0].confidence == 65 / 100  # percent normalized
    assert result.ranked[1].confidence == 0.4       # already a fraction


def test_parse_vision_payload_empty_top_is_not_sure_and_bad_json_is_none():
    result = parse_vision_payload('{"is_tomato_leaf": true, "top": []}', model="m", provider="p", latency_ms=1)
    assert result is not None and result.not_sure is True and result.ranked == []
    assert parse_vision_payload("garbage", model="m", provider="p", latency_ms=1) is None


def test_image_data_url_downscales_large_images():
    big = Image.new("RGB", (2400, 1600), (20, 120, 30))
    url = _image_data_url(big)
    assert url.startswith("data:image/jpeg;base64,")


# --- the real network call, fully mocked ------------------------------------

class _FakeResponse:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _enable_vision(monkeypatch):
    monkeypatch.setattr(settings, "external_vision_enabled", True)
    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://example.test/v1/chat/completions")


def test_vision_diagnose_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "external_vision_enabled", False)
    assert vision_enabled() is False
    assert vision_diagnose(GREEN) is None


def test_vision_diagnose_success(monkeypatch):
    _enable_vision(monkeypatch)
    payload = '{"is_tomato_leaf": true, "not_sure": false, "top": [{"disease": "Septoria leaf spot", "confidence": 80}], "visible_signs": "spots"}'
    monkeypatch.setattr(vision_llm.httpx, "post", lambda *a, **k: _FakeResponse(payload))
    result = vision_diagnose(GREEN)
    assert result is not None
    assert result.ranked[0].key == "septoria_leaf_spot_tomato"


def test_vision_diagnose_retries_on_empty_then_succeeds(monkeypatch):
    _enable_vision(monkeypatch)
    payloads = ["", '{"is_tomato_leaf": true, "top": [{"disease": "Early blight", "confidence": 70}]}']
    calls = {"n": 0}

    def fake_post(*a, **k):
        content = payloads[calls["n"]]
        calls["n"] += 1
        return _FakeResponse(content)

    monkeypatch.setattr(vision_llm.httpx, "post", fake_post)
    result = vision_diagnose(GREEN)
    assert calls["n"] == 2  # retried once
    assert result is not None and result.ranked[0].key == "tomato_early_blight"


def test_vision_diagnose_swallows_errors(monkeypatch):
    _enable_vision(monkeypatch)

    def boom(*a, **k):
        raise vision_llm.httpx.HTTPError("network down")

    monkeypatch.setattr(vision_llm.httpx, "post", boom)
    assert vision_diagnose(GREEN) is None


# --- fusion state machine ----------------------------------------------------

def test_fuse_confident_when_both_models_agree():
    assessment = _assessment(
        [("Tomato___Early_blight", 0.8), ("Tomato___Septoria_leaf_spot", 0.2)],
        accepted=True, crop_mass=1.0,
    )
    fused = fuse_diagnosis(assessment, _vision([("tomato_early_blight", "Early blight", 0.9)]))
    assert fused.state == "confident"
    assert fused.top_key == "tomato_early_blight"
    assert fused.agreement is True
    assert fused.confidence <= 0.85  # never near-certain


def test_fuse_screening_pulls_septoria_up_when_models_disagree():
    # The real Septoria photo: local leads with early blight, a moderately-sure vision
    # opinion sees Septoria -> screening (not confirmed) with Septoria on top.
    assessment = _assessment(
        [("Tomato___Early_blight", 0.5), ("Tomato___Septoria_leaf_spot", 0.25), ("Tomato___Late_blight", 0.19)],
        accepted=False, crop_mass=0.42,
        reasons=["The multi-crop model gave only 42% of its score to tomato labels."],
    )
    fused = fuse_diagnosis(assessment, _vision([("septoria_leaf_spot_tomato", "Septoria leaf spot", 0.65)]))
    assert fused.state == "screening"
    assert fused.top_key == "septoria_leaf_spot_tomato"
    assert fused.agreement is False
    assert fused.confidence <= 0.62  # screening stays low and honest
    assert any("AI second opinion" in line for line in fused.evidence)


def test_fuse_confident_when_vision_is_sure_and_local_unsure_of_host():
    # When the local model is unsure it is even tomato (low crop mass) but the vision
    # model is very sure and its pick is plausible, present a confident screening match.
    assessment = _assessment(
        [("Tomato___Early_blight", 0.5), ("Tomato___Septoria_leaf_spot", 0.25)],
        accepted=False, crop_mass=0.42,
    )
    fused = fuse_diagnosis(assessment, _vision([("septoria_leaf_spot_tomato", "Septoria leaf spot", 0.92)]))
    assert fused.state == "confident"
    assert fused.top_key == "septoria_leaf_spot_tomato"
    assert fused.confidence <= 0.85


def test_fuse_local_only_preserves_original_gate():
    accepted = _assessment([("Tomato___Early_blight", 0.8)], accepted=True, crop_mass=1.0)
    assert fuse_diagnosis(accepted, None).state == "confident"
    rejected = _assessment(
        [("Tomato___Early_blight", 0.5)], accepted=False, crop_mass=0.4,
        reasons=["only 40% of its score to tomato labels"],
    )
    fused = fuse_diagnosis(rejected, None)
    assert fused.state == "not_sure"
    assert fused.used_vision is False
    assert any("offline" in line for line in fused.evidence)


def test_fuse_not_tomato_when_vision_rejects_and_local_weak():
    weak = _assessment([("Tomato___Early_blight", 0.3)], accepted=False, crop_mass=0.3)
    fused = fuse_diagnosis(weak, _vision([("tomato_early_blight", "Early blight", 0.2)], is_tomato=False))
    assert fused.state == "not_tomato"
    assert fused.accepted is False


def test_fused_named_candidates_leads_with_marker_when_unconfirmed():
    rejected = _assessment([("Tomato___Early_blight", 0.5), ("Tomato___Septoria_leaf_spot", 0.25)],
                           accepted=False, crop_mass=0.4)
    fused = fuse_diagnosis(rejected, None)
    names = [name for name, _ in fused_named_candidates(fused)]
    assert names[0] == "Not enough visual evidence"


# --- integration through analyze_image --------------------------------------

class _ScriptedRuntime:
    provider = "scripted"

    def __init__(self, scores):
        self._scores = scores

    def predict(self, image):
        top_label, top_conf = self._scores[0]
        return DiseasePrediction(top_label, top_conf, self.provider, ValidationLevel.EXPERIMENTAL, self._scores)


def test_analyze_image_screening_surfaces_septoria_honestly():
    runtime = _ScriptedRuntime([
        ("Strawberry___Leaf_scorch", 0.40),
        ("Tomato___Early_blight", 0.30),
        ("Tomato___Septoria_leaf_spot", 0.18),
        ("Tomato___Late_blight", 0.12),
    ])
    vision = _vision([("septoria_leaf_spot_tomato", "Septoria leaf spot", 0.65)])
    result = analyze_image(GREEN, "leaf.png", runtime, crop="tomato", vision=vision)
    disease = next(item for item in result.results if item.feature == "disease")
    assert disease.value.startswith("Most likely (screening): Septoria leaf spot")
    assert result.fused_state == "screening"
    assert any("Screening result only" in alert.en for alert in result.alerts)
    assert result.diagnosis_candidates[0].disease == "Septoria leaf spot (tomato)"


def test_tta_views_are_deterministic_and_bounded(tmp_path):
    from app.model_runtime import DiseaseRuntime

    runtime = DiseaseRuntime(tmp_path / "missing.onnx")  # no session needed for the view helper
    views = runtime._tta_views(Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8)))
    assert len(views) == 3
    tiny = runtime._tta_views(Image.new("RGB", (1, 1)))
    assert len(tiny) == 2  # too small to crop further
