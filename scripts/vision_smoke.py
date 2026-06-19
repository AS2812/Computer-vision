"""Live end-to-end smoke for the fused tomato diagnosis engine.

Runs the REAL pipeline (local ONNX with test-time augmentation + the hosted vision
second opinion) on a real photo and prints the honest fused result. This makes a
real network call, so it is NOT part of the automated test suite.

Usage (from the repo root):

    uv run --project services/api python scripts/vision_smoke.py "C:\\path\\to\\leaf.jpg"

With no path it falls back to the bundled Septoria sample location.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from PIL import Image  # noqa: E402

from app.config import settings  # noqa: E402
from app.analysis import analyze_image  # noqa: E402
from app.vision_llm import vision_diagnose, vision_enabled  # noqa: E402

DEFAULT_PHOTO = Path.home() / "Downloads" / (
    "septoria-lycopersici--septoria-leaf-spot---ascomycota--common-fungal-leaf-disease-of-tomatoes--"
    "tomato-leaf-showing-small-brown-spots-characteristic-of-the-disease-and-some-chlorosis-or-yellowing--"
    "franklin-county--o.jpg"
)


def main() -> int:
    settings.external_vision_enabled = True  # this script opts in to the real call
    photo = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PHOTO
    if not photo.exists():
        print(f"Photo not found: {photo}")
        return 1

    print(f"Photo: {photo.name}")
    print(f"Vision enabled: {vision_enabled()}  model: {settings.external_vision_model}")
    image = Image.open(photo).convert("RGB")

    print("\n--- Raw hosted vision second opinion ---")
    vision = vision_diagnose(image)
    if vision is None:
        print("Vision returned None (disabled, offline, or error) — local-only fallback.")
    else:
        print(f"is_tomato_leaf={vision.is_tomato_leaf}  not_sure={vision.not_sure}  ({vision.latency_ms} ms)")
        print(f"visible_signs: {vision.visible_signs}")
        for ranked in vision.ranked:
            print(f"  - {ranked.name} -> {ranked.key}  {ranked.confidence:.0%}")

    print("\n--- Fused diagnosis card ---")
    result = analyze_image(image, photo.name, crop="tomato", vision=vision)
    disease = next(item for item in result.results if item.feature == "disease")
    print(f"value: {disease.value}")
    print(f"level: {disease.level}  confidence: {disease.confidence:.0%}")
    print("evidence:")
    for line in disease.evidence:
        print(f"  - {line}")
    print("limitation:")
    print(f"  {disease.limitation}")
    print("alerts:")
    for alert in result.alerts:
        print(f"  - {alert.en}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
