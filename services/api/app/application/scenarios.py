"""Phase 6: the six Egyptian farm scenarios.

Generated for every case so the recommendation phase is never blank, even when the
farmer's real context is unknown. Each scenario says how diagnosis confidence,
protection, treatment, cost, and the recommendation change for that context. Text
is practical and Arabic-friendly; it is adjusted by the disease class and the
image-based severity, but never invents farm-specific numbers.
"""

from __future__ import annotations

from app.contracts.cases import CropCase, ScenarioOutput, SeverityEstimate


def _urgency(severity: str, lang: str) -> str:
    if severity in {"high", "severe"}:
        return "تحرك دلوقتي، الإصابة واضحة وكبيرة." if lang == "ar" else "Act now — the visible infection is already high."
    if severity == "moderate":
        return "ابدأ الوقاية بدري قبل ما تكبر." if lang == "ar" else "Start protection early before it spreads."
    if severity == "low":
        return "راقب وكرر التصوير كل يومين." if lang == "ar" else "Monitor and re-photograph every couple of days."
    return "صوّر ورقة واضحة عشان نقدّر الخطورة." if lang == "ar" else "Add a clear leaf photo so we can judge severity."


def _no_cure_note(disease_class: str, lang: str) -> str:
    if disease_class in {"viral", "abiotic"}:
        return (
            " ملاحظة: مفيش رشّة بتشفي الحالة دي — المكافحة بإزالة المصاب والنظافة والأصناف المقاومة."
            if lang == "ar"
            else " Note: no spray cures this — control is roguing infected plants, sanitation, and resistant varieties."
        )
    if disease_class == "bacterial":
        return (
            " ملاحظة: البكتيريا ما بتتعالجش بالمبيد الفطري — النحاس والنظافة هما المكافحة."
            if lang == "ar"
            else " Note: bacteria are not cured by fungicides — copper sprays plus sanitation are the control."
        )
    return ""


# Static, reviewed per-scenario text per phase dimension. Disease/severity context is
# appended at generation time so the wording stays practical, not academic.
_SCENARIOS: list[dict[str, str]] = [
    {
        "key": "home_garden",
        "name_en": "Home garden", "name_ar": "حديقة منزلية",
        "confidence_en": "Few plants and close photos make the visual check easier; you can inspect every leaf yourself.",
        "confidence_ar": "نباتات قليلة وصور قريبة بتسهّل الفحص؛ تقدر تبص على كل ورقة بنفسك.",
        "protection_en": "Pick off and bin spotted leaves, water at the soil in the morning, and keep plants spaced for airflow.",
        "protection_ar": "شيل الورق المبقّع وارميه بعيد، اروي على الأرض الصبح، وسيب مسافة بين النباتات للتهوية.",
        "treatment_en": "Start with cultural control; a small bottle of garden fungicide is usually enough — no field sprayer needed.",
        "treatment_ar": "ابدأ بالمكافحة الزراعية؛ عبوة صغيرة مبيد للحديقة بتكفي غالبًا — مش محتاج رشّاشة حقل.",
        "cost_en": "Very low cost (tens of EGP). Hand removal of infected leaves is free and effective at this scale.",
        "cost_ar": "تكلفة بسيطة جدًا (عشرات الجنيهات). شيل الورق المصاب باليد مجاني وفعّال في الحجم ده.",
        "recommendation_en": "Hand-sanitation first; only spray if it keeps spreading after a week.",
        "recommendation_ar": "النظافة باليد الأول؛ ما ترشّش غير لو فضل ينتشر بعد أسبوع.",
    },
    {
        "key": "open_field",
        "name_en": "Open-field farm", "name_ar": "حقل مكشوف",
        "confidence_en": "Wind and dust can blur photos; take several close shots of different plants for a steadier read.",
        "confidence_ar": "الهوا والتراب ممكن يأثروا على الصور؛ صوّر كذا لقطة قريبة من نباتات مختلفة.",
        "protection_en": "Remove lower infected leaves, avoid working plants when wet, and rotate away from tomato/potato next season.",
        "protection_ar": "شيل الورق السفلي المصاب، ما تشتغلش في الزرع وهو مبلّل، ودوّر بعيد عن الطماطم/البطاطس الموسم الجاي.",
        "treatment_en": "A planned 7–10 day protective spray program with rotation to avoid resistance.",
        "treatment_ar": "برنامج رش وقائي كل ٧–١٠ أيام مع تبديل المبيدات لتفادي المقاومة.",
        "cost_en": "Cost scales with feddans; budget several applications of labour + product. Worth it on a clear infection.",
        "cost_ar": "التكلفة بتزيد بعدد الأفدنة؛ احسب كذا رشّة عمالة + منتج. بتستاهل لو الإصابة واضحة.",
        "recommendation_en": "Confirm the disease, then run the protective program on the whole block, not just hot spots.",
        "recommendation_ar": "أكّد المرض، وبعدين شغّل البرنامج الوقائي على القطعة كلها مش بس الأماكن المصابة.",
    },
    {
        "key": "greenhouse",
        "name_en": "Greenhouse", "name_ar": "صوبة",
        "confidence_en": "Controlled light gives clearer photos, but high humidity hides early symptoms — scout daily.",
        "confidence_ar": "الإضاءة المنتظمة بتدّي صور أوضح، بس الرطوبة العالية بتخفي الأعراض المبكرة — افحص يوميًا.",
        "protection_en": "Vent and heat to drop humidity, widen spacing, water early in the day, and remove infected leaves fast.",
        "protection_ar": "هوّي وسخّن لتقليل الرطوبة، وسّع المسافات، اروي بدري بالنهار، وشيل الورق المصاب بسرعة.",
        "treatment_en": "Humidity control is half the cure; combine it with a rotated fungicide program for the enclosed air.",
        "treatment_ar": "التحكم في الرطوبة نص العلاج؛ مع برنامج مبيد متبادل للهوا المغلق.",
        "cost_en": "Higher crop value justifies climate control spend; ventilation/heating cost offsets lost yield.",
        "cost_ar": "قيمة المحصول الأعلى بتبرّر صرف التحكم في المناخ؛ تكلفة التهوية/التدفئة بتعوّض خسارة المحصول.",
        "recommendation_en": "Fix humidity first; a greenhouse beats most foliar disease with climate, not just chemicals.",
        "recommendation_ar": "ظبّط الرطوبة الأول؛ الصوبة بتغلب أغلب أمراض الورق بالمناخ مش بالكيماوي بس.",
    },
    {
        "key": "desert_farm",
        "name_en": "Desert / new-land farm", "name_ar": "مزرعة صحراوية / أرض جديدة",
        "confidence_en": "Dry, bright conditions usually mean fewer fungal lesions — double-check it is disease, not heat/sun scorch.",
        "confidence_ar": "الجو الناشف المشمس غالبًا بيقلّل البقع الفطرية — اتأكد إنها مرض مش حرق شمس أو حرارة.",
        "protection_en": "Drip irrigation keeps leaves dry (good); watch for spider mites and nutrient/heat stress instead.",
        "protection_ar": "الري بالتنقيط بيخلّي الورق ناشف (كويس)؛ خلّي بالك من العنكبوت الأحمر وإجهاد الحرارة والعناصر.",
        "treatment_en": "Lower fungal pressure means fewer sprays; prioritise balanced feeding and mite scouting.",
        "treatment_ar": "ضغط فطري أقل يعني رش أقل؛ ركّز على التسميد المتوازن ومتابعة الأكاروس.",
        "cost_en": "Save on fungicides but budget for water, fertigation, and possible miticide; ROI depends on water cost.",
        "cost_ar": "بتوفّر في المبيد الفطري بس احسب الميّة والتسميد واحتمال أكاروسيد؛ العائد بيعتمد على تكلفة الميّة.",
        "recommendation_en": "Rule out heat/mite damage before spraying for fungus; keep nutrition balanced.",
        "recommendation_ar": "استبعد ضرر الحرارة/الأكاروس قبل ما ترشّ للفطر؛ خلّي التسميد متوازن.",
    },
    {
        "key": "small_commercial",
        "name_en": "Small commercial farm", "name_ar": "مزرعة تجارية صغيرة",
        "confidence_en": "You sell the crop, so a lab/agronomist confirmation is worth it before a big spend.",
        "confidence_ar": "بتبيع المحصول، فتأكيد المعمل/المهندس بيستاهل قبل أي صرف كبير.",
        "protection_en": "Map infected blocks, clean tools between blocks, and protect healthy areas first.",
        "protection_ar": "حدّد القطع المصابة، نضّف الأدوات بين القطع، واحمِ السليم الأول.",
        "treatment_en": "Run a rotation program and keep spray records for residue/PHI compliance before market.",
        "treatment_ar": "شغّل برنامج تبديل وسجّل الرش لمراعاة فترة الأمان قبل التسويق.",
        "cost_en": "Decide by ROI: compare the EGP value of saved yield against the full program cost across feddans.",
        "cost_ar": "قرّر بالعائد: قارن قيمة المحصول المحفوظ بالجنيه بتكلفة البرنامج كامل على الأفدنة.",
        "recommendation_en": "Confirm, treat the whole block on a schedule, and respect pre-harvest intervals for the market.",
        "recommendation_ar": "أكّد، عالج القطعة كلها بجدول، واحترم فترة ما قبل الحصاد للسوق.",
    },
    {
        "key": "coastal_humid",
        "name_en": "Coastal / high-humidity (e.g. Alexandria)", "name_ar": "ساحلي / رطوبة عالية (زي الإسكندرية)",
        "confidence_en": "High humidity and dew make foliar diseases spread fast and look similar — confirm the exact one.",
        "confidence_ar": "الرطوبة والندى بيخلّوا أمراض الورق تنتشر بسرعة وتتشابه — أكّد النوع بالظبط.",
        "protection_en": "This is the highest-risk setting: maximise airflow, avoid evening watering, and remove infected tissue daily.",
        "protection_ar": "ده أعلى وضع خطورة: زوّد التهوية، ابعد عن الري بالليل، وشيل المصاب يوميًا.",
        "treatment_en": "Start a protectant program EARLY and preventively; in this humidity, once you see it you are already late.",
        "treatment_ar": "ابدأ برنامج وقائي بدري وقبل الظهور؛ في الرطوبة دي أول ما تشوفه تكون اتأخّرت.",
        "cost_en": "Expect more applications here, so costs run higher — but skipping protection risks the whole crop.",
        "cost_ar": "متوقع رشّات أكتر هنا فالتكلفة أعلى — بس إهمال الوقاية بيخاطر بالمحصول كله.",
        "recommendation_en": "Treat preventively on the calendar, not on symptoms; watch the weather for cool, wet spells.",
        "recommendation_ar": "عالج وقائيًا بالتقويم مش بالأعراض؛ راقب الجو في فترات البرد والبلل.",
    },
]


def generate_scenarios(
    case: CropCase,
    severity: SeverityEstimate,
    disease_name_en: str,
    disease_name_ar: str,
) -> list[ScenarioOutput]:
    sev = severity.severity_label
    disease_class = case.disease_class or "unknown"
    cure_en = _no_cure_note(disease_class, "en")
    cure_ar = _no_cure_note(disease_class, "ar")
    named = bool(disease_name_en) and disease_name_en not in {"Not enough visual evidence", ""}
    lead_en = f"For {disease_name_en}: " if named else "Until the disease is confirmed: "
    lead_ar = f"بالنسبة لـ {disease_name_ar}: " if named else "لحد ما يتأكد المرض: "

    scenarios: list[ScenarioOutput] = []
    for spec in _SCENARIOS:
        scenarios.append(
            ScenarioOutput(
                key=spec["key"],
                name_en=spec["name_en"], name_ar=spec["name_ar"],
                confidence_en=spec["confidence_en"], confidence_ar=spec["confidence_ar"],
                protection_en=spec["protection_en"], protection_ar=spec["protection_ar"],
                treatment_en=lead_en + spec["treatment_en"] + cure_en,
                treatment_ar=lead_ar + spec["treatment_ar"] + cure_ar,
                cost_en=spec["cost_en"], cost_ar=spec["cost_ar"],
                recommendation_en=spec["recommendation_en"] + " " + _urgency(sev, "en"),
                recommendation_ar=spec["recommendation_ar"] + " " + _urgency(sev, "ar"),
            )
        )
    return scenarios
