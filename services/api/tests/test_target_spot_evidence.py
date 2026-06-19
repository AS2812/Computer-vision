"""Tests for the Target Spot image symptom helper (supporting evidence only)."""

import numpy as np
from PIL import Image

from app.target_spot import TargetSpotEvidence, supporting_lines, target_spot_evidence


def _leaf_with_brown_spots() -> Image.Image:
    """A green leaf with a few brown spots and a yellow ring around them."""
    arr = np.full((160, 160, 3), (40, 150, 50), dtype=np.uint8)
    for cy, cx in [(40, 40), (110, 60), (70, 120)]:
        yy, xx = np.ogrid[:160, :160]
        ring = (yy - cy) ** 2 + (xx - cx) ** 2
        arr[ring <= 36] = (120, 70, 40)          # brown spot core
        halo = (ring > 36) & (ring <= 100)
        arr[halo] = (180, 170, 60)               # yellow halo
    return Image.fromarray(arr)


def test_evidence_detects_brown_spotting_pattern():
    ev = target_spot_evidence(_leaf_with_brown_spots())
    assert isinstance(ev, TargetSpotEvidence)
    assert ev.brown_spot_percent > 0
    assert ev.spot_clusters >= 1
    assert ev.has_spot_pattern is True


def test_clean_green_leaf_has_no_spot_pattern():
    ev = target_spot_evidence(Image.new("RGB", (128, 128), (30, 160, 40)))
    assert ev.brown_spot_percent < 1.0
    assert ev.has_spot_pattern is False
    lines = supporting_lines(ev, "en")
    assert any("No clear spotting pattern" in line for line in lines)


def test_supporting_lines_always_disclose_lookalikes_in_both_languages():
    ev = target_spot_evidence(_leaf_with_brown_spots())
    en = supporting_lines(ev, "en")
    ar = supporting_lines(ev, "ar")
    assert any("Early Blight" in line and "Bacterial Spot" in line for line in en)
    assert any("اللفحة المبكرة" in line and "التبقّع البكتيري" in line for line in ar)
    # The wording is supporting, not proof — no "confirmed"/"definitely".
    assert not any("confirmed" in line.lower() for line in en)


def test_blurry_and_small_leaf_flags_are_surfaced():
    # A nearly-flat image has almost no gradient => flagged blurry.
    ev = target_spot_evidence(Image.new("RGB", (128, 128), (60, 60, 60)))
    assert ev.blurry is True
    lines = supporting_lines(ev, "en")
    assert any("blurry" in line.lower() for line in lines)
