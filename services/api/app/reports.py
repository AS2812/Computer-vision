import csv
import csv
import io
import json
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .case_guidance import irrigation_scheme, resistant_variety_note
from .contracts.cases import SystemOutput
from .schemas import AnalysisResponse


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _fmt_optional_number(value: float | int | None, arabic: bool, digits: int = 0) -> str:
    if value is None:
        return "n/a" if not arabic else "غير متاح"
    return f"{value:,.{digits}f}" if digits else f"{int(round(value)):,}"


def _fmt_optional_range(
    low: float | int | None,
    high: float | int | None,
    arabic: bool,
    unit: str = "",
    digits: int = 0,
) -> str:
    if low is None or high is None:
        return "n/a" if not arabic else "غير متاح"
    suffix = unit if not unit or unit == "%" else f" {unit}"
    return f"{_fmt_optional_number(low, arabic, digits)} - {_fmt_optional_number(high, arabic, digits)}{suffix if unit != '%' else '%'}"


def _compact_display(value: str | int | float | None, unit: str, arabic: bool) -> str:
    if value is None:
        return "n/a" if not arabic else "غير متاح"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        text = _fmt_optional_number(value, arabic)
    else:
        text = str(value)
    if not unit:
        return text
    return f"{text}%" if unit == "%" else f"{text} {unit}"


def analysis_csv(analysis: AnalysisResponse) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["crop", analysis.crop])
    writer.writerow(["feature", "level", "value", "confidence", "limitation"])
    for result in analysis.results:
        writer.writerow([result.feature, result.level, result.value, result.confidence, result.limitation or ""])
    return output.getvalue().encode("utf-8-sig")


def _disease_result(analysis: AnalysisResponse):
    return next((item for item in analysis.results if item.feature == "disease"), None)


def analysis_pdf(analysis: AnalysisResponse) -> bytes:
    output = io.BytesIO()
    page = canvas.Canvas(output, pagesize=A4)
    page.setTitle(f"AgroVision analysis {analysis.analysis_id}")
    y = 800

    def ensure(height: int = 30) -> None:
        nonlocal y
        if y - height < 55:
            page.showPage()
            y = 800

    def write(text: str, *, font: str = "Helvetica", size: int = 10, indent: int = 0) -> None:
        nonlocal y
        width = max(55, 100 - indent // 3)
        for wrapped in textwrap.wrap(str(text), width=width) or [""]:
            ensure(15)
            page.setFont(font, size)
            page.drawString(48 + indent, y, wrapped[:115])
            y -= 14

    def heading(text: str, size: int = 12) -> None:
        nonlocal y
        ensure(32)
        y -= 7
        write(text, font="Helvetica-Bold", size=size)
        y -= 3

    write("AgroVision Egypt - Tomato/Banana Local Analysis", font="Helvetica-Bold", size=15)
    write(f"File: {analysis.filename} | Selected crop: {analysis.crop.title()}")
    write(f"Analysis ID: {analysis.analysis_id}")
    write(
        "Provider: "
        f"{analysis.provider} | Processing: {_fmt_optional_number(analysis.processing_ms, False)} ms | "
        f"Peak process memory: {_fmt_optional_number(analysis.peak_memory_mb, False, 2)} MB"
    )
    model_name = "PlantVillage MobileNetV2 tomato classifier" if analysis.crop == "tomato" else "Banana VGG19 INT8 classifier"
    write(f"Selected model: {model_name}")
    write("Model status: experimental local screening model; confidence is uncalibrated and field accuracy is not claimed.", font="Helvetica-Oblique", size=9)

    heading("Prioritized dashboard results")
    for result in analysis.results:
        write(f"- {result.title}: {result.value} [{result.level}; confidence {result.confidence:.0%}]")
        for evidence in result.evidence[:3]:
            write(f"  Evidence: {evidence}", size=9, indent=10)
        if result.limitation:
            write(f"  Limitation: {result.limitation}", font="Helvetica-Oblique", size=9, indent=10)

    disease = _disease_result(analysis)
    if disease and disease.disease_info:
        info = disease.disease_info
        heading("Diagnosis details")
        write(f"{info.name_en} ({info.crop_en or analysis.crop.title()})", font="Helvetica-Bold", size=11)
        write(info.summary_en)
        heading("Signs to verify in the field", size=10)
        for item in info.symptoms_en:
            write(f"- {item}")
        heading("Immediate non-chemical management", size=10)
        for item in info.management_en:
            write(f"- {item}")

        heading("Resistant variety options", size=10)
        write(resistant_variety_note(analysis.crop, info.key, "en"))

        heading("Irrigation scheme", size=10)
        write(irrigation_scheme(analysis.crop, "en"))

        heading("Treatment options - best first", size=11)
        if not info.treatments:
            write("No reviewed chemical treatment is listed for this condition. Focus on cultural control and confirm with an agronomist.")
        for treatment in info.treatments:
            write(f"{treatment.rank}. {treatment.name_en} | FRAC {treatment.frac}", font="Helvetica-Bold", size=10)
            write(f"Dose: {treatment.dose_en}", indent=10)
            write(f"How to apply: {treatment.application_en}", indent=10)
            write(f"Wait before harvest: {treatment.phi_en}", indent=10)
            write(f"Hazard/care: {treatment.hazard_en}", indent=10)
            write(f"Approximate price: {treatment.price_en}", indent=10)
            write(f"Why this rank: {treatment.note_en}", indent=10)

    heading("Case-specific assistant questions", size=10)
    for question in analysis.assistant_questions:
        write(f"- {question.en}")

    if analysis.alerts:
        heading("Alerts", size=10)
        for alert in analysis.alerts:
            write(f"- {alert.en}")
    if analysis.recommendations:
        heading("Recommended next steps", size=10)
        for recommendation in analysis.recommendations:
            write(f"- {recommendation.en}")

    ensure(35)
    y -= 8
    write("Educational reference only. Read the current product label and have a local agricultural engineer confirm before any treatment.", font="Helvetica-Oblique", size=9)
    page.save()
    return output.getvalue()


def case_csv(report: SystemOutput) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "field", "value"])
    writer.writerow(["case", "case_id", report.case_id])
    writer.writerow(["case", "crop", report.crop])
    writer.writerow(["case", "location", report.location])
    writer.writerow(["case", "farm_type", report.farm_type or ""])
    writer.writerow(["case", "growth_stage", report.growth_stage or ""])
    writer.writerow(["case", "symptoms", json.dumps(report.symptoms, ensure_ascii=False)])
    for key, value in report.observations.items():
        writer.writerow(
            [
                "observation",
                key,
                json.dumps(
                    {"value": value, "source": report.observation_sources.get(key, "farmer_answer")},
                    ensure_ascii=False,
                ),
            ]
        )
    writer.writerow(["diagnosis", "top_disease", report.diagnosis.top_disease])
    writer.writerow(["diagnosis", "confidence", report.diagnosis.confidence])
    writer.writerow(["diagnosis", "confirmation_status", report.diagnosis.confirmation_status])
    writer.writerow(
        [
            "diagnosis",
            "confirmation",
            json.dumps(
                report.diagnosis.confirmation.model_dump(mode="json")
                if report.diagnosis.confirmation
                else None,
                ensure_ascii=False,
            ),
        ]
    )
    writer.writerow(["diagnosis", "evidence", json.dumps(report.diagnosis.evidence, ensure_ascii=False)])
    writer.writerow(["diagnosis", "missing_info", json.dumps(report.diagnosis.missing_info, ensure_ascii=False)])
    writer.writerow(["diagnosis", "primary_detected_disease", _json(report.primary_detected_disease.model_dump(mode="json"))])
    writer.writerow(
        [
            "diagnosis",
            "confidence_warning",
            _json(report.confidence_warning.model_dump(mode="json")) if report.confidence_warning else "",
        ]
    )
    writer.writerow(["protection", "plan", json.dumps(report.protection_plan, ensure_ascii=False)])
    writer.writerow(["treatment", "plan", json.dumps(report.treatment_plan.model_dump(mode="json"), ensure_ascii=False)])
    writer.writerow(["economics", "result", json.dumps(report.cost_benefit.model_dump(mode="json"), ensure_ascii=False)])
    writer.writerow(["severity", "result", json.dumps(report.severity.model_dump(mode="json"), ensure_ascii=False)])
    writer.writerow(["cost_estimate", "result", json.dumps(report.cost_estimate.model_dump(mode="json"), ensure_ascii=False)])
    writer.writerow(["prediction", "result", json.dumps(report.prediction.model_dump(mode="json"), ensure_ascii=False)])
    writer.writerow(["recommendation", "result", json.dumps(report.recommendation.model_dump(mode="json"), ensure_ascii=False)])
    writer.writerow(["summary_cards", "result", _json(report.summary_cards.model_dump(mode="json"))])
    writer.writerow(["phases", "result", _json(report.phases.model_dump(mode="json"))])
    writer.writerow(["sidebar_chatbot_context", "result", _json(report.sidebar_chatbot_context.model_dump(mode="json"))])
    writer.writerow(["scenarios", "egypt_cases", json.dumps([s.model_dump(mode="json") for s in report.scenarios], ensure_ascii=False)])
    writer.writerow(["area_range_cases", "egypt_sizes", _json([s.model_dump(mode="json") for s in report.area_range_cases])])
    writer.writerow(["source_metadata", "items", _json([item.model_dump(mode="json") for item in report.source_metadata])])
    writer.writerow(["egypt_sources", "official", _json([item.model_dump(mode="json") for item in report.egypt_sources])])
    writer.writerow(["assumptions", "items", _json([item.model_dump(mode="json") for item in report.assumptions])])
    writer.writerow(["safety_notes", "items", _json(report.safety_notes)])
    writer.writerow(["chatbot_followup_questions", "items", _json(report.chatbot_followup_questions)])
    writer.writerow(["completeness", "estimated_phases", json.dumps(report.completeness, ensure_ascii=False)])
    writer.writerow(["conclusion", "text", report.conclusion])
    writer.writerow(["safety", "disclaimer", report.disclaimer])
    return output.getvalue().encode("utf-8-sig")


def case_pdf(report: SystemOutput) -> bytes:
    output = io.BytesIO()
    page = canvas.Canvas(output, pagesize=A4)
    page.setTitle(f"AgroVision case {report.case_id}")
    y = 800

    def write(text: str, *, bold: bool = False, indent: int = 0) -> None:
        nonlocal y
        for wrapped in textwrap.wrap(str(text), width=max(55, 100 - indent // 3)) or [""]:
            if y < 55:
                page.showPage()
                y = 800
            page.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
            page.drawString(48 + indent, y, wrapped[:115])
            y -= 14

    def section(title: str, values: list[str]) -> None:
        nonlocal y
        y -= 7
        write(title, bold=True)
        for value in values:
            write(f"- {value}", indent=10)

    def heading(text: str, size: int = 11) -> None:
        nonlocal y
        y -= 5
        write(text, bold=True)
        y -= 2

    write("AgroVision Egypt - Crop Case Report", bold=True)
    write(f"Case ID: {report.case_id}")
    write(f"Crop: {report.crop.title()} | Location: {report.location or 'Not supplied'}")
    write(f"Farm type: {report.farm_type or 'Not supplied'} | Growth stage: {report.growth_stage or 'Not supplied'}")
    section("Reported symptoms", report.symptoms or ["Not supplied."])
    section(
        "Evidence log with provenance",
        [
            f"{key}: {value} [{report.observation_sources.get(key, 'farmer_answer')}]"
            for key, value in report.observations.items()
        ]
        or ["No observations recorded."],
    )
    diagnosis_lines = [
        f"{report.diagnosis.top_disease or 'Not enough evidence'} ({report.diagnosis.confidence:.0%} visual-model score)",
        f"Confirmation status: {report.diagnosis.confirmation_status}",
        *report.diagnosis.evidence,
        *[f"Missing: {item}" for item in report.diagnosis.missing_info],
    ]
    if report.diagnosis.confirmation:
        diagnosis_lines.extend(
            [
                f"Submitted confirmation organization: {report.diagnosis.confirmation.organization}",
                f"Submitted confirmation reference: {report.diagnosis.confirmation.report_reference}",
                report.diagnosis.confirmation.verification_notice,
            ]
        )
    section("Diagnosis", diagnosis_lines)
    section("Protection plan", report.protection_plan or ["No protection plan generated yet."])
    section("Non-chemical treatment", report.treatment_plan.non_chemical or ["No treatment plan generated yet."])
    section("Chemical category if needed", report.treatment_plan.chemical_category_if_needed or ["Locked or not recommended."])
    section("Safety notes", [*report.treatment_plan.safety_notes, *report.safety_notes] or [report.disclaimer])
    section(
        "Official Egypt sources",
        [f"{source.title}: {source.url}" for source in report.egypt_sources],
    )
    heading("Summary cards", size=11)
    section(
        "Image and engine summary",
        [
            f"Primary disease: {report.summary_cards.detected_disease.label_en} = {_compact_display(report.summary_cards.detected_disease.value, report.summary_cards.detected_disease.unit, False)}",
            f"Visual score: {_compact_display(report.summary_cards.visual_score.value, report.summary_cards.visual_score.unit, False)}",
            f"Top candidates: {', '.join(_compact_display(item.value, item.unit, False) for item in report.summary_cards.top_candidates) or 'None'}",
            f"Visible infection: {_compact_display(report.summary_cards.infection_extent.value, report.summary_cards.infection_extent.unit, False)}",
            f"Weather risk: {_compact_display(report.summary_cards.weather_risk.value, report.summary_cards.weather_risk.unit, False)}",
            f"Engine: {report.summary_cards.engine_stats.engine} | {_fmt_optional_number(report.summary_cards.engine_stats.analysis_time_ms, False)} ms | {_fmt_optional_number(report.summary_cards.engine_stats.memory_used_mb, False, 2)} MB",
        ],
    )
    heading("Generated phases", size=11)
    phase1 = report.phases.disease_information
    section(
        "Phase 1 - Disease information",
        [
            f"{phase1.disease_name_en} / {phase1.disease_name_ar}",
            phase1.meaning_en,
            phase1.spread_en,
            phase1.why_it_appears_en,
            phase1.worse_weather_en,
            phase1.danger_en,
            f"Lookalikes: {', '.join(phase1.lookalikes_en)}",
            f"Today check: {', '.join(phase1.today_check_en)}",
        ],
    )
    section(
        "Phase 2 - Protection",
        [
            item.summary_en for item in report.phases.protection.scenario_cases
        ]
        or ["Protection scenarios are generated from the photo and weather context."],
    )
    section(
        "Phase 3 - Consulting",
        [
            f"Q: {item.question_en} / A: {item.answer_en}"
            for item in report.phases.consulting.auto_questions_with_answers
        ]
        or ["Consulting answers are generated from the photo and farmer context."],
    )
    section(
        "Phase 4 - Treatment",
        [
            item.summary_en for item in report.phases.treatment.scenario_cases
        ]
        or ["Treatment scenarios are generated behind the safety gate."],
    )
    section(
        "Phase 5 - Cost and forecast",
        [
            f"{item.name_en}: {item.recommendation_en}" for item in report.area_range_cases
        ]
        or ["Area-range cases are generated for common Egyptian farm sizes."],
    )
    section(
        "Phase 6 - Conclusion and recommendation",
        [
            item.summary_en for item in report.phases.conclusion_recommendation.scenario_recommendations
        ]
        or ["Conclusion scenarios are generated from the report context."],
    )
    section(
        "Sidebar assistant context",
        [
            report.sidebar_chatbot_context.summary_en,
            f"Quick questions: {', '.join(report.sidebar_chatbot_context.quick_questions_en)}",
            f"Allowed topics: {', '.join(report.sidebar_chatbot_context.allowed_topics_en)}",
        ],
    )
    section(
        "Source metadata",
        [
            f"{item.title} [{item.source_type}] - {item.note_en}"
            for item in report.source_metadata
        ]
        or ["Source metadata not available."],
    )
    severity = report.severity
    section(
        "Severity & damage estimate (from image)",
        [
            f"Severity: {severity.severity_label} | Visible affected: "
            f"{_fmt_optional_number(severity.visible_affected_percent, False) + '%' if severity.visible_affected_percent is not None else 'n/a'}",
            "Estimated yield loss: "
            + (
                _fmt_optional_range(
                    severity.estimated_yield_loss_low_percent,
                    severity.estimated_yield_loss_high_percent,
                    False,
                    "%",
                )
                if severity.estimated_yield_loss_low_percent is not None and severity.estimated_yield_loss_high_percent is not None
                else "n/a"
            )
            + f" | Recovery: {severity.recovery_probability_label}"
            f" | Weather risk: {severity.weather_risk_label}",
            *severity.drivers,
            severity.basis,
        ],
    )
    cost = report.cost_estimate
    section(
        "Cost-benefit estimate",
        [
            f"Basis: {cost.basis}"
            + (f" | Assumed area: {cost.area_feddan_assumed} feddan" if cost.area_feddan_assumed is not None else ""),
            f"Treatment cost: {_fmt_optional_range(cost.treatment_cost_egp_low, cost.treatment_cost_egp_high, False, 'EGP')}",
            f"Potential loss avoided: "
            + (
                _fmt_optional_range(cost.potential_loss_egp_low, cost.potential_loss_egp_high, False, 'EGP')
                if cost.potential_loss_egp_low is not None and cost.potential_loss_egp_high is not None else "needs a clear photo to estimate"
            ),
            cost.decision_hint or "",
            *cost.assumptions,
            cost.note,
        ],
    )
    section(
        "Recommendation",
        [
            report.recommendation.best_action_now or "Collect more evidence.",
            report.recommendation.next_3_to_7_days or "Recheck the crop in 3-7 days.",
            report.recommendation.when_to_call_expert or "Call an expert when risk or crop value is high.",
        ],
    )
    for scenario in report.scenarios:
        section(
            f"Scenario — {scenario.name_en}",
            [
                f"Confidence: {scenario.confidence_en}",
                f"Protection: {scenario.protection_en}",
                f"Treatment: {scenario.treatment_en}",
                f"Cost: {scenario.cost_en}",
                f"Recommendation: {scenario.recommendation_en}",
            ],
        )
    if report.completeness:
        section("Where the report estimated (missing farmer data)", report.completeness)
    section("Conclusion", [report.conclusion, *report.safety_notes, report.disclaimer])
    page.save()
    return output.getvalue()
