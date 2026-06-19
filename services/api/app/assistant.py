"""Bilingual (English / Arabic) farming assistant.

The assistant answers crop questions grounded ONLY in the reviewed Egyptian crop
disease + treatment knowledge base and the current image analysis. When an online
provider is configured it generates the reply; otherwise a reviewed bilingual
offline template answers from the same grounded data.

Honesty rules: it uses only the supplied facts. It never invents a product, dose,
or price. If the farmer's crop/disease is not in the knowledge base, it says so
plainly and points them to an agronomist instead of guessing.

Language handling: the UI passes ``language`` ("en" / "ar"). If it is missing we
detect Arabic from the question text and otherwise default to English.
"""

from __future__ import annotations

import httpx

from .case_guidance import irrigation_scheme, question_guidance
from .config import settings
from .crop_knowledge import SOURCES as CROP_SOURCES
from .crop_knowledge import SOURCE_URLS as CROP_SOURCE_URLS
from .crop_knowledge import tomato_grounding
from .diseases import disease_info
from .schemas import AnalysisResponse, AssistantResponse, DiseaseInfo, FeatureResult, Treatment
from .treatment_prices import price_sources_for_treatment


LANG_NAMES = {"en": "English", "ar": "Arabic"}

SYSTEM_PROMPTS = {
    "en": (
        "You are AgroVision Egypt's farming assistant for tomato and banana only. Reply ONLY in English, in "
        "simple, practical words a farmer understands. "
        "Use the CROP KNOWLEDGE, DISEASE REFERENCE, TREATMENT PROGRAM, and IMAGE READINGS in the user message "
        "as your ONLY source of facts. NEVER invent a product, dose, price, or number that is "
        "not given there. If a detail (e.g. an exact price) is not provided, say you do not have "
        "it and tell them to confirm at their local dealer — do not guess. "
        "When asked about treatment/spraying, list the products from the TREATMENT PROGRAM in the "
        "given order (most effective first). For each product give: active ingredient/name, the "
        "dose, how and when to spray (and rotate to avoid resistance), the pre-harvest interval, "
        "the hazard/side-effects, and the approximate price with 'confirm locally'. "
        "If the crop or disease is NOT in the reference, say you don't have a reviewed treatment "
        "for it yet and to ask a local agronomist. Always end by reminding them to read the "
        "product label and have an agricultural engineer confirm before spraying. "
        "Write plain text only: no Markdown symbols (**, ##, backticks) and no emoji; use a "
        "leading dash or a number for list items."
    ),
    "ar": (
        "إنت مساعد AgroVision الزراعي للطماطم والموز فقط. جاوب بالعربي المصري البسيط بس، بكلام عملي يفهمه الفلاح. "
        "اعتمد فقط على «معرفة المحصول» و«مرجع المرض» و«برنامج الرش» و«قياسات الصورة» اللي في رسالة المستخدم كمصدر "
        "وحيد للحقائق. ما تختلقش منتج أو جرعة أو سعر أو رقم مش مكتوب. لو في تفصيلة (زي سعر بالظبط) "
        "مش موجودة، قول إنك مش عندك السعر بالظبط واطلب منه يأكّده من محل المبيدات — ما تخمّنش. "
        "لما يسأل عن العلاج/الرش، اعرض المنتجات من «برنامج الرش» بالترتيب (الأقوى الأول)، وكل منتج "
        "قول: الاسم/المادة الفعّالة، الجرعة، إزاي وإمتى ترش (وبدّل عشان ما تحصلش مقاومة)، فترة الأمان "
        "قبل الحصاد، الخطورة/الأعراض الجانبية، والسعر التقريبي مع «أكّده محليًا». "
        "لو المحصول أو المرض مش موجود في المرجع، قول إنك لسه ماعندكش علاج موثّق ليه واطلب منه يسأل "
        "مهندس زراعي. اختم دايمًا بتذكيره إنه يقرا لافتة المنتج ويخلّي مهندس زراعي يأكّد قبل الرش. "
        "اكتب نص عادي بس من غير رموز Markdown (زي ** أو ##) ومن غير إيموجي، واستخدم شَرطة أو رقم للقوائم."
    ),
}

SAFE_ACTIONS = {
    "en": {
        "inspect_field": "Inspect the affected leaves in person and record the real symptoms.",
        "consult_agronomist": "Read the product label and have an agricultural engineer confirm before applying any treatment.",
        "compare_records": "Compare the result with your irrigation, soil, and weather records.",
        "name_crop": "Choose tomato or banana, then tell me what you see on the leaves and I will give you the reviewed treatment or irrigation guidance.",
    },
    "ar": {
        "inspect_field": "بصّ على الورق المصاب بنفسك وسجّل الأعراض الحقيقية.",
        "consult_agronomist": "اقرا لافتة المنتج وخلّي مهندس زراعي يأكّد قبل ما ترش أي علاج.",
        "compare_records": "قارن النتيجة بسجلات الري والتربة والطقس عندك.",
        "name_crop": "اختار طماطم أو موز، وقول لي إيه اللي شايفه على الورق عشان أديك علاج أو برنامج ري موثّق.",
    },
}

# Specific disease keywords -> knowledge-base key (checked in order).
_DISEASE_KEYWORDS: list[tuple[list[str], str]] = [
    (["septoria", "سبتوريا", "septoria_leaf_spot_tomato"], "septoria_leaf_spot_tomato"),
    (["late blight", "الندوة المتأخرة", "اللفحة المتأخرة", "phytophthora", "فيتوفثورا", "tomato_late_blight"], "tomato_late_blight"),
    (["early blight", "الندوة المبكرة", "اللفحة المبكرة", "alternaria", "ألترناريا", "الترناريا", "tomato_early_blight"], "tomato_early_blight"),
    (["downy", "البياض الزغبي", "زغبي"], "downy_mildew"),
    (["powdery", "البياض الدقيقي", "دقيقي"], "powdery_mildew"),
    (["sigatoka", "سيجاتوكا", "سيغاتوكا"], "sigatoka_leaf_spot"),
    (["cordana", "كوردانا"], "cordana_leaf_spot"),
    (["panama", "fusarium", "بنما", "فيوزاريوم", "ذبول"], "panama_disease"),
    (["bunchy", "قمة مجعدة", "التورد", "تورد"], "bunchy_top"),
]

# Crop keywords -> (crop label en/ar, candidate disease keys) for "crop named, disease unknown".
_CROP_KEYWORDS: list[tuple[list[str], tuple[str, str], list[str]]] = [
    (["tomato", "طماطم", "قوطة", "أوطة"], ("Tomato", "طماطم"),
     ["septoria_leaf_spot_tomato", "tomato_late_blight", "tomato_early_blight", "powdery_mildew"]),
    (["banana", "موز"], ("Banana", "موز"),
     ["sigatoka_leaf_spot", "cordana_leaf_spot", "panama_disease", "bunchy_top"]),
]

_TREATMENT_WORDS = [
    "treat", "treatment", "cure", "spray", "fungicide", "pesticide", "product", "dose", "price",
    "buy", "market", "علاج", "رش", "مبيد", "فطري", "جرعة", "سعر", "منتج", "السوق", "اشتري", "ارش",
]


def _resolve_language(question: str, language: str | None) -> str:
    if language in LANG_NAMES:
        return language  # type: ignore[return-value]
    if any("؀" <= ch <= "ۿ" for ch in question):
        return "ar"
    return "en"


def _disease_item(analysis: AnalysisResponse | None) -> FeatureResult | None:
    if not analysis:
        return None
    for item in analysis.results:
        if item.feature == "disease":
            return item
    return None


def _match_disease_key(question: str) -> str | None:
    q = question.lower()
    for words, key in _DISEASE_KEYWORDS:
        if any(word in q for word in words):
            return key
    return None


def _match_crop(question: str) -> tuple[tuple[str, str], list[str]] | None:
    q = question.lower()
    for words, label, keys in _CROP_KEYWORDS:
        if any(word in q for word in words):
            return label, keys
    return None


def _resolve_disease(analysis: AnalysisResponse | None, question: str) -> DiseaseInfo | None:
    """Pick the disease to ground on: first what the farmer named, then the analysis."""
    key = _match_disease_key(question)
    if key:
        return disease_info(key)
    disease = _disease_item(analysis)
    if disease and disease.disease_info:
        return disease.disease_info
    return None


def _with_price_sources(treatments: list[Treatment]) -> list[Treatment]:
    enriched: list[Treatment] = []
    for treatment in treatments:
        if treatment.price_sources:
            enriched.append(treatment)
            continue
        enriched.append(treatment.model_copy(update={"price_sources": price_sources_for_treatment(treatment)}))
    return enriched


def _format_price_sources(treatment: Treatment, lang: str, include_urls: bool = True) -> str:
    if not treatment.price_sources:
        return ""
    is_ar = lang == "ar"
    lines = ["   - فحص أسعار أونلاين:" if is_ar else "   - Online price checks:"]
    for source in treatment.price_sources[:3]:
        price = source.price_text or ("لا يوجد سعر مقروء" if is_ar else "no parsed price")
        availability = source.availability_ar if is_ar else source.availability_en
        note = source.note_ar if is_ar else source.note_en
        url_part = f"; {source.url}" if include_urls else ""
        lines.append(f"     • {source.source}: {source.title} — {price}; {availability}; checked {source.checked_at}{url_part}; {note}")
    return "\n".join(lines)


def _format_treatments(
    treatments: list[Treatment],
    lang: str,
    limit: int = 6,
    compact: bool = False,
    include_source_urls: bool = True,
) -> str:
    is_ar = lang == "ar"
    head = "برنامج الرش (الأحسن الأول):" if is_ar else "TREATMENT PROGRAM (most effective first):"
    lines = [head]
    for t in _with_price_sources(treatments[:limit]):
        name = t.name_ar if is_ar else t.name_en
        if compact:
            dose = t.dose_ar if is_ar else t.dose_en
            price = t.price_sources[0].price_text if t.price_sources and t.price_sources[0].price_text else (t.price_ar if is_ar else t.price_en)
            lines.append(f"{t.rank}) {name} — {dose}; {price}")
            continue
        dose = t.dose_ar if is_ar else t.dose_en
        app = t.application_ar if is_ar else t.application_en
        phi = t.phi_ar if is_ar else t.phi_en
        hazard = t.hazard_ar if is_ar else t.hazard_en
        price = t.price_ar if is_ar else t.price_en
        note = t.note_ar if is_ar else t.note_en
        if is_ar:
            lines.append(
                f"{t.rank}) {name} [FRAC {t.frac}]\n"
                f"   - الجرعة: {dose}\n   - الرش: {app}\n   - فترة الأمان: {phi}\n"
                f"   - الخطورة: {hazard}\n   - السعر المرجعي: {price}\n{_format_price_sources(t, lang, include_source_urls)}\n   - ليه بالترتيب ده: {note}"
            )
        else:
            lines.append(
                f"{t.rank}) {name} [FRAC {t.frac}]\n"
                f"   - Dose: {dose}\n   - Apply: {app}\n   - PHI: {phi}\n"
                f"   - Hazard: {hazard}\n   - Reference price: {price}\n{_format_price_sources(t, lang, include_source_urls)}\n   - Why this rank: {note}"
            )
    return "\n".join(lines)


def _disease_block(info: DiseaseInfo, lang: str) -> str:
    is_ar = lang == "ar"
    name = info.name_ar if is_ar else info.name_en
    summary = info.summary_ar if is_ar else info.summary_en
    crop = info.crop_ar if is_ar else info.crop_en
    head = "المرض المكتشف" if is_ar else "DETECTED CONDITION"
    crop_lead = f" ({crop})" if crop else ""
    block = [f"{head}: {name}{crop_lead}. {summary}"]
    management = (info.management_ar if is_ar else info.management_en)[:3]
    if management:
        block.append(("اعمل إيه: " if is_ar else "What to do: ") + " ".join(management))
    return "\n".join(block)


def _disease_brief(analysis: AnalysisResponse, lang: str, question: str = "") -> str:
    """Minimal grounding — used for the lean retry to keep reasoning small."""
    info = _resolve_disease(analysis, question)
    if not info:
        return ""
    block = _disease_block(info, lang)
    if info.treatments:
        block += "\n" + _format_treatments(info.treatments, lang, limit=3, compact=True)
    return block


def _grounding_text(analysis: AnalysisResponse, lang: str, question: str = "") -> str:
    """Grounding for the online model: disease + the full treatment program + key readings."""
    is_ar = lang == "ar"
    parts: list[str] = []

    info = _resolve_disease(analysis, question)
    if info:
        parts.append(_disease_block(info, lang))
        if info.treatments:
            parts.append(_format_treatments(info.treatments, lang, include_source_urls=False))
        else:
            parts.append(
                "لا يوجد علاج كيميائي موثّق لهذه الحالة في المرجع — ركّز على المكافحة الزراعية واسأل مهندس زراعي."
                if is_ar
                else "No reviewed chemical treatment for this condition in the reference — focus on cultural control and ask an agronomist."
            )
    else:
        crop = _match_crop(question)
        if crop:
            (_label_en, _label_ar), keys = crop
            names = [
                (disease_info(k).name_ar if is_ar else disease_info(k).name_en) for k in keys
            ]
            head = "أمراض شائعة في المحصول ده" if is_ar else "COMMON DISEASES FOR THIS CROP"
            parts.append(head + ": " + "؛ ".join(names))

    key_features = {"infection_extent", "resistant_varieties", "weather"}
    lines = [
        f"- {(item.title_ar if is_ar else item.title)}: {(item.value_ar if is_ar else item.value)}"
        for item in analysis.results
        if item.feature in key_features
    ]
    if lines:
        head2 = "قياسات الصورة" if is_ar else "IMAGE READINGS"
        parts.append(head2 + ":\n" + "\n".join(lines))

    if analysis.alerts:
        alert_texts = [(a.ar if is_ar else a.en) for a in analysis.alerts[:2]]
        parts.append(("تنبيهات: " if is_ar else "ALERTS: ") + " ".join(alert_texts))
    return "\n\n".join(parts)


def _post_chat(system: str, user: str, max_tokens: int) -> str:
    """One call to the configured chat endpoint; returns the visible answer text."""
    response = httpx.post(
        settings.external_llm_api_url,
        headers={
            "Authorization": f"Bearer {settings.external_llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.external_llm_model,
            "temperature": settings.external_llm_temperature,
            "max_tokens": max_tokens,
            "reasoning_effort": settings.external_llm_reasoning_effort,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=settings.external_llm_timeout_seconds,
    )
    response.raise_for_status()
    return (response.json()["choices"][0]["message"].get("content") or "").strip()


def _standalone_grounding(question: str, lang: str) -> str:
    info = _resolve_disease(None, question)
    parts: list[str] = []
    if info:
        parts.append(_disease_block(info, lang))
        if info.treatments:
            parts.append(_format_treatments(info.treatments, lang))
    crop = _match_crop(question)
    if crop and not info:
        (_label_en, _label_ar), keys = crop
        is_ar = lang == "ar"
        names = [(disease_info(k).name_ar if is_ar else disease_info(k).name_en) for k in keys]
        parts.append(("أمراض شائعة لهذا المحصول: " if is_ar else "COMMON DISEASES FOR THIS CROP: ") + ("؛ ".join(names) if is_ar else "; ".join(names)))
    tomato = tomato_grounding(question, lang)
    if tomato:
        parts.append(tomato)
    return "\n\n".join(parts)


def _external_answer(
    question: str,
    analysis: AnalysisResponse | None,
    lang: str,
    case_context: str | None = None,
) -> AssistantResponse:
    system = SYSTEM_PROMPTS[lang]
    user_lead = "سؤال المزارع" if lang == "ar" else "Farmer question"
    budget = settings.external_llm_max_tokens
    grounding = _standalone_grounding(question, lang)
    if analysis:
        info = _resolve_disease(analysis, question)
        case = question_guidance(question, analysis.crop, info.key if info else "", lang)
        if analysis.crop == "banana" or case:
            grounding = ""
        grounding = "\n\n".join(part for part in [_grounding_text(analysis, lang, question), case, grounding] if part)
    if case_context:
        label = "FRONTEND CASE CONTEXT" if lang == "en" else "سياق الحالة من التطبيق"
        grounding = "\n\n".join(part for part in [f"{label}:\n{case_context}", grounding] if part)

    answer = _post_chat(system, f"{user_lead}: {question}\n\n{grounding}", budget)
    if not answer:
        # Reasoning models can spend the whole budget before returning visible content.
        # Retry once with a lean prompt and a larger budget before the offline template.
        brief = _disease_brief(analysis, lang, question) if analysis else grounding
        answer = _post_chat(system, f"{user_lead}: {question}\n\n{brief}", budget + 1200)
    if not answer:
        raise ValueError("External assistant returned an empty answer.")
    return AssistantResponse(
        answer=answer,
        sources=[
            "Online grounded assistant",
            "AgroVision reviewed disease + treatment reference",
            *CROP_SOURCES,
            *CROP_SOURCE_URLS,
            *([f"Analysis {analysis.analysis_id}"] if analysis else []),
        ],
        mode="external-grounded-assistant",
    )


def _offline_answer(
    question: str,
    analysis: AnalysisResponse | None,
    lang: str,
    case_context: str | None = None,
) -> AssistantResponse:
    actions = SAFE_ACTIONS[lang]
    is_ar = lang == "ar"
    normalized = question.lower()
    sources = ["AgroVision reviewed bilingual treatment guidance"]
    if analysis:
        sources.append(f"Analysis {analysis.analysis_id}")

    water_words = ["water", "irrig", "ماء", "ري", "سقي", "رطوب"]
    disease_words = ["disease", "مرض", "تشخيص", "spot", "wilt", "virus", "فطر", "بقع", "ذبول"]
    wants_treatment = any(word in normalized for word in _TREATMENT_WORDS)
    info = _resolve_disease(analysis, question)
    context_question = f"{question}\n{case_context or ''}"
    has_named_disease = _match_disease_key(question) is not None

    # Treatment request → give the ranked spray program if we can identify the disease.
    if wants_treatment:
        if info and info.treatments:
            lead = f"علاج {info.name_ar}:\n" if is_ar else f"Treatment for {info.name_en}:\n"
            answer = lead + _format_treatments(info.treatments, lang) + "\n\n" + actions["consult_agronomist"]
        elif info and not info.treatments:
            answer = (
                (f"{info.name_ar}: مفيش علاج كيميائي موثّق ليه — المكافحة بتبقى زراعية (شيل وأعدم المصاب، أصناف مقاومة، نظافة الأرض). "
                 if is_ar else
                 f"{info.name_en}: there is no reviewed chemical cure — control is cultural (remove and destroy infected plants, resistant varieties, field sanitation). ")
                + actions["consult_agronomist"]
            )
        else:
            crop = _match_crop(question)
            if crop:
                (_en, _ar), keys = crop
                names = [(disease_info(k).name_ar if is_ar else disease_info(k).name_en) for k in keys]
                joiner = "؛ " if is_ar else "; "
                pick = ("قول لي المرض من دول عشان أديك برنامج الرش: " if is_ar
                        else "Tell me which of these it is and I'll give the spray program: ")
                answer = pick + joiner.join(names)
            else:
                answer = actions["name_crop"]
        return AssistantResponse(answer=answer, sources=sources, mode="grounded-case-answer")

    case_grounding = question_guidance(
        question,
        analysis.crop if analysis else "tomato",
        info.key if info else "",
        lang,
    )
    crop_grounding = (
        tomato_grounding(question, lang)
        if not case_grounding and (not analysis or analysis.crop == "tomato")
        else ""
    )

    if case_grounding or crop_grounding:
        answer = "\n\n".join(part for part in [case_grounding, crop_grounding] if part)
        return AssistantResponse(
            answer=answer,
            sources=["AgroVision reviewed tomato/banana guidance", *CROP_SOURCES, *CROP_SOURCE_URLS],
            mode="grounded-case-answer",
        )

    if any(word in normalized for word in water_words):
        answer = irrigation_scheme(analysis.crop if analysis else "tomato", lang)
    elif info and (has_named_disease or any(word in normalized for word in disease_words)):
        name = info.name_ar if is_ar else info.name_en
        summary = info.summary_ar if is_ar else info.summary_en
        management = (info.management_ar if is_ar else info.management_en)[:2]
        lead = f"التشخيص المبدئي: {name}. " if is_ar else f"Likely condition: {name}. "
        answer = lead + summary + " " + " ".join(management) + " " + actions["consult_agronomist"]
    elif any(word in normalized for word in disease_words):
        note = (
            "قول لي المحصول والأعراض عشان أحدّد المرض. "
            if is_ar
            else "Tell me the crop and the symptoms so I can identify the disease. "
        )
        answer = note + actions["name_crop"]
    else:
        intro = (
            "أقدر أشرح نتيجة التحليل وأديك برنامج العلاج. "
            if is_ar
            else "I can explain the result and give you the treatment program. "
        )
        answer = intro + actions["name_crop"]

    return AssistantResponse(answer=answer, sources=sources, mode="grounded-case-answer")


def answer_question(
    question: str,
    analysis: AnalysisResponse | None,
    language: str | None = None,
    case_context: str | None = None,
) -> AssistantResponse:
    lang = _resolve_language(question, language)
    context_question = f"{question}\n{case_context or ''}"
    has_grounding = bool(analysis or _standalone_grounding(context_question, lang) or case_context)
    if has_grounding and settings.external_llm_api_key and settings.external_llm_api_url:
        try:
            return _external_answer(context_question, analysis, lang, case_context)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            pass
    return _offline_answer(context_question, analysis, lang, case_context)
