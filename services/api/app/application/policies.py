from __future__ import annotations

from app.contracts.cases import (
    CostBenefitOutput,
    CropCase,
    PredictionOutput,
    RecommendationOutput,
)


LOW_CONFIDENCE_THRESHOLD = 0.65


def protection_plan(case: CropCase) -> list[str]:
    plan = [
        "Separate or mark affected plants and inspect nearby healthy plants.",
        "Remove heavily affected tissue only when it can be done without spreading contamination.",
        "Clean tools before moving from affected plants to healthy plants.",
        "Inspect the same marked plants again in 3 days and record whether symptoms spread.",
        "Do not over-spray.",
    ]
    if case.observations.get("irrigation_method") in {"flood", "sprinkler", "canal"}:
        plan.insert(2, "Reduce leaf wetness and soil splash; irrigate early where practical.")
    if case.farm_type and case.farm_type.value == "greenhouse":
        plan.insert(2, "Improve greenhouse airflow and avoid prolonged high humidity.")
    return plan


def prediction(case: CropCase) -> PredictionOutput:
    affected = case.observations.get("affected_plants_percent")
    if not isinstance(affected, (int, float)):
        risks = ["Affected-plant percentage is not available, so crop-wide damage cannot be predicted."]
        visible = case.observations.get("image_visible_discoloration_percent")
        if isinstance(visible, (int, float)):
            risks.append(
                f"The uploaded image contains {visible:g}% measured visible discoloration; "
                "this is an image measurement, not the percentage of plants affected."
            )
        return PredictionOutput(main_risk_factors=risks)
    if affected < 10:
        degree = "low"
    elif affected < 30:
        degree = "medium"
    elif affected < 60:
        degree = "high"
    else:
        degree = "severe"
    risks = [f"Approximately {affected:g}% of plants are reported affected."]
    if case.observations.get("spread_speed") == "fast":
        risks.append("Symptoms are reported to be spreading quickly.")
    return PredictionOutput(damage_degree=degree, main_risk_factors=risks)


def recommendation(case: CropCase, economics: CostBenefitOutput) -> RecommendationOutput:
    confirmed = case.diagnosis.confirmation_status != "unconfirmed"
    if not case.diagnosis.top_disease or (
        case.diagnosis.confidence < LOW_CONFIDENCE_THRESHOLD and not confirmed
    ):
        best = "Collect the missing evidence and confirm the likely cause before chemical treatment."
    elif economics.decision == "treat_now":
        best = "Use immediate non-chemical controls and have an agricultural engineer confirm the treatment plan."
    elif economics.decision == "treatment_not_economically_justified":
        best = "Use low-cost protection steps and monitor; the entered treatment cost is not economically justified."
    else:
        best = "Apply immediate protection steps and collect the missing economic inputs before deciding on treatment."
    return RecommendationOutput(
        best_action_now=best,
        next_3_to_7_days="Recheck marked plants, record spread and affected-plant percentage, and compare new photos.",
        when_to_call_expert=(
            "Call an agricultural engineer now if spread is fast, fruit or roots are affected, "
            "more than one third of plants are affected, or harvest is close."
        ),
    )
