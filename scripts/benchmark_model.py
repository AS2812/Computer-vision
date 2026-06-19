"""Repeatable local CPU inference and memory benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from pathlib import Path

import psutil
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))

from app.analysis import analyze_image  # noqa: E402
from app.model_runtime import runtime_for_crop  # noqa: E402


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * percentile), len(ordered) - 1)
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--image", type=Path, default=ROOT / "tests/fixtures/banana_cordana_public_domain.jpg")
    parser.add_argument("--crop", choices=["tomato", "banana"], default="banana")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    runtime = runtime_for_crop(args.crop)
    if not runtime.session:
        print("No checksum-verified ONNX model installed; benchmark skipped.")
        return 0
    image = Image.open(args.image).convert("RGB")
    process = psutil.Process()
    peak_rss = process.memory_info().rss
    stop = threading.Event()

    def sample_memory() -> None:
        nonlocal peak_rss
        while not stop.wait(0.01):
            peak_rss = max(peak_rss, process.memory_info().rss)

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    durations: list[float] = []
    try:
        for _ in range(max(args.runs, 1)):
            started = time.perf_counter()
            analyze_image(image, args.image.name, runtime=runtime, crop=args.crop)
            durations.append(time.perf_counter() - started)
    finally:
        stop.set()
        sampler.join(timeout=1)

    report = {
        "runs": len(durations),
        "provider": runtime.provider,
        "mean_seconds": round(statistics.mean(durations), 4),
        "p95_seconds": round(_percentile(durations, 0.95), 4),
        "peak_rss_mb": round(peak_rss / 1024 / 1024, 2),
        "image": str(args.image.relative_to(ROOT)),
        "crop": args.crop,
    }
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.check and (report["p95_seconds"] >= 15 or report["peak_rss_mb"] >= 4096):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
