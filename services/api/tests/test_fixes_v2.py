import pytest
from app.contracts.cases import PhotoQuality, SeverityEstimate, SourcedRange, CropCase, CropType, DiagnosisOutput, DiagnosisCandidate, CaseStatus
from app.application.area_ranges import generate_area_range_cases
from app.application.case_service import CaseService
from app.adapters.case_repository import InMemoryCaseRepository

def test_evaluate_photo_quality():
    repo = InMemoryCaseRepository()
    service = CaseService(repo)
    
    case = CropCase(
        case_id="test-case-id",
        crop=CropType.TOMATO,
        location="Beheira, Egypt",
        status=CaseStatus.COLLECTING_EVIDENCE,
        diagnosis=DiagnosisOutput(
            top_disease="Spider mites",
            confidence=0.62,
            alternatives=[],
            evidence=["Crop-label support: 50%"],
        ),
        observations={
            "image_width_px": 200,
            "image_height_px": 200,
            "image_green_coverage_percent": 8.0,
            "image_dark_pixel_percent": 60.0,
            "image_visible_discoloration_percent": 0.0,
        }
    )
    
    quality = service._evaluate_photo_quality(case)
    assert quality.host_crop_support == "user_selected_not_visually_confirmed"
    assert any("Crop selected by user" in w for w in quality.warnings)
    assert quality.status == "host crop not visually confirmed"
    
    assert any("Low leaf coverage" in w for w in quality.warnings)
    assert any("Leaf area is not sufficient" in w for w in quality.warnings)
    assert any("resolution is low" in w for w in quality.warnings)
    assert any("Heavy shadows" in w for w in quality.warnings)

def test_area_range_cases_dynamic():
    severity = SeverityEstimate(
        severity_label="moderate",
        visible_affected_percent=25.0,
        estimated_yield_loss_low_percent=15.0,
        estimated_yield_loss_high_percent=35.0,
    )
    
    cases = generate_area_range_cases(severity, selected_treatment_id="confirm_first", disease_class="pest")
    assert len(cases) == 8
    assert cases[0].treatment_cost_egp.low == 50.0
    assert cases[1].treatment_cost_egp.low == 150.0
    
    cases = generate_area_range_cases(severity, selected_treatment_id="sanitation_only", disease_class="pest")
    assert cases[0].treatment_cost_egp.low == 0.0
    assert cases[0].treatment_cost_egp.measured_zero is True
    
    cases = generate_area_range_cases(severity, selected_treatment_id="prevention_only", disease_class="pest")
    assert cases[0].sprays.low == 1
    
    cases = generate_area_range_cases(severity, selected_treatment_id="strongest", disease_class="pest")
    assert cases[0].sprays.low == 3
    
    cases = generate_area_range_cases(severity, selected_treatment_id="balanced", disease_class="pest")
    assert cases[0].sprays.low == 2
