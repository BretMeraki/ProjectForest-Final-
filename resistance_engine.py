# forest_app/modules/resistance_engine.py

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def clamp01(x: float) -> float:
    """Clamp a float to the 0.0–1.0 range."""
    return max(0.0, min(1.0, x))


class ResistanceEngine:
    """
    Computes the 'resistance' value for a task, on a scale from 0.0 (very easy)
    to 1.0 (very difficult), based on:
      - shadow_score (σ): 0.0–1.0 (higher means more inner resistance)
      - capacity (c):    0.0–1.0 (higher means more available capacity)
      - momentum (μ):    0.0–1.0 (higher means more forward momentum)
      - magnitude (M):   1.0–10.0 (higher means greater intended impact)

    Formula (§8):
      R = clamp₀₋₁(
            0.4
          + 0.5 * σ
          - 0.3 * c
          - 0.2 * μ
          + 0.05 * (M - 5)
      )
    """

    @staticmethod
    def compute(
        shadow_score: float,
        capacity: float,
        momentum: float,
        magnitude: float
    ) -> float:
        """
        Calculate resistance based on the core metrics.

        Args:
            shadow_score: float in [0.0, 1.0]
            capacity:     float in [0.0, 1.0]
            momentum:     float in [0.0, 1.0]
            magnitude:    float, expected in [1.0, 10.0]

        Returns:
            resistance R, clamped to [0.0, 1.0]
        """
        base = 0.4
        comp = (
            base
            + 0.5 * shadow_score
            - 0.3 * capacity
            - 0.2 * momentum
            + 0.05 * (magnitude - 5.0)
        )
        r = clamp01(comp)
        logger.debug(
            "Computed resistance: base=%.2f +0.5*σ(%.2f) -0.3*c(%.2f) -0.2*μ(%.2f) +0.05*(M-5)(%.2f) = %.2f → R=%.2f",
            base, shadow_score, capacity, momentum, (magnitude - 5.0), comp, r
        )
        return r