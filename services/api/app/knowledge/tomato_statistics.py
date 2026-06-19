from __future__ import annotations

from dataclasses import dataclass

from app.contracts.cases import SourceMetadata


@dataclass(frozen=True)
class TomatoStatisticsReference:
    key: str
    title: str
    organization: str
    url: str
    area_thousand_feddan: float
    production_million_tons: float
    retrieved_on: str

    @property
    def yield_kg_per_feddan(self) -> float:
        # million tons -> kg and thousand feddan -> feddan
        return self.production_million_tons * 1_000_000 / self.area_thousand_feddan


_TOMATO_STATISTICS = (
    TomatoStatisticsReference(
        key="capmas_tomato_2017_2018",
        title="Annual Bulletin of Movement of Production, Foreign Trade and Available for Consumption of Agricultural Commodities 2017/2018",
        organization="Central Agency for Public Mobilization and Statistics",
        url="https://censusinfo.capmas.gov.eg/metadata-en-v4.2/index.php/catalog/399/download/819",
        area_thousand_feddan=416.0,
        production_million_tons=6.8,
        retrieved_on="2026-06-16",
    ),
    TomatoStatisticsReference(
        key="capmas_tomato_2015_2016",
        title="Annual Bulletin of Agricultural Income Estimates 2015/2016",
        organization="Central Agency for Public Mobilization and Statistics",
        url="https://censusinfo.capmas.gov.eg/Metadata-ar-v4.2/index.php/catalog/1416/download/4729",
        area_thousand_feddan=440.2,
        production_million_tons=7.3,
        retrieved_on="2026-06-16",
    ),
)


def tomato_statistics_references() -> tuple[TomatoStatisticsReference, ...]:
    return _TOMATO_STATISTICS


def tomato_expected_yield_range() -> tuple[float, float]:
    yields = sorted(reference.yield_kg_per_feddan for reference in _TOMATO_STATISTICS)
    return yields[0], yields[-1]


def tomato_statistics_sources() -> list[SourceMetadata]:
    return [
        SourceMetadata(
            key=reference.key,
            title=reference.title,
            organization=reference.organization,
            source_kind="tomato_statistics",
            source_type="official",
            url=reference.url,
            confidence="high",
            retrieved_on=reference.retrieved_on,
            note_en=(
                f"Tomato area {reference.area_thousand_feddan:.1f} thousand feddan; "
                f"production {reference.production_million_tons:.1f} million tons; "
                f"implied yield {reference.yield_kg_per_feddan:.0f} kg per feddan."
            ),
            note_ar=(
                f"مساحة الطماطم {reference.area_thousand_feddan:.1f} ألف فدان؛ "
                f"الإنتاج {reference.production_million_tons:.1f} مليون طن؛ "
                f"الإنتاجية المستنتجة {reference.yield_kg_per_feddan:.0f} كجم/فدان."
            ),
        )
        for reference in _TOMATO_STATISTICS
    ]
