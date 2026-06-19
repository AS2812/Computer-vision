"""Unit tests for the tomato evaluation harness (pure metric functions).

These need no images and no model — they guard the metric maths, the temperature
fit, and the class-index ordering the harness depends on.
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "training"))
sys.path.insert(0, str(ROOT / "services" / "api"))

from evaluate_tomato import (  # noqa: E402
    confidence_distribution,
    confused_with,
    confusion_matrix,
    macro_f1,
    main,
    per_class_prf,
)
from app.calibration import TOMATO_MODEL_LABELS, fit_temperature  # noqa: E402


def test_confusion_matrix_counts_true_vs_pred():
    y_true = [0, 0, 1, 2, 2, 2]
    y_pred = [0, 1, 1, 2, 2, 0]
    m = confusion_matrix(y_true, y_pred, 3)
    assert m[0, 0] == 1 and m[0, 1] == 1
    assert m[1, 1] == 1
    assert m[2, 2] == 2 and m[2, 0] == 1
    assert int(m.sum()) == len(y_true)


def test_per_class_prf_and_macro_f1():
    # Perfect predictions => P=R=F1=1 for every class with support.
    y = [0, 1, 2, 0, 1, 2]
    m = confusion_matrix(y, y, 3)
    metrics = per_class_prf(m, ["a", "b", "c"])
    assert all(cm.precision == 1.0 and cm.recall == 1.0 and cm.f1 == 1.0 for cm in metrics)
    assert macro_f1(metrics) == 1.0


def test_confused_with_orders_by_count():
    labels = ["a", "b", "c", "d"]
    # Class 0 truth predicted as: a×1, b×3, c×2.
    y_true = [0, 0, 0, 0, 0, 0]
    y_pred = [0, 1, 1, 1, 2, 2]
    m = confusion_matrix(y_true, y_pred, 4)
    assert confused_with(m, labels, 0) == [("b", 3), ("c", 2)]


def test_confidence_distribution_splits_correct_and_wrong():
    dist = confidence_distribution([0.9, 0.8, 0.3, 0.4], [True, True, False, False])
    assert dist["correct"]["n"] == 2 and dist["wrong"]["n"] == 2
    assert dist["correct"]["mean"] > dist["wrong"]["mean"]


def test_harness_uses_the_same_class_order_as_serving():
    # The harness scores exactly the 10 tomato classes in model order.
    assert len(TOMATO_MODEL_LABELS) == 10
    assert TOMATO_MODEL_LABELS[6] == "Tomato___Target_Spot"


def test_fit_temperature_is_bounded_and_positive():
    rng = np.random.default_rng(1)
    logits = rng.normal(size=(50, 4))
    labels = rng.integers(0, 4, size=50)
    temperature = fit_temperature(logits, labels)
    assert 0.05 <= temperature <= 10.0


def test_main_without_dataset_prints_help_and_exits_zero(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "No dataset given" in out
    assert "Tomato___Target_Spot" in out
