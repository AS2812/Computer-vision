import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ml/models/manifest.json"


def setting(name: str) -> str | None:
    if value := os.getenv(name):
        return value
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key == name and value:
                return value
    return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key, model in manifest["models"].items():
        target = ROOT / "ml/models" / model["file"]
        expected = model.get("sha256")
        env_name = "AGROVISION_BANANA_DISEASE_MODEL_URL" if key == "banana_disease" else "AGROVISION_DISEASE_MODEL_URL"
        url = setting(env_name) or model.get("url")
        if target.exists() and expected not in (None, "pending") and sha256(target) == expected:
            print(f"Verified {target.name}")
            continue
        if not url or expected in (None, "pending"):
            print(f"Skipping {target.name}: no approved checksum-verified weights configured.")
            continue
        print(f"Downloading {target.name}")
        urllib.request.urlretrieve(url, target)
        if sha256(target) != expected:
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Checksum mismatch for {target.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
