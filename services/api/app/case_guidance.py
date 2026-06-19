"""Small, reviewed guidance layer for the tomato/banana local demo."""

from __future__ import annotations

from .crop_knowledge import greenhouse_text, tomato_resistant_variety_records, tomato_varieties_text
from .schemas import LocalizedText


_TOMATO_VARIETY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tomato_late_blight": ("late blight",),
    "tomato_early_blight": ("early blight",),
    "septoria_leaf_spot_tomato": ("septoria",),
    "tomato_yellow_leaf_curl_virus": ("tylcv", "yellow leaf curl", "virus"),
}

BANANA_VARIETIES_BY_DISEASE: dict[str, list[str]] = {
    "sigatoka_leaf_spot": ["FHIA-17", "FHIA-23", "FHIA-01 Goldfinger"],
    "panama_disease": ["GCTCV-218 Formosana", "FHIA-01 Goldfinger"],
}

GENERAL_TOMATO_VARIETIES = [record.name_en for record in tomato_resistant_variety_records()]
GENERAL_BANANA_VARIETIES = ["FHIA-17", "FHIA-23", "FHIA-01 Goldfinger"]


def _tomato_variety_names_for_disease(disease_key: str) -> list[str]:
    records = tomato_resistant_variety_records()
    keywords = _TOMATO_VARIETY_KEYWORDS.get(disease_key)
    if not keywords:
        return [record.name_en for record in records]
    matches = [
        record.name_en
        for record in records
        if any(keyword in " ".join(record.disease_coverage_en).lower() for keyword in keywords)
    ]
    return matches or [record.name_en for record in records]


def resistant_varieties(crop: str, disease_key: str) -> list[str]:
    if crop == "banana":
        return BANANA_VARIETIES_BY_DISEASE.get(disease_key, GENERAL_BANANA_VARIETIES)
    return _tomato_variety_names_for_disease(disease_key)


def resistant_variety_note(crop: str, disease_key: str, lang: str) -> str:
    varieties = resistant_varieties(crop, disease_key)
    if lang == "ar":
        lead = "أمثلة تستحق السؤال عنها محليًا: " + "، ".join(varieties) + "."
        caution = " المقاومة تقلل الخطر ولا تمنع العدوى تمامًا؛ تأكد من رموز المقاومة وتوفر الصنف في مصر."
    else:
        lead = "Examples to ask local suppliers about: " + ", ".join(varieties) + "."
        caution = " Resistance lowers risk but does not prevent infection; verify resistance codes and availability in Egypt."
    if disease_key in {"cordana_leaf_spot", "bunchy_top"}:
        caution = (
            " لا توجد في هذا العرض قائمة موثقة خاصة بهذا المرض؛ استخدم شتلات معتمدة ونظيفة واسأل مهندسًا زراعيًا."
            if lang == "ar"
            else " This demo has no reviewed disease-specific variety list; use certified clean planting material and confirm with an agronomist."
        )
    return lead + caution


def resistant_variety_note(crop: str, disease_key: str, lang: str) -> str:
    if crop == "tomato":
        return tomato_varieties_text(lang)

    varieties = resistant_varieties(crop, disease_key)
    if lang == "ar":
        lead = "أمثلة اطلبها من المورد المحلي: " + "، ".join(varieties) + "."
        caution = " المقاومة تقلل الخطر لكنها لا تمنع العدوى تمامًا؛ تأكد من رموز المقاومة وتوفر الصنف في مصر."
    else:
        lead = "Examples to ask local suppliers about: " + ", ".join(varieties) + "."
        caution = " Resistance lowers risk but does not prevent infection; verify resistance codes and availability in Egypt."
    if disease_key in {"cordana_leaf_spot", "bunchy_top"}:
        caution = (
            " لا توجد في هذا العرض قائمة موثقة خاصة بهذا المرض؛ استخدم شتلات معتمدة ونظيفة واسأل مهندسًا زراعيًا."
            if lang == "ar"
            else " This demo has no reviewed disease-specific variety list; use certified clean planting material and confirm with an agronomist."
        )
    return lead + caution


def irrigation_scheme(crop: str, lang: str) -> str:
    if crop == "banana":
        return (
            "برنامج ري الموز: حافظ على رطوبة منتظمة وعميقة بدون تغريق. استخدم التنقيط أو الأحواض جيدة الصرف، "
            "وافحص رطوبة التربة قبل كل رية. زِد التكرار في الحر والتربة الرملية، وقلله بعد المطر أو في التربة الثقيلة. "
            "امنع بقاء الماء حول الجذور وبلل الأوراق ليلًا. لا يمكن تحديد لتر/نبات بدقة بدون عمر النبات ونوع التربة وتصريف النقاط."
            if lang == "ar"
            else
            "Banana irrigation scheme: keep deep, even soil moisture without waterlogging. Use drip or well-drained basins "
            "and check soil moisture before each irrigation. Irrigate more often in heat or sandy soil and less after rain "
            "or in heavy soil. Do not leave water around roots or wet leaves overnight. Exact litres per plant require plant "
            "age, soil type, emitter flow, and local evapotranspiration."
        )
    return (
        "برنامج ري الطماطم: استخدم التنقيط وري الصباح عند قاعدة النبات. بعد الشتل استخدم ريات خفيفة ومتقاربة حتى تثبت الجذور، "
        "ثم ريات أعمق حسب رطوبة التربة. أثناء التزهير والعقد حافظ على رطوبة ثابتة وتجنب التعطيش ثم التغريق لأنه يزيد التشقق وعفن الطرف الزهري. "
        "قلل الري إذا ظلت التربة رطبة أو ظهرت مشاكل جذور. لا يمكن تحديد لتر/نبات بدقة بدون مرحلة النمو ونوع التربة وتصريف النقاط."
        if lang == "ar"
        else
        "Tomato irrigation scheme: use drip irrigation and water at the root zone in the morning. After transplanting, use "
        "small frequent irrigations until roots establish, then irrigate more deeply based on soil moisture. During flowering "
        "and fruit set, keep moisture steady and avoid dry-to-flood swings that increase cracking and blossom-end rot. Reduce "
        "irrigation when soil stays wet or root problems appear. Exact litres per plant require growth stage, soil type, and emitter flow."
    )


def case_questions(crop: str, disease_name_en: str, disease_name_ar: str) -> list[LocalizedText]:
    crop_en = "banana" if crop == "banana" else "tomato"
    crop_ar = "الموز" if crop == "banana" else "الطماطم"
    questions = [
        LocalizedText(
            en=f"What is the safest treatment plan for {disease_name_en} on {crop_en}?",
            ar=f"ما هي خطة العلاج الأكثر أمانًا لـ {disease_name_ar} في {crop_ar}؟",
        ),
        LocalizedText(
            en=f"Give me an irrigation scheme for {crop_en} with this condition.",
            ar=f"اعطني برنامج ري لـ {crop_ar} مع هذه الحالة.",
        ),
        LocalizedText(
            en=f"How can I prevent {disease_name_en} from spreading?",
            ar=f"كيف أمنع انتشار {disease_name_ar}؟",
        ),
    ]
    if crop == "tomato":
        questions.append(LocalizedText(
            en="Would a greenhouse reduce the infection risk for this tomato case?",
            ar="هل الصوبة تقلل خطر الإصابة في حالة الطماطم دي؟",
        ))
    return questions


def diagnosis_verification_questions(crop: str) -> list[LocalizedText]:
    crop_en = "banana" if crop == "banana" else "tomato"
    crop_ar = "الموز" if crop == "banana" else "الطماطم"
    return [
        LocalizedText(
            en=f"Which symptoms would help identify the problem on this {crop_en} plant?",
            ar=f"إيه الأعراض اللي تساعد نحدد المشكلة في نبات {crop_ar} ده؟",
        ),
        LocalizedText(
            en="Which extra photos should I take before considering treatment?",
            ar="أصوّر إيه تاني قبل ما أفكر في أي علاج؟",
        ),
        LocalizedText(
            en="What safe steps can I take while the diagnosis is uncertain?",
            ar="إيه الخطوات الآمنة اللي أعملها لحد ما نتأكد من التشخيص؟",
        ),
    ]


def question_guidance(question: str, crop: str, disease_key: str, lang: str) -> str:
    normalized = question.lower()
    parts: list[str] = []
    if any(word in normalized for word in ["irrig", "water", "watering", "ري", "ماء", "سقي"]):
        parts.append(irrigation_scheme(crop, lang))
    if crop == "tomato" and any(word in normalized for word in ["greenhouse", "high tunnel", "صوبة", "بيت محمي"]):
        parts.append(greenhouse_text(lang))
    if any(word in normalized for word in ["variet", "resistan", "cultivar", "صنف", "أصناف", "مقاوم"]):
        if crop == "tomato":
            parts.append(tomato_varieties_text(lang))
        else:
            parts.append(resistant_variety_note(crop, disease_key, lang))
    return "\n\n".join(parts)
