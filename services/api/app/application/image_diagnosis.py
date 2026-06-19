from __future__ import annotations

from PIL import Image

from app.analysis import infection_extent, vegetation_indices
from app.contracts.cases import DiagnosisCandidate, DiagnosisInput
from app.diagnosis_evidence import assess_visual_prediction, fuse_diagnosis, fused_named_candidates
from app.diseases import disease_info
from app.model_runtime import DiseaseRuntime, runtime_for_crop
from app.vision_llm import VisionDiagnosis


def diagnose_image(
    image: Image.Image,
    crop: str,
    runtime: DiseaseRuntime | None = None,
    vision: VisionDiagnosis | None = None,
) -> DiagnosisInput:
    """Convert the fused (local + AI second opinion) visual match into the case contract."""

    if crop != "tomato":
        raise ValueError("Image diagnosis currently supports tomato only.")

    runtime = runtime or runtime_for_crop(crop)
    prediction = runtime.predict(image)
    assessment = assess_visual_prediction(prediction, crop)
    fused = fuse_diagnosis(assessment, vision, crop)

    # Ranked candidates mapped to display names (shared with the analysis card).
    candidates = [
        DiagnosisCandidate(disease=name, confidence=confidence)
        for name, confidence in fused_named_candidates(fused)
    ]

    ranked_hypotheses = ", ".join(
        f"{disease_info(key).name_en} {score:.0%}" for key, score in fused.ranked
    )

    missing: list[str] = [
        *fused.reasons,
        *fused.limitations,
        "Confirm the affected plant part and symptoms with farmer observations.",
        "Add a whole-plant photo and a close photo of the leaf underside.",
    ]
    if not fused.accepted:
        missing.insert(0, "The image does not support a reliable disease diagnosis.")

    if fused.state == "screening" and fused.group_promoted:
        decision = "probable spot-complex match (medium confidence); confirm before treatment"
    else:
        decision = {
            "confident": "accepted visual match",
            "screening": "screening match (local model + AI second opinion); confirm before treatment",
        }.get(fused.state, "rejected; diagnosis unconfirmed")

    model_name = getattr(getattr(runtime, "model_path", None), "name", runtime.__class__.__name__)
    validation_level = getattr(getattr(runtime, "level", None), "value", "not supplied")
    return DiagnosisInput(
        candidates=candidates,
        evidence=[
            f"Model: {model_name}",
            f"Visual model provider: {prediction.provider}",
            f"Model validation level: {validation_level}",
            f"Crop filter: {crop}",
            *fused.evidence,
            f"Crop-label support: {fused.crop_probability_mass:.0%}",
            f"Top-match separation: {fused.margin:.0%}",
            f"Raw model confidence {fused.raw_confidence:.0%} vs calibrated {fused.confidence:.0%} ({fused.calibration_method})",
            f"Uncertainty level: {fused.uncertainty_level}",
            f"Decision gate: {decision}",
            *([f"Ranked visual hypotheses: {ranked_hypotheses}"] if ranked_hypotheses else []),
            "Image-model matches are visual hypotheses, not a laboratory diagnosis.",
        ],
        missing_info=missing[:20],
    )


def measure_image(image: Image.Image, view_type: str) -> dict[str, str | int | float]:
    """Return reproducible RGB measurements without interpreting them as crop-wide severity."""

    indices = vegetation_indices(image)
    return {
        "image_width_px": image.width,
        "image_height_px": image.height,
        "image_view_type": view_type,
        "image_visible_discoloration_percent": round(infection_extent(image) * 100, 1),
        "image_yellow_pixel_percent": round(indices["yellow"] * 100, 1),
        "image_dark_pixel_percent": round(indices["dark"] * 100, 1),
        "image_green_coverage_percent": round(indices["coverage"] * 100, 1),
        "image_excess_green_index": round(indices["exg"], 3),
        "image_vari_index": round(indices["vari"], 3),
        "image_measurement_scope": "Uploaded RGB image only; not crop-wide prevalence or biological severity.",
    }
