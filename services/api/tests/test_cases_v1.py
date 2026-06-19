import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.cases import case_repository
from app.application.cost_benefit import calculate_cost_benefit
from app.application.image_diagnosis import diagnose_image
from app.contracts.cases import CaseStatus, CostBenefitInput, DiagnosisCandidate, DiagnosisInput
from app.domain.case_state import can_transition, require_transition
from app.main import app
from app.model_runtime import DiseasePrediction
from app.schemas import ValidationLevel


client = TestClient(app)


def setup_function():
    case_repository.clear()


def create_case(**overrides):
    payload = {"crop": "tomato", "location": "Beheira, Egypt", **overrides}
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201
    return response.json()


def diagnose(case_id: str, confidence: float = 0.8):
    return client.post(
        f"/api/v1/cases/{case_id}/diagnosis",
        json={
            "candidates": [
                {"disease": "Early blight", "confidence": confidence},
                {"disease": "Septoria leaf spot", "confidence": 0.15},
                {"disease": "Bacterial spot", "confidence": 0.05},
            ],
            "evidence": ["Ringed brown spots on lower leaves"],
            "missing_info": ["Affected-plant percentage"],
        },
    )


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (128, 128), (30, 160, 40)).save(output, format="PNG")
    return output.getvalue()


class RankedRuntime:
    def predict(self, image):
        return DiseasePrediction(
            "Tomato___Early_blight",
            0.7,
            "test-onnx",
            ValidationLevel.EXPERIMENTAL,
            [
                ("Tomato___Early_blight", 0.7),
                ("Tomato___Septoria_leaf_spot", 0.2),
                ("Potato___Late_blight", 0.1),
            ],
        )


class RejectedRuntime:
    model_path = type("ModelPath", (), {"name": "rejected-test.onnx"})()
    level = ValidationLevel.EXPERIMENTAL

    def predict(self, image):
        return DiseasePrediction(
            "Potato___Late_blight",
            0.7,
            "test-onnx",
            ValidationLevel.EXPERIMENTAL,
            [
                ("Potato___Late_blight", 0.7),
                ("Tomato___Early_blight", 0.2),
                ("Tomato___Septoria_leaf_spot", 0.1),
            ],
        )


def test_case_lifecycle_questions_and_stable_report_contract():
    case = create_case(farm_type="open_field", symptoms=["spots", "yellowing"])
    case_id = case["case_id"]
    assert case["status"] == "collecting_evidence"
    assert client.get("/api/v1/cases?limit=1").json()[0]["case_id"] == case_id

    observations = client.post(
        f"/api/v1/cases/{case_id}/observations",
        json={"values": {"irrigation_method": "flood", "affected_plants_percent": 35, "spread_speed": "fast"}},
    )
    assert observations.status_code == 200

    first_questions = client.get(f"/api/v1/cases/{case_id}/questions?limit=3").json()
    second_questions = client.get(f"/api/v1/cases/{case_id}/questions?limit=3").json()
    assert len(first_questions) == 3
    assert len(second_questions) == 3
    assert not set(first_questions) & set(second_questions)

    diagnosis = diagnose(case_id)
    assert diagnosis.status_code == 200
    assert diagnosis.json()["diagnosis"]["alternatives"][0]["disease"] == "Septoria leaf spot"
    assert diagnosis.json()["prediction"]["damage_degree"] == "high"

    report = client.get(f"/api/v1/cases/{case_id}/report.json")
    assert report.status_code == 200
    body = report.json()
    assert set(body) == {
        "case_id",
        "crop",
        "location",
        "farm_type",
        "growth_stage",
        "symptoms",
        "observations",
        "observation_sources",
        "egypt_sources",
        "source_metadata",
        "diagnosis",
        "chatbot_followup_questions",
        "protection_plan",
        "treatment_plan",
        "cost_benefit",
        "severity",
        "cost_estimate",
        "prediction",
        "recommendation",
        "scenarios",
        "summary_cards",
        "phases",
        "sidebar_chatbot_context",
        "primary_detected_disease",
        "confidence_warning",
        "area_range_cases",
        "assumptions",
        "safety_notes",
        "conclusion",
        "completeness",
        "disclaimer",
        "photo_quality",
        "treatment_options",
        "selected_treatment_id",
        "cost_benefit_by_selected_treatment",
        "cost_benefit_comparison",
        "forecast_recalculation",
    }
    assert len(body["scenarios"]) == 6
    assert len(body["area_range_cases"]) == 8
    assert len(body["source_metadata"]) >= 5
    assert body["primary_detected_disease"]["detected"] is True
    assert body["severity"]["severity_label"] in {"unknown", "low", "moderate", "high", "severe"}
    assert body["cost_estimate"]["basis"] in {"farmer_inputs", "reference_estimate", "need_more_data"}
    assert len(body["chatbot_followup_questions"]) <= 5
    assert body["summary_cards"]["numbers_only"] is True
    assert body["phases"]["consulting"]["auto_questions_with_answers"]
    assert body["sidebar_chatbot_context"]["source_keys"]
    assert body["safety_notes"]
    assert any("soil splash" in item for item in body["protection_plan"])
    assert all(source["jurisdiction"] == "Egypt" for source in body["egypt_sources"])


def test_low_confidence_blocks_chemical_categories_and_requires_more_evidence():
    case_id = create_case()["case_id"]
    response = diagnose(case_id, confidence=0.42)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_expert"
    assert body["treatment_plan"]["chemical_category_if_needed"] == []
    assert any("Not enough evidence" in item for item in body["diagnosis"]["missing_info"])


def test_egyptian_lab_evidence_records_confirmation_without_inventing_ai_confidence():
    case_id = create_case()["case_id"]
    assert diagnose(case_id, confidence=0.42).status_code == 200

    response = client.post(
        f"/api/v1/cases/{case_id}/confirm-diagnosis",
        data={
            "disease": "Septoria leaf spot",
            "confirmation_type": "egyptian_plant_pathology_lab",
            "organization": "ARC Vegetable Diseases Research Department",
            "report_reference": "ARC-TEST-001",
            "confirmer_name": "Test plant pathologist",
        },
        files={"file": ("lab-report.pdf", b"%PDF-1.4 test report", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "diagnosis_ready"
    assert body["diagnosis"]["top_disease"] == "Septoria leaf spot"
    assert body["diagnosis"]["confidence"] == 0.15
    assert body["diagnosis"]["confirmation_status"] == "confirmed_by_egyptian_plant_pathology_lab"
    assert body["diagnosis"]["confirmation"]["report_reference"] == "ARC-TEST-001"
    assert len(body["diagnosis"]["confirmation"]["evidence_sha256"]) == 64
    assert body["treatment_plan"]["chemical_category_if_needed"]
    assert any("APC database" in item for item in body["treatment_plan"]["safety_notes"])
    assert "reliable_diagnosis" not in body["cost_benefit"]["missing_inputs"]
    assert case_repository._assets[case_id][-1]["view_type"] == "diagnosis_confirmation"

    report = client.get(f"/api/v1/cases/{case_id}/report.json").json()
    assert "has not independently authenticated" in report["conclusion"]


def test_diagnosis_confirmation_requires_real_pdf_or_image_evidence():
    case_id = create_case()["case_id"]
    response = client.post(
        f"/api/v1/cases/{case_id}/confirm-diagnosis",
        data={
            "disease": "Septoria leaf spot",
            "confirmation_type": "egyptian_plant_pathology_lab",
            "organization": "Egyptian lab",
            "report_reference": "LAB-1",
        },
        files={"file": ("claim.txt", b"not evidence", "text/plain")},
    )

    assert response.status_code == 422


def test_viral_case_explains_that_spraying_does_not_cure_the_virus():
    case_id = create_case()["case_id"]
    response = client.post(
        f"/api/v1/cases/{case_id}/diagnosis",
        json={"candidates": [{"disease": "Tomato mosaic virus", "confidence": 0.9}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["disease_class"] == "viral"
    assert body["treatment_rule_version"]
    assert any("does not cure" in item for item in body["treatment_plan"]["chemical_category_if_needed"])


def test_complete_cost_benefit_uses_deterministic_numbers():
    result = calculate_cost_benefit(
        CostBenefitInput(
            area_feddan=2,
            expected_yield_kg_per_feddan=10_000,
            market_price_egp_per_kg=10,
            yield_loss_without_treatment_percent=30,
            yield_loss_after_treatment_percent=10,
            product_cost_egp_per_application=1000,
            labor_cost_egp_per_application=300,
            sprayer_cost_egp_per_application=100,
            water_fuel_cost_egp_per_application=100,
            application_count=2,
        )
    )

    assert result.treatment_cost_egp == 3000
    assert result.estimated_saved_revenue_egp == 40000
    assert result.net_benefit_egp == 37000
    assert result.roi == 12.333
    assert result.decision == "treat_now"


def test_missing_economics_never_invents_values():
    case_id = create_case()["case_id"]
    assert diagnose(case_id).status_code == 200
    response = client.post(f"/api/v1/cases/{case_id}/cost-benefit", json={"area_feddan": 1})

    assert response.status_code == 200
    result = response.json()["cost_benefit"]
    assert result["decision"] == "need_more_data"
    assert result["treatment_cost_egp"] is None
    assert "market_price_egp_per_kg" in result["missing_inputs"]


def test_economics_never_recommends_treatment_without_reliable_diagnosis():
    case_id = create_case()["case_id"]
    assert diagnose(case_id, confidence=0.42).status_code == 200
    response = client.post(
        f"/api/v1/cases/{case_id}/cost-benefit",
        json={
            "area_feddan": 2,
            "expected_yield_kg_per_feddan": 10_000,
            "market_price_egp_per_kg": 10,
            "yield_loss_without_treatment_percent": 30,
            "yield_loss_after_treatment_percent": 10,
            "product_cost_egp_per_application": 1000,
            "labor_cost_egp_per_application": 300,
            "sprayer_cost_egp_per_application": 100,
            "water_fuel_cost_egp_per_application": 100,
            "application_count": 2,
        },
    )

    result = response.json()["cost_benefit"]
    assert result["net_benefit_egp"] == 37000
    assert result["decision"] == "need_more_data"
    assert "reliable_diagnosis" in result["missing_inputs"]


def test_case_validation_not_found_and_state_guard():
    assert client.post("/api/v1/cases", json={"crop": "rice"}).status_code == 422
    assert client.get("/api/v1/cases/missing").status_code == 404
    assert can_transition(CaseStatus.DRAFT, CaseStatus.COLLECTING_EVIDENCE)
    assert not can_transition(CaseStatus.DRAFT, CaseStatus.REPORT_READY)
    try:
        require_transition(CaseStatus.DRAFT, CaseStatus.REPORT_READY)
    except ValueError as error:
        assert "Invalid case status transition" in str(error)
    else:
        raise AssertionError("invalid transition must fail")


def test_image_adapter_returns_crop_conditioned_top_matches():
    result = diagnose_image(Image.new("RGB", (128, 128), "green"), "tomato", RankedRuntime())

    assert [item.disease for item in result.candidates] == [
        "Early blight (tomato & potato)",
        "Septoria leaf spot (tomato)",
    ]
    assert result.candidates[0].confidence == pytest.approx(7 / 9)
    assert any("visual hypotheses" in item for item in result.evidence)


def test_rejected_image_keeps_hypotheses_but_does_not_promote_them_to_diagnosis():
    result = diagnose_image(Image.new("RGB", (128, 128), "green"), "tomato", RejectedRuntime())
    assert result.candidates[0].disease == "Not enough visual evidence"
    assert result.candidates[1].disease == "Early blight (tomato & potato)"
    assert any("rejected; diagnosis unconfirmed" in item for item in result.evidence)

    case_id = create_case()["case_id"]
    response = client.post(f"/api/v1/cases/{case_id}/diagnosis", json=result.model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["diagnosis"]["top_disease"] == "Not enough visual evidence"
    assert body["diagnosis"]["alternatives"][0]["disease"] == "Early blight (tomato & potato)"
    assert body["treatment_plan"]["chemical_category_if_needed"] == []


def test_case_image_endpoint_uses_diagnosis_contract(monkeypatch):
    case_id = create_case()["case_id"]
    expected = DiagnosisInput(
        candidates=[DiagnosisCandidate(disease="Early blight", confidence=0.82)],
        evidence=["Model evidence"],
        missing_info=["Whole-plant photo"],
    )
    monkeypatch.setattr("app.api.cases.diagnose_image", lambda image, crop, vision=None: expected)

    response = client.post(
        f"/api/v1/cases/{case_id}/analyze-image",
        data={"view_type": "leaf_underside"},
        files={"file": ("leaf.png", image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["diagnosis"]["top_disease"] == "Early blight"
    assert body["status"] == "diagnosis_ready"
    assert body["observations"]["image_width_px"] == 128
    assert body["observation_sources"]["image_width_px"] == "image_measurement"
    assert body["consulting_questions"]
    assert body["protection_plan"]
    assert body["recommendation"]["best_action_now"]
    assert body["cost_benefit"]["decision"] == "need_more_data"
    assert "market_price_egp_per_kg" in body["cost_benefit"]["missing_inputs"]
    assert case_repository._assets[case_id][-1]["view_type"] == "leaf_underside"
    assert "measurements" in case_repository._assets[case_id][-1]["evidence"]


def test_observation_provenance_preserves_consented_device_sensor_source():
    case_id = create_case()["case_id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/observations",
        json={
            "source": "device_sensor",
            "values": {
                "device_latitude": 31.211,
                "device_longitude": 29.96,
                "location_capture_method": "Current device GPS at analysis time.",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observation_sources"]["device_latitude"] == "device_sensor"
    assert body["observation_sources"]["location_capture_method"] == "device_sensor"


def test_case_image_endpoint_rejects_bad_image_and_unsupported_crop():
    tomato_id = create_case()["case_id"]
    bad = client.post(
        f"/api/v1/cases/{tomato_id}/analyze-image",
        files={"file": ("bad.txt", b"bad", "text/plain")},
    )
    assert bad.status_code == 422

    potato_id = create_case(crop="potato")["case_id"]
    unsupported = client.post(
        f"/api/v1/cases/{potato_id}/analyze-image",
        files={"file": ("leaf.png", image_bytes(), "image/png")},
    )
    assert unsupported.status_code == 422


def test_case_report_export_routes_return_downloads():
    case_id = create_case()["case_id"]
    assert diagnose(case_id).status_code == 200

    csv_response = client.get(f"/api/v1/cases/{case_id}/report.csv")
    pdf_response = client.get(f"/api/v1/cases/{case_id}/report.pdf")

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert b"top_disease" in csv_response.content
    assert b"summary_cards" in csv_response.content
    assert b"source_metadata" in csv_response.content
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
