"""Image-based *supporting* evidence for Target Spot (Corynespora cassiicola).

Target Spot lesions are small brown/necrotic spots, often with faint concentric
rings (the "target" look) and a yellow halo, that start on older lower leaves and
look almost identical to Early Blight and Bacterial Spot. This module measures a
few cheap, honest RGB signals that *corroborate* that visual pattern.

It is deliberately **supporting evidence only** — never proof. The numbers are
plain pixel statistics, clearly labelled as such, and every output repeats that
Target Spot can be confused with its look-alikes. Nothing here is fed back into
the model's confidence; it only gives the farmer and the report something
concrete to check against the leaf in hand.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class TargetSpotEvidence:
    brown_spot_percent: float        # brown/necrotic pixels as % of leaf area
    yellow_halo_percent: float       # yellow pixels bordering brown spots, % of leaf
    spot_clusters: int               # count of distinct small brown clusters
    ring_texture_score: float        # 0..1 local-contrast proxy for concentric rings
    sharpness: float                 # variance-of-gradient proxy (low => blurry)
    leaf_area_percent: float         # green leaf coverage, % of the photo
    blurry: bool
    leaf_too_small: bool

    @property
    def has_spot_pattern(self) -> bool:
        """Whether the photo shows the brown-spot pattern Target Spot belongs to."""
        return self.brown_spot_percent >= 1.0 and self.spot_clusters >= 1


def _downscaled_rgb(image: Image.Image, max_side: int = 384) -> np.ndarray:
    sample = image.convert("RGB")
    sample.thumbnail((max_side, max_side))
    return np.asarray(sample, dtype=np.float32) / 255.0


def _count_clusters(mask: np.ndarray, min_pixels: int = 4, max_clusters: int = 400) -> int:
    """Flood-fill connected-component count, capped so a huge blob cannot run away."""
    mask = mask.astype(bool)
    visited = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    count = 0
    from collections import deque

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            size = 0
            queue = deque([(y, x)])
            visited[y, x] = True
            while queue:
                cy, cx = queue.popleft()
                size += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))
            if size >= min_pixels:
                count += 1
                if count >= max_clusters:
                    return count
    return count


def target_spot_evidence(image: Image.Image) -> TargetSpotEvidence:
    """Measure honest RGB signals that corroborate (never prove) Target Spot."""
    array = _downscaled_rgb(image)
    red, green, blue = array[..., 0], array[..., 1], array[..., 2]
    luminance = array.mean(axis=2)

    leaf_like = (green > 0.18) & (blue < 0.55) & ((green > red * 0.6) | (red > green * 1.02))
    leaf_pixels = max(int(leaf_like.sum()), 1)

    # Brown / necrotic lesion pixels: red dominant, mid-dark, low blue.
    brown = (red > green * 1.08) & (green > blue * 1.05) & (red > 0.2) & (luminance < 0.7)
    brown = brown & leaf_like
    brown_percent = 100.0 * int(brown.sum()) / leaf_pixels

    # Yellow halo: yellowish pixels next to the brown lesions.
    yellow = (red > 0.45) & (green > 0.40) & (blue < 0.4) & leaf_like
    halo = yellow & _dilate(brown)
    halo_percent = 100.0 * int(halo.sum()) / leaf_pixels

    clusters = _count_clusters(brown)

    # Ring/target texture proxy: concentric rings create alternating light/dark
    # bands, i.e. high local luminance contrast *inside* the brown regions.
    ring_score = 0.0
    if int(brown.sum()) > 12:
        gy, gx = np.gradient(luminance)
        grad = np.sqrt(gx * gx + gy * gy)
        ring_score = float(np.clip(grad[brown].mean() * 6.0, 0.0, 1.0))

    # Sharpness proxy: variance of the gradient magnitude over the whole image.
    gy, gx = np.gradient(luminance)
    sharpness = float(np.var(np.sqrt(gx * gx + gy * gy)))

    leaf_area_percent = 100.0 * leaf_pixels / luminance.size

    return TargetSpotEvidence(
        brown_spot_percent=round(brown_percent, 1),
        yellow_halo_percent=round(halo_percent, 1),
        spot_clusters=int(clusters),
        ring_texture_score=round(ring_score, 2),
        sharpness=round(sharpness, 5),
        leaf_area_percent=round(leaf_area_percent, 1),
        blurry=sharpness < 0.0008,
        leaf_too_small=leaf_area_percent < 8.0,
    )


def _dilate(mask: np.ndarray) -> np.ndarray:
    """Cheap 1-pixel dilation so 'adjacent to a spot' has a little tolerance."""
    out = mask.copy()
    out[:-1, :] |= mask[1:, :]
    out[1:, :] |= mask[:-1, :]
    out[:, :-1] |= mask[:, 1:]
    out[:, 1:] |= mask[:, :-1]
    return out


_LOOKALIKE_EN = "Target Spot can look like Early Blight and Bacterial Spot — confirm on the leaf."
_LOOKALIKE_AR = "التبقّع الهدفي ممكن يتشابه مع اللفحة المبكرة والتبقّع البكتيري — أكّد على الورقة نفسها."


def supporting_lines(ev: TargetSpotEvidence, lang: str = "en") -> list[str]:
    """Plain-language supporting bullets — explicitly evidence, not proof."""
    ar = lang == "ar"
    lines: list[str] = []

    if ev.brown_spot_percent >= 1.0:
        lines.append(
            f"بقع بنية/متنخّرة على حوالي {ev.brown_spot_percent:.0f}% من مساحة الورقة"
            if ar else
            f"Brown/necrotic spotting on ~{ev.brown_spot_percent:.0f}% of the visible leaf area."
        )
    if ev.spot_clusters >= 2:
        lines.append(
            f"عدد بقع منفصلة صغيرة: حوالي {ev.spot_clusters}"
            if ar else
            f"About {ev.spot_clusters} separate small spots (Target Spot is multi-spotted)."
        )
    if ev.ring_texture_score >= 0.3:
        lines.append(
            "ملمس حلقي/دواير جوّه البقع (شكل الهدف) — إشارة داعمة"
            if ar else
            "Ring-like texture inside the spots (the 'target' look) — a supporting sign."
        )
    if ev.yellow_halo_percent >= 0.3:
        lines.append(
            "هالة صفرا حوالين البقع"
            if ar else
            "A yellow halo bordering the spots."
        )
    # Say so plainly when the photo does not actually show the spot pattern, even
    # if other quality flags fire — honesty over a falsely reassuring bullet list.
    if not ev.has_spot_pattern:
        lines.append(
            "مفيش نمط بقع واضح في الصورة دي يدعم التبقّع الهدفي"
            if ar else
            "No clear spotting pattern in this photo to support Target Spot."
        )
    if ev.blurry:
        lines.append(
            "الصورة فيها رجفة/مش واضحة — صوّر أوضح يحسّن الدقة"
            if ar else
            "The photo looks soft/blurry — a sharper photo would improve reliability."
        )
    if ev.leaf_too_small:
        lines.append(
            "الورقة صغيرة في الصورة — قرّب الكاميرا من الورقة المصابة"
            if ar else
            "The leaf fills little of the frame — move closer to the affected leaf."
        )

    lines.append(_LOOKALIKE_AR if ar else _LOOKALIKE_EN)
    return lines
