"""Egypt price-provider abstraction.

Prices are a *swappable dependency* so they can come from a live API, an
admin-updated table, a CSV file, or this reviewed reference set. The reference
values are honest RANGES labelled "reference, confirm locally" — never presented
as live or exact. To plug in real data, implement ``PriceProvider`` and call
``set_price_provider``; nothing else in the app needs to change.

Items are coarse, farmer-meaningful buckets (a fungicide application, a kg of
tomato, a day of labour) rather than specific branded products, because the app
never recommends a brand and Egyptian registration must be checked separately.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.contracts.cases import PriceReference
from app.knowledge.tomato_statistics import tomato_expected_yield_range

REFERENCE_AS_OF = "2026-06-15"
_REFERENCE_NOTE = "Reference range — confirm the current local price before buying."


@dataclass(frozen=True)
class PriceRange:
    item: str
    unit: str
    low_egp: float
    high_egp: float
    source: str
    as_of: str = REFERENCE_AS_OF

    def to_reference(self) -> PriceReference:
        return PriceReference(
            item=self.item,
            unit=self.unit,
            low_egp=self.low_egp,
            high_egp=self.high_egp,
            source=self.source,
            as_of=self.as_of,
            note=_REFERENCE_NOTE,
        )


class PriceProvider(Protocol):
    def get(self, item: str) -> PriceRange | None: ...
    def all(self) -> list[PriceRange]: ...


# item -> (unit, low, high). Reviewed reference ranges for Egypt, NOT live prices.
_EXPECTED_YIELD_LOW, _EXPECTED_YIELD_HIGH = tomato_expected_yield_range()
_EGYPT_REFERENCE: dict[str, tuple[str, float, float]] = {
    "tomato_farmgate": ("EGP/kg", 5.0, 12.0),
    "expected_yield": ("kg/feddan", _EXPECTED_YIELD_LOW, _EXPECTED_YIELD_HIGH),
    "contact_fungicide": ("EGP/feddan/application", 120.0, 280.0),
    "systemic_fungicide": ("EGP/feddan/application", 250.0, 600.0),
    "copper_fungicide": ("EGP/feddan/application", 100.0, 240.0),
    "insecticide": ("EGP/feddan/application", 150.0, 450.0),
    "balanced_fertilizer": ("EGP/50kg bag", 600.0, 1400.0),
    "labor": ("EGP/feddan/application", 150.0, 400.0),
    "sprayer_use": ("EGP/feddan/application", 50.0, 150.0),
    "water_fuel": ("EGP/feddan/application", 60.0, 180.0),
    "greenhouse_setup": ("EGP/feddan/season", 20000.0, 120000.0),
    "home_garden_inputs": ("EGP/season", 100.0, 600.0),
}


class EgyptReferencePriceProvider:
    """Default provider: reviewed Egyptian reference ranges, not live."""

    source = "AgroVision Egypt reviewed reference (not live)"

    def get(self, item: str) -> PriceRange | None:
        ref = _EGYPT_REFERENCE.get(item)
        if ref is None:
            return None
        unit, low, high = ref
        return PriceRange(item=item, unit=unit, low_egp=low, high_egp=high, source=self.source)

    def all(self) -> list[PriceRange]:
        return [price for item in _EGYPT_REFERENCE if (price := self.get(item))]


class CsvPriceProvider:
    """Admin/CSV override. Columns: item,unit,low_egp,high_egp[,source,as_of].

    Missing items transparently fall back to the reviewed reference provider, so a
    partial admin sheet still yields a complete cost estimate.
    """

    def __init__(self, path: str | Path, fallback: PriceProvider | None = None) -> None:
        self._fallback: PriceProvider = fallback or EgyptReferencePriceProvider()
        self._rows: dict[str, PriceRange] = {}
        try:
            with open(path, newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    item = (row.get("item") or "").strip()
                    if not item:
                        continue
                    self._rows[item] = PriceRange(
                        item=item,
                        unit=(row.get("unit") or "").strip(),
                        low_egp=float(row["low_egp"]),
                        high_egp=float(row["high_egp"]),
                        source=(row.get("source") or "Admin CSV").strip(),
                        as_of=(row.get("as_of") or REFERENCE_AS_OF).strip(),
                    )
        except (OSError, KeyError, ValueError):
            self._rows = {}

    def get(self, item: str) -> PriceRange | None:
        return self._rows.get(item) or self._fallback.get(item)

    def all(self) -> list[PriceRange]:
        merged: dict[str, PriceRange] = {price.item: price for price in self._fallback.all()}
        merged.update(self._rows)
        return list(merged.values())


_provider: PriceProvider = EgyptReferencePriceProvider()


def price_provider() -> PriceProvider:
    return _provider


def set_price_provider(provider: PriceProvider) -> None:
    """Swap the price source (live API, admin table, CSV…) at startup."""
    global _provider
    _provider = provider
