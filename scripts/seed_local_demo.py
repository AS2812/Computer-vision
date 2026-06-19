"""Create a local demo account, farm, mission, and persisted sample analysis."""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))

from app.analysis import analyze_image  # noqa: E402
from app.persistence import analysis_store  # noqa: E402


def main() -> int:
    if not analysis_store.enabled:
        print("Supabase is not configured; demo persistence seed skipped.")
        return 0
    image = Image.new("RGB", (640, 420), (55, 135, 62))
    content = io.BytesIO()
    image.save(content, format="PNG")
    analysis = analyze_image(image, "seeded-demo-field.png")
    if not analysis_store.save_analysis(analysis, content.getvalue(), "image/png"):
        raise RuntimeError(f"Could not seed local Supabase persistence ({analysis_store.last_error}).")
    print("Seeded local demo account, farm, mission, image, and analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
