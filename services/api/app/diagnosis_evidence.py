from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .calibration import assess_confusion_group, load_calibration
from .config import settings
from .diseases import disease_info, labels_for_crop
from .model_runtime import DiseasePrediction
from .schemas import ValidationLevel
from .vision_llm import VisionDiagnosis


@dataclass(frozen=True)
class VisualDiagnosisAssessment:
    crop: str
    candidates: list[tuple[str, float]] = field(default_factory=list)
    crop_probability_mass: float = 0.0
    top_score: float = 0.0
    margin: float = 0.0
    accepted: bool = False
    rejection_reasons: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    # Full crop-conditioned distributions (calibrated + raw) for the confusion-group
    # rescue and honest raw-vs-calibrated reporting. ``candidates`` stays top-3 for
    # display compatibility; these keep the whole tail.
    all_candidates: list[tuple[str, float]] = field(default_factory=list)
    raw_candidates: list[tuple[str, float]] = field(default_factory=list)
    raw_top_score: float = 0.0


def assess_visual_prediction(
    prediction: DiseasePrediction,
    crop: str,
    leaf_coverage: float | None = None,
) -> VisualDiagnosisAssessment:
    """Grade a visual match without turning crop filtering into fake confidence."""

    def _condition(ranked: list[tuple[str, float]]) -> tuple[list[tuple[str, float]], float]:
        allowed = set(labels_for_crop(crop, [label for label, _ in ranked]))
        filtered = [(label, score) for label, score in ranked if label in allowed]
        mass = sum(score for _, score in filtered)
        ordered = (
            sorted(((label, score / mass) for label, score in filtered), key=lambda item: item[1], reverse=True)
            if mass > 0
            else []
        )
        return ordered, mass

    ranked = prediction.scores or [(prediction.label, prediction.confidence)]
    conditioned, crop_mass = _condition(ranked)
    raw_ranked = prediction.raw_scores or ranked
    raw_conditioned, _ = _condition(raw_ranked)
    raw_top_score = raw_conditioned[0][1] if raw_conditioned else 0.0
    top_score = conditioned[0][1] if conditioned else 0.0
    runner_up = conditioned[1][1] if len(conditioned) > 1 else 0.0
    margin = top_score - runner_up

    reasons: list[str] = []
    limitations = [
        "The score is an uncalibrated visual-model match, not the probability that the diagnosis is correct.",
        f"The crop was selected by the user as {crop}; the image model does not independently confirm the host crop.",
    ]
    if prediction.level == ValidationLevel.SAMPLE_DATA:
        reasons.append("A trained image model was not available.")
    if leaf_coverage is not None and leaf_coverage < settings.disease_min_leaf_coverage:
        reasons.append("Too little clear green leaf area is visible.")
    if not conditioned:
        reasons.append(f"The model produced no {crop}-compatible match.")
    if crop == "tomato" and crop_mass < settings.disease_min_crop_probability_mass:
        reasons.append(
            f"The multi-crop model gave only {crop_mass:.0%} of its score to tomato labels, "
            "so the selected host is not visually supported."
        )
    if conditioned and top_score < settings.disease_confidence_threshold:
        reasons.append(f"The strongest visual match is only {top_score:.0%}.")
    if len(conditioned) > 1 and margin < settings.disease_min_margin:
        reasons.append(f"The top two visual matches are too close, with only a {margin:.0%} gap.")
    if crop == "banana":
        limitations.append(
            "The installed banana model has no healthy or out-of-domain class, so it cannot rule out a healthy leaf "
            "or a non-banana image."
        )

    return VisualDiagnosisAssessment(
        crop=crop,
        candidates=conditioned[:3],
        crop_probability_mass=crop_mass,
        top_score=top_score,
        margin=margin,
        accepted=not reasons,
        rejection_reasons=reasons,
        limitations=limitations,
        all_candidates=conditioned,
        raw_candidates=raw_conditioned,
        raw_top_score=raw_top_score,
    )


# --- Honest fusion of the local ONNX model with the hosted vision second opinion -----
#
# Neither model is reliable alone on a real field photo (the lab-trained local model
# splits its score; the free hosted vision model is honest but imperfect). Combining
# them lets the app give a useful *screening* answer when they corroborate, while
# staying honest ("not sure", top-3) when they don't. Thresholds are uncalibrated and
# deliberately conservative — a single weak model never becomes a confident diagnosis.

FusionState = Literal["confident", "screening", "not_sure", "not_tomato"]

_CONFIDENT_AGREE = 0.50          # both models present + agree -> confident screening
_SCREENING_BOTH = 0.28          # both present, partial support -> show as screening
_VISION_ONLY_CONFIDENT = 0.60   # vision alone, strong + sure
_VISION_ONLY_SCREENING = 0.45   # vision alone, moderate
_VISION_SURE = 0.80             # vision confidence at/above this is treated as a sure read
_LOCAL_HOST_SURE = 0.55         # below this crop-label mass the local model is unsure of the host
_HEALTHY_CONFIDENT = 0.55
_MAX_DISPLAY_CONFIDENCE = 0.85   # never present a visual match as a near-certainty
_SCREENING_DISPLAY_CAP = 0.62


@dataclass(frozen=True)
class FusedDiagnosis:
    state: FusionState
    accepted: bool
    top_key: str = ""
    confidence: float = 0.0
    ranked: list[tuple[str, float]] = field(default_factory=list)  # (kb_key, fused_score)
    crop_probability_mass: float = 0.0
    margin: float = 0.0
    agreement: bool | None = None
    used_vision: bool = False
    evidence: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    # Honest confidence reporting: raw (uncalibrated) local probability for the
    # reported disease, the calibration method label, the plain uncertainty level,
    # and whether the confusion-group ("spot complex") rescue promoted this result.
    raw_confidence: float = 0.0
    calibration_method: str = ""
    uncertainty_level: str = "low"
    group_promoted: bool = False


def _local_key_probs(candidates: list[tuple[str, float]]) -> dict[str, float]:
    """Crop-conditioned local scores re-keyed onto knowledge-base keys."""
    probs: dict[str, float] = {}
    for label, score in candidates:
        key = disease_info(label).key
        probs[key] = probs.get(key, 0.0) + float(score)
    return probs


def _vision_key_probs(vision: VisionDiagnosis) -> dict[str, float]:
    """Vision per-disease confidences as INDEPENDENT beliefs (not a distribution).

    The model reports a separate 0..1 certainty for each disease, so a confident top
    pick must keep its full weight — normalising across items would wrongly dilute it.
    """
    probs: dict[str, float] = {}
    for ranked in vision.ranked:
        probs[ranked.key] = max(probs.get(ranked.key, 0.0), ranked.confidence)
    return probs


def fuse_diagnosis(
    assessment: VisualDiagnosisAssessment,
    vision: VisionDiagnosis | None,
    crop: str = "tomato",
) -> FusedDiagnosis:
    """Combine the local model with the optional hosted vision opinion, honestly."""
    local_probs = _local_key_probs(assessment.candidates)
    # Full crop-conditioned distributions for the confusion-group rescue and for
    # reporting the raw (uncalibrated) probability of whatever disease we display.
    local_full = _local_key_probs(assessment.all_candidates or assessment.candidates)
    raw_full = _local_key_probs(assessment.raw_candidates or assessment.candidates)
    has_local = bool(local_probs)
    vision_ok = bool(vision and vision.is_tomato_leaf and vision.ranked)

    if has_local and vision_ok:
        # Trust the local model in proportion to how strongly it recognises the chosen
        # crop; when it is unsure about the host (low crop mass), lean on the vision opinion.
        local_belief = max(0.0, min(1.0, assessment.crop_probability_mass))
        w_local = 0.30 + 0.40 * local_belief
        w_vision = 1.0 - w_local
    elif vision_ok:
        w_local, w_vision = 0.0, 1.0
    else:
        w_local, w_vision = 1.0, 0.0

    vision_probs = _vision_key_probs(vision) if vision_ok else {}
    fused: dict[str, float] = {}
    for key, value in local_probs.items():
        fused[key] = fused.get(key, 0.0) + w_local * value
    for key, value in vision_probs.items():
        fused[key] = fused.get(key, 0.0) + w_vision * value

    ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    top_key, top_score = ranked[0] if ranked else ("", 0.0)
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = top_score - runner_up
    top_is_healthy = top_key == "healthy"

    local_top = max(local_probs, key=local_probs.get) if has_local else None
    vision_top = vision.ranked[0].key if vision_ok else None
    vision_top_conf = vision.ranked[0].confidence if vision_ok else 0.0
    agreement = (local_top == vision_top) if (has_local and vision_ok) else None
    # Soft corroboration: the vision pick is at least among the local possibilities.
    soft_agreement = bool(vision_ok and vision_top in local_probs)

    if vision is not None and not vision.is_tomato_leaf and not assessment.accepted:
        state: FusionState = "not_tomato"
    elif top_is_healthy and top_score >= _HEALTHY_CONFIDENT:
        state = "confident"
    elif has_local and vision_ok:
        vision_sure = vision_top_conf >= _VISION_SURE and not vision.not_sure and not top_is_healthy
        local_unsure_host = assessment.crop_probability_mass < _LOCAL_HOST_SURE
        if (agreement and top_score >= _CONFIDENT_AGREE) or (
            vision_sure and (soft_agreement or local_unsure_host) and top_score >= 0.45
        ):
            state = "confident"
        elif top_score >= _SCREENING_BOTH or vision_top_conf >= _VISION_ONLY_SCREENING:
            state = "screening"
        else:
            state = "not_sure"
    elif has_local:
        # Local only (offline / vision unavailable): preserve the original honest gate.
        state = "confident" if assessment.accepted else "not_sure"
    elif vision_ok:
        if not vision.not_sure and top_score >= _VISION_ONLY_CONFIDENT:
            state = "confident"
        elif top_score >= _VISION_ONLY_SCREENING:
            state = "screening"
        else:
            state = "not_sure"
    else:
        state = "not_sure"

    # --- Confusion-group ("spot complex") rescue --------------------------------
    # A Target-Spot-like top-1 routinely splits its score with Early Blight /
    # Bacterial Spot / Septoria, so a flat threshold drops a correct prediction as
    # "not sure". When the COMBINED group mass is high and clearly beats everything
    # outside the group, promote to a *medium* ("probable") screening verdict. The
    # displayed number stays the honest, uncapped-then-screening-capped value — we
    # only change how an existing, coherent signal is described, never its size.
    group = assess_confusion_group(local_full, assessment.crop_probability_mass)
    group_promoted = False
    if state == "not_sure" and group.promote and not top_is_healthy:
        state = "screening"
        group_promoted = True

    accepted = state in {"confident", "screening"}
    if state == "confident":
        confidence = min(top_score, _MAX_DISPLAY_CONFIDENCE)
    elif state == "screening":
        confidence = min(top_score, _SCREENING_DISPLAY_CAP)
    else:
        confidence = top_score

    # Raw (uncalibrated) probability for the disease we actually display. Equals the
    # calibrated value until a validation set fits a temperature (then they diverge).
    raw_confidence = float(raw_full.get(top_key, confidence))
    calibration_method = load_calibration().describe()

    evidence: list[str] = []
    if has_local:
        evidence.append(f"Local model: {disease_info(local_top).name_en} {local_probs[local_top]:.0%}")
    else:
        evidence.append("Local model: no tomato-compatible match")
    if vision_ok:
        vtop = vision.ranked[0]
        suffix = " (not sure)" if vision.not_sure else ""
        evidence.append(
            f"AI second opinion ({vision.model}): {disease_info(vtop.key).name_en} {vtop.confidence:.0%}{suffix}"
        )
        if vision.visible_signs:
            evidence.append(f"AI sees: {vision.visible_signs}")
    elif vision is not None and not vision.is_tomato_leaf:
        evidence.append(f"AI second opinion ({vision.model}): this may not be a clear tomato leaf")
    else:
        evidence.append("AI second opinion: unavailable (offline) — using the local model only")
    if agreement is True:
        evidence.append(f"The two models agree on {disease_info(top_key).name_en}.")
    elif agreement is False:
        evidence.append("The two models differ, so these are ranked possibilities, not a confirmed diagnosis.")

    uncertainty_level = {"confident": "high", "screening": "medium"}.get(state, "low")

    limitations = list(assessment.limitations)
    limitations.append(
        f"Confidence calibration: {calibration_method}. The score is a screening signal, "
        "not the probability that the diagnosis is correct."
    )
    if group_promoted and group.note_en:
        limitations.append(group.note_en)
        evidence.append(
            f"Spot-complex group: {group.group_mass:.0%} combined across "
            f"{', '.join(disease_info(k).name_en for k in group.members_present)} "
            f"(margin {group.margin_vs_outside:.0%} over other diseases)."
        )
    reasons = list(assessment.rejection_reasons)
    if state == "not_tomato":
        reasons.insert(0, "The AI second opinion did not see a clear tomato leaf and the local model could not confirm one.")

    return FusedDiagnosis(
        state=state,
        accepted=accepted,
        top_key=top_key,
        confidence=confidence,
        ranked=ranked[:3],
        crop_probability_mass=assessment.crop_probability_mass,
        margin=margin,
        agreement=agreement,
        used_vision=vision_ok,
        evidence=evidence,
        reasons=reasons,
        limitations=limitations,
        raw_confidence=raw_confidence,
        calibration_method=calibration_method,
        uncertainty_level=uncertainty_level,
        group_promoted=group_promoted,
    )


def fused_named_candidates(fused: FusedDiagnosis) -> list[tuple[str, float]]:
    """Top-3 (display name, confidence) candidates from a fused result.

    The top score caps the rest so the most likely disease always stays first,
    and an unconfirmed result leads with the explicit "not enough evidence" marker.
    Shared by the analysis card and the case diagnosis so both surfaces agree.
    """
    out: list[tuple[str, float]] = []
    seen: set[str] = set()
    for index, (key, score) in enumerate(fused.ranked):
        name = disease_info(key).name_en
        if name in seen:
            continue
        confidence = fused.confidence if index == 0 else min(score, fused.confidence)
        out.append((name, max(0.0, min(1.0, confidence))))
        seen.add(name)
        if len(out) == 3:
            break
    if not fused.accepted:
        out = [("Not enough visual evidence", 0.0), *out[:2]]
    if not out:
        out = [("Not enough visual evidence", 0.0)]
    return out
