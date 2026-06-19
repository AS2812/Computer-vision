from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.contracts.cases import CostBenefitInput, CostBenefitOutput


_REQUIRED_FIELDS = tuple(CostBenefitInput.model_fields)
_MONEY = Decimal("0.01")
_RATIO = Decimal("0.001")


def _decimal(value: float | int) -> Decimal:
    return Decimal(str(value))


def _rounded(value: Decimal, quantum: Decimal = _MONEY) -> float:
    return float(value.quantize(quantum, rounding=ROUND_HALF_UP))


def calculate_cost_benefit(inputs: CostBenefitInput) -> CostBenefitOutput:
    missing = [name for name in _REQUIRED_FIELDS if getattr(inputs, name) is None]
    if missing:
        return CostBenefitOutput(
            decision="need_more_data",
            missing_inputs=missing,
        )

    values = inputs.model_dump()
    area = _decimal(values["area_feddan"])
    expected_yield = _decimal(values["expected_yield_kg_per_feddan"])
    price = _decimal(values["market_price_egp_per_kg"])
    untreated_loss = _decimal(values["yield_loss_without_treatment_percent"]) / Decimal(100)
    treated_loss = _decimal(values["yield_loss_after_treatment_percent"]) / Decimal(100)
    repetitions = _decimal(values["application_count"])
    per_application = sum(
        _decimal(values[field])
        for field in (
            "product_cost_egp_per_application",
            "labor_cost_egp_per_application",
            "sprayer_cost_egp_per_application",
            "water_fuel_cost_egp_per_application",
        )
    )

    treatment_cost = per_application * repetitions
    base_revenue = area * expected_yield * price
    saved_revenue = max(Decimal(0), base_revenue * (untreated_loss - treated_loss))
    net_benefit = saved_revenue - treatment_cost
    roi = net_benefit / treatment_cost if treatment_cost else Decimal(0)
    break_even_yield = treatment_cost / price if price else Decimal(0)

    if saved_revenue <= 0:
        decision = "monitor_only"
    elif net_benefit > 0 and roi >= Decimal("0.25"):
        decision = "treat_now"
    elif net_benefit > 0:
        decision = "monitor_and_confirm_costs"
    else:
        decision = "treatment_not_economically_justified"

    return CostBenefitOutput(
        treatment_cost_egp=_rounded(treatment_cost),
        estimated_saved_revenue_egp=_rounded(saved_revenue),
        net_benefit_egp=_rounded(net_benefit),
        roi=_rounded(roi, _RATIO),
        break_even_yield_saved_kg=_rounded(break_even_yield),
        decision=decision,
    )
