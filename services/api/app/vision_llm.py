"""Real hosted vision second-opinion for tomato leaf diagnosis.

The local ONNX model (PlantVillage MobileNetV2) is lab-trained and unreliable on
real field photos. To get an honest answer on real photos we ask a hosted
multimodal model to look at the same leaf and rank the likely tomato disease,
then the fusion layer (``diagnosis_evidence.fuse_diagnosis``) combines the two.

This module is a SECOND OPINION, never a single source of truth:

* It is constrained to the app's known tomato disease set and must say when it is
  *not sure* or when the image is *not a tomato leaf*.
* Its confidence is one uncalibrated signal, never treated as ground truth.
* Any missing key, disabled flag, timeout, HTTP error, or unparsable answer
  returns ``None`` so diagnosis falls back to the local model alone. It never
  blocks the request and never fabricates a result.

The chat assistant model (``deepseek-v4-flash-free``) is text-only and rejects
images, so vision uses its own multimodal model (``external_vision_model``,
default ``mimo-v2.5-free``) on the same OpenAI-compatible gateway and API key.
"""

from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import dataclass, field

import httpx
from PIL import Image

from .config import settings


# Tomato diagnoses the vision model may choose from -> internal knowledge-base key.
# Names are the human labels sent in the prompt; keys match ``diseases.py``.
VISION_DISEASE_CHOICES: dict[str, str] = {
    "Septoria leaf spot": "septoria_leaf_spot_tomato",
    "Early blight": "tomato_early_blight",
    "Late blight": "tomato_late_blight",
    "Bacterial spot": "tomato_bacterial_spot",
    "Leaf mold": "tomato_leaf_mold",
    "Target spot": "tomato_target_spot",
    "Spider mites": "tomato_spider_mites",
    "Yellow leaf curl virus": "tomato_yellow_leaf_curl_virus",
    "Mosaic virus": "tomato_mosaic_virus",
    "Powdery mildew": "powdery_mildew",
    "Healthy": "healthy",
}

# Substring aliases (checked after exact match) so wording variants still map home.
_ALIASES: list[tuple[str, str]] = [
    ("septoria", "septoria_leaf_spot_tomato"),
    ("early blight", "tomato_early_blight"),
    ("alternaria", "tomato_early_blight"),
    ("late blight", "tomato_late_blight"),
    ("phytophthora", "tomato_late_blight"),
    ("bacterial spot", "tomato_bacterial_spot"),
    ("bacterial leaf spot", "tomato_bacterial_spot"),
    ("bacterial speck", "tomato_bacterial_spot"),
    ("xanthomonas", "tomato_bacterial_spot"),
    ("leaf mold", "tomato_leaf_mold"),
    ("leaf mould", "tomato_leaf_mold"),
    ("target spot", "tomato_target_spot"),
    ("corynespora", "tomato_target_spot"),
    ("spider mite", "tomato_spider_mites"),
    ("two-spotted", "tomato_spider_mites"),
    ("two spotted", "tomato_spider_mites"),
    ("yellow leaf curl", "tomato_yellow_leaf_curl_virus"),
    ("tylcv", "tomato_yellow_leaf_curl_virus"),
    ("leaf curl", "tomato_yellow_leaf_curl_virus"),
    ("mosaic", "tomato_mosaic_virus"),
    ("tomv", "tomato_mosaic_virus"),
    ("tmv", "tomato_mosaic_virus"),
    ("powdery mildew", "powdery_mildew"),
    ("downy mildew", "downy_mildew"),
    ("healthy", "healthy"),
    ("no disease", "healthy"),
    ("no visible disease", "healthy"),
]

_SYSTEM_PROMPT = (
    "You are a tomato plant pathologist helping Egyptian farmers. Look ONLY at the "
    "leaf photo and decide the most likely tomato disease. Choose disease names ONLY "
    "from this list: " + "; ".join(VISION_DISEASE_CHOICES) + ". "
    "Be strictly honest: if the photo is blurry, too far, or not a tomato leaf, set "
    "is_tomato_leaf or not_sure appropriately and lower your confidence. Never invent "
    "a disease outside the list. Confidence is your visual certainty from 0 to 100. "
    "Reply with ONLY a compact JSON object, no prose and no markdown fences, using "
    'exactly these keys: {"is_tomato_leaf": true/false, "not_sure": true/false, '
    '"top": [{"disease": "<name from the list>", "confidence": 0-100}], '
    '"visible_signs": "<short phrase>"}. Give up to 3 ranked items in "top".'
)


@dataclass(frozen=True)
class VisionRanked:
    key: str
    name: str
    confidence: float  # 0..1


@dataclass(frozen=True)
class VisionDiagnosis:
    is_tomato_leaf: bool
    not_sure: bool
    ranked: list[VisionRanked] = field(default_factory=list)
    visible_signs: str = ""
    model: str = ""
    provider: str = "external-vision"
    latency_ms: int = 0
    raw: str = ""


def vision_enabled() -> bool:
    """Whether a real hosted vision call is configured and switched on."""
    return bool(
        settings.external_vision_enabled
        and settings.external_llm_api_key
        and settings.external_llm_api_url
    )


def resolve_disease_key(name: str) -> str | None:
    """Map a free-text disease name from the model onto an internal KB key."""
    text = (name or "").strip().lower()
    if not text:
        return None
    for label, key in VISION_DISEASE_CHOICES.items():
        if text == label.lower():
            return key
    for needle, key in _ALIASES:
        if needle in text:
            return key
    return None


def _image_data_url(image: Image.Image) -> str:
    """JPEG-encode (down-scaled) the leaf image as a base64 data URL."""
    sample = image.convert("RGB")
    longest = max(sample.size)
    limit = settings.external_vision_max_side_px
    if longest > limit:
        scale = limit / longest
        sample = sample.resize((round(sample.width * scale), round(sample.height * scale)), Image.LANCZOS)
    buffer = io.BytesIO()
    sample.save(buffer, format="JPEG", quality=88)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _extract_json(content: str) -> dict | None:
    """Parse the model's reply into a dict, tolerating fences and surrounding prose."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_vision_payload(content: str, *, model: str, provider: str, latency_ms: int) -> VisionDiagnosis | None:
    """Turn the raw model reply into a VisionDiagnosis, or None if unusable."""
    data = _extract_json(content)
    if data is None:
        return None

    ranked: list[VisionRanked] = []
    seen: set[str] = set()
    for item in data.get("top", []) or []:
        if not isinstance(item, dict):
            continue
        key = resolve_disease_key(str(item.get("disease", "")))
        if not key or key in seen:
            continue
        try:
            confidence = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence / 100.0 if confidence > 1 else confidence))
        ranked.append(VisionRanked(key=key, name=str(item.get("disease", "")).strip(), confidence=confidence))
        seen.add(key)
    ranked.sort(key=lambda r: r.confidence, reverse=True)

    is_tomato = bool(data.get("is_tomato_leaf", True))
    not_sure = bool(data.get("not_sure", False)) or not ranked
    return VisionDiagnosis(
        is_tomato_leaf=is_tomato,
        not_sure=not_sure,
        ranked=ranked[:3],
        visible_signs=str(data.get("visible_signs", "")).strip()[:200],
        model=model,
        provider=provider,
        latency_ms=latency_ms,
        raw=content[:500],
    )


def _post_vision(data_url: str, max_tokens: int) -> str:
    """One multimodal call; returns the visible answer text (may be empty)."""
    body = {
        "model": settings.external_vision_model,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        # mimo is a reasoning model; keep hidden reasoning small so the JSON answer fits.
        "reasoning_effort": settings.external_llm_reasoning_effort,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Diagnose this tomato leaf. Egyptian field photo."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    }
    response = httpx.post(
        settings.external_llm_api_url,
        headers={
            "Authorization": f"Bearer {settings.external_llm_api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=settings.external_vision_timeout_seconds,
    )
    response.raise_for_status()
    return (response.json()["choices"][0]["message"].get("content") or "").strip()


def vision_diagnose(image: Image.Image) -> VisionDiagnosis | None:
    """Ask the hosted vision model for an honest tomato diagnosis; None on any failure."""
    if not vision_enabled():
        return None
    try:
        data_url = _image_data_url(image)
        started = time.perf_counter()
        content = _post_vision(data_url, settings.external_vision_max_tokens)
        if not content:
            # Reasoning models can spend the whole budget before emitting the answer.
            content = _post_vision(data_url, settings.external_vision_max_tokens + 1500)
        latency_ms = int((time.perf_counter() - started) * 1000)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, OSError):
        return None
    if not content:
        return None
    return parse_vision_payload(
        content,
        model=settings.external_vision_model,
        provider="external-vision",
        latency_ms=latency_ms,
    )
