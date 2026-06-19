"""Honest probability calibration and decision policy for the tomato classifier.

The local PlantVillage MobileNetV2 model outputs *uncalibrated* softmax logits.
Two consequences matter for Target Spot specifically:

1. Target Spot lesions (brown necrotic spots with faint concentric rings and a
   yellow halo) look almost identical to Early Blight, Bacterial Spot and
   Septoria leaf spot. The model therefore *splits* its probability mass across
   this "spot complex", so the correct class is often top-1 but only ~40 %.
2. A single flat "must be >= 65 %" gate then buries that correct top-1 as
   "no reliable diagnosis", even though the model clearly believes the leaf has a
   spot-complex disease.

This module fixes that **without faking confidence**:

* ``apply_temperature`` / ``fit_temperature`` implement temperature scaling — the
  standard, honest post-hoc calibration. Out of the box the temperature is 1.0
  (identity) and we label the output "uncalibrated"; a real validation set fitted
  by :mod:`ml.training.evaluate_tomato` writes a sidecar that flips this on.
* ``assess_confusion_group`` recognises when the top-1 is a member of the spot
  complex and the *combined* group mass is high with a clear margin over
  everything outside the group. That earns a **medium** ("probable") verdict
  instead of silence — while the displayed number stays the raw, honest value.

Nothing here inflates a probability. It only changes how an existing,
already-computed probability is *thresholded and described*.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence

import numpy as np

from .config import settings


# --- Tomato class identity (frozen, guarded by tests) ------------------------
#
# These are the tomato labels exactly as the model emits them, in model order.
# ``TARGET_SPOT_INDEX`` is the absolute index inside the full 38-class output.
# A test asserts this matches ``ml/models/plant_disease_mobilenetv2.labels.json``
# so a silent re-ordering of the labels can never go unnoticed.

TOMATO_MODEL_LABELS: tuple[str, ...] = (
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
)

TARGET_SPOT_LABEL = "Tomato___Target_Spot"
TARGET_SPOT_INDEX = 34  # absolute index in the 38-class output
TARGET_SPOT_KEY = "tomato_target_spot"


# --- Confusion groups (knowledge-base keys) ----------------------------------
#
# The "spot complex": small/round to angular brown necrotic foliar spots that the
# model (and the human eye) routinely confuse. Target Spot lives here together
# with the two diseases the user reported it is mistaken for — Early Blight and
# Bacterial Spot — plus Septoria, which shares the same visual niche.

SPOT_COMPLEX: frozenset[str] = frozenset({
    "tomato_target_spot",
    "tomato_early_blight",
    "tomato_bacterial_spot",
    "septoria_leaf_spot_tomato",
})

_CONFUSION_GROUPS: dict[str, frozenset[str]] = {key: SPOT_COMPLEX for key in SPOT_COMPLEX}


def confusion_group(key: str) -> frozenset[str]:
    """The set of look-alike diseases ``key`` is routinely confused with.

    Returns a single-element set for diseases without a known look-alike cluster.
    """
    return _CONFUSION_GROUPS.get(key, frozenset({key}))


def is_confusable(key: str) -> bool:
    """True when ``key`` belongs to a multi-member confusion group."""
    return len(confusion_group(key)) > 1


def class_high_threshold(key: str, calibration: "Calibration | None" = None) -> float:
    """The confidence a class needs to be reported as a *high*-confidence match.

    Per-class thresholds come from a fitted calibration sidecar when present;
    otherwise the uniform global gate is used. This is deliberately *not* lowered
    for Target Spot — the medium ("probable") tier, not a weaker high gate, is how
    a confusable top-1 is surfaced honestly.
    """
    cal = calibration or load_calibration()
    return float(cal.per_class_threshold.get(key, settings.disease_confidence_threshold))


# --- Temperature scaling -----------------------------------------------------

def softmax(logits: np.ndarray, axis: int = -1) -> np.ndarray:
    z = logits - np.max(logits, axis=axis, keepdims=True)
    exp = np.exp(z)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def apply_temperature(logits: Sequence[float] | np.ndarray, temperature: float) -> np.ndarray:
    """Softmax with temperature scaling. ``temperature == 1`` is the identity.

    Temperature scaling is monotonic, so it never changes the ranking or which
    class is top-1 — it only rescales how peaked/flat the probabilities are, which
    is exactly what honest confidence calibration should do.
    """
    arr = np.asarray(logits, dtype=np.float64)
    temperature = max(float(temperature), 1e-3)
    return softmax(arr / temperature)


def fit_temperature(
    logits: np.ndarray,
    labels: Sequence[int],
    bounds: tuple[float, float] = (0.05, 10.0),
) -> float:
    """Fit a single temperature by minimising validation NLL (standard method).

    ``logits`` is ``(n_samples, n_classes)`` raw model logits; ``labels`` are the
    integer ground-truth class indices. Optimised in log-space so the temperature
    stays strictly positive.
    """
    logits = np.asarray(logits, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    if logits.ndim != 2 or len(labels) != len(logits) or len(labels) == 0:
        raise ValueError("logits must be (n, k) and align with labels")

    rows = np.arange(len(labels))

    def nll(log_t: float) -> float:
        temperature = np.exp(log_t)
        z = logits / temperature
        z -= z.max(axis=1, keepdims=True)
        log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        return float(-log_probs[rows, labels].mean())

    from scipy.optimize import minimize_scalar

    result = minimize_scalar(
        nll,
        bounds=(float(np.log(bounds[0])), float(np.log(bounds[1]))),
        method="bounded",
    )
    return float(np.exp(result.x))


@dataclass(frozen=True)
class Calibration:
    """Loaded calibration parameters (or honest identity defaults)."""

    temperature: float = 1.0
    per_class_threshold: Mapping[str, float] = None  # type: ignore[assignment]
    method: str = "uncalibrated (no validation set fitted)"
    fitted_on: str = ""
    n_samples: int = 0

    def __post_init__(self) -> None:
        if self.per_class_threshold is None:
            object.__setattr__(self, "per_class_threshold", {})

    @property
    def is_calibrated(self) -> bool:
        return abs(self.temperature - 1.0) > 1e-6 or bool(self.per_class_threshold)

    def describe(self) -> str:
        if not self.is_calibrated:
            return self.method
        return f"temperature scaling (T={self.temperature:.3f}, n={self.n_samples})"


_DEFAULT_CALIBRATION = Calibration()
_cache: dict[str, Calibration] = {}


def load_calibration(path: Path | None = None) -> Calibration:
    """Load the calibration sidecar if present, else honest identity defaults.

    The sidecar is written by the evaluation harness only when a real labelled
    validation set is supplied, so the default app never *claims* calibration it
    has not actually performed.
    """
    sidecar = path or getattr(settings, "disease_calibration_path", None)
    if sidecar is None:
        return _DEFAULT_CALIBRATION
    sidecar = Path(sidecar)
    key = str(sidecar)
    if key in _cache:
        return _cache[key]
    cal = _DEFAULT_CALIBRATION
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            cal = Calibration(
                temperature=float(data.get("temperature", 1.0)),
                per_class_threshold={str(k): float(v) for k, v in data.get("per_class_threshold", {}).items()},
                method=str(data.get("method", "temperature scaling")),
                fitted_on=str(data.get("fitted_on", "")),
                n_samples=int(data.get("n_samples", 0)),
            )
        except Exception:
            cal = _DEFAULT_CALIBRATION
    _cache[key] = cal
    return cal


def clear_calibration_cache() -> None:
    _cache.clear()


# --- Decision policy ---------------------------------------------------------

UncertaintyLevel = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class GroupAssessment:
    """Whether a confusable top-1 earns a 'probable' (medium) verdict."""

    promote: bool
    leader: str = ""
    group_mass: float = 0.0
    margin_vs_outside: float = 0.0
    members_present: tuple[str, ...] = ()
    note_en: str = ""
    note_ar: str = ""


def assess_confusion_group(
    probs_by_key: Mapping[str, float],
    crop_probability_mass: float,
) -> GroupAssessment:
    """Decide if a split-but-coherent spot-complex prediction is *probably* correct.

    The top-1 is promoted to a medium ("probable") verdict only when ALL hold:

    * the model is visually sure of the host crop (crop mass >= the configured min),
    * the top-1 belongs to a confusion group and leads that group,
    * the group's *combined* probability mass clears ``disease_group_mass_threshold``,
    * the top-1 beats everything *outside* the group by ``disease_group_margin_min``.

    None of this changes the reported probability — only whether a real, coherent
    signal is allowed to be described as "probable" instead of discarded.
    """
    if not probs_by_key:
        return GroupAssessment(promote=False)

    leader = max(probs_by_key, key=lambda k: probs_by_key[k])
    group = confusion_group(leader)
    if len(group) <= 1:
        return GroupAssessment(promote=False, leader=leader)

    present = tuple(k for k in group if k in probs_by_key)
    group_mass = float(sum(probs_by_key[k] for k in present))
    outside = [v for k, v in probs_by_key.items() if k not in group]
    outside_best = max(outside) if outside else 0.0
    margin_vs_outside = float(probs_by_key[leader] - outside_best)
    leads_group = all(probs_by_key[leader] >= probs_by_key[k] for k in present)

    promote = bool(
        crop_probability_mass >= settings.disease_min_crop_probability_mass
        and group_mass >= settings.disease_group_mass_threshold
        and margin_vs_outside >= settings.disease_group_margin_min
        and leads_group
    )

    note_en = note_ar = ""
    if promote:
        from .diseases import disease_info

        lookalikes = [disease_info(k).name_en for k in present if k != leader]
        lookalikes_ar = [disease_info(k).name_ar for k in present if k != leader]
        note_en = (
            "Probable spot-complex disease: the model's evidence is shared across "
            f"look-alikes ({', '.join(lookalikes)}), which is why the single-class "
            "score looks low. Confirm the symptoms before treating."
        )
        note_ar = (
            "الأرجح مرض من مجموعة التبقّع: الموديل وزّع ثقته على أمراض متشابهة "
            f"({'، '.join(lookalikes_ar)})، علشان كده النسبة لمرض واحد بتبان قليلة. "
            "أكّد الأعراض قبل العلاج."
        )

    return GroupAssessment(
        promote=promote,
        leader=leader,
        group_mass=group_mass,
        margin_vs_outside=margin_vs_outside,
        members_present=present,
        note_en=note_en,
        note_ar=note_ar,
    )


def uncertainty_from_state(state: str) -> UncertaintyLevel:
    """Map a fusion state onto the plain high/medium/low uncertainty ladder."""
    if state == "confident":
        return "high"
    if state == "screening":
        return "medium"
    return "low"


def uncertainty_explanation(level: UncertaintyLevel, lang: str = "en") -> str:
    """A short, plain-language reason for the uncertainty level."""
    text = {
        "high": (
            "High confidence: a strong, well-separated visual match.",
            "ثقة عالية: تطابق بصري قوي وواضح.",
        ),
        "medium": (
            "Medium confidence: the most likely disease is stable, but it shares "
            "symptoms with look-alikes, so confirm before treating.",
            "ثقة متوسطة: المرض الأرجح ثابت، بس بيشبه أمراض تانية، فأكّد قبل العلاج.",
        ),
        "low": (
            "Low confidence: the top possibilities are close or the photo is "
            "unclear. Treat this as a screening hint, not a diagnosis.",
            "ثقة منخفضة: الاحتمالات متقاربة أو الصورة مش واضحة. اعتبرها إشارة فرز "
            "مش تشخيص.",
        ),
    }[level]
    return text[1] if lang == "ar" else text[0]
