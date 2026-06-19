"""Verify that installed model metadata and checksum remain internally consistent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ml/models/manifest.json"


def main() -> int:
    manifests = json.loads(MANIFEST.read_text(encoding="utf-8"))["models"]
    for manifest in manifests.values():
        model = ROOT / "ml/models" / manifest["file"]
        if not model.exists():
            print(f"No local {model.name} weights installed; checksum audit skipped.")
            continue
        digest = hashlib.sha256(model.read_bytes()).hexdigest()
        if digest != manifest["sha256"]:
            raise RuntimeError(f"Checksum mismatch for {model.name}")
        if "field_accuracy" not in manifest.get("metrics", {}):
            raise RuntimeError(f"Missing field_accuracy declaration for {model.name}")
        if manifest["validation_level"] == "validated" and manifest["metrics"]["field_accuracy"] is None:
            raise RuntimeError("A validated model must include independent field accuracy.")
        print(f"Verified {model.name}: checksum and honest validation metadata are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
