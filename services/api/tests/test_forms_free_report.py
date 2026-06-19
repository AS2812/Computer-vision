"""The report must be generated from the image alone — no input fields, no
"missing information", and a low-confidence disease is still the primary result.

These tests drive the CaseService directly (offline) and assert the new forms-free
contract: area-range cost-benefit cases, sourced numbers, an honest low-confidence
warning that never blocks the report, and zero "missing information" text in the
farmer-facing fields.
"""

import pytest

from app.adapters.case_repository import InMemoryCaseRepository
from app.application.area_ranges import AREA_PRESETS, _source_type, generate_area_range_cases
from app.application.case_service import CaseService
from app.application.prices import EgyptReferencePriceProvider
from app.contracts.cases import (
    CropCaseCreate,
    CropType,
    DiagnosisCandidate,
    DiagnosisInput,
    SeverityEstimate,
)


def _service() -> CaseService:
    return CaseService(InMemoryCaseRepository())


def _report_with_diagnosis(disease: str, confidence: float):
    svc = _service()
    case = svc.create(CropCaseCreate(crop=CropType.TOMATO, location="", symptoms=[]))
    svc.set_diagnosis(
        case.case_id,
        DiagnosisInput(
            candidates=[DiagnosisCandidate(disease=disease, confidence=confidence)],
            evidence=["local model + AI second opinion"],
            missing_info=[],
        ),
    )
    return svc.report(case.case_id)


# Farmer-facing fields we forbid from ever containing "missing information".
_FORBIDDEN = ("missing information", "معلومات ناقصة", "معلومات مفقودة", "الحقول المفقودة")


# --- area-range cost-benefit generated with NO farmer input ------------------

def test_area_range_cases_generated_for_every_egyptian_size():
    severity = SeverityEstimate(
        severity_label="high",
        estimated_yield_loss_low_percent=20,
        estimated_yield_loss_high_percent=40,
    )
    cases = generate_area_range_cases(severity)
    assert [c.key for c in cases] == [preset[0] for preset in AREA_PRESETS]
    assert len(cases) == 8
    # home garden up to ten feddans
    assert {"home_garden", "one_feddan", "ten_feddan"} <= {c.key for c in cases}


def test_every_generated_number_carries_unit_source_and_assumption():
    cases = generate_area_range_cases(SeverityEstimate(severity_label="moderate"))
    numeric_fields = (
        "sprays", "treatment_cost_egp", "labor_cost_egp", "expected_yield_kg",
        "loss_without_action_egp", "saved_with_action_egp", "revenue_egp", "net_benefit_egp",
    )
    for case in cases:
        for field in numeric_fields:
            value = getattr(case, field)
            assert value.unit, f"{case.key}.{field} has no unit"
            assert value.source_type in {"live_market", "admin_table", "csv_fallback", "estimated_range"}
            assert value.confidence in {"low", "medium", "high"}
            assert value.low <= value.high
        assert case.recommendation_en and case.recommendation_ar


def test_reference_prices_are_never_labelled_live():
    # The default Egyptian reference source contains the word "live" ("not live") —
    # it must still map to estimated_range, never live_market.
    assert _source_type(EgyptReferencePriceProvider().get("tomato_farmgate")) == "estimated_range"
    cases = generate_area_range_cases(SeverityEstimate(severity_label="high"))
    assert all(c.revenue_egp.source_type == "estimated_range" for c in cases)


def test_severity_unknown_still_generates_full_area_ranges():
    # No image severity at all -> still generate every area case (never blank).
    cases = generate_area_range_cases(SeverityEstimate())  # unknown
    assert len(cases) == 8
    assert all(c.expected_yield_kg.high > 0 for c in cases)


# --- low-confidence disease stays primary, never blocks ----------------------

def test_low_confidence_disease_is_still_the_primary_result():
    report = _report_with_diagnosis("Target spot (tomato)", 0.42)
    assert report.primary_detected_disease.detected is True
    assert report.primary_detected_disease.name_en == "Target spot (tomato)"
    assert report.primary_detected_disease.confidence == pytest.approx(0.42)
    assert report.primary_detected_disease.certainty_level == "low"


def test_low_confidence_shows_the_exact_arabic_warning():
    report = _report_with_diagnosis("Target spot (tomato)", 0.42)
    assert report.confidence_warning is not None
    assert report.confidence_warning.level == "low"
    assert "خلي بالك" in report.confidence_warning.text_ar
    assert "مهندس زراعي" in report.confidence_warning.text_ar
    # The report is NOT blocked — phases and cases are still generated.
    assert report.area_range_cases and report.scenarios
    assert "Target spot (tomato)" in report.conclusion


def test_high_confidence_has_no_warning():
    report = _report_with_diagnosis("Early blight (tomato & potato)", 0.88)
    assert report.primary_detected_disease.certainty_level == "high"
    assert report.confidence_warning is None


def test_no_detection_still_generates_full_report():
    # Genuinely nothing matched -> primary not detected, but the report is complete.
    report = _report_with_diagnosis("Not enough visual evidence", 0.0)
    assert report.primary_detected_disease.detected is False
    assert report.confidence_warning is not None
    assert len(report.area_range_cases) == 8
    assert report.scenarios  # farm scenarios still generated


# --- no "missing information" anywhere farmer-facing -------------------------

def test_report_has_no_missing_information_text():
    report = _report_with_diagnosis("Target spot (tomato)", 0.42)
    blob = " ".join([
        report.conclusion,
        report.confidence_warning.text_en if report.confidence_warning else "",
        report.confidence_warning.text_ar if report.confidence_warning else "",
        *[a.text_en for a in report.assumptions],
        *[a.text_ar for a in report.assumptions],
        *[c.recommendation_en for c in report.area_range_cases],
        *[c.recommendation_ar for c in report.area_range_cases],
        *[s.recommendation_en for s in report.scenarios],
    ]).lower()
    for phrase in _FORBIDDEN:
        assert phrase.lower() not in blob
    # Unknown context becomes positive assumptions, and the old completeness notes are gone.
    assert report.completeness == []
    assert report.assumptions
    assert any("not given" in a.text_en.lower() for a in report.assumptions)
