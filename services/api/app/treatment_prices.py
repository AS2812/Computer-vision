from __future__ import annotations

import re
from html import unescape
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import httpx

from .schemas import PriceEvidence, Treatment


@dataclass(frozen=True)
class PriceSource:
    product_terms: tuple[str, ...]
    page_terms: tuple[str, ...]
    source: str
    title: str
    url: str
    note_en: str
    note_ar: str


PRICE_SOURCES: tuple[PriceSource, ...] = (
    PriceSource(
        product_terms=("metalaxyl", "ridomil"),
        page_terms=("ريدوميل جولد", "Ridomil"),
        source="AgriCash",
        title="Ridomil Gold MZ 68% WG 400 g",
        url="https://kz.agricash.app/shop/ridomil-gold/",
        note_en="Egyptian online retail page; verify APC registration, label, pack size, and stock before buying.",
        note_ar="صفحة بيع أونلاين داخل مصر؛ أكّد التسجيل في لجنة المبيدات والعبوة والتوفر قبل الشراء.",
    ),
    PriceSource(
        product_terms=("metalaxyl", "ridomil"),
        page_terms=("RidomilGold", "ريدوميل"),
        source="Cowboyzz Egypt",
        title="RidomilGold MZ 68%",
        url="https://cowboyzz.com/products/ridomilgold-mz-68-%D8%B1%D9%8A%D8%AF%D9%88%D9%85%D9%8A%D9%84-%D8%AC%D9%88%D9%84%D8%AF-68-%D8%A7%D9%85-%D8%B0%D8%AF",
        note_en="Egyptian online retail page; page may show sold-out stock.",
        note_ar="صفحة بيع أونلاين داخل مصر؛ ممكن تعرض أن المنتج غير متوفر.",
    ),
    PriceSource(
        product_terms=("mandipropamid", "revus"),
        page_terms=("Revus Top", "ريفوس توب"),
        source="ERADCO",
        title="Revus Top 500 SC",
        url="https://eradco.online/ar/%D8%B1%D9%8A%D9%81%D9%88%D8%B3-%D8%AA%D9%88%D8%A8-500-%D8%A5%D8%B3-%D8%B3%D9%8A---syngenta---%D8%A5%D9%8A%D8%B1%D8%A7%D8%AF%D9%83%D9%88/p1170295695",
        note_en="Retail/supplier page for a mandipropamid + difenoconazole product; confirm the exact formulation.",
        note_ar="صفحة مورد/بيع لمنتج مانديبروباميد + ديفينوكونازول؛ أكّد التركيب بالضبط.",
    ),
    PriceSource(
        product_terms=("chlorothalonil", "bravo", "daconil"),
        page_terms=("مورفيس", "Chlorothalonil"),
        source="AgriMisr",
        title="Morfus 72% SC chlorothalonil",
        url="https://agrimisr.com/index.php?category_id=834&dispatch=categories.view&items_per_page=48&sort_by=popularity&sort_order=desc%402376%3A8%3A2363%3A7%3A2379%3A8",
        note_en="Marketplace category page; price is parsed near the matching product name when available.",
        note_ar="صفحة سوق إلكتروني؛ السعر يُقرأ قرب اسم المنتج المطابق عند توفره.",
    ),
    PriceSource(
        product_terms=("mancozeb", "dithane", "penncozeb"),
        page_terms=("مانكوزيب", "mancozeb", "بوليرام"),
        source="AgriMisr",
        title="Mancozeb-family fungicide listings",
        url="https://agrimisr.com/index.php?category_id=834&dispatch=categories.view&items_per_page=48&sort_by=popularity&sort_order=desc%402376%3A8%3A2363%3A7%3A2379%3A8",
        note_en="Marketplace listings for mancozeb-family products; compare active ingredient and concentration.",
        note_ar="قوائم سوق لمنتجات عائلة المانكوزيب؛ قارن المادة الفعالة والتركيز قبل الشراء.",
    ),
    PriceSource(
        product_terms=("mancozeb", "dithane", "penncozeb"),
        page_terms=("هاي مانكو", "مانكوزيب 80"),
        source="AgroKima",
        title="Hi-Manco 80% mancozeb 750 g",
        url="https://agrokima.com/ar/products/hi-manco-750g",
        note_en="Supplier product page; may list product without a usable retail price.",
        note_ar="صفحة مورد للمنتج؛ قد تعرض المنتج بدون سعر بيع واضح.",
    ),
    PriceSource(
        product_terms=("copper", "kocide", "champion", "cupravit"),
        page_terms=("البركة", "شامبيون", "كبريتات النحاس", "Copper"),
        source="AgriMisr",
        title="Copper fungicide listings",
        url="https://agrimisr.com/index.php?category_id=834&dispatch=categories.view&items_per_page=48&sort_by=popularity&sort_order=desc%402376%3A8%3A2363%3A7%3A2379%3A8",
        note_en="Marketplace category page for copper products; verify active ingredient and crop label.",
        note_ar="صفحة سوق لمنتجات النحاس؛ أكّد المادة الفعالة ولافتة محصول الطماطم.",
    ),
    PriceSource(
        product_terms=("sulfur", "thiovit", "kumulus"),
        page_terms=("كبريت", "سلفور"),
        source="AgriMisr",
        title="Wettable sulfur listings",
        url="https://agrimisr.com/index.php?category_id=834&dispatch=categories.view&items_per_page=48&sort_by=popularity&sort_order=desc%402376%3A8%3A2363%3A7%3A2379%3A8",
        note_en="Marketplace category page for sulfur products; do not spray sulfur in high heat.",
        note_ar="صفحة سوق لمنتجات الكبريت؛ لا ترش الكبريت في الحر العالي.",
    ),
    PriceSource(
        product_terms=("difenoconazole 25", "score"),
        page_terms=("بيكول", "Difenoconazole", "ديفينوكونازول"),
        source="AgriMisr",
        title="Difenoconazole-family listings",
        url="https://agrimisr.com/index.php?category_id=834&dispatch=categories.view&items_per_page=48&sort_by=popularity&sort_order=desc%402376%3A8%3A2363%3A7%3A2379%3A8",
        note_en="Marketplace category page; confirm this is registered for tomato and the diagnosed disease.",
        note_ar="صفحة سوق؛ أكّد تسجيل المنتج للطماطم والمرض قبل الاستخدام.",
    ),
    PriceSource(
        product_terms=("azoxystrobin", "ortiva", "amistar"),
        page_terms=("أزوكسي", "كابريو", "Ortiva", "Amistar"),
        source="AgriMisr",
        title="Azoxystrobin-family listings",
        url="https://agrimisr.com/index.php?category_id=834&dispatch=categories.view&items_per_page=48&sort_by=popularity&sort_order=desc%402376%3A8%3A2363%3A7%3A2379%3A8",
        note_en="Marketplace category page; compare active ingredient because names vary.",
        note_ar="صفحة سوق؛ قارن المادة الفعالة لأن الأسماء التجارية تختلف.",
    ),
)


def _normalize(text: str) -> str:
    text = text.replace("\u200e", " ").replace("\u200f", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _strip_html(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return _normalize(unescape(text))


def _price_matches(text: str) -> list[tuple[int, str]]:
    patterns = (
        r"(?:EGP|LE)\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?",
        r"[0-9][0-9,]*(?:\.[0-9]{1,2})?\s*(?:EGP|LE)",
        r"(?:جم|جنيه)\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?",
    )
    seen: list[tuple[int, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            value = match.group(0).strip()
            if re.search(r"\b0(?:\.00)?\b", value):
                continue
            if value not in [item[1] for item in seen]:
                seen.append((match.start(), value))
    return seen


def _price_candidates(text: str, anchor_idx: int | None = None) -> list[str]:
    matches = _price_matches(text)
    if anchor_idx is not None:
        matches = [m for m in matches if abs(m[0] - anchor_idx) <= 650]
        matches.sort(key=lambda m: abs(m[0] - anchor_idx))
    return [value for _, value in matches[:3]]


def _availability(text: str) -> tuple[str, str]:
    low = text.lower()
    if any(token in low for token in ("sold out", "غير متوفر", "انتهى", "out of stock")):
        return "not available online", "غير متوفر أونلاين"
    if any(token in low for token in ("add to cart", "إضافة إلى السلة", "متوفر بالمخزون", "اطلب الآن")):
        return "available online", "متوفر أونلاين"
    return "check stock", "أكّد التوفر"


def _focused_window(text: str, terms: tuple[str, ...]) -> tuple[str, bool]:
    lowered = text.lower()
    for term in terms:
        idx = lowered.find(term.lower())
        if idx != -1:
            return text[max(0, idx - 180) : idx + 650], True
    return text[:1200], False


def _term_index(text: str, terms: tuple[str, ...]) -> int | None:
    lowered = text.lower()
    found = [lowered.find(term.lower()) for term in terms]
    found = [idx for idx in found if idx != -1]
    return min(found) if found else None


@lru_cache(maxsize=32)
def _fetch_text(url: str, timeout_seconds: float) -> tuple[bool, str]:
    try:
        response = httpx.get(
            url,
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "AgroVisionEgypt/0.1 price-check"},
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return False, ""
    return True, _strip_html(response.text)


def _evidence_for_source(source: PriceSource, timeout_seconds: float) -> PriceEvidence:
    checked_at = datetime.now(timezone.utc).date().isoformat()
    ok, text = _fetch_text(source.url, timeout_seconds)
    if not ok:
        return PriceEvidence(
            source=source.source,
            title=source.title,
            url=source.url,
            availability_en="source unreachable",
            availability_ar="المصدر غير متاح",
            checked_at=checked_at,
            live=False,
            note_en=f"{source.note_en} Could not read the page during this check.",
            note_ar=f"{source.note_ar} لم نقدر نقرأ الصفحة في هذا الفحص.",
        )

    focused, matched_term = _focused_window(text, source.page_terms)
    term_idx = _term_index(text, source.page_terms)
    prices = _price_candidates(text, term_idx) if matched_term else []
    is_listing_page = "category_id=" in source.url or "/categories/" in source.url
    if is_listing_page:
        prices = prices[:1]
    if not prices and matched_term and not is_listing_page:
        prices = _price_candidates(text)[:1]
    availability_en, availability_ar = _availability(focused or text)
    return PriceEvidence(
        source=source.source,
        title=source.title,
        url=source.url,
        price_text="; ".join(prices),
        availability_en=availability_en,
        availability_ar=availability_ar,
        checked_at=checked_at,
        live=True,
        note_en=source.note_en if prices else f"{source.note_en} No price was parsed from the page.",
        note_ar=source.note_ar if prices else f"{source.note_ar} لم يظهر سعر واضح في الصفحة.",
    )


def price_sources_for_treatment(treatment: Treatment, timeout_seconds: float = 2.5) -> list[PriceEvidence]:
    product_name = f"{treatment.name_en} {treatment.name_ar}".lower()
    matched = [
        source
        for source in PRICE_SOURCES
        if any(term.lower() in product_name for term in source.product_terms)
    ]
    return [_evidence_for_source(source, timeout_seconds) for source in matched[:3]]
