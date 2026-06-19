from __future__ import annotations

from datetime import UTC, datetime
from math import isnan
import re
from uuid import uuid4

from app.adapters.case_repository import InMemoryCaseRepository
from app.application.area_ranges import generate_area_range_cases
from app.application.cost_benefit import calculate_cost_benefit
from app.application.policies import (
    LOW_CONFIDENCE_THRESHOLD,
    prediction,
    protection_plan,
    recommendation,
)
from app.application.question_engine import QUESTIONS, next_questions
from app.application.scenarios import generate_scenarios
from app.application.severity import estimate_severity, reference_cost_estimate
from app.crop_knowledge import tomato_resistant_variety_records
from app.diseases import disease_by_name_en
from app.contracts.cases import (
    Assumption,
    CaseStatus,
    ConfidenceWarning,
    CompactValue,
    CostBenefitInput,
    CostEstimate,
    CropCase,
    CropCaseCreate,
    CropCasePatch,
    ConsultingPhase,
    ConsultingQuestionAnswer,
    DiagnosisCandidate,
    DiagnosisConfirmationInput,
    DiagnosisConfirmationOutput,
    DiagnosisInput,
    DiagnosisOutput,
    DiseaseInformationPhase,
    EngineStats,
    GeneratedPhases,
    ConclusionRecommendationPhase,
    CostForecastPhase,
    DiseaseCandidateInsight,
    ProtectionPhase,
    ObservationInput,
    PrimaryDisease,
    ResistantVarietyOption,
    ScenarioCase,
    ScenarioSection,
    SidebarChatbotContext,
    SourceMetadata,
    SummaryCards,
    SystemOutput,
    SourcedRange,
    TreatmentModeOption,
    TreatmentPhase,
    PhotoQuality,
    TreatmentOptionSchema,
    CostBenefitBySelectedTreatment,
    ForecastRecalculation,
)
from app.domain.case_state import require_transition
from app.application.prices import price_provider
from app.knowledge.egypt_sources import (
    EGYPT_FOOD_SAFETY_LAB_URL,
    EGYPT_PESTICIDE_DATABASE_URL,
    egypt_official_sources,
)
from app.knowledge.tomato_statistics import tomato_statistics_sources
from app.knowledge.treatment_rules import treatment_rule
from app.weather import WeatherObservation, current_weather, egypt_reference_weather, weather_for_coords, weather_pressure_calculator


class CaseNotFoundError(LookupError):
    pass


_MARKER = "Not enough visual evidence"
_LOW_CONFIDENCE_WARNING_AR = (
    "خلي بالك: دقة التعرف قليلة، راجع الصورة أو اسأل مهندس زراعي قبل أي قرار مهم."
)


def _primary_disease(case: CropCase) -> PrimaryDisease:
    """Always surface the detected disease as primary — even at low confidence.

    The report is never blocked: a 42 % match is still shown as the primary disease
    with an honest low-certainty label, not hidden behind "no diagnosis".
    """
    dx = case.diagnosis
    candidates = [(dx.top_disease, dx.confidence)]
    candidates += [(alt.disease, alt.confidence) for alt in dx.alternatives]
    real = [(name, conf) for name, conf in candidates if name and name != _MARKER]
    if not real:
        return PrimaryDisease(detected=False, certainty_level="low")
    name_en, conf = real[0]
    info = disease_by_name_en(name_en)
    name_ar = info.name_ar if info else name_en
    if conf >= 0.70:
        level = "high"
    elif conf >= LOW_CONFIDENCE_THRESHOLD:
        level = "medium"
    else:
        level = "low"
    return PrimaryDisease(
        name_en=name_en, name_ar=name_ar, confidence=conf, certainty_level=level, detected=True
    )


def _confidence_warning(primary: PrimaryDisease) -> ConfidenceWarning | None:
    """Honest low-confidence warning — shown, but never blocks the report."""
    if not primary.detected:
        return ConfidenceWarning(
            level="low",
            text_en=(
                "No clear disease was matched in this photo. The phases below are general "
                "scenarios — retake a clear leaf photo or ask an agronomist before acting."
            ),
            text_ar=(
                "مفيش مرض واضح اتطابق في الصورة دي. اللي تحت ده سيناريوهات عامة — صوّر "
                "ورقة واضحة أو اسأل مهندس زراعي قبل أي تصرّف."
            ),
        )
    if primary.certainty_level == "low":
        return ConfidenceWarning(
            level="low",
            text_en=(
                "Heads up: recognition confidence is low. Re-check the photo or ask an "
                "agricultural engineer before any important decision."
            ),
            text_ar=_LOW_CONFIDENCE_WARNING_AR,
        )
    return None


def _report_assumptions(case: CropCase, area_cases) -> list[Assumption]:
    """Positive 'generated because X was unknown' notes — never the word 'missing'."""
    notes: list[Assumption] = []
    if not case.farm_type:
        notes.append(Assumption(
            text_en="Farm type was not given, so every Egyptian farm scenario is generated below.",
            text_ar="نوع المزرعة مش متحدد، فاتولّدت كل سيناريوهات المزارع المصرية تحت.",
        ))
    if not isinstance(case.observations.get("area_feddan"), (int, float)):
        notes.append(Assumption(
            text_en="Area was not given, so cost-benefit is generated for every common Egyptian area size.",
            text_ar="المساحة مش متحددة، فالتكلفة والعائد اتولّدوا لكل المساحات المصرية الشائعة.",
        ))
    if area_cases:
        price_source = area_cases[-1].revenue_egp.source_type
        if price_source == "estimated_range":
            notes.append(Assumption(
                text_en="Prices are Egyptian reference estimates, not live market prices.",
                text_ar="الأسعار تقديرية مرجعية مصرية، مش أسعار سوق مباشرة.",
                source_type="estimated_range",
            ))
        else:
            notes.append(Assumption(
                text_en="Prices come from the configured Egyptian price source.",
                text_ar="الأسعار جاية من مصدر الأسعار المصري المضبوط.",
                source_type=price_source,
            ))
    return notes


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _observation_number(case: CropCase, key: str) -> float | None:
    value = case.observations.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value == value:
        return float(value)
    return None


def _observation_text(case: CropCase, key: str) -> str:
    value = case.observations.get(key)
    return str(value).strip() if isinstance(value, str) and value.strip() else ""


def _certainty(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.65:
        return "medium"
    return "low"


def _weather_risk_score(label: str) -> int | None:
    return {"high": 82, "medium": 58, "low": 25}.get(label)


def _compact_value(
    label_en: str,
    label_ar: str,
    value: str | int | float | None,
    *,
    unit: str = "",
    source_type: str = "generated",
    confidence: str = "low",
    assumption_en: str = "",
    assumption_ar: str = "",
    measured_zero: bool = False,
) -> CompactValue:
    return CompactValue(
        label_en=label_en,
        label_ar=label_ar,
        value=value,
        unit=unit,
        source_type=source_type,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        assumption_en=assumption_en,
        assumption_ar=assumption_ar,
        measured_zero=measured_zero,
    )


def _section(
    title_en: str,
    title_ar: str,
    bullets_en: list[str],
    bullets_ar: list[str],
    *,
    source_type: str = "generated",
    confidence: str = "low",
    assumption_en: str = "",
    assumption_ar: str = "",
) -> ScenarioSection:
    return ScenarioSection(
        title_en=title_en,
        title_ar=title_ar,
        bullets_en=bullets_en,
        bullets_ar=bullets_ar,
        source_type=source_type,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        assumption_en=assumption_en,
        assumption_ar=assumption_ar,
    )


def _scenario(
    key: str,
    name_en: str,
    name_ar: str,
    summary_en: str,
    summary_ar: str,
    sections: list[ScenarioSection],
) -> ScenarioCase:
    return ScenarioCase(
        key=key,
        name_en=name_en,
        name_ar=name_ar,
        summary_en=summary_en,
        summary_ar=summary_ar,
        sections=sections,
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _candidate_insights(case: CropCase, primary: PrimaryDisease) -> list[DiseaseCandidateInsight]:
    raw_candidates: list[DiagnosisCandidate] = []
    top_disease = case.diagnosis.top_disease.strip() if case.diagnosis.top_disease else ""
    if top_disease and top_disease != _MARKER:
        raw_candidates.append(DiagnosisCandidate(disease=top_disease, confidence=case.diagnosis.confidence))
    for candidate in case.diagnosis.alternatives:
        disease = candidate.disease.strip()
        if disease and disease != _MARKER and all(disease != item.disease for item in raw_candidates):
            raw_candidates.append(candidate)
    if not raw_candidates:
        fallback_name = primary.name_en if primary.detected else "Not enough visual evidence"
        raw_candidates.append(DiagnosisCandidate(disease=fallback_name, confidence=0.0))

    evidence_en = case.diagnosis.evidence[0] if case.diagnosis.evidence else ""
    evidence_ar = evidence_en
    insights: list[DiseaseCandidateInsight] = []
    for rank, candidate in enumerate(raw_candidates[:3], start=1):
        info = disease_by_name_en(candidate.disease)
        disease_name_en = info.name_en if info else candidate.disease
        disease_name_ar = info.name_ar if info else candidate.disease
        support_en: list[str] = []
        support_ar: list[str] = []
        if rank == 1:
            support_en.append("Highest visual match from the uploaded photo.")
            support_ar.append("أعلى تطابق بصري من الصورة المرفوعة.")
        else:
            support_en.append("Alternative ranked by the same image model.")
            support_ar.append("بديل رتبه نفس نموذج الصورة.")
        if info:
            support_en.extend(info.symptoms_en[:2])
            support_ar.extend(info.symptoms_ar[:2])
        if evidence_en:
            support_en.append(f"Evidence note: {evidence_en}")
            support_ar.append(f"ملاحظة الدليل: {evidence_ar}")
        if not primary.detected:
            note_en = "No confident disease match yet; this is the best screening-level candidate."
            note_ar = "لا يوجد تطابق مرضي واثق بعد؛ هذه أفضل مرشحة على مستوى الفحص."
        else:
            note_en = f"Ranked from the uploaded photo at {candidate.confidence:.0%} confidence."
            note_ar = f"تم ترتيبها من الصورة المرفوعة بثقة {candidate.confidence:.0%}."
        insights.append(
            DiseaseCandidateInsight(
                rank=rank,
                disease_name_en=disease_name_en,
                disease_name_ar=disease_name_ar,
                confidence=candidate.confidence,
                confidence_label=_certainty(candidate.confidence),
                support_en=support_en[:4],
                support_ar=support_ar[:4],
                source_type="generated",
                source_note_en=note_en,
                source_note_ar=note_ar,
            )
        )
    return insights


def _candidate_terms(case: CropCase, primary: PrimaryDisease, info) -> list[str]:
    # Use only the PRIMARY detected disease — not alternatives — so variety
    # recommendations stay disease-specific and never pull in varieties for
    # lookalike candidates (e.g. bacterial spot alternatives include "early blight"
    # which would otherwise cause blight-resistant varieties to appear).
    terms = [
        case.diagnosis.top_disease,
        primary.name_en,
        primary.name_ar,
    ]
    if info:
        terms.extend([info.key, info.name_en, info.name_ar])
    return [term for term in (_normalize_text(term) for term in terms) if term]


def _resistant_variety_options(
    case: CropCase,
    primary: PrimaryDisease,
    info,
    require_disease_match: bool = False,
) -> list[ResistantVarietyOption]:
    if case.crop.value != "tomato":
        return []

    terms = _candidate_terms(case, primary, info)
    ranked: list[tuple[int, int, object]] = []
    for index, record in enumerate(tomato_resistant_variety_records()):
        # Match only against disease coverage items, not the full source/name blob.
        # This prevents "bacterial" (from "bacterial spot") matching "bacterial wilt"
        # in a variety that only covers wilt, not spot.
        coverage_items = [_normalize_text(c) for c in record.disease_coverage_en]
        coverage_blob = " ".join(coverage_items)
        score = 0
        for term in terms:
            if not term:
                continue
            # Exact coverage-item match (highest confidence)
            if any(term in item or item in term for item in coverage_items):
                score += 5
            # Partial coverage blob match (lower confidence)
            elif term in coverage_blob:
                score += 2
        ranked.append((score, index, record))

    ranked.sort(key=lambda item: (-item[0], -len(item[2].disease_coverage_en), item[2].name_en))
    chosen = [record for score, _, record in ranked if score > 0][:4]
    if not chosen and not require_disease_match:
        chosen = [record for _, _, record in ranked[:4]]

    return [
        ResistantVarietyOption(
            name_en=record.name_en,
            name_ar=record.name_ar,
            resistance_codes_en=record.resistance_codes_en,
            resistance_codes_ar=record.resistance_codes_ar,
            disease_coverage_en=list(record.disease_coverage_en),
            disease_coverage_ar=list(record.disease_coverage_ar),
            resistance_strength_en=record.resistance_strength_en,
            resistance_strength_ar=record.resistance_strength_ar,
            prevention_only_warning_en=record.prevention_only_warning_en,
            prevention_only_warning_ar=record.prevention_only_warning_ar,
            egypt_availability_status=record.egypt_availability_status,  # type: ignore[arg-type]
            source_kind=record.source_kind,  # type: ignore[arg-type]
            source_type=record.source_type,  # type: ignore[arg-type]
            source_title=record.source_title,
            source_organization=record.source_organization,
            source_url=record.source_url,
            source_note_en=record.source_note_en,
            source_note_ar=record.source_note_ar,
            farmer_wording_en=record.farmer_wording_en,
            farmer_wording_ar=record.farmer_wording_ar,
        )
        for record in chosen
    ]


def _money_range(
    label_en: str,
    label_ar: str,
    low: float | None,
    high: float | None,
    *,
    assumption_en: str,
    assumption_ar: str,
    measured_zero: bool = False,
    confidence: str = "medium",
) -> SourcedRange:
    return SourcedRange(
        label_en=label_en,
        label_ar=label_ar,
        low=low,
        high=high,
        unit="EGP",
        source_type="estimated_range",
        confidence=confidence,  # type: ignore[arg-type]
        assumption_en=assumption_en,
        assumption_ar=assumption_ar,
        measured_zero=measured_zero,
    )


def _treatment_mode_options(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    cost_estimate: CostEstimate,
    area_range_cases,
) -> list[TreatmentModeOption]:
    disease_class = case.disease_class or "unknown"
    low_confidence = primary.certainty_level == "low" or not primary.detected
    confirmed = case.diagnosis.confirmation is not None
    base_low = cost_estimate.treatment_cost_egp_low
    base_high = cost_estimate.treatment_cost_egp_high
    balanced_assumption_en = (
        "Based on the reference cost estimate for the current case."
        if cost_estimate.basis != "farmer_inputs"
        else "Based on the real numbers already entered for this case."
    )
    balanced_assumption_ar = (
        "مبنية على التقدير الرجعي للحالة الحالية."
        if cost_estimate.basis != "farmer_inputs"
        else "مبنية على الأرقام الحقيقية المدخلة مباشرة."
    )
    strong_low = round(base_low * 1.30) if base_low is not None else None
    strong_high = round(base_high * 1.30) if base_high is not None else None
    prev_low = round(base_low * 0.40) if base_low is not None else None
    prev_high = round(base_high * 0.60) if base_high is not None else None

    return [
        TreatmentModeOption(
            key="confirm_first",
            label_en="Confirm first",
            label_ar="أكد أولاً",
            summary_en="Hold chemical spending and confirm the diagnosis in the field or with a lab.",
            summary_ar="أوقف الصرف الكيميائي وأكد التشخيص ميدانياً أو معملياً.",
            cost_egp=_money_range(
                "Confirm first cost",
                "تكلفة التأكد أولاً",
                150.0,
                300.0,
                assumption_en="Estimated confirmation cost including engineer visit, lab fee, or transport.",
                assumption_ar="تكلفة التأكيد التقديرية تشمل زيارة المهندس، رسوم المختبر، أو الانتقال.",
                confidence="low",
            ),
            budget_egp=_money_range(
                "Confirm first budget",
                "ميزانية التأكد أولاً",
                150.0,
                300.0,
                assumption_en="Budget for diagnosis verification before chemical spend.",
                assumption_ar="ميزانية التحقق من التشخيص قبل الصرف الكيميائي.",
                confidence="low",
            ),
            expected_benefit_en="Avoids buying the wrong product before the diagnosis is firm.",
            expected_benefit_ar="يمنع شراء منتج خاطئ قبل ثبات التشخيص.",
            risk_en="Delay risk only; suitable when the match is weak or the disease is viral.",
            risk_ar="خطر التأخير فقط؛ مناسب عندما يكون التطابق ضعيفاً أو المرض فيروسياً.",
            apc_gate_en="No spray until the diagnosis is confirmed and the label can be checked.",
            apc_gate_ar="لا يوجد رش حتى يتأكد التشخيص ويمكن مراجعة الملصق.",
            requires_apc_verification=False,
            requires_engineer_confirmation=True,
            source_kind="treatment_knowledge",
            source_type="generated",
            source_note_en="Used when the current photo is not strong enough to justify a purchase.",
            source_note_ar="يُستخدم عندما لا تكون الصورة قوية بما يكفي لتبرير الشراء.",
            farmer_wording_ar="ابدأ بالتأكيد قبل أي شراء كيماوي.",
        ),
        TreatmentModeOption(
            key="sanitation_only",
            label_en="Sanitation only",
            label_ar="تنظيف فقط",
            summary_en="Rogue badly affected tissue, keep the canopy dry, and re-check before spending.",
            summary_ar="أزل الأجزاء الشديدة، وحافظ على جفاف المجموع الخضري، وأعد الفحص قبل الصرف.",
            cost_egp=_money_range(
                "Sanitation only cost",
                "تكلفة التنظيف فقط",
                0.0,
                0.0,
                assumption_en="No pesticide purchase; only field sanitation and follow-up.",
                assumption_ar="لا يوجد شراء مبيد؛ فقط نظافة حقلية ومتابعة.",
                measured_zero=True,
                confidence="low",
            ),
            budget_egp=_money_range(
                "Sanitation only budget",
                "ميزانية التنظيف فقط",
                0.0,
                0.0,
                assumption_en="Zero purchase budget because this option stays non-chemical.",
                assumption_ar="ميزانية شراء صفر لأن هذا الخيار غير كيميائي.",
                measured_zero=True,
                confidence="low",
            ),
            expected_benefit_en="Lowest cash spend, but it only slows the problem rather than curing it.",
            expected_benefit_ar="أقل صرف نقدي، لكنه يبطئ المشكلة ولا يشفيها.",
            risk_en="May be too weak if the disease is already spreading fast.",
            risk_ar="قد يكون ضعيفاً إذا كان المرض ينتشر بسرعة بالفعل.",
            apc_gate_en="No pesticide purchase; still confirm the diagnosis if the crop value is high.",
            apc_gate_ar="لا شراء مبيد؛ ومع ذلك أكد التشخيص إذا كانت قيمة المحصول عالية.",
            requires_apc_verification=False,
            requires_engineer_confirmation=False,
            source_kind="treatment_knowledge",
            source_type="generated",
            source_note_en="Used when the safest near-term step is hygiene rather than spending.",
            source_note_ar="يُستخدم عندما تكون الخطوة الآمنة الأقرب هي النظافة لا الصرف.",
            farmer_wording_ar="البدء بالنظافة هو الأرخص والأكثر أماناً.",
        ),
        TreatmentModeOption(
            key="balanced",
            label_en="Balanced",
            label_ar="متوازن",
            summary_en="Use the reference treatment program that fits the current severity and economics.",
            summary_ar="استخدم برنامج العلاج المرجعي المناسب لشدة الحالة والاقتصاد الحالي.",
            cost_egp=_money_range(
                "Balanced cost",
                "تكلفة متوازنة",
                base_low,
                base_high,
                assumption_en=balanced_assumption_en,
                assumption_ar=balanced_assumption_ar,
            ),
            budget_egp=_money_range(
                "Balanced budget",
                "ميزانية متوازنة",
                base_low,
                base_high,
                assumption_en=balanced_assumption_en,
                assumption_ar=balanced_assumption_ar,
            ),
            expected_benefit_en="Best balance between spending, control, and confirmation discipline.",
            expected_benefit_ar="أفضل توازن بين الصرف والسيطرة والانضباط في التأكد.",
            risk_en="Requires APC label verification before any spray purchase.",
            risk_ar="يتطلب مراجعة ملصق APC قبل شراء أي رش.",
            apc_gate_en="Allowed only after label verification and a confident disease match.",
            apc_gate_ar="مسموح فقط بعد مراجعة الملصق وتأكد التطابق المرضي.",
            requires_apc_verification=True,
            requires_engineer_confirmation=False,
            source_kind="treatment_knowledge",
            source_type="generated",
            source_note_en="Reference program derived from the current case severity and Egyptian price table.",
            source_note_ar="برنامج مرجعي مشتق من شدة الحالة الحالية وجدول الأسعار المصري.",
            farmer_wording_ar="هذا هو الاختيار المتوازن إذا تأكد المرض وظهر الملصق.",
        ),
        TreatmentModeOption(
            key="strongest",
            label_en="Strongest",
            label_ar="الأقوى",
            summary_en="Use the broader, more expensive program when the crop is clearly under heavy pressure.",
            summary_ar="استخدم البرنامج الأوسع والأغلى عندما يكون الضغط المرضي واضحاً وشديداً.",
            cost_egp=_money_range(
                "Strongest cost",
                "تكلفة الأقوى",
                strong_low,
                strong_high,
                assumption_en="Modeled as a broader program with an extra protection pass.",
                assumption_ar="نمذج كبرنامج أوسع مع تمريرة حماية إضافية.",
            ),
            budget_egp=_money_range(
                "Strongest budget",
                "ميزانية الأقوى",
                strong_low,
                strong_high,
                assumption_en="Budget includes an extra buffer for the broader pass.",
                assumption_ar="الميزانية تشمل هامشاً إضافياً للبرنامج الأوسع.",
            ),
            expected_benefit_en="Highest control ceiling, but only if the APC label supports the action.",
            expected_benefit_ar="أعلى سقف للسيطرة، ولكن فقط إذا دعم الملصق المعتمد هذا الإجراء.",
            risk_en="Higher spend and higher misuse risk if the label or crop stage is wrong.",
            risk_ar="صرف أعلى وخطر استخدام خاطئ أعلى إذا كان الملصق أو مرحلة المحصول غير مناسبين.",
            apc_gate_en="Needs APC verification and agronomist confirmation before use.",
            apc_gate_ar="يتطلب تحقق APC وتأكيد مهندس زراعي قبل الاستخدام.",
            requires_apc_verification=True,
            requires_engineer_confirmation=True,
            source_kind="treatment_knowledge",
            source_type="generated",
            source_note_en="Modeled escalation for severe pressure; not a live product quote.",
            source_note_ar="تصعيد نمذجي للضغط الشديد؛ ليس عرض سعر حيّاً لمنتج.",
            farmer_wording_ar="استخدمه فقط عندما تكون الحالة شديدة والملصق واضحاً.",
        ),
        TreatmentModeOption(
            key="prevention_only",
            label_en="Prevention only",
            label_ar="وقائي فقط",
            summary_en="Apply preventive products and culture controls before disease/pest spreads.",
            summary_ar="طبق منتجات وقائية ومكافحة زراعية قبل انتشار المرض/الآفة.",
            cost_egp=_money_range(
                "Prevention only cost",
                "تكلفة وقائية فقط",
                prev_low,
                prev_high,
                assumption_en="Prevention cost using contact protectants and basic sanitation.",
                assumption_ar="تكلفة وقائية باستخدام مركبات وقائية بالملامسة ونظافة أساسية.",
            ),
            budget_egp=_money_range(
                "Prevention only budget",
                "ميزانية وقائية فقط",
                prev_low,
                prev_high,
                assumption_en="Budget for preventive applications.",
                assumption_ar="ميزانية التطبيقات الوقائية.",
            ),
            expected_benefit_en="Low cost, prevents future outbreaks.",
            expected_benefit_ar="تكلفة منخفضة، يمنع التفشي المستقبلي.",
            risk_en="Will not cure existing infection.",
            risk_ar="لن يعالج الإصابة الحالية.",
            apc_gate_en="Allowed for prevention.",
            apc_gate_ar="مسموح للوقاية.",
            requires_apc_verification=False,
            requires_engineer_confirmation=False,
            source_kind="treatment_knowledge",
            source_type="generated",
            source_note_en="Best when disease is not yet active in the block.",
            source_note_ar="الأفضل عندما لا يكون المرض نشطاً بعد في البلوك.",
            farmer_wording_ar="الخيار الوقائي الأرخص قبل انتشار الآفة.",
        ),
        TreatmentModeOption(
            key="custom",
            label_en="Custom from sidebar chatbot",
            label_ar="حسب تخصيص المساعد",
            summary_en="Use a custom tailored scenario generated during chatbot interaction.",
            summary_ar="استخدم سيناريو مخصص تم توليده أثناء التفاعل مع المساعد.",
            cost_egp=_money_range(
                "Custom cost",
                "تكلفة مخصصة",
                base_low,
                base_high,
                assumption_en="Reference estimate. Use the sidebar chatbot only if you want a more exact personal calculation.",
                assumption_ar="تقدير مرجعي. استخدم مساعد الشريط الجانبي فقط إذا كنت تريد حساباً شخصياً أكثر دقة.",
            ),
            budget_egp=_money_range(
                "Custom budget",
                "ميزانية مخصصة",
                base_low,
                base_high,
                assumption_en="Custom budget from user customization.",
                assumption_ar="الميزانية المخصصة بناءً على تخصيص المستخدم.",
            ),
            expected_benefit_en="Customized to your exact farm inputs.",
            expected_benefit_ar="مخصص لمدخلات مزرعتك بالضبط.",
            risk_en="Depends on accuracy of custom inputs.",
            risk_ar="يعتمد على دقة المدخلات المخصصة.",
            apc_gate_en="Needs expert verification.",
            apc_gate_ar="يتطلب تحقق خبير.",
            requires_apc_verification=True,
            requires_engineer_confirmation=True,
            source_kind="treatment_knowledge",
            source_type="generated",
            source_note_en="Custom mode from chat.",
            source_note_ar="الوضع المخصص من المحادثة.",
            farmer_wording_ar="سيناريو مخصص من خلال المحادثة الجانبية.",
        ),
    ]


def _phase_accuracy_hint(case: CropCase, primary: PrimaryDisease) -> tuple[str, str]:
    if primary.detected and primary.certainty_level == "high":
        return (
            "If you want even tighter confirmation, add a whole-plant photo and a leaf-underside photo with the device GPS visible.",
            "لو عايز تأكيد أدق، أضف صورة للنبات كامل وصورة لظهر الورقة مع ظهور GPS الجهاز.",
        )
    if primary.detected:
        return (
            "Add a whole-plant photo, a leaf-underside photo, and the device GPS to tighten the next pass.",
            "أضف صورة للنبات كامل وصورة لظهر الورقة وGPS الجهاز لتقوية الجولة التالية.",
        )
    return (
        "The model did not reach a firm match; add clearer photos from more than one angle before buying anything.",
        "النموذج لم يصل لتطابق حاسم؛ أضف صوراً أوضح من أكثر من زاوية قبل شراء أي شيء.",
    )


def _selected_treatment_mode_key(case: CropCase, primary: PrimaryDisease, severity) -> str:
    conf_level = primary.certainty_level
    infection_level = severity.severity_label
    
    if conf_level == "low" or not primary.detected:
        return "confirm_first"
        
    if conf_level == "medium" and (infection_level == "low" or (severity.visible_affected_percent or 0) < 15.0):
        return "sanitation_only"
        
    has_confirmation = case.diagnosis.confirmation is not None
    harvest_days = case.observations.get("harvest_days_remaining")
    near_harvest_safe = harvest_days is None or harvest_days > 7
    
    if (conf_level == "high" and 
        infection_level in {"high", "severe"} and 
        case.crop.value == "tomato" and 
        has_confirmation and 
        near_harvest_safe):
        return "strongest"
        
    return "balanced"


def _parse_coords(case: CropCase) -> tuple[float, float] | None:
    lat = _observation_number(case, "device_latitude")
    lon = _observation_number(case, "device_longitude")
    if lat is not None and lon is not None:
        return lat, lon
    match = re.search(r"GPS\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", case.location or "", re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _resolve_weather(case: CropCase) -> tuple[WeatherObservation, SourceMetadata]:
    coords = _parse_coords(case)
    weather = weather_for_coords(*coords) if coords else current_weather()
    if weather is not None:
        source_type = "live"
        note_en = (
            f"Weather fetched for device GPS {coords[0]:.5f}, {coords[1]:.5f}."
            if coords
            else "Weather fetched from the configured Egypt weather coordinates."
        )
        note_ar = (
            f"تم جلب الطقس لإحداثيات GPS {coords[0]:.5f}، {coords[1]:.5f}."
            if coords
            else "تم جلب الطقس من إحداثيات الطقس المضبوطة لمصر."
        )
        return (
            weather,
            SourceMetadata(
                key="weather",
                title="Live weather from the analysis location" if coords else "Configured Egypt weather feed",
                organization="Open-Meteo",
                source_kind="weather",
                source_type=source_type,  # type: ignore[arg-type]
                url="https://api.open-meteo.com/v1/forecast",
                confidence="high",
                retrieved_on=_today_iso(),
                note_en=note_en,
                note_ar=note_ar,
            ),
        )

    weather = egypt_reference_weather()
    return (
        weather,
        SourceMetadata(
            key="weather",
            title="Egypt reference weather",
            organization="AgroVision",
            source_kind="weather",
            source_type="estimated_range",
            url=None,
            confidence="medium",
            retrieved_on=_today_iso(),
            note_en="No live weather source was available, so a clearly labelled Egypt reference weather sample was used.",
            note_ar="لم يتوفر مصدر طقس مباشر، لذلك استُخدمت عينة طقس مرجعية لمصر وموسومة بوضوح.",
        ),
    )


def _consulting_answer(
    question_key: str,
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    weather: WeatherObservation,
) -> ConsultingQuestionAnswer:
    spread = _observation_text(case, "spread_speed")
    affected = _observation_number(case, "affected_plants_percent")
    irrigation = _observation_text(case, "irrigation_method")
    previous = _observation_text(case, "previous_treatment")
    nearby = _observation_text(case, "nearby_crop_symptoms")
    harvest_days = _observation_number(case, "harvest_days_remaining")

    if question_key == "affected_part":
        answer_en = (
            "The photo mainly shows the leaf surface, so the safest next check is the lower leaves and the underside."
        )
        answer_ar = "الصورة بتوضح سطح الورقة أكثر، فافحص الأوراق السفلية والوجه السفلي للورقة كخطوة تالية."
        why_en = "Disease spread often starts low in the canopy and moves upward."
        why_ar = "المرض غالبًا يبدأ في الأوراق السفلية ثم يتحرك لأعلى."
        decision_en = "If lower leaves are hit first, sanitation matters more than waiting."
        decision_ar = "لو الورق السفلي هو الأول، فالنظافة وإزالة الأوراق المصابة مهمين أكثر من الانتظار."
        notes_en = [
            "Check the oldest leaves first.",
            "Move the inspection to the underside of the leaf.",
        ]
        notes_ar = [
            "افحص الأوراق الأقدم أولًا.",
            "انقل الفحص للوجه السفلي للورقة.",
        ]
    elif question_key == "symptom_origin":
        answer_en = (
            "The current match is consistent with symptoms starting on older leaves, which is common for tomato foliar disease."
            if primary.detected
            else "Start by checking the oldest leaves; they often show the first visible damage."
        )
        answer_ar = (
            "المطابقة الحالية متسقة مع بداية الأعراض في الأوراق الأكبر سنًا، وده شائع في أمراض أوراق الطماطم."
            if primary.detected
            else "ابدأ بفحص الأوراق الأقدم؛ هي غالبًا أول مكان تظهر فيه الأعراض."
        )
        why_en = "Knowing where symptoms start helps separate disease from a uniform stress pattern."
        why_ar = "معرفة بداية الأعراض تساعد في التفرقة بين المرض والإجهاد المنتظم."
        decision_en = "If the lower canopy leads, treat it as disease pressure."
        decision_ar = "إذا بدأت المشكلة في المجموع السفلي، تعامل معها كضغط مرضي."
        notes_en = ["Older leaves tell you the timing.", "Uniform yellowing would push the check toward stress or nutrition."]
        notes_ar = ["الأوراق القديمة تكشف التوقيت.", "الاصفرار المنتظم قد يشير إلى إجهاد أو تغذية."]
    elif question_key == "spread_speed":
        answer_en = (
            f"The pattern looks {spread or severity.severity_label}; for a tomato foliar disease, keep it under active watch today."
        )
        answer_ar = (
            f"النمط يبدو {spread or severity.severity_label}؛ ولو هو مرض ورقي في الطماطم فتابعه اليوم بشكل نشط."
        )
        why_en = "Spread speed changes whether you can monitor or need to move immediately."
        why_ar = "سرعة الانتشار تحدد هل يكفي المتابعة أو لازم التحرك فورًا."
        decision_en = "Fast spread means you should protect healthy leaves immediately."
        decision_ar = "الانتشار السريع يعني حماية الأوراق السليمة فورًا."
        notes_en = ["Quick spread raises urgency.", "Slow spread still needs sanitation."]
        notes_ar = ["الانتشار السريع يرفع الاستعجال.", "الانتشار البطيء مازال يحتاج نظافة."]
    elif question_key == "affected_plants_percent":
        share = affected if affected is not None else severity.visible_affected_percent
        answer_en = (
            f"Roughly {share:.0f}% of plants or visible canopy is affected if you use the photo estimate."
            if isinstance(share, (int, float))
            else "Count the affected plants in the block and compare them with the healthy ones before deciding the spray area."
        )
        answer_ar = (
            f"حوالي {share:.0f}% من النباتات أو من الغطاء الظاهر متأثر لو اعتمدنا تقدير الصورة."
            if isinstance(share, (int, float))
            else "عدّ النباتات المصابة في الحقل وقارنها بالسليمة قبل ما تحدد مساحة الرش."
        )
        why_en = "Area affected determines whether a small spot treatment or a block treatment is justified."
        why_ar = "نسبة الإصابة تحدد هل يكفي علاج موضعي أو لازم التعامل مع البلوك كله."
        decision_en = "Higher affected percentage pushes the plan toward whole-block action."
        decision_ar = "كلما زادت النسبة، اتجهت الخطة إلى التعامل مع البلوك كاملًا."
        notes_en = ["Use the same counting method each time.", "Do not rely on one leaf alone."]
        notes_ar = ["استخدم نفس طريقة العد كل مرة.", "لا تعتمد على ورقة واحدة فقط."]
    elif question_key == "irrigation_method":
        answer_en = (
            f"You recorded {irrigation}. That matters because splash, overhead watering, and wet leaves speed up leaf disease."
            if irrigation
            else "Record whether you use drip, flood, sprinkler, or canal water; splash and leaf wetness change the risk a lot."
        )
        answer_ar = (
            f"أنت سجلت {irrigation}. وده مهم لأن الرش على الورق أو تناثر الماء أو البلل الزائد يسرّع أمراض الأوراق."
            if irrigation
            else "سجل هل الري تنقيط أو غمر أو رش أو مياه ترعة؛ لأن تناثر الماء وبلل الورق يغيران الخطر كثيرًا."
        )
        why_en = "Water on leaves is a major spread driver for tomato foliar disease."
        why_ar = "وجود الماء على الأوراق من أهم عوامل انتشار أمراض الطماطم الورقية."
        decision_en = "If you water overhead, protect the crop more aggressively."
        decision_ar = "إذا كان الري علويًا، فالحماية تحتاج تشددًا أكبر."
        notes_en = ["Morning drip irrigation is safer.", "Keep foliage dry overnight."]
        notes_ar = ["الري الصباحي بالتنقيط أكثر أمانًا.", "حافظ على جفاف الأوراق ليلًا."]
    elif question_key == "recent_weather":
        answer_en = (
            f"Current weather is {weather.condition}, about {weather.temperature_c:.0f}°C, wind {weather.wind_kph:.0f} km/h."
            if weather
            else "Use the nearest weather record you trust; warm and humid periods usually raise fungal pressure."
        )
        answer_ar = (
            f"الطقس الحالي {weather.condition_ar}، حوالي {weather.temperature_c:.0f}°م، والرياح {weather.wind_kph:.0f} كم/س."
            if weather
            else "اعتمد على أقرب سجل طقس موثوق؛ الفترات الدافئة والرطبة ترفع الضغط الفطري عادةً."
        )
        why_en = "Weather helps separate active spread from a static symptom pattern."
        why_ar = "الطقس يساعد في التفرقة بين انتشار نشط ونمط أعراض ثابت."
        decision_en = "Wet or humid weather means the report should be treated as active pressure."
        decision_ar = "الطقس الرطب أو الندي يعني أن التقرير يُعامل كضغط مرضي نشط."
        notes_en = ["Warm humid weather raises spread risk.", "Wind can move spores and dry the leaf edge."]
        notes_ar = ["الجو الدافئ الرطب يرفع خطر الانتشار.", "الرياح تنقل الأبواغ وتجفف حواف الورقة."]
    elif question_key == "previous_treatment":
        answer_en = (
            f"You recorded: {previous}. Before repeating anything, verify the APC registration and the action group."
            if previous
            else "No prior spray was recorded in this case. Check what was used before repeating a product or action group."
        )
        answer_ar = (
            f"أنت سجلت: {previous}. قبل تكرار أي شيء، راجع تسجيل APC ومجموعة المقاومة."
            if previous
            else "لم يُسجّل رش سابق في هذه الحالة. افحص ما تم استخدامه قبل تكرار نفس المنتج أو مجموعة المقاومة."
        )
        why_en = "Repeating the same mode of action can waste money and increase resistance."
        why_ar = "تكرار نفس آلية التأثير قد يهدر المال ويزيد المقاومة."
        decision_en = "Always check the label and rotate the action group."
        decision_ar = "راجع الملصق دائمًا وبدّل مجموعة التأثير."
        notes_en = ["Never spray blind.", "Record dose and date before the next pass."]
        notes_ar = ["لا ترش بدون تحقق.", "سجل الجرعة والتاريخ قبل الرشة التالية."]
    elif question_key == "nearby_crop_symptoms":
        answer_en = (
            f"Nearby crop symptoms were recorded as {nearby}. If neighbors also show spots, treat the block as active."
            if nearby
            else "Inspect the neighboring plants and the next row; identical spots nearby usually mean the problem is spreading."
        )
        answer_ar = (
            f"تم تسجيل أعراض في المحاصيل المجاورة على أنها {nearby}. لو الجيران مصابين أيضًا، تعامل مع البلوك كإصابة نشطة."
            if nearby
            else "افحص النباتات المجاورة والصف التالي؛ تكرار نفس البقع هناك غالبًا يعني أن المشكلة تنتشر."
        )
        why_en = "Neighboring symptoms tell you if it is one plant or a field problem."
        why_ar = "أعراض الجوار توضح هل المشكلة في نبات واحد أم في الحقل."
        decision_en = "Block-level spread needs block-level action."
        decision_ar = "انتشار على مستوى البلوك يحتاج تصرفًا على مستوى البلوك."
        notes_en = ["Check wind direction.", "Mark hot spots with tape or paint."]
        notes_ar = ["افحص اتجاه الرياح.", "علّم البقع الساخنة بشريط أو دهان."]
    elif question_key == "harvest_days_remaining":
        if harvest_days is not None:
            answer_en = f"You recorded about {harvest_days:.0f} days to harvest. That means pre-harvest interval and residue safety matter."
            answer_ar = f"أنت سجلت حوالي {harvest_days:.0f} يومًا للحصاد. وده يجعل فترة الأمان وبقايا المبيد مهمة جدًا."
        else:
            answer_en = (
                "If harvest is close, choose the lowest-residue route and confirm the pre-harvest interval before any spray."
            )
            answer_ar = "إذا كان الحصاد قريبًا، فاختر أقل مسار متبقٍّ وراجع فترة الأمان قبل أي رش."
        why_en = "Harvest timing changes the treatment choice and the residue risk."
        why_ar = "موعد الحصاد يغيّر اختيار العلاج وخطر البقايا."
        decision_en = "Closer harvest means stricter safety gates."
        decision_ar = "كلما اقترب الحصاد زادت الحاجة إلى بوابات أمان أشد."
        notes_en = ["Respect the label PHI.", "Use non-chemical control first if the crop is near market."]
        notes_ar = ["التزم بفترة الأمان على الملصق.", "استخدم المكافحة غير الكيميائية أولًا لو الحصاد قريب."]
    else:
        answer_en = "Add a close leaf photo, a whole-plant photo, and the underside of the leaf so the diagnosis can be tightened."
        answer_ar = "أضف صورة قريبة للورقة وصورة للنبات كاملًا وصورة للوجه السفلي للورقة حتى تصبح المطابقة أدق."
        why_en = "More angles reduce false matches between disease and stress."
        why_ar = "الزوايا الإضافية تقلل الخلط بين المرض والإجهاد."
        decision_en = "Better photos improve the confidence band."
        decision_ar = "الصور الأفضل ترفع جودة نطاق الثقة."
        notes_en = ["Use strong daylight.", "Avoid shadow and blur."]
        notes_ar = ["استخدم ضوء النهار القوي.", "ابتعد عن الظل والاهتزاز."]

    return ConsultingQuestionAnswer(
        key=question_key,
        question_en=next((item.text for item in QUESTIONS if item.key == question_key), question_key),
        question_ar={
            "affected_part": "أي جزء متأثر: الأوراق السفلية أم العلوية أم الساق أم الجذور أم الثمار؟",
            "symptom_origin": "بدأت الأعراض من أين على النبات؟",
            "spread_speed": "هل المشكلة تنتشر ببطء أم بشكل متوسط أم سريع؟",
            "affected_plants_percent": "حوالي كم نبات من كل 100 يظهر عليهم نفس الأعراض؟",
            "irrigation_method": "هل الري غمر أم تنقيط أم رش أم مياه ترعة أم طريقة أخرى؟",
            "recent_weather": "هل كان الطقس مؤخرًا حارًا أو رطبًا أو ممطرًا أو مغبرًا أو عاصفًا؟",
            "previous_treatment": "ما الرش أو السماد المستخدم مؤخرًا وبأي جرعة؟",
            "nearby_crop_symptoms": "هل النباتات أو المحاصيل المجاورة تظهر نفس الأعراض؟",
            "harvest_days_remaining": "كم يومًا تقريبًا يفصلنا عن الحصاد؟",
            "extra_photos": "من فضلك أضف صورة قريبة للورقة وصورة للوجه السفلي وصورة للنبات كاملًا.",
        }.get(question_key, question_key),
        answer_en=answer_en,
        answer_ar=answer_ar,
        why_it_matters_en=why_en,
        why_it_matters_ar=why_ar,
        decision_change_en=decision_en,
        decision_change_ar=decision_ar,
        scenario_notes_en=notes_en,
        scenario_notes_ar=notes_ar,
        source_type="generated",
        assumption_en="Generated from the uploaded photo, the current case, and the weather context.",
        assumption_ar="تم توليدها من الصورة المرفوعة والحالة الحالية وسياق الطقس.",
    )


def _disease_information_phase(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    weather: WeatherObservation,
    info,
) -> DiseaseInformationPhase:
    disease_class = (case.disease_class or "unknown").lower()
    disease_name_en = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
    disease_name_ar = primary.name_ar or (info.name_ar if info else disease_name_en)
    leaf_symptoms_en = list(info.symptoms_en[:4]) if info and info.symptoms_en else [
        "Lower leaves show the first visible spots or yellowing.",
        "The leaf surface develops a patterned lesion rather than a uniform color change.",
    ]
    leaf_symptoms_ar = list(info.symptoms_ar[:4]) if info and info.symptoms_ar else [
        "تظهر أولًا بقع أو اصفرار على الأوراق السفلية.",
        "سطح الورقة يظهر نمطًا مرضيًا بدل تغير لون موحد.",
    ]
    fruit_symptoms_en = [
        "Fruit is usually affected indirectly through weaker leaf cover and sun exposure.",
        "Watch for small or sun-scalded fruit where the canopy has thinned.",
    ]
    fruit_symptoms_ar = [
        "الثمار تتأثر غالبًا بشكل غير مباشر بسبب ضعف الغطاء الورقي وزيادة الشمس.",
        "راقب صغر الحجم أو حروق الشمس في الثمار عند ضعف المجموع الخضري.",
    ]
    stem_symptoms_en = [
        "The stem is usually a check point rather than the first symptom area.",
        "Look for general weakening or lesions near the base if the problem is severe.",
    ]
    stem_symptoms_ar = [
        "الساق غالبًا يكون نقطة فحص أكثر من كونه أول مكان تظهر فيه الأعراض.",
        "راقب الضعف العام أو أي تقرحات قرب القاعدة إذا كانت الإصابة شديدة.",
    ]
    lookalikes_en = [item.disease for item in case.diagnosis.alternatives[:3]] or [
        "nutrient stress",
        "sunscald",
        "water stress",
    ]
    lookalikes_ar = [disease_by_name_en(item).name_ar if disease_by_name_en(item) else item for item in [alt.disease for alt in case.diagnosis.alternatives[:3]]] or [
        "إجهاد غذائي",
        "حروق شمس",
        "إجهاد مائي",
    ]
    is_bacterial = disease_class == "bacterial"
    if is_bacterial:
        spread_en = (
            f"Bacterial spot spreads through rain splash, wind-driven water, and contaminated tools moving wet tissue. "
            f"Each infected lesion can release millions of bacteria when wet. Weather source: {weather.source}."
        )
        spread_ar = (
            f"التبقع البكتيري ينتشر بالرذاذ والمطر المحمول بالرياح والأدوات الملوثة على الأنسجة الرطبة. "
            f"كل بؤرة إصابة ممكن تطلق ملايين البكتيريا عند البلل. مصدر الطقس: {weather.source}."
        )
        why_en = (
            "Bacterial spot is caused by Xanthomonas bacteria — not a fungus. "
            "Bacteria enter through stomata or wounds and spread through splash water and tools. "
            "Fungicides do not cure this disease. Sanitation, keeping leaves dry, and reducing overhead splash are the primary controls."
        )
        why_ar = (
            "التبقع البكتيري سببه بكتيريا الزانثوموناس — مش فطر. "
            "البكتيريا بتدخل من الثغور الهوائية أو الجروح، وبتنتشر بالرذاذ والأدوات الملوثة. "
            "المبيدات الفطرية لا تشفي هذا المرض. النظافة وإبقاء الأوراق جافة وتقليل الرذاذ هي الأدوات الأساسية للسيطرة."
        )
        danger_en = (
            "The real danger is leaf loss, weaker fruit fill, and block spread. "
            "Important: fungicides do not cure bacterial spot. "
            "If a copper-based or bactericide product is considered, it must be APC-registered, label-verified, and applied preventively — not as a cure after infection."
        )
        danger_ar = (
            "الخطر الحقيقي هو فقدان الورق وضعف امتلاء الثمار والانتشار على مستوى البلوك. "
            "تنبيه مهم: المبيدات الفطرية لا تشفي التبقع البكتيري. "
            "لو فُكِّر في منتج نحاسي أو مبيد بكتيري، لازم يكون مسجل في هيئة سلامة الغذاء المصرية لهذا الاستخدام، ومتحقق من الملصق، ومستخدم وقائيًا — مش علاجًا بعد الإصابة."
        )
    else:
        spread_en = (
            f"Warm, humid weather and wet leaves let {disease_name_en} move faster; the current weather source is {weather.source}."
        )
        spread_ar = (
            f"الجو الدافئ الرطب وبلل الأوراق يسرّع حركة {disease_name_ar}؛ ومصدر الطقس الحالي هو {weather.source}."
        )
        why_en = (
            "Leaf spots usually start where splash, dew, or crowded foliage keep the tissue wet long enough for spores to take hold."
        )
        why_ar = "البقع الورقية تبدأ غالبًا حيث تبقى الرطوبة أو الرذاذ أو التزاحم كافيًا ليتمكن الفطر من الاستقرار."
        danger_en = "The real danger is leaf loss, weaker fruit fill, sunscald, and a higher chance of secondary infection."
        danger_ar = "الخطر الحقيقي هو فقدان الورق، وضعف امتلاء الثمار، وحروق الشمس، وازدياد فرصة العدوى الثانوية."
    worse_weather_en = f"{weather.condition} weather at about {weather.temperature_c:.0f}°C with {weather.wind_kph:.0f} km/h wind can still raise spread pressure."
    worse_weather_ar = f"الجو {weather.condition_ar} عند حوالي {weather.temperature_c:.0f}°م ومع رياح {weather.wind_kph:.0f} كم/س قد يرفع ضغط الانتشار أيضًا."
    today_check_en = [
        "Inspect the lowest leaves first and check the underside of the spots.",
        "Count how many plants carry the same pattern.",
        "Note whether irrigation or dew keeps leaves wet overnight.",
    ]
    today_check_ar = [
        "افحص الأوراق السفلية أولًا وشاهد الوجه السفلي للبقع.",
        "عدّ عدد النباتات التي تحمل نفس النمط.",
        "لاحظ هل الري أو الندى يترك الأوراق مبللة ليلًا.",
    ]
    worsening_en = [
        "More plants showing the same spots in the next row.",
        "Yellowing moving upward through the canopy.",
        "Spots merging into larger dead patches.",
    ]
    worsening_ar = [
        "ظهور نفس البقع في نباتات أكثر بالصف التالي.",
        "انتقال الاصفرار لأعلى خلال المجموع الخضري.",
        "اندماج البقع إلى مساحات ميتة أكبر.",
    ]
    stable_en = [
        "Only old leaves are touched and new leaves stay clean.",
        "The pattern does not change after a few days of dry weather.",
        "No neighbor plants show the same spots.",
    ]
    stable_ar = [
        "الأوراق القديمة فقط متأثرة والأوراق الجديدة نظيفة.",
        "النمط لا يتغير بعد عدة أيام من الجو الجاف.",
        "النباتات المجاورة لا تظهر نفس البقع.",
    ]

    cause_type_en = {
        "fungal": "Fungal leaf disease",
        "bacterial": "Bacterial leaf disease",
        "viral": "Viral disease",
        "pest": "Pest damage",
    }.get(disease_class, "Leaf disease or disorder")
    cause_type_ar = {
        "fungal": "مرض فطري ورقي",
        "bacterial": "مرض بكتيري ورقي",
        "viral": "مرض فيروسي",
        "pest": "ضرر حشري",
    }.get(disease_class, "مرض أو اضطراب ورقي")

    irrigation_method = _normalize_text(str(case.observations.get("irrigation_method") or ""))
    if irrigation_method in {"flood", "sprinkler", "overhead"}:
        if is_bacterial:
            irrigation_conditions_en = "Overhead watering or flood irrigation splashes bacteria from infected tissue to healthy leaves — this directly raises spread pressure in bacterial disease."
            irrigation_conditions_ar = "الري من أعلى أو بالغمر يرش البكتيريا من الأنسجة المصابة إلى الأوراق السليمة — وهذا يرفع ضغط الانتشار مباشرة في الأمراض البكتيرية."
        else:
            irrigation_conditions_en = "Overhead watering or flood irrigation can wet leaves and splash spores, which raises spread pressure."
            irrigation_conditions_ar = "الري من أعلى أو الري بالغمر يمكن أن يبلل الأوراق ويرش الأبواغ، وهذا يرفع ضغط الانتشار."
    elif irrigation_method == "drip":
        irrigation_conditions_en = "Drip irrigation lowers leaf wetness, but crowded plants can still keep the canopy damp."
        irrigation_conditions_ar = "الري بالتنقيط يقلل بلل الأوراق، لكن التزاحم قد يبقي المجموع الخضري رطبًا."
    elif irrigation_method:
        irrigation_conditions_en = f"Current irrigation method: {irrigation_method}. Check whether it leaves the canopy wet or splashes soil."
        irrigation_conditions_ar = f"طريقة الري الحالية: {irrigation_method}. تحقق هل تترك المجموع الخضري رطبًا أو ترش التربة."
    else:
        irrigation_conditions_en = "Use soil-level watering and avoid long leaf wetness if you want to lower spread pressure."
        irrigation_conditions_ar = "استخدم الري عند سطح التربة وتجنب طول مدة بلل الأوراق إذا أردت خفض ضغط الانتشار."

    single_leaf = _scenario(
        "single_leaf",
        "Single-leaf signal",
        "إشارة على ورقة واحدة",
        "The photo matches a disease pattern on the visible leaf, but the plant still needs an in-person check.",
        "الصورة تطابق نمطًا مرضيًا على الورقة الظاهرة، لكن النبات مازال يحتاج فحصًا ميدانيًا.",
        [
            _section("What to do today", "ماذا تفعل اليوم", today_check_en, today_check_ar),
            _section("Why it matters", "لماذا هذا مهم", ["A small spot can still move upward if the canopy stays wet."], ["البقعة الصغيرة قد تصعد لأعلى إذا ظل المجموع الخضري رطبًا."]),
        ],
    )
    spread_block = _scenario(
        "spread_block",
        "Block spread",
        "انتشار في البلوك",
        "If the same spotting appears on nearby plants, treat it as block-level disease pressure.",
        "إذا ظهرت نفس البقع في النباتات المجاورة، فتعامل معها كضغط مرضي على مستوى البلوك.",
        [
            _section("Check nearby rows", "افحص الصفوف المجاورة", ["Walk the next row and count matched plants."], ["امشِ في الصف التالي وعدّ النباتات المطابقة."]),
            _section("Why it matters", "لماذا هذا مهم", ["Block spread means the action plan must cover more than one plant."], ["انتشار البلوك يعني أن خطة العمل لازم تشمل أكثر من نبات واحد."]),
        ],
    )
    mixup = _scenario(
        "mixup",
        "Possible lookalike",
        "احتمال تشابه",
        "If the leaf looks uniformly pale or heat-stressed, the disease match may be sharing the picture with stress symptoms.",
        "إذا كانت الورقة شاحبة بشكل موحد أو تبدو متأثرة بالحرارة، فقد تكون المطابقة المرضية مختلطة مع أعراض إجهاد.",
        [
            _section("Lookalike check", "فحص التشابه", lookalikes_en[:3], lookalikes_ar[:3]),
            _section("What to verify", "ما الذي تتحقق منه", ["Compare the leaf with irrigation and recent spray history."], ["قارن الورقة مع الري وسجل الرش الأخير."]),
        ],
    )

    # Only include varieties that genuinely match the detected disease.
    # For bacterial spot there are no disease-specific resistance codes,
    # so require_disease_match=True returns an empty list rather than
    # falling back to generic tomato varieties.
    resistant_variety_options = _resistant_variety_options(case, primary, info, require_disease_match=True)

    if is_bacterial:
        higher_accuracy_hint_en = (
            "Bacterial spot has no curative spray. If you consider a copper-based or bactericide product, "
            "verify it is registered with Egypt's APC for this specific use and read the full label. "
            "Priority actions: remove infected leaves, reduce water splash, switch to drip irrigation if possible, and keep leaves dry."
        )
        higher_accuracy_hint_ar = (
            "التبقع البكتيري ليس له رش علاجي. لو فكرت في منتج نحاسي أو مبيد بكتيري، "
            "تأكد إنه مسجل في هيئة سلامة الغذاء المصرية لهذا الاستخدام تحديدًا واقرأ الملصق كامل. "
            "الأولويات: أزل الأوراق المصابة، وقلل رذاذ الماء، وحوِّل للري بالتنقيط لو أمكن، وابقي الأوراق جافة."
        )
    else:
        higher_accuracy_hint_en = ""
        higher_accuracy_hint_ar = ""

    return DiseaseInformationPhase(
        disease_name_en=disease_name_en,
        disease_name_ar=disease_name_ar,
        cause_type_en=cause_type_en,
        cause_type_ar=cause_type_ar,
        meaning_en=info.summary_en if info else "The uploaded photo matches a tomato leaf disease pattern and should be treated as an active field screening result.",
        meaning_ar=info.summary_ar if info else "الصورة المرفوعة تطابق نمط مرض ورقي في الطماطم ويجب التعامل معها كفحص حقلي نشط.",
        leaf_symptoms_en=leaf_symptoms_en,
        leaf_symptoms_ar=leaf_symptoms_ar,
        fruit_symptoms_en=fruit_symptoms_en,
        fruit_symptoms_ar=fruit_symptoms_ar,
        stem_symptoms_en=stem_symptoms_en,
        stem_symptoms_ar=stem_symptoms_ar,
        spread_en=spread_en,
        spread_ar=spread_ar,
        why_it_appears_en=why_en,
        why_it_appears_ar=why_ar,
        irrigation_conditions_en=irrigation_conditions_en,
        irrigation_conditions_ar=irrigation_conditions_ar,
        worse_weather_en=worse_weather_en,
        worse_weather_ar=worse_weather_ar,
        lookalikes_en=lookalikes_en,
        lookalikes_ar=lookalikes_ar,
        danger_en=danger_en,
        danger_ar=danger_ar,
        top_candidates=_candidate_insights(case, primary),
        resistant_varieties=resistant_variety_options,
        today_check_en=today_check_en,
        today_check_ar=today_check_ar,
        worsening_en=worsening_en,
        worsening_ar=worsening_ar,
        stable_en=stable_en,
        stable_ar=stable_ar,
        scenario_cases=[single_leaf, spread_block, mixup],
        higher_accuracy_hint_en=higher_accuracy_hint_en,
        higher_accuracy_hint_ar=higher_accuracy_hint_ar,
    )


def _protection_phase(case: CropCase, primary: PrimaryDisease, severity) -> ProtectionPhase:
    name_en = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
    name_ar = primary.name_ar or name_en
    base_actions_en = list(case.protection_plan[:4]) or [
        "Remove infected lower leaves and keep the canopy open.",
        "Water at the soil line instead of wetting the leaves.",
        "Clean tools and hands between suspect plants.",
    ]
    base_actions_ar = [
        "أزل الأوراق السفلية المصابة وافتح المجموع الخضري للتهوية.",
        "اروِ عند سطح التربة بدل بلّ الأوراق.",
        "نظّف الأدوات واليدين بين النباتات المشتبه بها.",
    ]
    avoid_en = [
        "Do not work the crop while the leaves are wet.",
        "Do not keep infected debris under the plants.",
        "Do not repeat the same spray pattern without checking the label.",
    ]
    avoid_ar = [
        "لا تعمل في الحقل والورق مبلل.",
        "لا تترك المخلفات المصابة تحت النباتات.",
        "لا تكرر نفس نمط الرش بدون مراجعة الملصق.",
    ]
    escalate_en = [
        "Escalate to an agronomist if the same spots appear on new leaves within a few days.",
        "Escalate if the block spread is moving row by row.",
    ]
    escalate_ar = [
        "ارفع الحالة لمهندس زراعي إذا ظهرت نفس البقع على أوراق جديدة خلال أيام قليلة.",
        "ارفع الحالة إذا كان الانتشار يتحرك صفًا بعد صف.",
    ]
    home_garden = _scenario(
        "home_garden",
        "Home garden",
        "حديقة منزلية",
        "Use hand sanitation and leaf removal first; the garden scale usually does not justify a broad spray.",
        "ابدأ بالنظافة اليدوية وإزالة الأوراق؛ حجم الحديقة غالبًا لا يبرر رشًا واسعًا.",
        [
            _section("Immediate action", "إجراء فوري", base_actions_en, base_actions_ar),
            _section("Avoid", "تجنب", avoid_en, avoid_ar),
        ],
    )
    open_field = _scenario(
        "open_field",
        "Open-field block",
        "حقل مكشوف",
        "Open-field disease is a block problem: clean rows, manage splash, and watch wind movement.",
        "مرض الحقل المكشوف مشكلة على مستوى البلوك: نظف الصفوف، وتحكم في الرذاذ، وراقب حركة الرياح.",
        [
            _section("Field action", "إجراء حقلي", ["Mark the hot spots and move sanitation row by row."], ["حدد البؤر الساخنة ونفذ النظافة صفًا بعد صف."]),
            _section("Avoid", "تجنب", ["Avoid moving from infected rows to clean rows without cleaning tools."], ["لا تنتقل من الصفوف المصابة إلى السليمة بدون تنظيف الأدوات."]),
        ],
    )
    greenhouse = _scenario(
        "greenhouse",
        "Greenhouse",
        "صوبة",
        "In a greenhouse, humidity control is part of protection, not an extra step.",
        "في الصوبة، التحكم في الرطوبة جزء من الحماية وليس خطوة إضافية.",
        [
            _section("Climate action", "إجراء مناخي", ["Vent early, water in the morning, and avoid condensation overnight."], ["هَوِّ باكرًا، واروِ صباحًا، وتجنب تكثف الماء ليلًا."]),
            _section("Avoid", "تجنب", ["Do not crowd plants or keep wet foliage under the cover."], ["لا تزاحم النباتات ولا تترك الأوراق مبللة تحت الغطاء."]),
        ],
    )
    return ProtectionPhase(scenario_cases=[home_garden, open_field, greenhouse])


def _treatment_phase(case: CropCase) -> TreatmentPhase:
    disease_class = case.disease_class or "unknown"
    non_chemical = list(case.treatment_plan.non_chemical) or [
        "Remove the worst leaves and infected debris first.",
        "Keep the crop dry and airy.",
    ]
    chemical = list(case.treatment_plan.chemical_category_if_needed)
    safety = list(case.treatment_plan.safety_notes)
    if not chemical:
        chemical = ["Chemical treatment is locked until the diagnosis is confident enough and the APC label is verified."]

    non_chemical_case = _scenario(
        "non_chemical_first",
        "Non-chemical first",
        "الأولوية للمكافحة غير الكيميائية",
        "Start with sanitation and airflow while the report is being confirmed.",
        "ابدأ بالنظافة والتهوية بينما يتم تأكيد التقرير.",
        [
            _section("Non-chemical path", "المسار غير الكيميائي", non_chemical, non_chemical),
            _section("Safety gate", "بوابة الأمان", safety, safety),
        ],
    )
    chemical_case = _scenario(
        "chemical_gate",
        "Chemical gate",
        "بوابة الكيميائي",
        "Use a chemical category only after confirmation, registration checks, and PHI review.",
        "استخدم أي فئة كيميائية فقط بعد التأكيد ومراجعة التسجيل وفترة الأمان.",
        [
            _section("Chemical path", "المسار الكيميائي", chemical, chemical),
            _section("Safety gate", "بوابة الأمان", safety, safety),
        ],
    )
    no_cure_case = _scenario(
        "no_cure_route",
        "No-cure route",
        "مسار بلا علاج كيميائي",
        "When the disease class has no curative spray, roguing and quarantine matter more than product choice.",
        "عندما لا يوجد رش علاجي للمرض، تصبح الإزالة والحجر أهم من اختيار المنتج.",
        [
            _section("Non-chemical path", "المسار غير الكيميائي", non_chemical, non_chemical),
            _section("What to avoid", "ما الذي يجب تجنبه", ["Do not keep chasing the same product if the disease class says the spray will not cure it."], ["لا تكرر نفس المنتج إذا كان المرض من النوع الذي لا يشفيه الرش."]),
        ],
    )
    if disease_class == "viral":
        scenario_cases = [no_cure_case, non_chemical_case, chemical_case]
    else:
        scenario_cases = [non_chemical_case, chemical_case, no_cure_case]
    return TreatmentPhase(scenario_cases=scenario_cases)


def _cost_forecast_phase(area_range_cases) -> CostForecastPhase:
    provider_priority = [
        "CAPMAS tomato production bulletins for yield",
        "Egypt tomato farmgate reference price",
        "APC pesticide registration database",
        "Open-Meteo live weather or Egypt reference weather",
        "AgroVision treatment rules and fallback assumptions",
    ]
    return CostForecastPhase(area_range_cases=area_range_cases, provider_priority=provider_priority)


def _conclusion_phase(case: CropCase, primary: PrimaryDisease, severity, cost_estimate: CostEstimate) -> ConclusionRecommendationPhase:
    disease_name_en = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
    disease_name_ar = primary.name_ar or disease_name_en
    low_confidence = primary.certainty_level == "low" or not primary.detected
    confirmed = case.diagnosis.confirmation is not None
    today = _section(
        "Today",
        "اليوم",
        [
            "Inspect the plant in person and remove the most affected lower leaves.",
            "Keep the canopy dry and open.",
            "Save a fresh photo if the pattern changes.",
        ],
        [
            "افحص النبات ميدانيًا وأزل أكثر الأوراق السفلية إصابة.",
            "حافظ على جفاف المجموع الخضري وفتحته للهواء.",
            "احفظ صورة جديدة إذا تغيّر النمط.",
        ],
    )
    next_days = _section(
        "Next 3 to 7 days",
        "خلال 3 إلى 7 أيام",
        [
            "Re-check the nearest rows and compare the spread.",
            "Review irrigation and weather against the symptom pattern.",
            "Use a registered treatment only after the label and diagnosis are clear.",
        ],
        [
            "أعد فحص الصفوف القريبة وقارن الانتشار.",
            "راجع الري والطقس مقابل نمط الأعراض.",
            "استخدم أي معاملة مسجلة فقط بعد وضوح الملصق والتشخيص.",
        ],
    )
    call_expert = _section(
        "Call an expert when",
        "اتصل بخبير عندما",
        [
            "The same pattern reaches new healthy leaves.",
            "You are near harvest and a spray would affect residue safety.",
            "The diagnosis stays low-confidence after a new photo.",
        ],
        [
            "يصل نفس النمط إلى أوراق سليمة جديدة.",
            "تكون قريبًا من الحصاد ويؤثر الرش على الأمان المتبقي.",
            "يبقى التشخيص منخفض الثقة بعد صورة جديدة.",
        ],
    )
    action_plan = [today, next_days, call_expert]
    if confirmed:
        action_plan.insert(
            1,
            _section(
                "Confirmation",
                "التأكيد",
                [f"The disease is recorded from submitted Egyptian evidence: {case.diagnosis.confirmation.organization}."],
                [f"المرض مسجل من دليل مصري مُقدم: {case.diagnosis.confirmation.organization}."],
                confidence="high",
            ),
        )
    elif low_confidence:
        action_plan.insert(
            1,
            _section(
                "Photo confidence",
                "ثقة الصورة",
                ["The match is real but low-confidence, so keep the wording conservative and confirm in person."],
                ["المطابقة حقيقية لكنها منخفضة الثقة، لذا حافظ على التحفظ وأكد ميدانيًا."],
                confidence="medium",
            ),
        )

    scenario_recommendations = [
        _scenario(
            "act_now",
            "Act now",
            "تحرك الآن",
            f"Use this when the disease match is strong and the spread pressure is already visible for {disease_name_en}.",
            f"استخدم هذا عندما تكون المطابقة قوية وضغط الانتشار ظاهرًا بالفعل في {disease_name_ar}.",
            [
                _section("What to do", "ماذا تفعل", ["Sanitation first, then the registered path if the diagnosis is clear."], ["النظافة أولًا ثم المسار المسجل إذا كان التشخيص واضحًا."]),
            ],
        ),
        _scenario(
            "verify_first",
            "Verify first",
            "أكد أولًا",
            "Use this when the match is real but confidence is not high enough for chemical action.",
            "استخدم هذا عندما تكون المطابقة حقيقية لكن الثقة ليست عالية بما يكفي للإجراء الكيميائي.",
            [
                _section("What to do", "ماذا تفعل", ["Take a better photo and check the plant in person before buying products."], ["التقط صورة أفضل وافحص النبات ميدانيًا قبل شراء أي منتجات."]),
            ],
        ),
        _scenario(
            "economics_check",
            "Economics check",
            "فحص اقتصادي",
            "Use this when the cost forecast is borderline and the decision should be based on the actual area and price.",
            "استخدم هذا عندما تكون التكاليف على الحافة ويجب أن يستند القرار إلى المساحة والسعر الفعلي.",
            [
                _section("What to do", "ماذا تفعل", ["Compare the reference forecast with your real area and local price before spending."], ["قارن التوقع المرجعي بمساحتك وسعرك المحلي قبل أي صرف."]),
            ],
        ),
    ]
    if severity.severity_label in {"high", "severe"}:
        summary = (
            f"{disease_name_en} is the lead match and the visible damage is already high, so the crop should be treated as active pressure."
        )
    elif low_confidence:
        summary = (
            f"{disease_name_en} is the lead match, but the photo confidence is low, so the report stays conservative and asks for a field check."
        )
    else:
        summary = (
            f"{disease_name_en} is the lead match and the plan below is ready for a normal field response."
        )
    action_text = (
        f"Treat the crop now with the protection and safety steps above, then confirm the result in person."
        if not low_confidence or confirmed
        else "Use the protection steps now, but keep the chemical gate closed until the photo is confirmed in the field."
    )
    if cost_estimate.basis == "reference_estimate":
        action_text += " The cost forecast is reference-based until a live market quote or farmer-entered numbers replace it."
    return ConclusionRecommendationPhase(
        scenario_recommendations=scenario_recommendations,
        action_plan=action_plan,
    )


def _treatment_phase(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    cost_estimate: CostEstimate,
    area_range_cases,
) -> TreatmentPhase:
    disease_class = (case.disease_class or "unknown").lower()
    disease_name_en = primary.name_en.lower()
    
    is_spider_mite = "mite" in disease_name_en or disease_class == "insect"
    is_viral = disease_class == "viral" or "virus" in disease_name_en
    is_bacterial = disease_class == "bacterial" or "bacteri" in disease_name_en
    
    # 1. Build dynamic paths
    if is_spider_mite:
        confirm_en = [
            "Inspect the underside of leaves for tiny moving mites, fine webbing, or light stippling.",
            "Retake a close-up photo of the leaf underside in bright, indirect light.",
            "Best when visual confidence is low to avoid unnecessary treatment."
        ]
        confirm_ar = [
            "افحص الجانب السفلي للأوراق بحثًا عن عنكبوت صغير يتحرك، خيوط رفيعة، أو تنقيط فاتح.",
            "صوّر صورة قريبة لظهر الورقة في إضاءة واضحة وغير مباشرة.",
            "الخيار الأفضل عند انخفاض ثقة التعرف لتجنب العلاج غير الضروري."
        ]
        
        sanitation_en = [
            "Remove and safely destroy badly affected leaves immediately.",
            "Reduce dust on plants (dust encourages spider mite reproduction).",
            "Avoid plant stress by maintaining irrigation consistency.",
            "Check nearby plants to map and slow the infestation spread."
        ]
        sanitation_ar = [
            "أزل الأوراق المصابة بشدة وتخلص منها بأمان فوراً.",
            "قلل الغبار على النباتات (الغبار بيشجع تكاثر العنكبوت الأحمر).",
            "تجنب عطش النباتات وحافظ على انتظام الري.",
            "افحص النباتات المجاورة لتحديد مسار الإصابة وإبطائها."
        ]
        
        physical_en = [
            "Spray water on the underside of leaves (fine mist) if appropriate for a small home garden.",
            "Note: water spray has strict limits and is not a cure for large field infestations."
        ]
        physical_ar = [
            "رش الماء على الجانب السفلي للأوراق (رذاذ خفيف) إذا كان ذلك مناسباً لحديقة المنزل الصغيرة.",
            "ملحوظة: رش الماء له حدود واضحة وليس علاجاً للإصابات الحقلية الواسعة."
        ]
        
        biological_en = [
            "Deploy biological or low-risk support (such as predatory mites) if locally verified and available.",
            "Do not purchase unverified products; check local availability first."
        ]
        biological_ar = [
            "استخدم الأعداء الحيوية أو المركبات خفيفة المخاطر (مثل المفترسات) إذا كانت مسجلة ومتوفرة محلياً.",
            "لا تشترِ منتجات غير معتمدة؛ تأكد من توافرها محلياً أولاً."
        ]
        
        chemical_en = [
            "Chemical/miticide path is locked until APC registration and label are verified.",
            "Do not use or recommend product names without official registration check.",
            "Always follow PPE (personal protective equipment), PHI (pre-harvest interval), REI (re-entry interval), and label dose warnings.",
            "Note: Spider mites are pests (mites), not fungus, so they require miticides, not fungicides."
        ]
        chemical_ar = [
            "المسار الكيميائي (مبيد أكاروسي) مغلق حتى التحقق من تسجيل APC ومراجعة الملصق.",
            "لا تستخدم أو توصِ بأسماء تجارية بدون التحقق من التسجيل الرسمي.",
            "التزم بأدوات الحماية (PPE)، فترة الأمان قبل الحصاد (PHI)، فترة منع الدخول (REI)، والجرعة المدونة.",
            "ملحوظة: العنكبوت الأحمر آفة (أكاروس) وليس فطراً، وبالتالي يحتاج مبيد أكاروسي وليس مبيداً فطرياً."
        ]
        
    elif is_viral:
        confirm_en = ["Verify symptom details and crop history; viral diseases cannot be cured by spraying."]
        confirm_ar = ["تأكد من تفاصيل الأعراض وتاريخ المحصول؛ الأمراض الفيروسية لا تشفى بالرش."]
        sanitation_en = [
            "Remove and destroy infected plants immediately to prevent vector spread.",
            "Clean tools thoroughly before moving to healthy plants."
        ]
        sanitation_ar = [
            "أزل النباتات المصابة وتخلص منها فوراً لمنع انتشار العدوى بالناقل.",
            "طهّر الأدوات جيداً قبل الانتقال للنباتات السليمة."
        ]
        physical_en = ["Vector control: use insect nets and physical traps if greenhouse-grown."]
        physical_ar = ["مكافحة الناقل: استخدم شاش حشرات ومصايد فيزيائية إذا كنت تزرع في صوبة."]
        biological_en = ["Manage vector pests (like whiteflies or aphids) using approved biological controls."]
        biological_ar = ["كافح الحشرات الناقلة (مثل الذبابة البيضاء أو المن) بالوسائل الحيوية المعتمدة."]
        chemical_en = [
            "No curative chemical spray exists for plant viruses.",
            "Fungicides or bactericides are completely ineffective.",
            "Chemical treatment is limited to registered vector control under expert guidance."
        ]
        chemical_ar = [
            "لا يوجد أي رش كيميائي شافي للفيروسات النباتية.",
            "المبيدات الفطرية أو البكتيرية غير مفيدة تماماً في هذه الحالة.",
            "العلاج الكيميائي يقتصر على مكافحة الحشرات الناقلة المسجلة بتوجيه من خبير."
        ]
        
    elif is_bacterial:
        confirm_en = ["Verify symptoms under dry conditions; ensure they are bacterial spots/wilts, not fungal."]
        confirm_ar = ["تأكد من الأعراض في ظروف جافة؛ تحقق أنها تبقعات أو ذبول بكتيري وليس فطرياً."]
        sanitation_en = [
            "Remove affected tissue only when plants are dry; disinfect pruning tools.",
            "Avoid overhead irrigation to reduce splash dispersal."
        ]
        sanitation_ar = [
            "أزل الأجزاء المصابة فقط عندما يكون النبات جافاً؛ طهّر أدوات التقليم.",
            "تجنب الري العلوي لتقليل انتشار البكتيريا مع رذاذ الماء."
        ]
        physical_en = ["Ensure good field drainage and avoid working in wet fields."]
        physical_ar = ["تأكد من الصرف الجيد للحقل وتجنب العمل أو التقليم أثناء بلل النباتات."]
        biological_en = ["Use registered bio-bactericides if available and officially verified."]
        biological_ar = ["استخدم مبيدات بكتيرية حيوية مسجلة إذا كانت متوفرة ومعتمدة رسمياً."]
        chemical_en = [
            "Bactericide/copper-style pathway is locked until officially allowed and verified.",
            "Do not treat bacterial disease like fungi; standard fungicides will not work.",
            "Follow strict PPE, PHI, and REI label requirements for registered copper/bactericide sprays."
        ]
        chemical_ar = [
            "مسار المركبات النحاسية/البكتيرية مغلق حتى يتم السماح والتحقق رسمياً.",
            "لا تعامل الأمراض البكتيرية كالفطريات؛ المبيدات الفطرية المعتادة لن تفيد.",
            "اتبع اشتراطات الملصق لمركبات النحاس أو المبيدات البكتيرية المسجلة (PPE، PHI، REI)."
        ]
        
    else:
        confirm_en = ["Verify if symptoms are fungal lesions (spots, blights, mildews) before buying fungicides."]
        confirm_ar = ["تأكد إذا كانت الأعراض بقعاً فطرية أو لفحات أو بياض قبل شراء مبيدات فطريات."]
        sanitation_en = [
            "Remove heavily affected leaves and clear fallen debris to lower spore pressure.",
            "Keep the canopy dry and open to airflow."
        ]
        sanitation_ar = [
            "أزل الأوراق شديدة الإصابة ونظف البقايا المتساقطة لتقليل ضغط الجراثيم الفطرية.",
            "حافظ على جفاف المجموع الخضري وفتحته للتهوية."
        ]
        physical_en = ["Use drip irrigation instead of sprinkler/flood to prevent wet foliage."]
        physical_ar = ["استخدم الري بالتنقيط بدلاً من الري بالرش أو الغمر لمنع بلل الأوراق."]
        biological_en = ["Apply registered bio-fungicides if verified for prevention in organic systems."]
        biological_ar = ["استخدم مبيدات فطريات حيوية مسجلة إذا تم التحقق منها للوقاية."]
        chemical_en = [
            "Fungicide path is locked until disease identification and APC registration are verified.",
            "Follow PPE, PHI, REI, and dose guidelines on the official registered label.",
            "Rotate chemical classes to prevent fungal resistance development."
        ]
        chemical_ar = [
            "مسار مبيدات الفطريات مغلق حتى التحقق من هوية المرض وتسجيل APC.",
            "التزم بإرشادات الملصق الرسمي المسجل (أدوات الحماية، فترة الأمان قبل الحصاد، وفترة منع الدخول).",
            "قم بتدوير المجموعات الكيميائية لمنع نشوء مقاومة لدى الفطريات."
        ]

    selected_mode_key = _selected_treatment_mode_key(case, primary, severity)
    treatment_options = _treatment_mode_options(case, primary, severity, cost_estimate, area_range_cases)

    confirm_first_case = _scenario(
        "confirm_first",
        "Confirm first",
        "أكد أولاً",
        "Hold chemical spending and confirm the diagnosis in the field or with a lab.",
        "أوقف الصرف الكيميائي وأكد التشخيص ميدانياً أو معملياً.",
        [
            _section("What to do", "ما الذي تفعله", confirm_en, confirm_ar),
        ],
    )
    sanitation_only_case = _scenario(
        "sanitation_only",
        "Sanitation only",
        "تنظيف فقط",
        "Rogue badly affected tissue, keep the canopy dry, and re-check before spending.",
        "أزل الأجزاء الشديدة، وحافظ على جفاف المجموع الخضري، وأعد الفحص قبل الصرف.",
        [
            _section("Sanitation & physical", "النظافة والرش الفيزيائي", sanitation_en + physical_en, sanitation_ar + physical_ar),
        ],
    )
    balanced_case = _scenario(
        "balanced",
        "Balanced program",
        "برنامج متوازن",
        "Use the reference treatment program that fits the current severity and economics.",
        "استخدم برنامج العلاج المرجعي المناسب لشدة الحالة والاقتصاد الحالي.",
        [
            _section("Sanitation & physical", "النظافة والرش الفيزيائي", sanitation_en + physical_en, sanitation_ar + physical_ar),
            _section("Biological/low-risk", "المسار الحيوي خفيف المخاطر", biological_en, biological_ar),
            _section("Chemical path", "المسار الكيميائي", chemical_en, chemical_ar),
        ],
    )
    strongest_case = _scenario(
        "strongest",
        "Strongest program",
        "البرنامج الأقوى",
        "Use the broader, more expensive program when the crop is clearly under heavy pressure.",
        "استخدم البرنامج الأوسع والأغلى عندما يكون الضغط المرضي واضحاً وشديداً.",
        [
            _section("Intense sanitation", "النظافة المكثفة", sanitation_en, sanitation_ar),
            _section("Biological control", "المكافحة الحيوية", biological_en, biological_ar),
            _section("Chemical path", "المسار الكيميائي", chemical_en, chemical_ar),
        ],
    )
    no_cure_case = _scenario(
        "no_cure_route",
        "No-cure route",
        "مسار بلا علاج كيميائي",
        "When the disease class has no curative spray, roguing and quarantine matter more than product choice.",
        "عندما لا يوجد رش علاجي للمرض، تصبح الإزالة والحجر أهم من اختيار المنتج.",
        [
            _section("Non-chemical path", "المسار غير الكيميائي", sanitation_en, sanitation_ar),
            _section("What to avoid", "ما الذي يجب تجنبه", ["Do not spray chemicals; it will not cure the virus."], ["لا ترش كيماويات؛ لن تشفي الفيروس."]),
        ],
    )

    if disease_class == "viral":
        scenario_cases = [no_cure_case, confirm_first_case, sanitation_only_case]
    else:
        scenario_cases = [confirm_first_case, sanitation_only_case, balanced_case, strongest_case]

    hint_en, hint_ar = _phase_accuracy_hint(case, primary)
    return TreatmentPhase(
        scenario_cases=scenario_cases,
        treatment_options=treatment_options,
        selected_mode_key=selected_mode_key,
        higher_accuracy_hint_en=hint_en,
        higher_accuracy_hint_ar=hint_ar,
    )


def _cost_forecast_phase(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    cost_estimate: CostEstimate,
    area_range_cases,
    treatment_options: list[TreatmentModeOption],
    selected_mode_key: str,
) -> CostForecastPhase:
    provider_priority = [
        "CAPMAS tomato production bulletins for yield",
        "Egypt tomato farmgate reference price",
        "APC pesticide registration database",
        "Open-Meteo live weather or Egypt reference weather",
        "AgroVision treatment rules and fallback assumptions",
    ]
    if cost_estimate.basis == "farmer_inputs":
        hint_en = "The forecast already uses the numbers entered for this case; add a local quote if you want to cross-check them."
        hint_ar = "التوقع يستخدم الأرقام المدخلة بالفعل في الحالة؛ أضف عرض سعر محلياً لو أردت المراجعة."
    else:
        hint_en = "Add the actual treated area and a local product quote to tighten the cost comparison."
        hint_ar = "أضف المساحة الفعلية وعرض سعر محلي للمنتج لتضييق مقارنة التكلفة."
    return CostForecastPhase(
        area_range_cases=area_range_cases,
        provider_priority=provider_priority,
        treatment_comparison=treatment_options,
        selected_mode_key=selected_mode_key,
        higher_accuracy_hint_en=hint_en,
        higher_accuracy_hint_ar=hint_ar,
    )


def _conclusion_phase(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    cost_estimate: CostEstimate,
    treatment_options: list[TreatmentModeOption],
    selected_mode_key: str,
) -> ConclusionRecommendationPhase:
    disease_name_en = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
    disease_name_ar = primary.name_ar or disease_name_en
    low_confidence = primary.certainty_level == "low" or not primary.detected
    confirmed = case.diagnosis.confirmation is not None
    selected_mode = next((item for item in treatment_options if item.key == selected_mode_key), None)
    if selected_mode:
        best_balanced_choice_en = f"{selected_mode.label_en}: {selected_mode.summary_en}"
        best_balanced_choice_ar = f"{selected_mode.label_ar}: {selected_mode.summary_ar}"
        comparison_summary_en = (
            f"{selected_mode.label_en} is the current default because it fits the confidence level and the cost band."
        )
        comparison_summary_ar = (
            f"{selected_mode.label_ar} هو الاختيار الافتراضي الحالي لأنه يناسب مستوى الثقة ونطاق التكلفة."
        )
        action_mode_section = _section(
            "Selected treatment mode",
            "وضع العلاج المختار",
            [selected_mode.summary_en, selected_mode.expected_benefit_en, selected_mode.apc_gate_en],
            [selected_mode.summary_ar, selected_mode.expected_benefit_ar, selected_mode.apc_gate_ar],
            confidence="medium",
            assumption_en=selected_mode.source_note_en,
            assumption_ar=selected_mode.source_note_ar,
        )
    else:
        best_balanced_choice_en = "No treatment mode was selected."
        best_balanced_choice_ar = "لم يتم اختيار وضع علاج."
        comparison_summary_en = "No mode comparison is available yet."
        comparison_summary_ar = "لا توجد مقارنة أوضاع متاحة بعد."
        action_mode_section = None

    today = _section(
        "Today",
        "اليوم",
        [
            "Inspect the plant in person and remove the most affected lower leaves.",
            "Keep the canopy dry and open.",
            "Save a fresh photo if the pattern changes.",
        ],
        [
            "افحص النبات ميدانياً وأزل أكثر الأوراق السفلية إصابة.",
            "حافظ على جفاف المجموع الخضري وفتحته للهواء.",
            "احفظ صورة جديدة إذا تغيّر النمط.",
        ],
    )
    next_days = _section(
        "Next 3 to 7 days",
        "خلال 3 إلى 7 أيام",
        [
            "Re-check the nearest rows and compare the spread.",
            "Review irrigation and weather against the symptom pattern.",
            "Use a registered treatment only after the label and diagnosis are clear.",
        ],
        [
            "أعد فحص الصفوف القريبة وقارن الانتشار.",
            "راجع الري والطقس مقابل نمط الأعراض.",
            "استخدم أي معاملة مسجلة فقط بعد وضوح الملصق والتشخيص.",
        ],
    )
    call_expert = _section(
        "Call an expert when",
        "اتصل بخبير عندما",
        [
            "The same pattern reaches new healthy leaves.",
            "You are near harvest and a spray would affect residue safety.",
            "The diagnosis stays low-confidence after a new photo.",
        ],
        [
            "يصل نفس النمط إلى أوراق سليمة جديدة.",
            "تكون قريباً من الحصاد ويؤثر الرش على أمان المتبقي.",
            "يبقى التشخيص منخفض الثقة بعد صورة جديدة.",
        ],
    )

    action_plan = [today, next_days, call_expert]
    if action_mode_section:
        action_plan.insert(1, action_mode_section)
    if confirmed:
        action_plan.insert(
            1,
            _section(
                "Confirmation",
                "التأكيد",
                [f"The disease is recorded from submitted Egyptian evidence: {case.diagnosis.confirmation.organization}."],
                [f"المرض مسجل من دليل مصري مقدم: {case.diagnosis.confirmation.organization}."],
                confidence="high",
            ),
        )
    elif low_confidence:
        action_plan.insert(
            1,
            _section(
                "Photo confidence",
                "ثقة الصورة",
                ["The match is real but low-confidence, so keep the wording conservative and confirm in person."],
                ["المطابقة حقيقية لكنها منخفضة الثقة، لذا حافظ على التحفظ وأكد ميدانياً."],
                confidence="medium",
            ),
        )

    scenario_recommendations = [
        _scenario(
            "act_now",
            "Act now",
            "تحرك الآن",
            f"Use this when the disease match is strong and the spread pressure is already visible for {disease_name_en}.",
            f"استخدم هذا عندما تكون المطابقة قوية وضغط الانتشار ظاهراً بالفعل في {disease_name_ar}.",
            [
                _section(
                    "What to do",
                    "ما الذي تفعله",
                    ["Sanitation first, then the registered path if the diagnosis is clear."],
                    ["النظافة أولاً ثم المسار المسجل إذا كان التشخيص واضحاً."],
                ),
            ],
        ),
        _scenario(
            "verify_first",
            "Verify first",
            "أكد أولاً",
            "Use this when the match is real but confidence is not high enough for chemical action.",
            "استخدم هذا عندما تكون المطابقة حقيقية لكن الثقة ليست عالية بما يكفي للإجراء الكيميائي.",
            [
                _section(
                    "What to do",
                    "ما الذي تفعله",
                    ["Take a better photo and check the plant in person before buying products."],
                    ["التقط صورة أفضل وافحص النبات ميدانياً قبل شراء أي منتجات."],
                ),
            ],
        ),
        _scenario(
            "economics_check",
            "Economics check",
            "فحص اقتصادي",
            "Use this when the cost forecast is borderline and the decision should be based on the actual area and price.",
            "استخدم هذا عندما تكون التكاليف على الحافة ويجب أن يعتمد القرار على المساحة والسعر الفعليين.",
            [
                _section(
                    "What to do",
                    "ما الذي تفعله",
                    ["Compare the reference forecast with your real area and local price before spending."],
                    ["قارن التوقع المرجعي بمساحتك وسعرك المحلي قبل أي صرف."],
                ),
            ],
        ),
    ]

    if severity.severity_label in {"high", "severe"}:
        summary = (
            f"{disease_name_en} is the lead match and the visible damage is already high, so the crop should be treated as active pressure."
        )
    elif low_confidence:
        summary = (
            f"{disease_name_en} is the lead match, but the photo confidence is low, so the report stays conservative and asks for a field check."
        )
    else:
        summary = (
            f"{disease_name_en} is the lead match and the plan below is ready for a normal field response."
        )
    if selected_mode:
        comparison_summary_en = f"{comparison_summary_en} {selected_mode.expected_benefit_en}"
        comparison_summary_ar = f"{comparison_summary_ar} {selected_mode.expected_benefit_ar}"
    if cost_estimate.basis == "reference_estimate":
        comparison_summary_en += " The economics stay reference-based until a live market quote or farmer-entered numbers replace them."
        comparison_summary_ar += " تظل التكاليف مرجعية حتى يحل محلها عرض سعر حي أو أرقام مدخلة من المزارع."

    hint_en, hint_ar = _phase_accuracy_hint(case, primary)
    if cost_estimate.basis != "farmer_inputs":
        hint_en = "Add the actual treated area and a local price quote if you want tighter economics."
        hint_ar = "أضف المساحة الفعلية وعرض سعر محلي إذا أردت اقتصاديات أدق."

    return ConclusionRecommendationPhase(
        scenario_recommendations=scenario_recommendations,
        action_plan=action_plan,
        selected_mode_key=selected_mode_key,
        best_balanced_choice_en=best_balanced_choice_en,
        best_balanced_choice_ar=best_balanced_choice_ar,
        comparison_summary_en=comparison_summary_en,
        comparison_summary_ar=comparison_summary_ar,
        higher_accuracy_hint_en=hint_en,
        higher_accuracy_hint_ar=hint_ar,
    )


def _sidebar_chatbot_context(case: CropCase, primary: PrimaryDisease, weather: WeatherObservation, source_keys: list[str]) -> SidebarChatbotContext:
    disease_name_en = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
    disease_name_ar = primary.name_ar or disease_name_en
    return SidebarChatbotContext(
        summary_en=(
            f"Ground the sidebar assistant in the confirmed photo evidence, the weather source {weather.source}, CAPMAS yield references, APC registration, and treatment rules for {disease_name_en}."
        ),
        summary_ar=(
            f"أبقِ مساعد الشريط الجانبي مرتبطًا بأدلة الصورة المؤكدة ومصدر الطقس {weather.source} ومرجع CAPMAS للتقدير وتسجيل APC وقواعد العلاج الخاصة بـ {disease_name_ar}."
        ),
        quick_questions_en=[
            "What is the primary disease from this photo?",
            "What should I do today before spraying anything?",
            "Which treatment path is allowed by the safety gate?",
            "How does the weather change the risk today?",
            "What should I check before calling an agronomist?",
        ],
        quick_questions_ar=[
            "ما المرض الأساسي من هذه الصورة؟",
            "ماذا أفعل اليوم قبل رش أي شيء؟",
            "ما مسار العلاج المسموح به بعد بوابة الأمان؟",
            "كيف يغير الطقس الخطر اليوم؟",
            "ماذا أراجع قبل الاتصال بمهندس زراعي؟",
        ],
        allowed_topics_en=[
            "photo diagnosis",
            "weather and spread pressure",
            "protection steps",
            "treatment safety gate",
            "cost forecast",
            "confirmation and next steps",
        ],
        allowed_topics_ar=[
            "تشخيص الصورة",
            "الطقس وضغط الانتشار",
            "خطوات الوقاية",
            "بوابة أمان العلاج",
            "التكلفة والتوقع",
            "التأكيد والخطوات التالية",
        ],
        source_keys=source_keys,
    )


def _source_metadata(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    weather: WeatherObservation,
    weather_metadata: SourceMetadata,
    area_range_cases,
) -> list[SourceMetadata]:
    provider = price_provider()
    tomato_farmgate = provider.get("tomato_farmgate")
    expected_yield = provider.get("expected_yield")
    disease_name = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
    disease_ar = primary.name_ar or disease_name
    entries = [
        SourceMetadata(
            key="visual_model",
            title="Local tomato disease detector",
            organization="AgroVision local runtime",
            source_kind="visual_model",
            source_type="generated",
            url=None,
            confidence=_certainty(primary.confidence if primary.detected else 0.0),
            retrieved_on=_today_iso(),
            note_en=(
                f"{disease_name} was selected from the uploaded photo with {primary.confidence:.0%} visual confidence."
            ),
            note_ar=(
                f"تم اختيار {disease_ar} من الصورة المرفوعة بثقة بصرية {primary.confidence:.0%}."
            ),
        ),
        SourceMetadata(
            key="disease_information",
            title="Reviewed tomato disease knowledge base",
            organization="AgroVision knowledge layer",
            source_kind="disease_information",
            source_type="generated",
            url=None,
            confidence="medium",
            retrieved_on=_today_iso(),
            note_en=(
                f"Tomato symptom descriptions, lookalikes, and checks were generated from the reviewed disease knowledge for {disease_name}."
            ),
            note_ar=(
                f"وُلدت أوصاف الأعراض وأشباه الأمراض وفحوصها من قاعدة المعرفة المراجعة الخاصة بـ {disease_ar}."
            ),
        ),
        weather_metadata,
    ]
    variety_options = _resistant_variety_options(case, primary, disease_by_name_en(disease_name) if primary.detected else None)
    if variety_options:
        first_option = variety_options[0]
        entries.append(
            SourceMetadata(
                key="variety_knowledge",
                title="Reviewed tomato resistant variety references",
                organization="Cornell University and reviewed catalog references",
                source_kind="variety_knowledge",
                source_type="official",
                url=first_option.source_url,
                confidence="medium",
                retrieved_on=_today_iso(),
                note_en=(
                    "Resistance packages were taken from reviewed variety references; Egypt availability was not verified in the report."
                ),
                note_ar=(
                    "تم أخذ حزم المقاومة من مراجع أصناف مراجعة؛ ولم يتم التحقق من التوافر في مصر داخل التقرير."
                ),
            )
        )
    entries.extend([
        SourceMetadata(
            key="market_price",
            title="Egypt tomato farmgate reference price",
            organization="AgroVision reference price table",
            source_kind="market_price",
            source_type="estimated_range",
            url=None,
            confidence="medium",
            retrieved_on=_today_iso(),
            note_en=(
                f"Reference range only: {tomato_farmgate.low_egp:.2f}-{tomato_farmgate.high_egp:.2f} EGP/kg. Confirm locally before buying."
                if tomato_farmgate
                else "No live market feed is connected; the report falls back to a reference price range."
            ),
            note_ar=(
                f"نطاق مرجعي فقط: {tomato_farmgate.low_egp:.2f}-{tomato_farmgate.high_egp:.2f} جنيه/كجم. أكد السعر محليًا قبل الشراء."
                if tomato_farmgate
                else "لا يوجد ربط حي بسوق الأسعار؛ لذلك يعود التقرير إلى نطاق مرجعي."
            ),
        ),
        SourceMetadata(
            key="pesticide_registration",
            title="Egyptian pesticides registration database",
            organization="Egyptian Agricultural Pesticides Committee",
            source_kind="pesticide_registration",
            source_type="official",
            url=EGYPT_PESTICIDE_DATABASE_URL,
            confidence="high",
            retrieved_on=_today_iso(),
            note_en="Use APC registration to verify crop, pest, label dose, and pre-harvest interval before any spray.",
            note_ar="استخدم تسجيل APC للتحقق من المحصول والآفة والجرعة وفترة الأمان قبل أي رش.",
        ),
    ])
    entries.extend(tomato_statistics_sources())
    entries.append(
        SourceMetadata(
            key="treatment_knowledge",
            title="Reviewed treatment rules",
            organization="AgroVision treatment rule set",
            source_kind="treatment_knowledge",
            source_type="generated",
            url=EGYPT_FOOD_SAFETY_LAB_URL,
            confidence="medium",
            retrieved_on=_today_iso(),
            note_en="Chemical advice stays behind a safety gate: diagnosis confidence, APC registration, residue safety, and crop stage all matter.",
            note_ar="الجزء الكيميائي يظل خلف بوابة أمان: ثقة التشخيص وتسجيل APC وسلامة المتبقي ومرحلة النمو كلها مهمة.",
        )
    )
    if not case.farm_type:
        entries.append(
            SourceMetadata(
                key="fallback_assumption",
                title="Generated fallback assumptions",
                organization="AgroVision report builder",
                source_kind="fallback_assumption",
                source_type="generated",
                url=None,
                confidence="low",
                retrieved_on=_today_iso(),
                note_en="The farm type was not supplied, so the report generated multiple farm-context scenarios instead of stopping.",
                note_ar="نوع المزرعة لم يُقدَّم، لذلك ولّد التقرير عدة سيناريوهات سياقية بدل أن يتوقف.",
            )
        )
    if not _observation_number(case, "analysis_processing_ms"):
        entries.append(
            SourceMetadata(
                key="analysis_runtime",
                title="Local analysis runtime metadata",
                organization="AgroVision local runtime",
                source_kind="visual_model",
                source_type="generated",
                url=None,
                confidence="low",
                retrieved_on=_today_iso(),
                note_en="The app did not store the photo-analysis runtime statistics, so the report cannot claim them here.",
                note_ar="لم يحتفظ التطبيق بإحصاءات تشغيل تحليل الصورة، لذلك لا يدعي التقرير هذه الأرقام هنا.",
            )
        )
    return entries


def _build_weather_pressure_value(
    case: CropCase,
    weather: WeatherObservation,
    severity,
) -> int | None:
    """Use weather_pressure_calculator for a partial-safe score; fall back to label-based score."""
    disease_class = (case.disease_class or "unknown").lower()
    if disease_class in {"bacterial", "fungal"}:
        result = weather_pressure_calculator(
            disease_class=disease_class,
            temp=getattr(weather, "temperature_c", None),
            humidity=None,  # Open-Meteo free tier doesn't include humidity
            precip=getattr(weather, "precipitation_mm", None),
            wind=getattr(weather, "wind_kph", None),
        )
        return int(result["weather_pressure_score"])
    return _weather_risk_score(severity.weather_risk_label)


def _summary_cards(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    weather: WeatherObservation,
    weather_metadata: SourceMetadata,
) -> SummaryCards:
    candidates: list[CompactValue] = []
    for candidate in [DiagnosisCandidate(disease=case.diagnosis.top_disease, confidence=case.diagnosis.confidence), *case.diagnosis.alternatives]:
        if not candidate.disease:
            continue
        info = disease_by_name_en(candidate.disease)
        score = round(candidate.confidence * 100)
        candidates.append(
            _compact_value(
                info.name_en if info else candidate.disease,
                info.name_ar if info else candidate.disease,
                score,
                unit="%",
                source_type="generated",
                confidence=_certainty(candidate.confidence),
                measured_zero=score == 0,
            )
        )
        if len(candidates) == 3:
            break

    analysis_time_value = _observation_number(case, "analysis_processing_ms")
    analysis_time_ms = int(round(analysis_time_value)) if analysis_time_value is not None else None
    memory_used_value = _observation_number(case, "analysis_peak_memory_mb")
    memory_used_mb = round(memory_used_value, 2) if memory_used_value is not None else None
    engine = _observation_text(case, "analysis_provider") or "Local vision model"
    source_status = (
        f"{weather.source}; reference price range"
        if weather_metadata.source_type != "live"
        else f"{weather.source}; live weather + reference prices"
    )
    return SummaryCards(
        detected_disease=_compact_value(
            "Primary disease",
            "المرض الأساسي",
            primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder",
            source_type="generated",
            confidence=primary.certainty_level,  # type: ignore[arg-type]
            measured_zero=primary.confidence == 0,
            assumption_en="The disease name is the lead visual match from the uploaded photo.",
            assumption_ar="اسم المرض هو المطابقة البصرية الأساسية من الصورة المرفوعة.",
        ),
        visual_score=_compact_value(
            "Visual match",
            "التطابق البصري",
            round(primary.confidence * 100),
            unit="%",
            source_type="generated",
            confidence=primary.certainty_level,  # type: ignore[arg-type]
            measured_zero=primary.confidence == 0,
        ),
        top_candidates=candidates,
        infection_extent=_compact_value(
            "Visible infection",
            "الانتشار الظاهر",
            round(severity.visible_affected_percent) if severity.visible_affected_percent is not None else None,
            unit="%",
            source_type="generated",
            confidence=_certainty((severity.estimated_yield_loss_high_percent or 0) / 100),
            assumption_en="Derived from the visible discoloration measurement when available.",
            assumption_ar="مستنتج من قياس الاصفرار/التغير الظاهر في الصورة عندما يكون متاحًا.",
            measured_zero=bool(severity.visible_affected_percent == 0),
        ),
        weather_risk=_compact_value(
            "Weather pressure",
            "ضغط الطقس",
            _build_weather_pressure_value(case, weather, severity),
            unit="%",
            source_type=weather_metadata.source_type,  # type: ignore[arg-type]
            confidence="high" if weather_metadata.source_type == "live" else "medium",
            assumption_en="Spread-pressure score based on temperature and precipitation; not a soil-moisture reading. Humidity not included — value is partial.",
            assumption_ar="درجة ضغط انتشار بناءً على الحرارة والهطول؛ ليست قراءة رطوبة تربة. الرطوبة غير مدرجة — القيمة جزئية.",
        ),
        engine_stats=EngineStats(
            analysis_time_ms=analysis_time_ms,
            engine=engine,
            memory_used_mb=memory_used_mb,
            source_status=source_status,
        ),
    )


def _build_report_sections(
    case: CropCase,
    primary: PrimaryDisease,
    severity,
    cost_estimate: CostEstimate,
    weather: WeatherObservation,
    weather_metadata: SourceMetadata,
    area_range_cases,
) -> tuple[
    SummaryCards,
    GeneratedPhases,
    list[SourceMetadata],
    SidebarChatbotContext,
]:
    info = disease_by_name_en(primary.name_en) if primary.detected else None
    source_metadata = _source_metadata(case, primary, severity, weather, weather_metadata, area_range_cases)
    summary_cards = _summary_cards(case, primary, severity, weather, weather_metadata)
    treatment_phase = _treatment_phase(case, primary, severity, cost_estimate, area_range_cases)
    selected_mode_key = treatment_phase.selected_mode_key
    phases = GeneratedPhases(
        disease_information=_disease_information_phase(case, primary, severity, weather, info),
        protection=_protection_phase(case, primary, severity),
        consulting=ConsultingPhase(
            auto_questions_with_answers=[
                _consulting_answer(question.key, case, primary, severity, weather)
                for question in QUESTIONS
            ]
        ),
        treatment=treatment_phase,
        cost_forecast=_cost_forecast_phase(case, primary, severity, cost_estimate, area_range_cases, treatment_phase.treatment_options, selected_mode_key),
        conclusion_recommendation=_conclusion_phase(case, primary, severity, cost_estimate, treatment_phase.treatment_options, selected_mode_key),
    )
    chatbot_context = _sidebar_chatbot_context(case, primary, weather, [item.key for item in source_metadata])
    return summary_cards, phases, source_metadata, chatbot_context


class CaseService:
    def __init__(self, repository: InMemoryCaseRepository) -> None:
        self.repository = repository

    def _get(self, case_id: str) -> CropCase:
        case = self.repository.get(case_id)
        if not case:
            raise CaseNotFoundError(case_id)
        return case

    def _save(self, case: CropCase) -> CropCase:
        case.updated_at = datetime.now(UTC)
        return self.repository.save(case)

    @staticmethod
    def _transition(case: CropCase, target: CaseStatus) -> None:
        require_transition(case.status, target)
        case.status = target

    @staticmethod
    def _refresh_generated_fields(case: CropCase) -> None:
        case.egypt_sources = egypt_official_sources()
        case.protection_plan = protection_plan(case)
        treatment = treatment_rule(case.diagnosis, LOW_CONFIDENCE_THRESHOLD)
        case.disease_class = treatment.disease_class
        case.treatment_rule_version = treatment.rule_version
        case.treatment_plan = treatment.plan
        case.prediction = prediction(case)
        case.recommendation = recommendation(case, case.cost_benefit)
        case.consulting_questions = [question.text for question in next_questions(case, 5)]

    def create(self, request: CropCaseCreate) -> CropCase:
        case = CropCase(case_id=str(uuid4()), **request.model_dump())
        self._refresh_generated_fields(case)
        self._transition(case, CaseStatus.COLLECTING_EVIDENCE)
        return self._save(case)

    def get(self, case_id: str) -> CropCase:
        return self._get(case_id)

    def list(self, limit: int = 20) -> list[CropCase]:
        return self.repository.list(limit)

    def patch(self, case_id: str, request: CropCasePatch) -> CropCase:
        case = self._get(case_id)
        for name, value in request.model_dump(exclude_unset=True).items():
            setattr(case, name, value)
        return self._save(case)

    def add_observations(self, case_id: str, request: ObservationInput) -> CropCase:
        case = self._get(case_id)
        case.observations.update(request.values)
        case.observation_sources.update({key: request.source for key in request.values})
        if case.status in {CaseStatus.NEEDS_EXPERT, CaseStatus.FAILED}:
            self._transition(case, CaseStatus.COLLECTING_EVIDENCE)
        self._refresh_generated_fields(case)
        return self._save(case)

    def ask_questions(self, case_id: str, limit: int) -> list[str]:
        case = self._get(case_id)
        questions = next_questions(case, limit)
        case.asked_question_keys.extend(question.key for question in questions)
        if case.status == CaseStatus.DIAGNOSIS_READY:
            self._transition(case, CaseStatus.CONSULTING)
        case.consulting_questions = [question.text for question in next_questions(case, 5)]
        self._save(case)
        return [question.text for question in questions]

    def set_diagnosis(self, case_id: str, request: DiagnosisInput) -> CropCase:
        case = self._get(case_id)
        existing_confirmation = case.diagnosis.confirmation
        unconfirmed = next(
            (item for item in request.candidates if item.disease == "Not enough visual evidence"),
            None,
        )
        ranked = sorted(
            (item for item in request.candidates if item is not unconfirmed),
            key=lambda item: item.confidence,
            reverse=True,
        )
        ordered = [unconfirmed, *ranked] if unconfirmed else ranked
        missing = list(request.missing_info)
        if ordered[0].confidence < LOW_CONFIDENCE_THRESHOLD:
            missing.append("Not enough evidence for chemical treatment; collect more photos and farmer answers.")
        if existing_confirmation:
            confirmed_disease = existing_confirmation.disease
            visual_match = next(
                (item for item in ordered if item.disease == confirmed_disease),
                DiagnosisCandidate(disease=confirmed_disease, confidence=0),
            )
            case.diagnosis = DiagnosisOutput(
                top_disease=confirmed_disease,
                confidence=visual_match.confidence,
                alternatives=[item for item in ordered if item.disease != confirmed_disease][:2],
                evidence=[
                    *request.evidence,
                    f"Recorded Egyptian confirmation reference: {existing_confirmation.report_reference}",
                ],
                missing_info=list(dict.fromkeys(request.missing_info)),
                confirmation_status=case.diagnosis.confirmation_status,
                confirmation=existing_confirmation,
            )
        else:
            case.diagnosis = DiagnosisOutput(
                top_disease=ordered[0].disease,
                confidence=ordered[0].confidence,
                alternatives=ordered[1:3],
                evidence=request.evidence,
                missing_info=list(dict.fromkeys(missing)),
            )
        case.cost_benefit = calculate_cost_benefit(CostBenefitInput())
        if case.diagnosis.confidence < LOW_CONFIDENCE_THRESHOLD and not existing_confirmation:
            case.cost_benefit.missing_inputs.append("reliable_diagnosis")
        self._refresh_generated_fields(case)
        target = (
            CaseStatus.DIAGNOSIS_READY
            if case.diagnosis.confidence >= LOW_CONFIDENCE_THRESHOLD or existing_confirmation
            else CaseStatus.NEEDS_EXPERT
        )
        if case.status in {CaseStatus.COLLECTING_EVIDENCE, CaseStatus.CONSULTING, CaseStatus.NEEDS_EXPERT}:
            if case.status == CaseStatus.NEEDS_EXPERT and target == CaseStatus.DIAGNOSIS_READY:
                self._transition(case, CaseStatus.COLLECTING_EVIDENCE)
            self._transition(case, target)
        return self._save(case)

    def confirm_diagnosis(
        self,
        case_id: str,
        request: DiagnosisConfirmationInput,
        evidence_filename: str,
        evidence_sha256: str,
    ) -> CropCase:
        case = self._get(case_id)
        current = case.diagnosis
        prior = [
            DiagnosisCandidate(disease=current.top_disease, confidence=current.confidence),
            *current.alternatives,
        ]
        visual_match = next(
            (item for item in prior if item.disease == request.disease),
            DiagnosisCandidate(disease=request.disease, confidence=0),
        )
        confirmation = DiagnosisConfirmationOutput(
            **request.model_dump(),
            evidence_filename=evidence_filename,
            evidence_sha256=evidence_sha256,
        )
        status = (
            "confirmed_by_egyptian_agronomist"
            if request.confirmation_type.value == "egyptian_agronomist"
            else "confirmed_by_egyptian_plant_pathology_lab"
        )
        removable_missing = (
            "The image does not support a reliable disease diagnosis.",
            "Not enough evidence for chemical treatment;",
        )
        case.diagnosis = DiagnosisOutput(
            top_disease=request.disease,
            confidence=visual_match.confidence,
            alternatives=[
                item
                for item in prior
                if item.disease not in {request.disease, "Not enough visual evidence", ""}
            ][:2],
            evidence=[
                *current.evidence,
                f"Recorded Egyptian confirmation: {request.organization}, reference {request.report_reference}.",
                f"Confirmation evidence SHA-256: {evidence_sha256}",
            ],
            missing_info=[
                item
                for item in current.missing_info
                if not any(item.startswith(prefix) for prefix in removable_missing)
            ],
            confirmation_status=status,
            confirmation=confirmation,
        )
        case.cost_benefit.missing_inputs = [
            item for item in case.cost_benefit.missing_inputs if item != "reliable_diagnosis"
        ]
        self._refresh_generated_fields(case)
        if case.status in {CaseStatus.NEEDS_EXPERT, CaseStatus.FAILED}:
            self._transition(case, CaseStatus.COLLECTING_EVIDENCE)
        if case.status in {CaseStatus.COLLECTING_EVIDENCE, CaseStatus.CONSULTING}:
            self._transition(case, CaseStatus.DIAGNOSIS_READY)
        return self._save(case)

    def calculate_economics(self, case_id: str, request: CostBenefitInput) -> CropCase:
        case = self._get(case_id)
        case.cost_benefit = calculate_cost_benefit(request)
        confirmed = case.diagnosis.confirmation_status != "unconfirmed"
        if not case.diagnosis.top_disease or (
            case.diagnosis.confidence < LOW_CONFIDENCE_THRESHOLD and not confirmed
        ):
            case.cost_benefit.decision = "need_more_data"
            case.cost_benefit.missing_inputs = list(
                dict.fromkeys([*case.cost_benefit.missing_inputs, "reliable_diagnosis"])
            )
        self._refresh_generated_fields(case)
        if case.status == CaseStatus.DIAGNOSIS_READY:
            self._transition(case, CaseStatus.PROTECTION_READY)
        if case.status == CaseStatus.PROTECTION_READY:
            self._transition(case, CaseStatus.TREATMENT_READY)
        if case.status == CaseStatus.TREATMENT_READY:
            self._transition(case, CaseStatus.ECONOMICS_READY)
        return self._save(case)

    def build_recommendation(self, case_id: str) -> CropCase:
        case = self._get(case_id)
        self._refresh_generated_fields(case)
        if case.status in {CaseStatus.DIAGNOSIS_READY, CaseStatus.CONSULTING}:
            self._transition(case, CaseStatus.PROTECTION_READY)
        if case.status == CaseStatus.PROTECTION_READY:
            self._transition(case, CaseStatus.TREATMENT_READY)
        if case.status == CaseStatus.TREATMENT_READY:
            self._transition(case, CaseStatus.RECOMMENDATION_READY)
        if case.status == CaseStatus.ECONOMICS_READY:
            self._transition(case, CaseStatus.RECOMMENDATION_READY)
        return self._save(case)

    def _evaluate_photo_quality(self, case: CropCase) -> PhotoQuality:
        obs = case.observations or {}
        width = obs.get("image_width_px")
        height = obs.get("image_height_px")
        green_pct = obs.get("image_green_coverage_percent")
        dark_pct = obs.get("image_dark_pixel_percent")
        discoloration_pct = obs.get("image_visible_discoloration_percent")

        warnings = []

        # 1. Host crop confirmation check
        crop_support_mass = 1.0
        for ev in case.diagnosis.evidence:
            if "Crop-label support" in ev:
                try:
                    val_str = ev.split(":")[1].replace("%", "").strip()
                    crop_support_mass = float(val_str) / 100.0
                except Exception:
                    pass

        host_crop_support = "visually_supported"
        if crop_support_mass < 0.70:
            host_crop_support = "user_selected_not_visually_confirmed"
            warnings.append("Crop selected by user: tomato. Image model did not independently confirm host crop.")

        # 2. Leaf present?
        leaf_present = True
        if green_pct is not None:
            try:
                g_pct = float(green_pct)
                if g_pct < 10.0:
                    leaf_present = False
                    warnings.append("Low leaf coverage: Leaf may not be present or is too small in the frame.")
            except Exception:
                pass

        # 3. Leaf area enough?
        if green_pct is not None:
            try:
                g_pct = float(green_pct)
                if g_pct < 20.0:
                    warnings.append("Leaf area is not sufficient for robust diagnosis.")
            except Exception:
                pass

        # 4. Resolution check
        if width is not None and height is not None:
            try:
                w_px = int(width)
                h_px = int(height)
                if w_px < 256 or h_px < 256:
                    warnings.append("Image resolution is low. Clear photos should be at least 256x256 pixels.")
            except Exception:
                pass

        # 5. Background/shadow issues
        if dark_pct is not None:
            try:
                d_pct = float(dark_pct)
                if d_pct > 50.0:
                    warnings.append("Heavy shadows or dark background detected. This may obscure leaf details.")
            except Exception:
                pass

        # 6. Disease symptoms visible?
        has_symptoms = False
        if discoloration_pct is not None:
            try:
                d_pct = float(discoloration_pct)
                if d_pct > 0.0:
                    has_symptoms = True
            except Exception:
                pass
        
        if not has_symptoms and not case.diagnosis.top_disease:
            warnings.append("No clear disease/pest symptoms visible in the photo.")

        # Determine status
        if host_crop_support == "user_selected_not_visually_confirmed":
            status = "host crop not visually confirmed"
        elif not leaf_present:
            status = "low leaf coverage"
        elif dark_pct is not None and float(dark_pct) > 50.0:
            status = "shadowed"
        elif width is not None and (int(width) < 256 or int(height) < 256):
            status = "small image"
        else:
            if case.diagnosis.confidence < 0.50:
                status = "blurry"
            else:
                status = "clear"

        return PhotoQuality(
            status=status,
            leaf_area_score=float(green_pct) if green_pct is not None else None,
            host_crop_support=host_crop_support,
            warnings=warnings,
        )

    def report(self, case_id: str) -> SystemOutput:
        case = self.build_recommendation(case_id)
        questions = [question.text for question in next_questions(case, 5)]
        severity = estimate_severity(case)
        cost_estimate = reference_cost_estimate(case, severity)
        primary = _primary_disease(case)

        # 1. Photo quality & Host crop confirmation checks
        photo_quality = self._evaluate_photo_quality(case)
        if photo_quality.host_crop_support == "user_selected_not_visually_confirmed":
            if primary.certainty_level == "high":
                primary.certainty_level = "medium"
            elif primary.certainty_level == "medium":
                primary.certainty_level = "low"

        selected_mode_key = _selected_treatment_mode_key(case, primary, severity)
        disease_class = case.disease_class or "unknown"
        area_range_cases = generate_area_range_cases(severity, selected_mode_key, disease_class)

        confidence_warning = _confidence_warning(primary)
        assumptions = _report_assumptions(case, area_range_cases)
        weather, weather_metadata = _resolve_weather(case)
        summary_cards, phases, source_metadata, chatbot_context = _build_report_sections(
            case, primary, severity, cost_estimate, weather, weather_metadata, area_range_cases
        )

        disease_name_en = primary.name_en or case.diagnosis.top_disease or "Unconfirmed leaf disorder"
        info = disease_by_name_en(disease_name_en) if primary.detected else None
        disease_name_ar = primary.name_ar or (info.name_ar if info else disease_name_en)
        scenarios = generate_scenarios(case, severity, disease_name_en, disease_name_ar)

        # Build conclusion
        if case.diagnosis.confirmation:
            confirmation = case.diagnosis.confirmation
            conclusion = (
                f"{disease_name_en} is recorded from submitted Egyptian "
                f"{confirmation.confirmation_type.value.replace('_', ' ')} evidence "
                f"from {confirmation.organization}, reference {confirmation.report_reference}. "
                f"{confirmation.verification_notice} "
            )
        elif primary.detected:
            conclusion = (
                f"The most likely disease is {disease_name_en} "
                f"({primary.confidence:.0%} AI confidence, {primary.certainty_level} certainty). "
            )
            if primary.certainty_level == "low":
                conclusion += "Confidence is low, so verify the photo or ask an engineer before any costly action. "
        else:
            conclusion = (
                "No clear disease was matched from this photo, so the plan below uses general scenarios. "
            )
        conclusion += (
            "Use the protection steps now, keep the safety gates closed until the diagnosis is clear, "
            "and confirm high-value or high-risk decisions with an expert. "
        )
        if case.cost_benefit.decision == "need_more_data":
            conclusion += (
                "The cost forecast stays reference-based until a live market quote or farmer-entered numbers are available. "
            )
        if weather_metadata.source_type == "live":
            conclusion += f"Weather is based on live location data from {weather.source}. "
        else:
            conclusion += "Weather falls back to a clearly labelled Egypt reference sample when live coordinates are unavailable. "
        if primary.detected:
            conclusion += f"Primary match: {disease_name_en}. "
        if confidence_warning and confidence_warning.level == "low":
            conclusion += "Confidence is low, so treat the diagnosis as a screening result, not a lab confirmation. "
        if photo_quality.host_crop_support == "user_selected_not_visually_confirmed":
            conclusion += " Crop selected by user: tomato. Image model did not independently confirm host crop."
        
        conclusion = conclusion.strip()
        if case.status == CaseStatus.RECOMMENDATION_READY:
            self._transition(case, CaseStatus.REPORT_READY)
            self._save(case)

        # 2. Build new contract outputs
        treatment_options_schema = []
        for opt in phases.treatment.treatment_options:
            treatment_options_schema.append(
                TreatmentOptionSchema(
                    id=opt.key,
                    name=opt.label_en,
                    type="chemical" if opt.key in {"balanced", "strongest", "prevention_only"} else "cultural",
                    budget_level="medium" if opt.key in {"balanced", "custom"} else ("high" if opt.key == "strongest" else "low"),
                    allowed_status="allowed" if not opt.requires_apc_verification else "locked_until_apc_verification",
                    cost_range={"low": opt.cost_egp.low, "high": opt.cost_egp.high},
                    labor_range={"low": opt.budget_egp.low, "high": opt.budget_egp.high},
                    source_type=opt.cost_egp.source_type,
                    assumptions=[opt.cost_egp.assumption_en],
                    safety_gate={
                        "requires_apc_verification": opt.requires_apc_verification,
                        "requires_engineer_confirmation": opt.requires_engineer_confirmation,
                        "apc_gate_en": opt.apc_gate_en,
                        "apc_gate_ar": opt.apc_gate_ar,
                    }
                )
            )

        area_scenarios_list = []
        for ar in area_range_cases:
            area_scenarios_list.append({
                "key": ar.key,
                "name_en": ar.name_en,
                "name_ar": ar.name_ar,
                "area_feddan": ar.area_feddan,
                "sprays": {"low": ar.sprays.low, "high": ar.sprays.high},
                "treatment_cost_egp": {"low": ar.treatment_cost_egp.low, "high": ar.treatment_cost_egp.high},
                "labor_cost_egp": {"low": ar.labor_cost_egp.low, "high": ar.labor_cost_egp.high},
                "expected_yield_kg": {"low": ar.expected_yield_kg.low, "high": ar.expected_yield_kg.high},
                "loss_without_action_egp": {"low": ar.loss_without_action_egp.low, "high": ar.loss_without_action_egp.high},
                "saved_with_action_egp": {"low": ar.saved_with_action_egp.low, "high": ar.saved_with_action_egp.high},
                "revenue_egp": {"low": ar.revenue_egp.low, "high": ar.revenue_egp.high},
                "net_benefit_egp": {"low": ar.net_benefit_egp.low, "high": ar.net_benefit_egp.high},
                "worth_spraying": ar.worth_spraying,
                "recommendation_en": ar.recommendation_en,
                "recommendation_ar": ar.recommendation_ar,
            })

        cost_benefit_by_selected_treatment = CostBenefitBySelectedTreatment(
            selected_treatment_id=selected_mode_key,
            area_scenarios=area_scenarios_list
        )

        cost_benefit_comparison_list = []
        for opt in phases.treatment.treatment_options:
            cost_benefit_comparison_list.append({
                "treatment_mode": opt.key,
                "label_en": opt.label_en,
                "label_ar": opt.label_ar,
                "cost_low": opt.cost_egp.low,
                "cost_high": opt.cost_egp.high,
                "when_to_use_en": opt.summary_en,
                "when_to_use_ar": opt.summary_ar,
                "expected_benefit_en": opt.expected_benefit_en,
                "expected_benefit_ar": opt.expected_benefit_ar,
                "risk_en": opt.risk_en,
                "risk_ar": opt.risk_ar,
                "apc_gate_en": opt.apc_gate_en,
                "apc_gate_ar": opt.apc_gate_ar,
                "best_farm_size_en": "Greenhouse / all sizes" if opt.key == "balanced" else "All sizes" if opt.key == "sanitation_only" else "Home garden" if opt.key == "confirm_first" else "Large farms",
                "best_farm_size_ar": "صوبة / كل المساحات" if opt.key == "balanced" else "كل المساحات" if opt.key == "sanitation_only" else "جنينة منزلية" if opt.key == "confirm_first" else "المزارع الكبيرة",
                "recommended": opt.key == selected_mode_key,
            })

        forecast_recalculation = ForecastRecalculation(
            function_used="calculateCostBenefitByTreatment",
            last_selected_treatment_id=selected_mode_key,
            updated_at=datetime.now(UTC).isoformat()
        )

        report = SystemOutput(
            case_id=case.case_id,
            crop=case.crop.value,
            location=case.location,
            farm_type=case.farm_type.value if case.farm_type else None,
            growth_stage=case.growth_stage,
            symptoms=case.symptoms,
            observations=case.observations,
            observation_sources=case.observation_sources,
            egypt_sources=case.egypt_sources,
            diagnosis=case.diagnosis,
            chatbot_followup_questions=questions,
            protection_plan=case.protection_plan,
            treatment_plan=case.treatment_plan,
            cost_benefit=case.cost_benefit,
            severity=severity,
            cost_estimate=cost_estimate,
            prediction=case.prediction,
            recommendation=case.recommendation,
            scenarios=scenarios,
            source_metadata=source_metadata,
            summary_cards=summary_cards,
            phases=phases,
            sidebar_chatbot_context=chatbot_context,
            primary_detected_disease=primary,
            confidence_warning=confidence_warning,
            area_range_cases=area_range_cases,
            assumptions=assumptions,
            safety_notes=[
                *case.treatment_plan.safety_notes,
                "Keep the APC registration and pre-harvest interval in view before any spray.",
                "Treat the weather and price figures as live only when the metadata says live.",
            ],
            conclusion=conclusion,
            completeness=[],
            photo_quality=photo_quality,
            treatment_options=treatment_options_schema,
            selected_treatment_id=selected_mode_key,
            cost_benefit_by_selected_treatment=cost_benefit_by_selected_treatment,
            cost_benefit_comparison=cost_benefit_comparison_list,
            forecast_recalculation=forecast_recalculation,
        )
        self.repository.save_report(case, report)
        return report

    def save_asset(
        self,
        case_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        view_type: str,
        evidence: dict[str, object],
    ) -> bool:
        case = self._get(case_id)
        return self.repository.save_asset(case, filename, content, content_type, view_type, evidence)
