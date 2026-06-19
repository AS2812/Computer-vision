"""Phase 5: image-derived severity + a transparent damage/recovery estimate, and a
reference-priced cost estimate so the cost-benefit phase is never blank.

Honesty: every number is a documented formula over a *measured* image statistic
(visible discoloration) and reviewed reference brackets. It is an ESTIMATE RANGE,
clearly labelled, never a field measurement or the farmer's real numbers. When the
farmer enters real values, the strict ``calculate_cost_benefit`` result is used
instead and ``CostEstimate.basis`` becomes ``farmer_inputs``.
"""

from __future__ import annotations

from app.application.prices import PriceProvider, price_provider
from app.contracts.cases import CostEstimate, CropCase, SeverityEstimate
from app.weather import WeatherObservation


# Reviewed yield-loss brackets per visible-severity band (low %, high %).
_SEVERITY_LOSS: dict[str, tuple[float, float]] = {
    "low": (2.0, 8.0),
    "moderate": (8.0, 20.0),
    "high": (20.0, 40.0),
    "severe": (40.0, 70.0),
}
# Disease classes with no chemical cure — recovery leans on roguing/sanitation.
_NO_CURE_CLASSES = {"viral", "abiotic"}
_AGGRESSIVE_CLASSES = {"viral", "bacterial"}
_TREATMENT_APPLICATIONS = 3


def _visible_percent(case: CropCase) -> float | None:
    value = case.observations.get("image_visible_discoloration_percent")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _weather_risk(weather: WeatherObservation | None, disease_class: str) -> str:
    """Coarse spread-risk band. Default leans on the humid Alexandria coastal reference."""
    if weather is not None:
        precip = getattr(weather, "precipitation_mm", 0.0) or 0.0
        temp = getattr(weather, "temperature_c", 25.0)
        if precip > 0.2 or 18 <= temp <= 30:
            return "high"
        if temp >= 35:
            return "medium"
        return "low"
    # No live reading: most tomato foliar diseases spread fast in coastal Egyptian humidity.
    return "high" if disease_class in {"fungal", "bacterial"} else "medium"


def estimate_severity(case: CropCase, weather: WeatherObservation | None = None) -> SeverityEstimate:
    visible = _visible_percent(case)
    disease_class = case.disease_class or "unknown"
    weather_risk = _weather_risk(weather, disease_class)
    if visible is None:
        return SeverityEstimate(
            weather_risk_label=weather_risk,  # type: ignore[arg-type]
            drivers=["No image discoloration measurement yet — upload a photo so the report can show a severity estimate."]
        )

    if visible < 8:
        label = "low"
    elif visible < 20:
        label = "moderate"
    elif visible < 40:
        label = "high"
    else:
        label = "severe"
    loss_low, loss_high = _SEVERITY_LOSS[label]

    drivers = [f"About {visible:.0f}% of the visible leaf area is discoloured in the photo."]
    if weather_risk == "high":
        loss_high = min(85.0, loss_high + 10.0)
        drivers.append("Warm, humid Egyptian conditions raise the spread risk for this disease.")
    if disease_class in _AGGRESSIVE_CLASSES:
        loss_high = min(90.0, loss_high + 10.0)
        drivers.append("This disease class has no chemical cure, so removing infected plants matters more than spraying.")

    if disease_class in _NO_CURE_CLASSES:
        recovery = "low"
    elif label in {"high", "severe"}:
        recovery = "fair"
    else:
        recovery = "good"

    return SeverityEstimate(
        severity_label=label,
        visible_affected_percent=round(visible, 1),
        estimated_yield_loss_low_percent=round(loss_low, 1),
        estimated_yield_loss_high_percent=round(loss_high, 1),
        recovery_probability_label=recovery,
        weather_risk_label=weather_risk,
        drivers=drivers,
    )


def _sum_prices(provider: PriceProvider, items: tuple[str, ...], bound: str) -> float:
    total = 0.0
    for item in items:
        price = provider.get(item)
        if price is not None:
            total += price.low_egp if bound == "low" else price.high_egp
    return total


def reference_cost_estimate(
    case: CropCase,
    severity: SeverityEstimate,
    provider: PriceProvider | None = None,
) -> CostEstimate:
    """Build Phase-5 numbers: prefer the farmer's real calculation, otherwise a
    clearly-labelled reference estimate from Egyptian reference prices + severity."""
    provider = provider or price_provider()
    cb = case.cost_benefit

    # The farmer entered real numbers -> defer to the strict deterministic result.
    if cb.treatment_cost_egp is not None and cb.decision != "need_more_data":
        return CostEstimate(
            basis="farmer_inputs",
            treatment_cost_egp_low=cb.treatment_cost_egp,
            treatment_cost_egp_high=cb.treatment_cost_egp,
            potential_loss_egp_low=cb.estimated_saved_revenue_egp,
            potential_loss_egp_high=cb.estimated_saved_revenue_egp,
            net_benefit_egp_low=cb.net_benefit_egp,
            net_benefit_egp_high=cb.net_benefit_egp,
            decision_hint=cb.decision,
            note="Based on the numbers you entered in the cost-benefit form.",
        )

    area_value = case.observations.get("area_feddan")
    area = float(area_value) if isinstance(area_value, (int, float)) and area_value > 0 else 1.0
    assumptions: list[str] = []
    if not isinstance(area_value, (int, float)) or not area_value:
        assumptions.append("No area entered — this assumes 1 feddan; multiply by your real area.")

    per_app_low = _sum_prices(provider, ("contact_fungicide", "labor", "sprayer_use", "water_fuel"), "low")
    per_app_high = _sum_prices(provider, ("systemic_fungicide", "labor", "sprayer_use", "water_fuel"), "high")
    cost_low = per_app_low * _TREATMENT_APPLICATIONS * area
    cost_high = per_app_high * _TREATMENT_APPLICATIONS * area
    assumptions.append(f"Assumes {_TREATMENT_APPLICATIONS} protective applications over the season.")

    price = provider.get("tomato_farmgate")
    yield_ref = provider.get("expected_yield")
    loss_low_pct = (severity.estimated_yield_loss_low_percent or 0.0) / 100.0
    loss_high_pct = (severity.estimated_yield_loss_high_percent or 0.0) / 100.0

    potential_loss_low: float | None = None
    potential_loss_high: float | None = None
    net_low: float | None = None
    net_high: float | None = None
    if price and yield_ref and severity.severity_label != "unknown":
        potential_loss_low = round(yield_ref.low_egp * price.low_egp * loss_low_pct * area)
        potential_loss_high = round(yield_ref.high_egp * price.high_egp * loss_high_pct * area)
        net_low = round(potential_loss_low - cost_high)   # conservative: high cost vs low avoided loss
        net_high = round(potential_loss_high - cost_low)
        worth_it = net_high > 0 and severity.severity_label in {"moderate", "high", "severe"}
        decision_hint = (
            "Protecting the crop is likely worth the cost." if worth_it
            else "Low damage estimate — monitor and confirm costs before spending."
        )
    else:
        decision_hint = "Reference estimate from photo, weather, and Egyptian fallback price table. Use sidebar chatbot for a more exact personal calculation."

    prices_used = [
        provider.get(item).to_reference()
        for item in (
            "tomato_farmgate", "expected_yield", "contact_fungicide",
            "systemic_fungicide", "labor", "sprayer_use", "water_fuel",
        )
        if provider.get(item) is not None
    ]

    return CostEstimate(
        basis="reference_estimate",
        area_feddan_assumed=area,
        treatment_cost_egp_low=round(cost_low),
        treatment_cost_egp_high=round(cost_high),
        potential_loss_egp_low=potential_loss_low,
        potential_loss_egp_high=potential_loss_high,
        net_benefit_egp_low=net_low,
        net_benefit_egp_high=net_high,
        decision_hint=decision_hint,
        prices_used=prices_used,
        assumptions=assumptions,
    )
