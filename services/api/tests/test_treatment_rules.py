from app.contracts.cases import (
    DiagnosisConfirmationOutput,
    DiagnosisConfirmationType,
    DiagnosisOutput,
)
from app.knowledge.treatment_rules import DiseaseClass, RULE_VERSION, classify_disease, treatment_rule


def diagnosis(name: str, confidence: float = 0.9) -> DiagnosisOutput:
    return DiagnosisOutput(top_disease=name, confidence=confidence)


def test_disease_classification_covers_safe_treatment_paths():
    assert classify_disease("Tomato early blight") == DiseaseClass.FUNGAL
    assert classify_disease("Bacterial spot") == DiseaseClass.BACTERIAL
    assert classify_disease("Tomato mosaic virus") == DiseaseClass.VIRAL
    assert classify_disease("Spider mites") == DiseaseClass.INSECT
    assert classify_disease("Potassium deficiency") == DiseaseClass.NUTRIENT
    assert classify_disease("Heat stress") == DiseaseClass.ABIOTIC
    assert classify_disease("Unclear leaf symptom") == DiseaseClass.UNKNOWN


def test_low_confidence_and_unknown_causes_block_chemical_advice():
    low = treatment_rule(diagnosis("Early blight", 0.4), 0.65)
    unknown = treatment_rule(diagnosis("Unclear leaf symptom"), 0.65)

    assert low.plan.chemical_category_if_needed == []
    assert any("Low diagnosis confidence" in item for item in low.plan.safety_notes)
    assert unknown.plan.chemical_category_if_needed == []
    assert any("cause is unknown" in item for item in unknown.plan.safety_notes)


def test_submitted_egyptian_confirmation_allows_only_category_guidance_at_low_visual_score():
    confirmed = DiagnosisOutput(
        top_disease="Septoria leaf spot",
        confidence=0.15,
        confirmation_status="confirmed_by_egyptian_plant_pathology_lab",
        confirmation=DiagnosisConfirmationOutput(
            disease="Septoria leaf spot",
            confirmation_type=DiagnosisConfirmationType.EGYPTIAN_PLANT_PATHOLOGY_LAB,
            organization="ARC Vegetable Diseases Research Department",
            report_reference="ARC-TEST-001",
            evidence_filename="report.pdf",
            evidence_sha256="a" * 64,
        ),
    )

    result = treatment_rule(confirmed, 0.65)

    assert result.plan.chemical_category_if_needed
    assert any("APC database" in item for item in result.plan.safety_notes)
    assert any("not independently authenticated" in item for item in result.plan.safety_notes)


def test_viral_nutrient_and_no_cure_rules_do_not_claim_a_cure():
    viral = treatment_rule(diagnosis("Tomato mosaic virus"), 0.65)
    nutrient = treatment_rule(diagnosis("Potassium deficiency"), 0.65)
    panama = treatment_rule(diagnosis("Panama disease"), 0.65)

    assert viral.disease_class == DiseaseClass.VIRAL
    assert "does not cure" in viral.plan.chemical_category_if_needed[0]
    assert nutrient.plan.chemical_category_if_needed == []
    assert any("soil" in item.lower() for item in nutrient.plan.non_chemical)
    assert panama.plan.chemical_category_if_needed == []
    assert any("no reliable curative spray" in item for item in panama.plan.safety_notes)


def test_fungal_bacterial_and_insect_rules_are_category_only_and_versioned():
    fungal = treatment_rule(diagnosis("Early blight"), 0.65)
    bacterial = treatment_rule(diagnosis("Bacterial spot"), 0.65)
    insect = treatment_rule(diagnosis("Spider mites"), 0.65)

    assert fungal.rule_version == RULE_VERSION
    assert any("fungicide category" in item for item in fungal.plan.chemical_category_if_needed)
    assert any("fungicides do not cure bacterial" in item for item in bacterial.plan.chemical_category_if_needed)
    assert any("insecticide or miticide category" in item for item in insect.plan.chemical_category_if_needed)
    combined = " ".join(
        fungal.plan.chemical_category_if_needed
        + bacterial.plan.chemical_category_if_needed
        + insect.plan.chemical_category_if_needed
    )
    assert "e.g." not in combined
