from enum import StrEnum

from pydantic import BaseModel, Field


class ValidationLevel(StrEnum):
    VALIDATED = "validated"
    EXPERIMENTAL = "experimental"
    SAMPLE_DATA = "sample-data"


class LocalizedText(BaseModel):
    """A short message available in both English and Arabic."""

    en: str
    ar: str


class PriceEvidence(BaseModel):
    """One online retail/dealer price observation.

    This is not an official government price. It is a live or recently checked
    retail signal from a named source, kept separate from label guidance.
    """

    source: str
    title: str
    url: str
    price_text: str = ""
    availability_en: str = ""
    availability_ar: str = ""
    checked_at: str = ""
    live: bool = False
    note_en: str = ""
    note_ar: str = ""


class Treatment(BaseModel):
    """One reviewed control product for a disease, ranked by effectiveness.

    All figures are typical label references for guidance only; the farmer must
    read the product label and confirm the current price with a local dealer.
    Prices are approximate and change often, so they are never stated as exact.
    """

    rank: int
    name_en: str
    name_ar: str
    frac: str = ""              # FRAC resistance group (or "cultural"/"none")
    dose_en: str = ""           # typical label rate range
    dose_ar: str = ""
    application_en: str = ""    # method + timing + spray scheme / rotation
    application_ar: str = ""
    phi_en: str = ""            # pre-harvest interval
    phi_ar: str = ""
    hazard_en: str = ""         # toxicity class + key precautions / side effects
    hazard_ar: str = ""
    price_en: str = ""          # approximate range, always "confirm locally"
    price_ar: str = ""
    price_sources: list[PriceEvidence] = []
    note_en: str = ""           # why it sits at this effectiveness rank / availability
    note_ar: str = ""


class DiseaseInfo(BaseModel):
    """Reviewed bilingual reference text for a detected condition."""

    key: str
    name_en: str
    name_ar: str
    crop_en: str = ""
    crop_ar: str = ""
    summary_en: str
    summary_ar: str
    symptoms_en: list[str] = []
    symptoms_ar: list[str] = []
    management_en: list[str] = []
    management_ar: list[str] = []
    treatments: list[Treatment] = []


class FeatureResult(BaseModel):
    feature: str
    title: str
    title_ar: str
    level: ValidationLevel
    score: float = Field(ge=0, le=1)
    value: str
    value_ar: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = []
    limitation: str | None = None
    disease_info: DiseaseInfo | None = None


class DiagnosisCandidateLite(BaseModel):
    """A single ranked disease possibility carried alongside the analysis so the
    unified UI can open a case without re-running the (slow) vision model."""

    disease: str
    confidence: float = Field(ge=0, le=1)


class AnalysisResponse(BaseModel):
    analysis_id: str
    filename: str
    crop: str = "tomato"
    width: int
    height: int
    processing_ms: int
    peak_memory_mb: float
    provider: str
    results: list[FeatureResult]
    alerts: list[LocalizedText]
    recommendations: list[LocalizedText]
    assistant_questions: list[LocalizedText] = []
    # Fused diagnosis summary for the one-photo-drives-everything dashboard.
    fused_state: str = ""
    diagnosis_candidates: list[DiagnosisCandidateLite] = []
    # Honest confidence reporting (item 4 of the report contract). Raw vs calibrated
    # diverge only once a validation set fits a temperature; until then they match
    # and ``calibration_method`` says "uncalibrated".
    raw_confidence: float = Field(default=0.0, ge=0, le=1)
    calibrated_confidence: float = Field(default=0.0, ge=0, le=1)
    calibration_method: str = ""
    uncertainty_level: str = ""  # "high" | "medium" | "low"
    # Image-derived supporting evidence (bilingual); never used as proof.
    visual_evidence: list[LocalizedText] = []
    # Raw image measurements forwarded to the case so the report can show
    # infection_extent and weather_risk without requiring a second photo upload.
    image_measurements: dict[str, float] = {}


class AssistantRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    analysis_id: str | None = None
    language: str | None = Field(default=None, description="UI language hint: 'en' or 'ar'.")
    case_context: str | None = Field(
        default=None,
        max_length=4000,
        description="Optional frontend case context when diagnosis ran on-device and has no backend analysis.",
    )


class AssistantResponse(BaseModel):
    answer: str
    sources: list[str]
    mode: str


class MarketPriceResponse(BaseModel):
    crop: str
    market: str
    low_egp_per_kg: float | None = None
    high_egp_per_kg: float | None = None
    unit: str = "EGP/kg"
    source: str
    source_url: str
    as_of: str
    live: bool
    note: str
