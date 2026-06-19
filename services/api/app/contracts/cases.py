from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DISCLAIMER = "AI prediction only. Confirm with an agricultural engineer or lab when crop value or risk is high."


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseStatus(StrEnum):
    DRAFT = "draft"
    COLLECTING_EVIDENCE = "collecting_evidence"
    DIAGNOSIS_READY = "diagnosis_ready"
    CONSULTING = "consulting"
    PROTECTION_READY = "protection_ready"
    TREATMENT_READY = "treatment_ready"
    ECONOMICS_READY = "economics_ready"
    PREDICTION_READY = "prediction_ready"
    RECOMMENDATION_READY = "recommendation_ready"
    REPORT_READY = "report_ready"
    NEEDS_EXPERT = "needs_expert"
    CLOSED = "closed"
    FAILED = "failed"


class CropType(StrEnum):
    TOMATO = "tomato"
    BANANA = "banana"
    POTATO = "potato"
    CUCUMBER = "cucumber"
    GRAPE = "grape"
    MANGO = "mango"
    CITRUS = "citrus"
    WHEAT = "wheat"


class FarmType(StrEnum):
    OPEN_FIELD = "open_field"
    GREENHOUSE = "greenhouse"
    ROOFTOP = "rooftop"
    HOME_GARDEN = "home_garden"


class IrrigationMethod(StrEnum):
    FLOOD = "flood"
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    CANAL = "canal"
    OTHER = "other"


class SpreadSpeed(StrEnum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class ImageViewType(StrEnum):
    CLOSE_UP_LEAF = "close_up_leaf"
    WHOLE_PLANT = "whole_plant"
    LEAF_UNDERSIDE = "leaf_underside"
    FRUIT = "fruit"
    STEM = "stem"
    ROOT = "root"
    HEALTHY_COMPARISON = "healthy_comparison"
    OTHER = "other"


class DiagnosisConfirmationType(StrEnum):
    EGYPTIAN_AGRONOMIST = "egyptian_agronomist"
    EGYPTIAN_PLANT_PATHOLOGY_LAB = "egyptian_plant_pathology_lab"


ObservationValue = str | int | float | bool
EvidenceSource = Literal[
    "farmer_answer",
    "image_model",
    "image_measurement",
    "device_sensor",
    "reviewed_rule",
    "expert",
    "lab",
]


class CropCaseCreate(StrictModel):
    crop: CropType
    location: str = Field(default="", max_length=200)
    farm_type: FarmType | None = None
    growth_stage: str | None = Field(default=None, max_length=100)
    symptoms: list[str] = Field(default_factory=list, max_length=20)


class CropCasePatch(StrictModel):
    location: str | None = Field(default=None, max_length=200)
    farm_type: FarmType | None = None
    growth_stage: str | None = Field(default=None, max_length=100)
    symptoms: list[str] | None = Field(default=None, max_length=20)


class ObservationInput(StrictModel):
    values: dict[str, ObservationValue] = Field(min_length=1, max_length=30)
    source: EvidenceSource = "farmer_answer"


class DiagnosisCandidate(StrictModel):
    disease: str = Field(min_length=2, max_length=160)
    confidence: float = Field(ge=0, le=1)


class DiagnosisInput(StrictModel):
    candidates: list[DiagnosisCandidate] = Field(min_length=1, max_length=3)
    evidence: list[str] = Field(default_factory=list, max_length=20)
    missing_info: list[str] = Field(default_factory=list, max_length=20)


class DiagnosisConfirmationInput(StrictModel):
    disease: str = Field(min_length=2, max_length=160)
    confirmation_type: DiagnosisConfirmationType
    organization: str = Field(min_length=2, max_length=200)
    report_reference: str = Field(min_length=2, max_length=200)
    confirmer_name: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)


class DiagnosisConfirmationOutput(DiagnosisConfirmationInput):
    evidence_filename: str = Field(min_length=1, max_length=255)
    evidence_sha256: str = Field(min_length=64, max_length=64)
    jurisdiction: Literal["Egypt"] = "Egypt"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    verification_notice: str = (
        "Recorded from submitted Egyptian expert or lab evidence; "
        "AgroVision has not independently authenticated the document."
    )


class DiagnosisOutput(StrictModel):
    top_disease: str = ""
    confidence: float = Field(default=0, ge=0, le=1)
    alternatives: list[DiagnosisCandidate] = Field(default_factory=list, max_length=2)
    evidence: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    confirmation_status: Literal[
        "unconfirmed",
        "confirmed_by_egyptian_agronomist",
        "confirmed_by_egyptian_plant_pathology_lab",
    ] = "unconfirmed"
    confirmation: DiagnosisConfirmationOutput | None = None


class EgyptSource(StrictModel):
    title: str
    organization: str
    url: str
    purpose: str
    source_kind: Literal["diagnosis", "pesticide_registration", "food_safety"]
    jurisdiction: Literal["Egypt"] = "Egypt"
    status: Literal["official"] = "official"
    retrieved_on: str = "2026-06-15"


NonNegative = Annotated[float, Field(ge=0)]
Percent = Annotated[float, Field(ge=0, le=100)]


class CostBenefitInput(StrictModel):
    area_feddan: NonNegative | None = None
    expected_yield_kg_per_feddan: NonNegative | None = None
    market_price_egp_per_kg: NonNegative | None = None
    yield_loss_without_treatment_percent: Percent | None = None
    yield_loss_after_treatment_percent: Percent | None = None
    product_cost_egp_per_application: NonNegative | None = None
    labor_cost_egp_per_application: NonNegative | None = None
    sprayer_cost_egp_per_application: NonNegative | None = None
    water_fuel_cost_egp_per_application: NonNegative | None = None
    application_count: Annotated[int, Field(ge=1, le=20)] | None = None


class CostBenefitOutput(StrictModel):
    treatment_cost_egp: float | None = None
    estimated_saved_revenue_egp: float | None = None
    net_benefit_egp: float | None = None
    roi: float | None = None
    break_even_yield_saved_kg: float | None = None
    decision: str = "need_more_data"
    missing_inputs: list[str] = Field(default_factory=list)


class TreatmentPlanOutput(StrictModel):
    non_chemical: list[str] = Field(default_factory=list)
    chemical_category_if_needed: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class SeverityEstimate(StrictModel):
    """Image-derived severity + a transparent yield-loss range. An ESTIMATE, not a
    field measurement — every value is a documented formula over measured inputs."""

    severity_label: Literal["unknown", "low", "moderate", "high", "severe"] = "unknown"
    visible_affected_percent: float | None = None
    estimated_yield_loss_low_percent: float | None = None
    estimated_yield_loss_high_percent: float | None = None
    recovery_probability_label: Literal["unknown", "low", "fair", "good"] = "unknown"
    weather_risk_label: Literal["unknown", "low", "medium", "high"] = "unknown"
    drivers: list[str] = Field(default_factory=list)
    basis: str = (
        "Estimated from the uploaded image and reviewed reference factors, not a field measurement."
    )


class PriceReference(StrictModel):
    item: str
    unit: str
    low_egp: float
    high_egp: float
    source: str
    as_of: str
    note: str = "Reference range — confirm the current local price before buying."


class CostEstimate(StrictModel):
    """Reference-priced fallback so Phase 5 is never blank when the farmer has not
    entered real numbers. Clearly labelled as an estimate from reference prices."""

    basis: Literal["farmer_inputs", "reference_estimate", "need_more_data"] = "reference_estimate"
    area_feddan_assumed: float | None = None
    treatment_cost_egp_low: float | None = None
    treatment_cost_egp_high: float | None = None
    potential_loss_egp_low: float | None = None
    potential_loss_egp_high: float | None = None
    net_benefit_egp_low: float | None = None
    net_benefit_egp_high: float | None = None
    decision_hint: str = ""
    prices_used: list[PriceReference] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    note: str = (
        "Estimate from Egyptian reference prices and image-based severity; "
        "enter your real numbers in the cost-benefit form for an exact result."
    )


SourceType = Literal["live_market", "admin_table", "csv_fallback", "estimated_range"]
Certainty = Literal["low", "medium", "high"]


class SourcedRange(StrictModel):
    """One generated number that always carries its unit, source, confidence and
    the assumption behind it — so a farmer-facing figure is never bare."""

    label_en: str
    label_ar: str
    low: float | None
    high: float | None
    unit: str
    source_type: SourceType = "estimated_range"
    confidence: Certainty = "low"
    assumption_en: str = ""
    assumption_ar: str = ""
    measured_zero: bool = False

    @model_validator(mode="after")
    def _validate_range(self) -> "SourcedRange":
        if (self.low is None) != (self.high is None):
            raise ValueError("SourcedRange.low and SourcedRange.high must both be set or both be None")
        if self.low is not None and self.high is not None:
            if (self.low == 0 or self.high == 0) and not self.measured_zero:
                raise ValueError("Zero sourced ranges require measured_zero=True")
        return self


class AreaRangeCase(StrictModel):
    """A ready cost-benefit scenario for one Egyptian area size, generated with no
    farmer input. Replaces the old 'enter your area' form with concrete ranges."""

    key: str
    name_en: str
    name_ar: str
    area_feddan: float
    sprays: SourcedRange
    treatment_cost_egp: SourcedRange
    labor_cost_egp: SourcedRange
    expected_yield_kg: SourcedRange
    loss_without_action_egp: SourcedRange
    saved_with_action_egp: SourcedRange
    revenue_egp: SourcedRange
    net_benefit_egp: SourcedRange
    worth_spraying: Literal["likely_worth", "maybe_not_worth", "ask_engineer"] = "ask_engineer"
    recommendation_en: str
    recommendation_ar: str


class PrimaryDisease(StrictModel):
    """The detected disease, ALWAYS surfaced — even at low confidence — so the
    report is never blocked. ``detected`` is False only when nothing was matched."""

    name_en: str = ""
    name_ar: str = ""
    confidence: float = Field(default=0, ge=0, le=1)
    certainty_level: Certainty = "low"
    detected: bool = False


class ConfidenceWarning(StrictModel):
    level: Certainty = "low"
    text_en: str = ""
    text_ar: str = ""


class Assumption(StrictModel):
    """A positive 'we generated this because X was unknown' note — never the word
    'missing'. Carries the source type so the farmer sees where a number came from."""

    text_en: str
    text_ar: str
    source_type: SourceType = "estimated_range"


class ScenarioOutput(StrictModel):
    """One Egyptian farm context with how each phase changes. Generated for every
    case so Phase 6 is never blank, even when the farmer's context is unknown."""

    key: str
    name_en: str
    name_ar: str
    confidence_en: str
    confidence_ar: str
    protection_en: str
    protection_ar: str
    treatment_en: str
    treatment_ar: str
    cost_en: str
    cost_ar: str
    recommendation_en: str
    recommendation_ar: str


class PredictionOutput(StrictModel):
    damage_degree: Literal["", "low", "medium", "high", "severe", "unknown"] = "unknown"
    yield_loss_percent: float | None = Field(default=None, ge=0, le=100)
    yield_kg_per_feddan: float | None = Field(default=None, ge=0)
    main_risk_factors: list[str] = Field(default_factory=list)


class RecommendationOutput(StrictModel):
    best_action_now: str = ""
    next_3_to_7_days: str = ""
    when_to_call_expert: str = ""


DataSourceKind = Literal[
    "visual_model",
    "disease_information",
    "variety_knowledge",
    "weather",
    "market_price",
    "pesticide_registration",
    "tomato_statistics",
    "treatment_knowledge",
    "fallback_assumption",
]
DataSourceOrigin = Literal["live", "official", "admin_table", "csv_fallback", "estimated_range", "generated"]


class CompactValue(StrictModel):
    label_en: str
    label_ar: str
    value: str | int | float | None
    unit: str = ""
    source_type: DataSourceOrigin = "generated"
    confidence: Certainty = "low"
    assumption_en: str = ""
    assumption_ar: str = ""
    measured_zero: bool = False

    @model_validator(mode="after")
    def _validate_zero_value(self) -> "CompactValue":
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool) and self.value == 0 and not self.measured_zero:
            raise ValueError("Zero compact values require measured_zero=True")
        return self


class EngineStats(StrictModel):
    analysis_time_ms: int | None = None
    engine: str
    memory_used_mb: float | None = None
    source_status: str


class SummaryCards(StrictModel):
    numbers_only: Literal[True] = True
    detected_disease: CompactValue
    visual_score: CompactValue
    top_candidates: list[CompactValue] = Field(default_factory=list)
    infection_extent: CompactValue
    weather_risk: CompactValue
    engine_stats: EngineStats


class DiseaseCandidateInsight(StrictModel):
    rank: int = Field(ge=1, le=3)
    disease_name_en: str
    disease_name_ar: str
    confidence: float = Field(ge=0, le=1)
    confidence_label: Certainty = "low"
    support_en: list[str] = Field(default_factory=list)
    support_ar: list[str] = Field(default_factory=list)
    source_type: DataSourceOrigin = "generated"
    source_note_en: str = ""
    source_note_ar: str = ""


class ResistantVarietyOption(StrictModel):
    name_en: str
    name_ar: str
    resistance_codes_en: str = ""
    resistance_codes_ar: str = ""
    disease_coverage_en: list[str] = Field(default_factory=list)
    disease_coverage_ar: list[str] = Field(default_factory=list)
    resistance_strength_en: str = ""
    resistance_strength_ar: str = ""
    prevention_only_warning_en: str = ""
    prevention_only_warning_ar: str = ""
    egypt_availability_status: Literal["verified_in_egypt", "not_verified_in_egypt", "unknown"] = "unknown"
    source_kind: DataSourceKind = "disease_information"
    source_type: DataSourceOrigin = "generated"
    source_title: str = ""
    source_organization: str = ""
    source_url: str | None = None
    source_note_en: str = ""
    source_note_ar: str = ""
    farmer_wording_en: str = ""
    farmer_wording_ar: str = ""


class TreatmentModeOption(StrictModel):
    key: str
    label_en: str
    label_ar: str
    summary_en: str
    summary_ar: str
    cost_egp: "SourcedRange"
    budget_egp: "SourcedRange"
    expected_benefit_en: str
    expected_benefit_ar: str
    risk_en: str
    risk_ar: str
    apc_gate_en: str
    apc_gate_ar: str
    requires_apc_verification: bool = False
    requires_engineer_confirmation: bool = False
    source_kind: DataSourceKind = "treatment_knowledge"
    source_type: DataSourceOrigin = "generated"
    source_note_en: str = ""
    source_note_ar: str = ""
    farmer_wording_ar: str = ""


class ScenarioSection(StrictModel):
    title_en: str
    title_ar: str
    bullets_en: list[str] = Field(default_factory=list)
    bullets_ar: list[str] = Field(default_factory=list)
    source_type: DataSourceOrigin = "generated"
    confidence: Certainty = "low"
    assumption_en: str = ""
    assumption_ar: str = ""


class ScenarioCase(StrictModel):
    key: str
    name_en: str
    name_ar: str
    summary_en: str
    summary_ar: str
    sections: list[ScenarioSection] = Field(default_factory=list)


class ConsultingQuestionAnswer(StrictModel):
    key: str
    question_en: str
    question_ar: str
    answer_en: str
    answer_ar: str
    why_it_matters_en: str
    why_it_matters_ar: str
    decision_change_en: str
    decision_change_ar: str
    scenario_notes_en: list[str] = Field(default_factory=list)
    scenario_notes_ar: list[str] = Field(default_factory=list)
    source_type: DataSourceOrigin = "generated"
    assumption_en: str = ""
    assumption_ar: str = ""


class DiseaseInformationPhase(StrictModel):
    disease_name_en: str
    disease_name_ar: str
    cause_type_en: str
    cause_type_ar: str
    meaning_en: str
    meaning_ar: str
    leaf_symptoms_en: list[str] = Field(default_factory=list)
    leaf_symptoms_ar: list[str] = Field(default_factory=list)
    fruit_symptoms_en: list[str] = Field(default_factory=list)
    fruit_symptoms_ar: list[str] = Field(default_factory=list)
    stem_symptoms_en: list[str] = Field(default_factory=list)
    stem_symptoms_ar: list[str] = Field(default_factory=list)
    spread_en: str
    spread_ar: str
    why_it_appears_en: str
    why_it_appears_ar: str
    irrigation_conditions_en: str
    irrigation_conditions_ar: str
    worse_weather_en: str
    worse_weather_ar: str
    lookalikes_en: list[str] = Field(default_factory=list)
    lookalikes_ar: list[str] = Field(default_factory=list)
    danger_en: str
    danger_ar: str
    top_candidates: list[DiseaseCandidateInsight] = Field(default_factory=list)
    resistant_varieties: list[ResistantVarietyOption] = Field(default_factory=list)
    today_check_en: list[str] = Field(default_factory=list)
    today_check_ar: list[str] = Field(default_factory=list)
    worsening_en: list[str] = Field(default_factory=list)
    worsening_ar: list[str] = Field(default_factory=list)
    stable_en: list[str] = Field(default_factory=list)
    stable_ar: list[str] = Field(default_factory=list)
    scenario_cases: list[ScenarioCase] = Field(default_factory=list)
    higher_accuracy_hint_en: str = ""
    higher_accuracy_hint_ar: str = ""


class ProtectionPhase(StrictModel):
    scenario_cases: list[ScenarioCase] = Field(default_factory=list)
    higher_accuracy_hint_en: str = ""
    higher_accuracy_hint_ar: str = ""


class ConsultingPhase(StrictModel):
    auto_questions_with_answers: list[ConsultingQuestionAnswer] = Field(default_factory=list)
    higher_accuracy_hint_en: str = ""
    higher_accuracy_hint_ar: str = ""


class TreatmentPhase(StrictModel):
    scenario_cases: list[ScenarioCase] = Field(default_factory=list)
    treatment_options: list[TreatmentModeOption] = Field(default_factory=list)
    selected_mode_key: str = ""
    higher_accuracy_hint_en: str = ""
    higher_accuracy_hint_ar: str = ""


class CostForecastPhase(StrictModel):
    area_range_cases: list[AreaRangeCase] = Field(default_factory=list)
    provider_priority: list[str] = Field(default_factory=list)
    treatment_comparison: list[TreatmentModeOption] = Field(default_factory=list)
    selected_mode_key: str = ""
    higher_accuracy_hint_en: str = ""
    higher_accuracy_hint_ar: str = ""


class ConclusionRecommendationPhase(StrictModel):
    scenario_recommendations: list[ScenarioCase] = Field(default_factory=list)
    action_plan: list[ScenarioSection] = Field(default_factory=list)
    selected_mode_key: str = ""
    best_balanced_choice_en: str = ""
    best_balanced_choice_ar: str = ""
    comparison_summary_en: str = ""
    comparison_summary_ar: str = ""
    higher_accuracy_hint_en: str = ""
    higher_accuracy_hint_ar: str = ""


class GeneratedPhases(StrictModel):
    disease_information: DiseaseInformationPhase = Field(default_factory=DiseaseInformationPhase)
    protection: ProtectionPhase = Field(default_factory=ProtectionPhase)
    consulting: ConsultingPhase = Field(default_factory=ConsultingPhase)
    treatment: TreatmentPhase = Field(default_factory=TreatmentPhase)
    cost_forecast: CostForecastPhase = Field(default_factory=CostForecastPhase)
    conclusion_recommendation: ConclusionRecommendationPhase = Field(default_factory=ConclusionRecommendationPhase)


def _placeholder_summary_cards() -> SummaryCards:
    return SummaryCards(
        detected_disease=CompactValue(
            label_en="Primary disease",
            label_ar="المرض الأساسي",
            value=None,
            confidence="low",
        ),
        visual_score=CompactValue(
            label_en="Visual match",
            label_ar="التطابق البصري",
            value=None,
            unit="%",
            confidence="low",
        ),
        top_candidates=[],
        infection_extent=CompactValue(
            label_en="Visible infection",
            label_ar="الانتشار الظاهر",
            value=None,
            unit="%",
            confidence="low",
        ),
        weather_risk=CompactValue(
            label_en="Weather risk",
            label_ar="خطر الطقس",
            value=None,
            unit="%",
            confidence="low",
        ),
        engine_stats=EngineStats(
            analysis_time_ms=None,
            engine="",
            memory_used_mb=None,
            source_status="",
        ),
    )


def _placeholder_generated_phases() -> GeneratedPhases:
    empty_section = ScenarioSection(title_en="", title_ar="")
    empty_case = ScenarioCase(key="", name_en="", name_ar="", summary_en="", summary_ar="", sections=[])
    return GeneratedPhases(
        disease_information=DiseaseInformationPhase(
            disease_name_en="",
            disease_name_ar="",
            cause_type_en="",
            cause_type_ar="",
            meaning_en="",
            meaning_ar="",
            leaf_symptoms_en=[],
            leaf_symptoms_ar=[],
            fruit_symptoms_en=[],
            fruit_symptoms_ar=[],
            stem_symptoms_en=[],
            stem_symptoms_ar=[],
            spread_en="",
            spread_ar="",
            why_it_appears_en="",
            why_it_appears_ar="",
            irrigation_conditions_en="",
            irrigation_conditions_ar="",
            worse_weather_en="",
            worse_weather_ar="",
            lookalikes_en=[],
            lookalikes_ar=[],
            danger_en="",
            danger_ar="",
            top_candidates=[],
            resistant_varieties=[],
            today_check_en=[],
            today_check_ar=[],
            worsening_en=[],
            worsening_ar=[],
            stable_en=[],
            stable_ar=[],
            scenario_cases=[],
            higher_accuracy_hint_en="",
            higher_accuracy_hint_ar="",
        ),
        protection=ProtectionPhase(scenario_cases=[], higher_accuracy_hint_en="", higher_accuracy_hint_ar=""),
        consulting=ConsultingPhase(auto_questions_with_answers=[], higher_accuracy_hint_en="", higher_accuracy_hint_ar=""),
        treatment=TreatmentPhase(
            scenario_cases=[],
            treatment_options=[],
            selected_mode_key="",
            higher_accuracy_hint_en="",
            higher_accuracy_hint_ar="",
        ),
        cost_forecast=CostForecastPhase(
            area_range_cases=[],
            provider_priority=[],
            treatment_comparison=[],
            selected_mode_key="",
            higher_accuracy_hint_en="",
            higher_accuracy_hint_ar="",
        ),
        conclusion_recommendation=ConclusionRecommendationPhase(
            scenario_recommendations=[empty_case],
            action_plan=[empty_section],
            selected_mode_key="",
            best_balanced_choice_en="",
            best_balanced_choice_ar="",
            comparison_summary_en="",
            comparison_summary_ar="",
            higher_accuracy_hint_en="",
            higher_accuracy_hint_ar="",
        ),
    )


class SidebarChatbotContext(StrictModel):
    summary_en: str = ""
    summary_ar: str = ""
    quick_questions_en: list[str] = Field(default_factory=list)
    quick_questions_ar: list[str] = Field(default_factory=list)
    allowed_topics_en: list[str] = Field(default_factory=list)
    allowed_topics_ar: list[str] = Field(default_factory=list)
    source_keys: list[str] = Field(default_factory=list)


class SourceMetadata(StrictModel):
    key: str
    title: str
    organization: str
    source_kind: DataSourceKind
    source_type: DataSourceOrigin = "generated"
    url: str | None = None
    confidence: Certainty = "low"
    retrieved_on: str | None = None
    note_en: str = ""
    note_ar: str = ""


class PhotoQuality(StrictModel):
    status: str = ""
    leaf_area_score: float | None = None
    host_crop_support: str = ""
    warnings: list[str] = Field(default_factory=list)


class TreatmentOptionSchema(StrictModel):
    id: str = ""
    name: str = ""
    type: str = ""
    budget_level: str = ""
    allowed_status: str = ""
    cost_range: dict[str, float | None] = Field(default_factory=dict)
    labor_range: dict[str, float | None] = Field(default_factory=dict)
    source_type: str = ""
    assumptions: list[str] = Field(default_factory=list)
    safety_gate: dict[str, object] = Field(default_factory=dict)


class CostBenefitBySelectedTreatment(StrictModel):
    selected_treatment_id: str = ""
    area_scenarios: list[dict[str, object]] = Field(default_factory=list)


class ForecastRecalculation(StrictModel):
    function_used: str = "calculateCostBenefitByTreatment"
    last_selected_treatment_id: str = ""
    updated_at: str = ""


class SystemOutput(StrictModel):
    photo_quality: PhotoQuality = Field(default_factory=PhotoQuality)
    treatment_options: list[TreatmentOptionSchema] = Field(default_factory=list)
    selected_treatment_id: str = ""
    cost_benefit_by_selected_treatment: CostBenefitBySelectedTreatment = Field(default_factory=CostBenefitBySelectedTreatment)
    cost_benefit_comparison: list[dict[str, object]] = Field(default_factory=list)
    forecast_recalculation: ForecastRecalculation = Field(default_factory=ForecastRecalculation)

    case_id: str
    crop: str
    location: str
    farm_type: str | None = None
    growth_stage: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    observations: dict[str, ObservationValue] = Field(default_factory=dict)
    observation_sources: dict[str, EvidenceSource] = Field(default_factory=dict)
    egypt_sources: list[EgyptSource] = Field(default_factory=list)
    source_metadata: list[SourceMetadata] = Field(default_factory=list)
    diagnosis: DiagnosisOutput
    chatbot_followup_questions: list[str] = Field(default_factory=list, max_length=5)
    protection_plan: list[str] = Field(default_factory=list)
    treatment_plan: TreatmentPlanOutput
    cost_benefit: CostBenefitOutput
    severity: SeverityEstimate = Field(default_factory=SeverityEstimate)
    cost_estimate: CostEstimate = Field(default_factory=CostEstimate)
    prediction: PredictionOutput
    recommendation: RecommendationOutput
    scenarios: list[ScenarioOutput] = Field(default_factory=list)
    summary_cards: SummaryCards = Field(default_factory=_placeholder_summary_cards)
    phases: GeneratedPhases = Field(default_factory=_placeholder_generated_phases)
    sidebar_chatbot_context: SidebarChatbotContext = Field(default_factory=SidebarChatbotContext)
    # The detected disease is ALWAYS surfaced as primary (even at low confidence) and
    # the cost-benefit phase is generated as area-range cases needing zero farmer input.
    primary_detected_disease: PrimaryDisease = Field(default_factory=PrimaryDisease)
    confidence_warning: ConfidenceWarning | None = None
    area_range_cases: list[AreaRangeCase] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    conclusion: str
    completeness: list[str] = Field(
        default_factory=list,
        description="Deprecated: kept empty. Unknown context now becomes generated scenarios, area-range cases, and positive assumptions instead of 'missing' notes.",
    )
    disclaimer: Literal[
        "AI prediction only. Confirm with an agricultural engineer or lab when crop value or risk is high."
    ] = DISCLAIMER


class CropCase(StrictModel):
    case_id: str
    status: CaseStatus = CaseStatus.DRAFT
    crop: CropType
    location: str = ""
    farm_type: FarmType | None = None
    growth_stage: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    observations: dict[str, ObservationValue] = Field(default_factory=dict)
    observation_sources: dict[str, EvidenceSource] = Field(default_factory=dict)
    egypt_sources: list[EgyptSource] = Field(default_factory=list)
    asked_question_keys: list[str] = Field(default_factory=list)
    consulting_questions: list[str] = Field(default_factory=list, max_length=5)
    diagnosis: DiagnosisOutput = Field(default_factory=DiagnosisOutput)
    disease_class: str = "unknown"
    treatment_rule_version: str = ""
    protection_plan: list[str] = Field(default_factory=list)
    treatment_plan: TreatmentPlanOutput = Field(default_factory=TreatmentPlanOutput)
    cost_benefit: CostBenefitOutput = Field(default_factory=CostBenefitOutput)
    prediction: PredictionOutput = Field(default_factory=PredictionOutput)
    recommendation: RecommendationOutput = Field(default_factory=RecommendationOutput)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
