"""Tests for the new Phase 5/6 building blocks: Egypt prices, image severity,
reference cost estimate, the six Egyptian scenarios, and report completeness."""

from app.application.prices import (
    CsvPriceProvider,
    EgyptReferencePriceProvider,
    PriceRange,
    price_provider,
    set_price_provider,
)
from app.application.scenarios import generate_scenarios
from app.application.severity import estimate_severity, reference_cost_estimate
from app.contracts.cases import CostBenefitOutput, CropCase, CropType, SeverityEstimate


def _case(**observations) -> CropCase:
    disease_class = observations.pop("disease_class", "fungal")
    return CropCase(
        case_id="t",
        crop=CropType.TOMATO,
        disease_class=disease_class,
        observations=observations,
    )


# --- price provider ----------------------------------------------------------

def test_egypt_reference_prices_are_ranges_with_source():
    provider = EgyptReferencePriceProvider()
    tomato = provider.get("tomato_farmgate")
    assert tomato is not None
    assert 0 < tomato.low_egp < tomato.high_egp
    assert "reference" in tomato.source.lower()
    assert provider.get("does_not_exist") is None
    assert len(provider.all()) >= 8


def test_csv_price_provider_overrides_and_falls_back(tmp_path):
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "item,unit,low_egp,high_egp,source\ntomato_farmgate,EGP/kg,9,15,Admin sheet\n",
        encoding="utf-8",
    )
    provider = CsvPriceProvider(csv_path)
    assert provider.get("tomato_farmgate").low_egp == 9.0
    assert provider.get("tomato_farmgate").source == "Admin sheet"
    # An item not in the CSV still resolves via the reviewed reference fallback.
    assert provider.get("labor") is not None


def test_set_price_provider_is_swappable():
    original = price_provider()
    try:
        class _Fake:
            def get(self, item):
                return PriceRange(item, "EGP", 1.0, 2.0, "fake")
            def all(self):
                return [self.get("tomato_farmgate")]
        set_price_provider(_Fake())
        assert price_provider().get("tomato_farmgate").source == "fake"
    finally:
        set_price_provider(original)


# --- severity + damage estimate ---------------------------------------------

def test_severity_scales_with_visible_discoloration():
    low = estimate_severity(_case(image_visible_discoloration_percent=4.0))
    high = estimate_severity(_case(image_visible_discoloration_percent=45.0))
    assert low.severity_label == "low"
    assert high.severity_label == "severe"
    assert high.estimated_yield_loss_high_percent > low.estimated_yield_loss_high_percent
    assert low.recovery_probability_label == "good"


def test_severity_unknown_without_image_measurement():
    result = estimate_severity(_case())
    assert result.severity_label == "unknown"
    assert result.estimated_yield_loss_low_percent is None
    assert any("photo" in d for d in result.drivers)


def test_no_cure_disease_class_lowers_recovery():
    viral = estimate_severity(_case(image_visible_discoloration_percent=10.0, disease_class="viral"))
    assert viral.recovery_probability_label == "low"


# --- reference cost estimate -------------------------------------------------

def test_reference_cost_estimate_fills_phase5_without_farmer_numbers():
    case = _case(image_visible_discoloration_percent=25.0, area_feddan=2.0)
    severity = estimate_severity(case)
    estimate = reference_cost_estimate(case, severity)
    assert estimate.basis == "reference_estimate"
    assert estimate.area_feddan_assumed == 2.0
    assert estimate.treatment_cost_egp_high > estimate.treatment_cost_egp_low > 0
    assert estimate.potential_loss_egp_low is not None
    assert estimate.prices_used  # reference prices are attached for transparency


def test_reference_cost_estimate_defers_to_farmer_inputs():
    case = _case(image_visible_discoloration_percent=25.0)
    case.cost_benefit = CostBenefitOutput(
        treatment_cost_egp=3000, estimated_saved_revenue_egp=40000,
        net_benefit_egp=37000, roi=12.333, decision="treat_now",
    )
    estimate = reference_cost_estimate(case, estimate_severity(case))
    assert estimate.basis == "farmer_inputs"
    assert estimate.treatment_cost_egp_low == 3000


def test_cost_estimate_assumes_one_feddan_when_area_missing():
    case = _case(image_visible_discoloration_percent=12.0)
    estimate = reference_cost_estimate(case, estimate_severity(case))
    assert estimate.area_feddan_assumed == 1.0
    assert any("1 feddan" in a for a in estimate.assumptions)


# --- six Egyptian scenarios --------------------------------------------------

def test_six_egyptian_scenarios_are_generated_with_every_dimension():
    case = _case(image_visible_discoloration_percent=30.0)
    scenarios = generate_scenarios(case, estimate_severity(case), "Septoria leaf spot (tomato)", "السبتوريا")
    keys = {s.key for s in scenarios}
    assert keys == {"home_garden", "open_field", "greenhouse", "desert_farm", "small_commercial", "coastal_humid"}
    for s in scenarios:
        assert s.confidence_en and s.protection_en and s.treatment_en and s.cost_en and s.recommendation_en
        assert s.confidence_ar and s.protection_ar and s.treatment_ar and s.cost_ar and s.recommendation_ar
        assert s.treatment_en.startswith("For Septoria leaf spot (tomato):")
    coastal = next(s for s in scenarios if s.key == "coastal_humid")
    assert "humidity" in coastal.protection_en.lower() or "airflow" in coastal.protection_en.lower()


def test_scenarios_note_no_cure_for_viral_class():
    case = _case(image_visible_discoloration_percent=15.0, disease_class="viral")
    scenarios = generate_scenarios(case, estimate_severity(case), "Tomato mosaic virus (ToMV)", "موزاييك")
    assert all("no spray cures" in s.treatment_en for s in scenarios)


def test_scenario_urgency_reflects_severity():
    severe = generate_scenarios(_case(image_visible_discoloration_percent=50.0),
                                estimate_severity(_case(image_visible_discoloration_percent=50.0)), "x", "x")
    assert any("Act now" in s.recommendation_en for s in severe)
