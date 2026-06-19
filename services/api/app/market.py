from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from .schemas import MarketPriceResponse


OBOOR_TODAY_URL = "http://www.oboormarket.org.eg/prices_today.aspx"


def _parse_oboor_tomato_price(html: str) -> tuple[float, float] | None:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    match = re.search(
        r"طماطم.{0,250}?من\s*سعر\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*الى\s*سعر\s*:?\s*([0-9]+(?:\.[0-9]+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    low = float(match.group(1))
    high = float(match.group(2))
    return (low, high) if low <= high else (high, low)


def unavailable_tomato_price(reason: str = "Live market page unavailable.") -> MarketPriceResponse:
    return MarketPriceResponse(
        crop="tomato",
        market="El-Obour wholesale market",
        source="El-Obour Market official daily prices",
        source_url=OBOOR_TODAY_URL,
        as_of=datetime.now(timezone.utc).date().isoformat(),
        live=False,
        note=f"{reason} No live tomato price is shown; enter a local market quote instead.",
    )


def current_tomato_market_price(timeout_seconds: float = 6.0) -> MarketPriceResponse:
    try:
        response = httpx.get(OBOOR_TODAY_URL, timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.HTTPError:
        return unavailable_tomato_price()

    parsed = _parse_oboor_tomato_price(response.text)
    if parsed is None:
        return unavailable_tomato_price("Could not parse the tomato row from the live market page.")

    low, high = parsed
    return MarketPriceResponse(
        crop="tomato",
        market="El-Obour wholesale market",
        low_egp_per_kg=low,
        high_egp_per_kg=high,
        source="El-Obour Market official daily prices",
        source_url=OBOOR_TODAY_URL,
        as_of=datetime.now(timezone.utc).date().isoformat(),
        live=True,
        note="Wholesale tomato range from the official El-Obour daily price page; retail and farmgate prices differ.",
    )
