"""Write local Supabase connection values into .env without printing secrets."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _status_values() -> dict[str, str]:
    pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not pnpm:
        raise RuntimeError("pnpm is required to read local Supabase status.")
    result = subprocess.run(
        [pnpm, "dlx", "supabase", "status", "-o", "env"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return dict(re.findall(r'^([A-Z0-9_]+)="(.*)"$', result.stdout, flags=re.MULTILINE))


def _update_env(updates: dict[str, str]) -> None:
    original = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    lines = original.splitlines()
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in updates:
            output.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    values = _status_values()
    required = {"API_URL", "ANON_KEY", "SERVICE_ROLE_KEY"}
    missing = required - values.keys()
    if missing:
        raise RuntimeError(f"Supabase status did not return: {', '.join(sorted(missing))}")
    _update_env(
        {
            "AGROVISION_API_URL": "http://localhost:8765",
            "VITE_API_URL": "http://localhost:8765",
            "VITE_SUPABASE_URL": values["API_URL"],
            "VITE_SUPABASE_ANON_KEY": values["ANON_KEY"],
            "SUPABASE_URL": values["API_URL"],
            "SUPABASE_SERVICE_ROLE_KEY": values["SERVICE_ROLE_KEY"],
        }
    )
    print("Configured local Supabase connection values in .env.")


if __name__ == "__main__":
    main()
