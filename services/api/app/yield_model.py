"""Transparent canopy-based yield indicator.

This is intentionally NOT a trained model. The earlier prototype fit a regressor
on randomly generated numbers, so its "predictions" were meaningless. It is
replaced by a documented, transparent formula over the real measured canopy-vigor
and vegetation-coverage indices, so the reported value is honest and reproducible.
It remains an image-derived indicator, not a calibrated agronomic yield prediction.
"""

import numpy as np


def predict_yield_potential(health: float, coverage: float) -> float:
    """Relative canopy-based yield indicator in [0, 1].

    Combines the canopy vigor index (``health``) with the measured vegetation
    coverage. Transparent and reproducible — not a calibrated yield model.
    """
    estimate = 0.6 * float(health) + 0.4 * float(coverage)
    return float(np.clip(estimate, 0, 1))
