"""Evaluation gate helpers used by a future training job."""

from dataclasses import dataclass


@dataclass
class Evaluation:
    macro_f1: float
    minimum_recall: float
    quantization_f1_loss: float
    inference_p95_seconds: float
    peak_memory_mb: float


def passes_release_gate(metrics: Evaluation) -> bool:
    return (
        metrics.macro_f1 >= 0.90
        and metrics.minimum_recall >= 0.80
        and metrics.quantization_f1_loss <= 0.02
        and metrics.inference_p95_seconds <= 1
        and metrics.peak_memory_mb < 4096
    )

