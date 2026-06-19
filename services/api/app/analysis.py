from __future__ import annotations

import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import psutil
from PIL import Image

from .calibration import TARGET_SPOT_KEY, confusion_group, uncertainty_explanation
from .case_guidance import case_questions, diagnosis_verification_questions, resistant_varieties, resistant_variety_note
from .config import settings
from .diagnosis_evidence import assess_visual_prediction, fuse_diagnosis, fused_named_candidates
from .diseases import disease_info
from .target_spot import supporting_lines, target_spot_evidence
from .model_runtime import DiseaseRuntime, runtime_for_crop
from .schemas import (
    AnalysisResponse,
    DiagnosisCandidateLite,
    DiseaseInfo,
    FeatureResult,
    LocalizedText,
    ValidationLevel,
)
from .vision_llm import VisionDiagnosis
from .weather import WeatherObservation


def _loc(en: str, ar: str) -> LocalizedText:
    return LocalizedText(en=en, ar=ar)


def _rgb(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def _tile_indices(image: Image.Image) -> dict[str, float]:
    array = _rgb(image)
    red, green, blue = array[..., 0], array[..., 1], array[..., 2]
    exg = 2 * green - red - blue
    vari = (green - red) / (green + red - blue + 1e-4)
    mask = (exg > 0.12) & (green > red) & (green > blue)
    return {
        "coverage": float(mask.mean()),
        "exg": float(np.clip(exg.mean(), -1, 1)),
        "vari": float(np.clip(np.nanmean(vari), -1, 1)),
        "yellow": float(((red > 0.45) & (green > 0.40) & (blue < 0.35)).mean()),
        "dark": float((array.mean(axis=2) < 0.2).mean()),
    }


def vegetation_indices(image: Image.Image) -> dict[str, float]:
    tiles = [
        image.crop((x, y, min(x + settings.tile_size, image.width), min(y + settings.tile_size, image.height)))
        for y in range(0, image.height, settings.tile_size)
        for x in range(0, image.width, settings.tile_size)
    ]
    with ThreadPoolExecutor(max_workers=settings.max_tile_workers) as executor:
        results = list(executor.map(_tile_indices, tiles))
    return {key: float(np.mean([result[key] for result in results])) for key in results[0]}


def _count_components(mask: np.ndarray, min_pixels: int = 12) -> int:
    mask = mask.astype(bool)
    visited = np.zeros_like(mask, dtype=bool)
    count = 0
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            size = 0
            queue = deque([(y, x)])
            visited[y, x] = True
            while queue:
                cy, cx = queue.popleft()
                size += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))
            if size >= min_pixels:
                count += 1
    return count


def plant_count(image: Image.Image) -> int:
    sample = image.convert("RGB")
    sample.thumbnail((384, 384))
    array = _rgb(sample)
    mask = (2 * array[..., 1] - array[..., 0] - array[..., 2]) > 0.22
    return _count_components(mask)


def infection_extent(image: Image.Image) -> float:
    """Estimate visibly discoloured leaf area; this is not biological severity."""
    sample = image.convert("RGB")
    sample.thumbnail((512, 512))
    array = _rgb(sample)
    red, green, blue = array[..., 0], array[..., 1], array[..., 2]
    leaf_like = (green > 0.18) & (blue < 0.48) & ((green > red * 0.68) | (red > green * 1.05))
    yellow = (red > 0.45) & (green > 0.38) & (blue < 0.34)
    brown = (red > green * 1.12) & (green > blue * 1.25) & (red > 0.25)
    denominator = int(leaf_like.sum())
    return float(((yellow | brown) & leaf_like).sum() / denominator) if denominator else 0.0


def _result(
    feature: str,
    title: str,
    title_ar: str,
    level: ValidationLevel,
    score: float,
    value: str,
    value_ar: str,
    confidence: float,
    evidence: list[str],
    limitation: str | None = None,
    disease: DiseaseInfo | None = None,
) -> FeatureResult:
    return FeatureResult(
        feature=feature,
        title=title,
        title_ar=title_ar,
        level=level,
        score=float(np.clip(score, 0, 1)),
        value=value,
        value_ar=value_ar,
        confidence=float(np.clip(confidence, 0, 1)),
        evidence=evidence,
        limitation=limitation,
        disease_info=disease,
    )


def _weather_card(weather: WeatherObservation | None) -> FeatureResult:
    if weather:
        is_reference = weather.source.startswith("Egypt demo")
        return _result(
            "weather",
            "Egypt weather reference",
            "طقس مصر المرجعي",
            ValidationLevel.SAMPLE_DATA if is_reference else ValidationLevel.VALIDATED,
            1.0,
            f"{weather.temperature_c:.0f}°C, {weather.condition}, wind {weather.wind_kph:.0f} km/h",
            f"{weather.temperature_c:.0f}°م، {weather.condition_ar}، رياح {weather.wind_kph:.0f} كم/س",
            0.6 if is_reference else 0.9,
            [
                f"Source: {weather.source}",
                f"Precipitation: {weather.precipitation_mm:.1f} mm",
            ],
            (
                "Fixed Egypt demo reference, not live weather. Check your local forecast before irrigation or spraying."
                if is_reference
                else "Regional live reading; conditions inside the field or greenhouse can differ."
            ),
        )
    return _result(
        "weather",
        "Weather (live)",
        "الطقس (مباشر)",
        ValidationLevel.SAMPLE_DATA,
        0.0,
        "No live weather source connected",
        "مفيش مصدر طقس مباشر متصل",
        0.0,
        ["The weather provider is disabled or currently unreachable."],
        "Turn on internet access so we can show the real local weather. We do not show made-up numbers.",
    )


def analyze_image(
    image: Image.Image,
    filename: str,
    runtime: DiseaseRuntime | None = None,
    weather: WeatherObservation | None = None,
    crop: str | None = "tomato",
    vision: VisionDiagnosis | None = None,
) -> AnalysisResponse:
    started = time.perf_counter()
    crop = "tomato"
    runtime = runtime or runtime_for_crop(crop)
    before_memory = psutil.Process().memory_info().rss
    indices = vegetation_indices(image)
    visible_extent = infection_extent(image)
    disease = runtime.predict(image)
    yellow_fraction = float(np.clip(indices["yellow"], 0, 1))
    dark_fraction = float(np.clip(indices["dark"], 0, 1))
    leaf_visible = indices["coverage"]  # fraction of green leaf pixels in the photo
    assessment = assess_visual_prediction(disease, crop, leaf_visible)
    fused = fuse_diagnosis(assessment, vision, crop)
    state = fused.state
    not_enough_info = state in {"not_sure", "not_tomato"}
    screening = state == "screening"
    confident = state == "confident"
    top_prob = fused.confidence
    possibilities = [(disease_info(key), score) for key, score in fused.ranked]

    if not_enough_info:
        disease_information = disease_info("possible_leaf_disease")
        if state == "not_tomato":
            disease_value = "This photo may not be a clear tomato leaf"
            disease_ar = "الصورة دي ممكن ما تكونش ورقة طماطم واضحة"
        else:
            disease_value = f"No reliable {crop} diagnosis from this photo"
            disease_ar = "المعلومات مش كفاية للتشخيص من الصورة دي"
        disease_card_level = ValidationLevel.SAMPLE_DATA
        disease_limitation = " ".join([*fused.reasons, *fused.limitations])
    else:
        disease_information = disease_info(fused.top_key)
        if disease_information.key == "healthy":
            disease_card_level = ValidationLevel.EXPERIMENTAL
            disease_value = f"Strong healthy visual match ({top_prob:.0%}) — keep monitoring"
            disease_ar = f"شكلها سليمة — مفيش مرض اتطابق ({top_prob:.0%})"
        elif screening and fused.group_promoted:
            disease_card_level = ValidationLevel.EXPERIMENTAL
            disease_value = (
                f"Probable {disease_information.name_en} ({top_prob:.0%}) — medium confidence; "
                "shares symptoms with look-alikes, confirm"
            )
            disease_ar = (
                f"الأرجح {disease_information.name_ar} ({top_prob:.0%}) — ثقة متوسطة؛ "
                "بيشبه أمراض تانية، أكّد"
            )
        elif screening:
            disease_card_level = ValidationLevel.EXPERIMENTAL
            disease_value = f"Most likely (screening): {disease_information.name_en} ({top_prob:.0%}) — not confirmed, verify"
            disease_ar = f"الأرجح (فرز مبدئي): {disease_information.name_ar} ({top_prob:.0%}) — مش مؤكد، أكّد"
        else:
            disease_card_level = ValidationLevel.EXPERIMENTAL
            disease_value = f"Strong visual match: {disease_information.name_en} ({top_prob:.0%}) — verify symptoms"
            disease_ar = f"تطابق بصري قوي: {disease_information.name_ar} ({top_prob:.0%}) — أكّد الأعراض"
        lead = (
            "This is a screening match from combining the local model and the AI second opinion; it still needs confirmation."
            if screening
            else "This passed the visual-match quality gates, but it is not a confirmed diagnosis."
        )
        disease_limitation = " ".join([lead, *fused.limitations])

    # Image-derived supporting evidence (never proof). Computed whenever the
    # reported disease is in the Target-Spot look-alike group so the report can
    # show concrete signs the farmer can check against the leaf.
    visual_evidence: list[LocalizedText] = []
    if not not_enough_info and fused.top_key in confusion_group(TARGET_SPOT_KEY):
        ts = target_spot_evidence(image)
        visual_evidence = [
            _loc(en, ar)
            for en, ar in zip(supporting_lines(ts, "en"), supporting_lines(ts, "ar"))
        ]

    model_name = getattr(getattr(runtime, "model_path", None), "name", runtime.__class__.__name__)
    disease_evidence = [
        f"Model: {model_name} ({disease.provider})",
        f"Crop selected by user: {crop}",
        *fused.evidence,
        f"Crop-label support: {fused.crop_probability_mass:.0%}",
        f"Top-match separation: {fused.margin:.0%}",
        *([f"Top match: {top_prob:.0%}"] if not not_enough_info else []),
        *([
            f"Raw model confidence {fused.raw_confidence:.0%} vs calibrated {top_prob:.0%} "
            f"({fused.calibration_method})"
        ] if not not_enough_info else []),
        *([f"Uncertainty: {fused.uncertainty_level} — {uncertainty_explanation(fused.uncertainty_level)}"]
          if fused.uncertainty_level else []),
        *([f"Supporting visual signs: {ev.en}" for ev in visual_evidence]),
        *([
            "Possibilities: " + ", ".join(f"{info.name_en} {p:.0%}" for info, p in possibilities)
        ] if possibilities else []),
    ]

    variety_names = resistant_varieties(crop, disease_information.key) if confident else []
    extent_label = "Low" if visible_extent < 0.15 else "Moderate" if visible_extent < 0.35 else "High"
    extent_label_ar = "منخفض" if visible_extent < 0.15 else "متوسط" if visible_extent < 0.35 else "مرتفع"

    results = [
        _result("disease", "Disease check (AI)", "كشف المرض (ذكاء)",
                disease_card_level, top_prob, disease_value, disease_ar, top_prob,
                disease_evidence, disease_limitation, disease=disease_information),
        _result("infection_extent", "Visible infection extent", "مدى الإصابة الظاهر",
                ValidationLevel.EXPERIMENTAL, visible_extent,
                f"{extent_label}: about {visible_extent:.0%} visibly affected",
                f"{extent_label_ar}: حوالي {visible_extent:.0%} متأثر ظاهريًا", 0.55,
                [
                    f"Visible discoloration estimate: {visible_extent:.1%}",
                    f"Yellow-pixel clue: {yellow_fraction:.1%}",
                    f"Dark-pixel clue: {dark_fraction:.1%}",
                ],
                "Visual discoloration estimate only. Shadows, old leaves, nutrient stress, and background can change it."),
        _result("resistant_varieties", "Resistant variety options", "خيارات أصناف مقاومة",
                ValidationLevel.SAMPLE_DATA, 0,
                ", ".join(variety_names) if variety_names else "Confirm the disease before choosing resistance traits",
                "، ".join(variety_names) if variety_names else "أكّد المرض قبل اختيار صفات المقاومة",
                0.7 if variety_names else 0,
                [resistant_variety_note(crop, disease_information.key, "en")] if variety_names else [
                    "A low-confidence image match is not enough to recommend disease-specific varieties."
                ],
                "Verify disease resistance codes, local availability, and Egyptian growing performance before buying seed or planting material."),
        _weather_card(weather),
    ]

    alerts: list[LocalizedText] = []
    if not_enough_info:
        reason = fused.reasons[0] if fused.reasons else "The visual evidence is insufficient."
        alerts.append(_loc(
            f"No reliable {crop} diagnosis. {reason} Do not choose a treatment from this image alone.",
            "مقدرناش نشخّص الصورة دي بثقة. اختار محصولك، صوّر ورقة واضحة تاني، أو اسأل المساعد.",
        ))
    elif screening:
        alerts.append(_loc(
            f"Screening result only: most likely {disease_information.name_en}, but the models are not fully sure. Confirm the symptoms before any treatment.",
            f"نتيجة فرز مبدئي بس: الأرجح {disease_information.name_ar}، بس النماذج مش متأكدة تمامًا. أكّد الأعراض قبل أي علاج.",
        ))
    elif disease_information.key != "healthy":
        alerts.append(_loc(
            f"Strong visual match only: {disease_information.name_en}. Confirm the listed symptoms and affected plant part before treatment.",
            f"تطابق بصري قوي فقط: {disease_information.name_ar}. أكّد الأعراض والجزء المصاب قبل العلاج.",
        ))
    if yellow_fraction > 0.25:
        alerts.append(_loc(
            "A lot of yellowing was measured in the photo; check the leaves closely.",
            "اتقاس اصفرار كتير في الصورة؛ بصّ على الورق كويس.",
        ))
    if dark_fraction > 0.30:
        alerts.append(_loc(
            "A lot of dark spotting/shadow was measured; make sure the photo is well lit and check the leaves.",
            "اتقاس بقع غامقة/ظل كتير؛ اتأكد إن الصورة مضيّة كويس وبصّ على الورق.",
        ))
    if weather and weather.temperature_c >= 35:
        alerts.append(_loc(
            "High temperature now; avoid spraying in the heat (burns leaves) and watch for heat/water stress.",
            "الحر عالي دلوقتي؛ ما ترشّش في الحر (بيحرق الورق) وخلّي بالك من إجهاد الحر والري.",
        ))

    recommendations = [
        _loc(
            "Look at the affected leaves yourself before you spray anything.",
            "بصّ على الورق المصاب بنفسك قبل ما ترش أي حاجة.",
        ),
        _loc(
            "Read the product label and confirm the current price with your local dealer.",
            "اقرا لافتة المنتج وأكّد السعر الحالي من محل المبيدات عندك.",
        ),
    ]
    if not_enough_info:
        recommendations.insert(0, _loc(
            "Do not select a treatment yet. Retake a close leaf photo plus a whole-plant photo and answer the symptom questions.",
            "ما تختارش علاج دلوقتي. صوّر الورقة من قريب والنبات كله وجاوب على أسئلة الأعراض.",
        ))
    elif screening:
        recommendations.insert(0, _loc(
            "This is a screening result, not a confirmed diagnosis. Start the safe protection steps and confirm the disease before any spraying.",
            "دي نتيجة فرز مبدئي مش تشخيص مؤكد. ابدأ خطوات الوقاية الآمنة وأكّد المرض قبل أي رش.",
        ))
    else:
        recommendations.insert(0, _loc(
            "Use the case workspace to confirm symptoms and affected plant parts before choosing any treatment.",
            "استخدم ملف الحالة لتأكيد الأعراض والجزء المصاب قبل اختيار أي علاج.",
        ))
    if weather and weather.precipitation_mm > 0:
        recommendations.append(_loc(
            "Rain is reported now; check field moisture before irrigating and don't spray right before rain.",
            "في مطر دلوقتي؛ اتأكد من رطوبة الأرض قبل الري وما ترشّش قبل المطر على طول.",
        ))

    after_memory = psutil.Process().memory_info().rss
    return AnalysisResponse(
        analysis_id=str(uuid.uuid4()),
        filename=filename,
        crop=crop,
        width=image.width,
        height=image.height,
        processing_ms=int((time.perf_counter() - started) * 1000),
        peak_memory_mb=round(max(after_memory, before_memory) / 1024 / 1024, 2),
        provider=disease.provider,
        results=results,
        alerts=alerts,
        recommendations=recommendations,
        assistant_questions=(
            diagnosis_verification_questions(crop)
            if not_enough_info
            else case_questions(crop, disease_information.name_en, disease_information.name_ar)
        ),
        fused_state=state,
        diagnosis_candidates=[
            DiagnosisCandidateLite(disease=name, confidence=confidence)
            for name, confidence in fused_named_candidates(fused)
        ],
        raw_confidence=float(np.clip(fused.raw_confidence, 0, 1)),
        calibrated_confidence=float(np.clip(top_prob, 0, 1)),
        calibration_method=fused.calibration_method,
        uncertainty_level=fused.uncertainty_level,
        visual_evidence=visual_evidence,
        image_measurements={
            "image_visible_discoloration_percent": round(visible_extent * 100, 1),
            "image_yellow_pixel_percent": round(yellow_fraction * 100, 1),
            "image_dark_pixel_percent": round(dark_fraction * 100, 1),
            "image_green_coverage_percent": round(float(np.clip(indices["coverage"], 0, 1)) * 100, 1),
            "image_width_px": float(image.width),
            "image_height_px": float(image.height),
        },
    )
