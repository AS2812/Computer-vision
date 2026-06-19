"""Auto-generated cost-benefit scenarios for every Egyptian area size.

The farmer never types an area. Instead, for each common Egyptian holding size
(from a home garden up to 10 feddans) we generate a complete cost-benefit case:
number of sprays, treatment + labour cost, expected yield, the EGP loss avoided
by acting, revenue, net benefit, and a plain Egyptian-Arabic recommendation.

Every number is a ``SourcedRange`` — it always carries its unit, a ``source_type``
(live_market / admin_table / csv_fallback / estimated_range), a confidence level,
and the assumption behind it. No bare numbers, no "missing data": when the real
price feed is not live, the figure is honestly labelled an ``estimated_range``.
"""

from __future__ import annotations

from app.application.prices import PriceProvider, PriceRange, price_provider
from app.contracts.cases import AreaRangeCase, SeverityEstimate, SourcedRange

FEDDAN_PER_QIRAT = 1.0 / 24.0

# (key, English name, Arabic name, area in feddan). Home garden is a handful of
# plants, so it is treated as a tiny area with hand-sanitation economics.
AREA_PRESETS: list[tuple[str, str, str, float]] = [
    ("home_garden", "Home garden", "جنينة بيت", 0.02),
    ("one_qirat", "1 qirat", "قيراط", 1 * FEDDAN_PER_QIRAT),
    ("six_qirat", "6 qirat", "٦ قراريط", 6 * FEDDAN_PER_QIRAT),
    ("twelve_qirat", "12 qirat (½ feddan)", "١٢ قيراط (نص فدان)", 12 * FEDDAN_PER_QIRAT),
    ("one_feddan", "1 feddan", "فدان", 1.0),
    ("three_feddan", "3 feddans", "٣ فدادين", 3.0),
    ("five_feddan", "5 feddans", "٥ فدادين", 5.0),
    ("ten_feddan", "10 feddans", "١٠ فدادين", 10.0),
]

# Protective applications assumed over a season (low–high) and residual loss the
# spraying programme is assumed to leave behind.
_SPRAYS_LOW, _SPRAYS_HIGH = 2, 4
_RESIDUAL_LOSS_PERCENT = 5.0
# Default visible-loss band used when the image gave no severity (so the phase is
# still generated, clearly as an estimate, never blank).
_DEFAULT_LOSS_LOW, _DEFAULT_LOSS_HIGH = 8.0, 20.0


def _source_type(price: PriceRange | None) -> str:
    """Map a price source string onto the report's source_type vocabulary.

    Order matters: 'reference/estimate/not live' must win first so the default
    Egyptian reference source ("…reviewed reference (not live)") is never mistaken
    for a live market quote — we must never imply a fake live price.
    """
    source = (price.source if price else "").lower()
    if not source or "not live" in source or "reference" in source or "estimate" in source:
        return "estimated_range"
    if "csv" in source:
        return "csv_fallback"
    if "admin" in source:
        return "admin_table"
    if "live" in source or "market api" in source:
        return "live_market"
    return "estimated_range"


def _confidence(source_type: str) -> str:
    return {"live_market": "high", "admin_table": "medium", "csv_fallback": "medium"}.get(
        source_type, "low"
    )


def _sum(provider: PriceProvider, items: tuple[str, ...], bound: str) -> tuple[float, str]:
    total = 0.0
    worst_source = "estimated_range"
    order = {"live_market": 0, "admin_table": 1, "csv_fallback": 2, "estimated_range": 3}
    for item in items:
        price = provider.get(item)
        if price is not None:
            total += price.low_egp if bound == "low" else price.high_egp
            st = _source_type(price)
            if order[st] > order[worst_source]:
                worst_source = st
    return total, worst_source


def _loss_band(severity: SeverityEstimate) -> tuple[float, float]:
    low = severity.estimated_yield_loss_low_percent
    high = severity.estimated_yield_loss_high_percent
    if low is None or high is None or high <= 0:
        return _DEFAULT_LOSS_LOW, _DEFAULT_LOSS_HIGH
    return low, high


def _range(
    label_en: str,
    label_ar: str,
    low: float | None,
    high: float | None,
    unit: str,
    source_type: str,
    assumption_en: str,
    assumption_ar: str,
    measured_zero: bool = False,
) -> SourcedRange:
    if low is None or high is None:
        return SourcedRange(
            label_en=label_en,
            label_ar=label_ar,
            low=None,
            high=None,
            unit=unit,
            source_type=source_type,
            confidence=_confidence(source_type),
            assumption_en=assumption_en,
            assumption_ar=assumption_ar,
            measured_zero=measured_zero,
        )
    lo, hi = (low, high) if low <= high else (high, low)
    if lo == 0.0 or hi == 0.0:
        measured_zero = True
    return SourcedRange(
        label_en=label_en, label_ar=label_ar,
        low=round(lo, 2), high=round(hi, 2), unit=unit,
        source_type=source_type, confidence=_confidence(source_type),
        assumption_en=assumption_en, assumption_ar=assumption_ar,
        measured_zero=measured_zero,
    )


def generate_area_range_cases(
    severity: SeverityEstimate,
    selected_treatment_id: str = "balanced",
    disease_class: str = "unknown",
    provider: PriceProvider | None = None,
) -> list[AreaRangeCase]:
    """Generate a full cost-benefit case for each Egyptian area size, no input needed."""
    provider = provider or price_provider()

    pest = disease_class.lower() == "pest"
    chem_key_low = "insecticide" if pest else "contact_fungicide"
    chem_key_high = "insecticide" if pest else "systemic_fungicide"

    per_app_low, src_cost_low = _sum(provider, (chem_key_low, "labor", "sprayer_use", "water_fuel"), "low")
    per_app_high, src_cost_high = _sum(provider, (chem_key_high, "labor", "sprayer_use", "water_fuel"), "high")
    cost_source = src_cost_high
    labor = provider.get("labor")
    labor_low = labor.low_egp if labor else 0.0
    labor_high = labor.high_egp if labor else 0.0
    labor_source = _source_type(labor)

    yield_ref = provider.get("expected_yield")
    yield_low = yield_ref.low_egp if yield_ref else 0.0
    yield_high = yield_ref.high_egp if yield_ref else 0.0
    yield_source = _source_type(yield_ref)

    price = provider.get("tomato_farmgate")
    price_low = price.low_egp if price else 0.0
    price_high = price.high_egp if price else 0.0
    price_source = _source_type(price)

    loss_low_pct, loss_high_pct = _loss_band(severity)
    avoidable_low = max(0.0, loss_low_pct - _RESIDUAL_LOSS_PERCENT) / 100.0
    avoidable_high = max(0.0, loss_high_pct - _RESIDUAL_LOSS_PERCENT) / 100.0

    price_assumption_en = (
        "Egyptian reference price; not a live market quote — confirm with your dealer/market."
        if price_source == "estimated_range"
        else "From the configured Egyptian price source."
    )
    price_assumption_ar = (
        "سعر مرجعي مصري؛ مش سعر سوق مباشر — أكّده من التاجر/السوق."
        if price_source == "estimated_range"
        else "من مصدر الأسعار المصري المضبوط."
    )

    cases: list[AreaRangeCase] = []
    for key, name_en, name_ar, area in AREA_PRESETS:
        home = key == "home_garden"

        if selected_treatment_id == "confirm_first":
            sprays_low = sprays_high = 0
            cost_low = 150.0 if not home else 50.0
            cost_high = 300.0 if not home else 100.0
            tcost_source = "estimated_range"
            labor_total_low = labor_total_high = 0.0
        elif selected_treatment_id == "sanitation_only":
            sprays_low = sprays_high = 0
            cost_low = cost_high = 0.0
            tcost_source = "estimated_range"
            labor_total_low = labor_total_high = 0.0
        elif selected_treatment_id == "prevention_only":
            sprays_low = 1
            sprays_high = 2
            if home:
                inputs = provider.get("home_garden_inputs")
                cost_low = (inputs.low_egp if inputs else 80.0) * 0.5
                cost_high = (inputs.high_egp if inputs else 400.0) * 0.5
                tcost_source = _source_type(inputs)
                labor_total_low = labor_total_high = 0.0
            else:
                cost_low = per_app_low * 0.5 * sprays_low * area
                cost_high = per_app_high * 0.5 * sprays_high * area
                tcost_source = cost_source
                labor_total_low = labor_low * sprays_low * area
                labor_total_high = labor_high * sprays_high * area
        elif selected_treatment_id == "strongest":
            sprays_low = 3
            sprays_high = 5
            if home:
                inputs = provider.get("home_garden_inputs")
                cost_low = (inputs.low_egp if inputs else 80.0) * 1.3
                cost_high = (inputs.high_egp if inputs else 400.0) * 1.3
                tcost_source = _source_type(inputs)
                labor_total_low = labor_total_high = 0.0
            else:
                cost_low = per_app_low * 1.3 * sprays_low * area
                cost_high = per_app_high * 1.3 * sprays_high * area
                tcost_source = cost_source
                labor_total_low = labor_low * sprays_low * area
                labor_total_high = labor_high * sprays_high * area
        else:  # balanced or custom
            sprays_low = _SPRAYS_LOW
            sprays_high = _SPRAYS_HIGH
            if home:
                inputs = provider.get("home_garden_inputs")
                cost_low = inputs.low_egp if inputs else 80.0
                cost_high = inputs.high_egp if inputs else 400.0
                tcost_source = _source_type(inputs)
                labor_total_low = labor_total_high = 0.0
            else:
                cost_low = per_app_low * sprays_low * area
                cost_high = per_app_high * sprays_high * area
                tcost_source = cost_source
                labor_total_low = labor_low * sprays_low * area
                labor_total_high = labor_high * sprays_high * area

        ey_low = yield_low * area
        ey_high = yield_high * area
        revenue_low = ey_low * price_low
        revenue_high = ey_high * price_high
        loss_low = revenue_low * (loss_low_pct / 100.0)
        loss_high = revenue_high * (loss_high_pct / 100.0)

        # Saved revenue based on treatment efficacy
        if selected_treatment_id == "confirm_first":
            saved_low = saved_high = 0.0
        elif selected_treatment_id == "sanitation_only":
            saved_low = loss_low * 0.30
            saved_high = loss_high * 0.30
        elif selected_treatment_id == "prevention_only":
            saved_low = revenue_low * avoidable_low * 0.50
            saved_high = revenue_high * avoidable_high * 0.50
        elif selected_treatment_id == "strongest":
            saved_low = revenue_low * avoidable_low * 0.95
            saved_high = revenue_high * avoidable_high * 0.95
        elif selected_treatment_id == "custom":
            saved_low = revenue_low * avoidable_low * 0.80
            saved_high = revenue_high * avoidable_high * 0.80
        else:  # balanced
            saved_low = revenue_low * avoidable_low * 0.85
            saved_high = revenue_high * avoidable_high * 0.85

        net_low = saved_low - cost_high
        net_high = saved_high - cost_low

        if home:
            worth = "likely_worth"
            if selected_treatment_id == "confirm_first":
                rec_en = "Confirm first: check underside of leaves; a small garden check costs very little."
                rec_ar = "أكد أولاً: افحص الورقة من تحت؛ فحص الجنينة الصغيرة مش مكلف."
            elif selected_treatment_id == "sanitation_only":
                rec_en = "Pick off and bin spotted leaves by hand first; a small garden rarely needs a paid spray."
                rec_ar = "شيل الورق المبقّع باليد الأول؛ الجنينة الصغيرة نادرًا ما تحتاج رشّة بفلوس."
            else:
                rec_en = "Apply low-risk garden treatments only if symptoms persist."
                rec_ar = "استخدم معالجات جنينة خفيفة إذا استمرت الأعراض."
        elif selected_treatment_id == "confirm_first":
            worth = "ask_engineer"
            rec_en = "Hold chemical spending and confirm the diagnosis before buying anything."
            rec_ar = "أوقف الصرف الكيميائي وتأكد من التشخيص قبل الشراء."
        elif selected_treatment_id == "sanitation_only":
            worth = "likely_worth" if net_low > 0 else "ask_engineer"
            rec_en = "Sanitation program: manual hygiene saves yield with zero chemical purchase cost."
            rec_ar = "تنظيف الحقل: النظافة اليدوية توفر المحصول بدون تكلفة شراء كيماويات."
        elif net_high <= 0:
            worth = "maybe_not_worth"
            rec_en = "The spray may not pay off at this size/severity — monitor first and re-check in a few days."
            rec_ar = "الرش ممكن ما يستاهلش في الحجم/الخطورة دي — راقب الأول وافحص تاني بعد كام يوم."
        elif net_low > 0 and severity.severity_label in {"moderate", "high", "severe"}:
            worth = "likely_worth"
            rec_en = "Protecting the crop is likely worth it here — run a planned spray programme and keep records."
            rec_ar = "حماية المحصول غالبًا بتستاهل هنا — اعمل برنامج رش مخطط وسجّل المواعيد."
        else:
            worth = "ask_engineer"
            rec_en = "Borderline economics — confirm the disease and costs with an agricultural engineer before spraying."
            rec_ar = "العائد على الحدّ — أكّد المرض والتكلفة مع مهندس زراعي قبل الرش."

        sprays_assumption_en = f"Assumes {sprays_low}–{sprays_high} protective applications this season."
        sprays_assumption_ar = f"على افتراض {sprays_low}–{sprays_high} رشّات وقائية في الموسم."
        area_note_en = f"For {name_en} (~{area:g} feddan)."
        area_note_ar = f"لـ {name_ar} (حوالي {area:g} فدان)."

        cases.append(AreaRangeCase(
            key=key, name_en=name_en, name_ar=name_ar, area_feddan=round(area, 4),
            sprays=_range("Number of sprays", "عدد الرشّات", sprays_low, sprays_high, "sprays/season",
                          "estimated_range", sprays_assumption_en, sprays_assumption_ar, measured_zero=(home or sprays_low == 0)),
            treatment_cost_egp=_range("Treatment cost", "تكلفة العلاج", cost_low, cost_high, "EGP",
                                      tcost_source, f"{area_note_en} {sprays_assumption_en}",
                                      f"{area_note_ar} {sprays_assumption_ar}", measured_zero=(cost_low == 0.0)),
            labor_cost_egp=_range("Labour cost", "أجرة العمالة", labor_total_low, labor_total_high, "EGP",
                                  labor_source, area_note_en, area_note_ar, measured_zero=(home or labor_total_low == 0.0)),
            expected_yield_kg=_range("Expected yield", "الإنتاجية المتوقعة", ey_low, ey_high, "kg",
                                     yield_source, "Egyptian reference yield per feddan × area.",
                                     "إنتاجية الفدان المرجعية × المساحة."),
            loss_without_action_egp=_range("Loss without action", "الخسارة من غير علاج", loss_low, loss_high, "EGP",
                                           price_source, f"Yield-loss band × revenue. {price_assumption_en}",
                                           f"شريحة خسارة المحصول × الإيراد. {price_assumption_ar}"),
            saved_with_action_egp=_range("Saved by acting", "اللي بيتحفظ بالعلاج", saved_low, saved_high, "EGP",
                                         price_source, "Avoidable share of the loss after a spray programme.",
                                         "الجزء اللي ينفع نتجنّبه من الخسارة بعد برنامج الرش.", measured_zero=(saved_low == 0.0)),
            revenue_egp=_range("Revenue", "الإيراد", revenue_low, revenue_high, "EGP",
                               price_source, price_assumption_en, price_assumption_ar),
            net_benefit_egp=_range("Net benefit", "صافي المكسب", net_low, net_high, "EGP",
                                   price_source, "Saved revenue minus treatment cost (conservative).",
                                   "اللي اتحفظ ناقص تكلفة العلاج (بتحفّظ)."),
            worth_spraying=worth, recommendation_en=rec_en, recommendation_ar=rec_ar,
        ))
    return cases
