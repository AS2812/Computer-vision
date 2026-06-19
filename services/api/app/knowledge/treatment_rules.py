from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.contracts.cases import DiagnosisOutput, TreatmentPlanOutput
from app.knowledge.egypt_sources import EGYPT_FOOD_SAFETY_LAB_URL, EGYPT_PESTICIDE_DATABASE_URL


RULE_VERSION = "egypt-safety-baseline-2026-06-15"


class DiseaseClass(StrEnum):
    FUNGAL = "fungal"
    BACTERIAL = "bacterial"
    VIRAL = "viral"
    INSECT = "insect"
    NUTRIENT = "nutrient"
    ABIOTIC = "abiotic"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TreatmentRuleResult:
    disease_class: DiseaseClass
    rule_version: str
    plan: TreatmentPlanOutput


_NO_CHEMICAL_CURE = ("panama", "fusarium", "esca", "greening")
_VIRAL = ("virus", "viral", "mosaic", "bunchy top", "yellow leaf curl")
_BACTERIAL = ("bacterial", "bacteriosis")
_INSECT = ("mite", "insect", "aphid", "whitefly", "thrip", "pest")
_NUTRIENT = ("nutrient", "deficiency", "chlorosis")
_FUNGAL = (
    "blight",
    "spot",
    "mold",
    "mildew",
    "rust",
    "sigatoka",
    "cordana",
    "anthracnose",
    "scab",
    "rot",
    "fung",
)
_ABIOTIC = ("heat stress", "water stress", "sunscald", "chemical injury")


def classify_disease(name: str) -> DiseaseClass:
    normalized = name.lower()
    if any(token in normalized for token in _VIRAL):
        return DiseaseClass.VIRAL
    if any(token in normalized for token in _BACTERIAL):
        return DiseaseClass.BACTERIAL
    if any(token in normalized for token in _INSECT):
        return DiseaseClass.INSECT
    if any(token in normalized for token in _NUTRIENT):
        return DiseaseClass.NUTRIENT
    if any(token in normalized for token in _ABIOTIC):
        return DiseaseClass.ABIOTIC
    if any(token in normalized for token in (*_FUNGAL, *_NO_CHEMICAL_CURE)):
        return DiseaseClass.FUNGAL
    return DiseaseClass.UNKNOWN


def _base_safety() -> list[str]:
    return [
        f"Verify the current Egyptian registration by crop and pest in the APC database: {EGYPT_PESTICIDE_DATABASE_URL}",
        "Use only the registered Egyptian label dose, PPE, re-entry interval, and pre-harvest interval.",
        "Ask an Egyptian agricultural engineer before applying a chemical treatment.",
        f"For food-safety or residue concerns, use an official Egyptian residue laboratory: {EGYPT_FOOD_SAFETY_LAB_URL}",
        "Do not use a chemical treatment based only on the AI result.",
        "Do not over-spray.",
    ]


def treatment_rule(diagnosis: DiagnosisOutput, confidence_threshold: float) -> TreatmentRuleResult:
    disease_class = classify_disease(diagnosis.top_disease)
    safety = _base_safety()
    chemicals: list[str] = []
    confirmed = diagnosis.confirmation_status != "unconfirmed"
    if confirmed:
        safety.insert(
            0,
            "Diagnosis identity is recorded from submitted Egyptian expert or lab evidence; "
            "AgroVision has not independently authenticated the document.",
        )

    if not diagnosis.top_disease or (diagnosis.confidence < confidence_threshold and not confirmed):
        non_chemical = [
            "Collect clearer photos and farmer observations before choosing a treatment category.",
            "Use field hygiene and moisture management while the likely cause is confirmed.",
        ]
        safety.insert(0, "Low diagnosis confidence blocks chemical-category advice.")
    elif disease_class == DiseaseClass.VIRAL:
        non_chemical = [
            "Isolate and mark suspected infected plants; remove them only after expert confirmation.",
            "Control weeds and inspect for likely insect vectors.",
            "Clean tools before moving to healthy plants.",
        ]
        chemicals = [
            "If an agricultural engineer confirms the virus and its vector, use only a locally registered vector-control category; spraying does not cure infected plants."
        ]
        safety.insert(0, "No spray cures a plant virus.")
    elif disease_class == DiseaseClass.BACTERIAL:
        non_chemical = [
            "Remove heavily affected tissue when conditions are dry and disinfect tools.",
            "Reduce leaf wetness, splash, and movement through wet plants.",
        ]
        chemicals = [
            "Use only a locally registered bactericide category appropriate to the crop after expert confirmation; fungicides do not cure bacterial disease."
        ]
    elif disease_class == DiseaseClass.INSECT:
        non_chemical = [
            "Confirm the pest on the leaf underside or affected plant part before treatment.",
            "Remove heavily infested tissue and reduce weeds that host the pest.",
        ]
        chemicals = [
            "Use only a locally registered insecticide or miticide category matched to the confirmed pest, and rotate resistance-action groups."
        ]
    elif disease_class == DiseaseClass.NUTRIENT:
        non_chemical = [
            "Request soil and irrigation-water testing before heavy fertilization.",
            "Check root health, drainage, pH, and irrigation consistency.",
        ]
        safety.insert(0, "Do not apply heavy fertilizer from an image-only nutrient diagnosis.")
    elif disease_class == DiseaseClass.FUNGAL and any(
        token in diagnosis.top_disease.lower() for token in _NO_CHEMICAL_CURE
    ):
        non_chemical = [
            "Isolate affected plants and improve drainage and field hygiene.",
            "Use clean planting material and ask an agricultural engineer about removal and rotation.",
        ]
        safety.insert(0, "This suspected disease has no reliable curative spray.")
    elif disease_class == DiseaseClass.FUNGAL:
        non_chemical = [
            "Remove heavily affected tissue and infected debris.",
            "Reduce leaf wetness, splash, crowding, and prolonged humidity.",
        ]
        chemicals = [
            "After expert confirmation, use only a locally registered protectant or systemic fungicide category appropriate to the crop and disease.",
            "Rotate resistance-action groups and do not repeat the same mode of action continuously.",
        ]
    else:
        non_chemical = [
            "Collect more evidence and check irrigation, roots, weather injury, and recent spray history.",
            "Use field hygiene and avoid unnecessary chemical treatment.",
        ]
        safety.insert(0, "The cause is unknown, so chemical-category advice is blocked.")

    return TreatmentRuleResult(
        disease_class=disease_class,
        rule_version=RULE_VERSION,
        plan=TreatmentPlanOutput(
            non_chemical=non_chemical,
            chemical_category_if_needed=chemicals,
            safety_notes=safety,
        ),
    )
