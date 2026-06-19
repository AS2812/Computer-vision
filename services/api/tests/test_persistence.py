from uuid import uuid4

import httpx
from PIL import Image

from app.adapters.case_repository import SupabaseCaseRepository
from app.analysis import analyze_image
from app.application.case_service import CaseService
from app.config import settings
from app.contracts.cases import (
    CostBenefitInput,
    CropCaseCreate,
    DiagnosisCandidate,
    DiagnosisConfirmationInput,
    DiagnosisConfirmationType,
    DiagnosisInput,
    ObservationInput,
)
from app.model_runtime import DiseasePrediction
from app.persistence import SupabaseAnalysisStore
from app.schemas import ValidationLevel


class FakeRuntime:
    def predict(self, image):
        return DiseasePrediction("healthy", 0.9, "test-runtime", ValidationLevel.VALIDATED)


class FakeResponse:
    def __init__(self, value=None):
        self.value = value

    def json(self):
        return self.value


def test_supabase_store_saves_loads_images_results_and_reports(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "http://supabase.test")
    monkeypatch.setattr(settings, "supabase_service_role_key", "service-key")
    store = SupabaseAnalysisStore()
    analysis = analyze_image(Image.new("RGB", (32, 32), (30, 160, 40)), "leaf.png", FakeRuntime())
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path.startswith("/auth/v1/admin/users?"):
            return FakeResponse({"users": [{"id": "owner-1", "email": settings.supabase_demo_email}]})
        if path.startswith("/rest/v1/farms?"):
            return FakeResponse([{"id": "farm-1"}])
        if path.startswith("/rest/v1/missions?"):
            return FakeResponse([{"id": "mission-1"}])
        if path == "/rest/v1/uploaded_assets":
            return FakeResponse([{"id": "asset-1"}])
        if path.startswith("/rest/v1/analysis_runs?id="):
            return FakeResponse([{"response": analysis.model_dump(mode="json")}])
        if path.startswith("/rest/v1/analysis_runs?response="):
            return FakeResponse([{"response": analysis.model_dump(mode="json")}])
        return FakeResponse([])

    monkeypatch.setattr(store, "_request", fake_request)

    assert store.save_analysis(analysis, b"image", "image/png")
    loaded = store.load_analysis(analysis.analysis_id)
    assert loaded is not None
    assert loaded.analysis_id == analysis.analysis_id
    assert store.list_analyses()[0].analysis_id == analysis.analysis_id
    assert store.save_report(analysis.analysis_id, "pdf", b"%PDF", "application/pdf")
    assert any("/storage/v1/object/mission-images/" in path for _, path, _ in calls)
    assert any(path == "/rest/v1/feature_results" for _, path, _ in calls)
    assert any("/storage/v1/object/analysis-reports/" in path for _, path, _ in calls)


def test_supabase_store_is_optional(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_service_role_key", None)
    store = SupabaseAnalysisStore()

    assert store.mode == "memory-only"
    assert store.load_analysis("missing") is None


def test_supabase_case_repository_persists_case_evidence_asset_and_report(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "http://supabase.test")
    monkeypatch.setattr(settings, "supabase_service_role_key", "service-key")
    store = SupabaseCaseRepository()
    service = CaseService(store)
    calls = []
    snapshots = {}

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path.startswith("/auth/v1/admin/users?"):
            return FakeResponse({"users": [{"id": str(uuid4()), "email": settings.supabase_demo_email}]})
        if path.startswith("/rest/v1/farms?"):
            return FakeResponse([{"id": str(uuid4())}])
        if path.startswith("/rest/v1/crop_cases?id="):
            return FakeResponse([{"snapshot": next(iter(snapshots.values()))}])
        if path.startswith("/rest/v1/crop_cases?on_conflict="):
            snapshots[kwargs["json"]["id"]] = kwargs["json"]["snapshot"]
        return FakeResponse([])

    monkeypatch.setattr(store, "_request", fake_request)

    case = service.create(CropCaseCreate(crop="tomato", location="Beheira, Egypt"))
    service.add_observations(
        case.case_id,
        ObservationInput(values={"affected_plants_percent": 30, "irrigation_method": "flood"}),
    )
    service.set_diagnosis(
        case.case_id,
        DiagnosisInput(
            candidates=[
                DiagnosisCandidate(disease="Early blight", confidence=0.8),
                DiagnosisCandidate(disease="Septoria leaf spot", confidence=0.2),
            ],
            evidence=["Ringed spots"],
            missing_info=["Whole-plant photo"],
        ),
    )
    service.confirm_diagnosis(
        case.case_id,
        DiagnosisConfirmationInput(
            disease="Early blight",
            confirmation_type=DiagnosisConfirmationType.EGYPTIAN_PLANT_PATHOLOGY_LAB,
            organization="ARC Vegetable Diseases Research Department",
            report_reference="ARC-PERSIST-001",
        ),
        "lab-report.pdf",
        "a" * 64,
    )
    service.calculate_economics(case.case_id, CostBenefitInput(area_feddan=1))
    assert service.save_asset(
        case.case_id,
        "leaf image.png",
        b"image",
        "image/png",
        "close_up_leaf",
        {"provider": "test-onnx"},
    )
    report = service.report(case.case_id)

    store.clear()
    loaded = store.get(case.case_id)
    assert loaded is not None
    assert loaded.diagnosis.top_disease == "Early blight"
    assert report.case_id == case.case_id
    assert store.mode == "supabase"
    assert any(path.startswith("/rest/v1/case_observations?on_conflict=") for _, path, _ in calls)
    assert any(path.startswith("/rest/v1/case_diagnoses?on_conflict=") for _, path, _ in calls)
    assert any(
        path.startswith("/rest/v1/case_diagnoses?on_conflict=")
        and details["json"]["source"] == "lab"
        for _, path, details in calls
    )
    assert any(path.startswith("/rest/v1/case_treatment_plans?on_conflict=") for _, path, _ in calls)
    assert any("/storage/v1/object/case-images/" in path for _, path, _ in calls)
    assert any(path.startswith("/rest/v1/case_reports?on_conflict=") for _, path, _ in calls)


def test_supabase_case_repository_keeps_memory_available_on_failure(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "http://supabase.test")
    monkeypatch.setattr(settings, "supabase_service_role_key", "service-key")
    store = SupabaseCaseRepository()

    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(store, "_request", fail)
    service = CaseService(store)
    case = service.create(CropCaseCreate(crop="banana"))

    assert store.get(case.case_id) is not None
    assert store.mode == "supabase-error"
