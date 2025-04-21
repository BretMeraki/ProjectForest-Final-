# forest_app/modules/development_index.py
# =====================================================================
#  FullDevelopmentIndex – 0‑to‑1 gauges of positive personal capacity
# =====================================================================
from __future__ import annotations

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Canonical ordered list (used by BaselineAssessmentEngine)
DEV_KEYS: List[str] = [
    "happiness",
    "career",
    "health",
    "financial",
    "relationship",
    "executive_functioning",
    "social_life",
    "charisma",
    "entrepreneurship",
    "family_planning",
    "generational_wealth",
    "adhd_risk",
    "odd_risk",
    "homeownership",
    "dream_location",
]

def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))

class FullDevelopmentIndex:
    """
    Mutable container of {dev_key: float}.
    • All values live in [0,1].
    • Provides helpers for baseline loading and task‑driven boosts.
    """

    # ---------------------------------------------------------------- #
    def __init__(self) -> None:
        self.indexes: Dict[str, float] = {k: 0.50 for k in DEV_KEYS}

    # ---------------------------------------------------------------- #
    #  Public APIs
    # ---------------------------------------------------------------- #
    def baseline_from_reflection(self, reflection: str) -> None:
        """
        Quick heuristic: if the reflection uses clearly positive language,
        nudge a few happiness‑adjacent gauges up slightly (0.01).
        This keeps things feeling responsive even before tasks complete.
        """
        low = reflection.lower()
        hints = ("grateful", "proud", "excited", "optimistic")
        if any(h in low for h in hints):
            for k in ("happiness", "social_life", "charisma"):
                self.indexes[k] = _clamp(self.indexes[k] + 0.01)

    def dynamic_adjustment(self, deltas: Dict[str, float]) -> None:
        """Arbitrary external tweak (used by Metrics engine)."""
        for k, dv in deltas.items():
            if k in self.indexes:
                self.indexes[k] = _clamp(self.indexes[k] + dv)

    def apply_task_effect(
        self,
        relevant_indexes: List[str],
        tier_mult: float,
        momentum: float,
    ) -> None:
        """
        Boost each relevant dev gauge.

        boost = 0.02 * tier_mult * momentum
        • tier_mult: 1.0 (Bud), 1.5 (Bloom), 2.0 (Blossom)
        • momentum  : EWMA overall momentum ∈ [0,1]
        """
        if not relevant_indexes:
            return
        boost = 0.02 * tier_mult * momentum
        for key in relevant_indexes:
            if key in self.indexes:
                self.indexes[key] = _clamp(self.indexes[key] + boost)
        logger.info(
            "Dev‑indexes boosted %s by %.3f (tier×μ)",
            relevant_indexes,
            boost,
        )

    # ---------------------------------------------------------------- #
    #  Persistence helpers
    # ---------------------------------------------------------------- #
    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return {"indexes": self.indexes}

    def update_from_dict(self, data: Dict[str, Dict[str, float]]) -> None:
        if "indexes" in data:
            for k, v in data["indexes"].items():
                if k in DEV_KEYS:
                    self.indexes[k] = _clamp(float(v))

    # ---------------------------------------------------------------- #
    #  Debug convenience
    # ---------------------------------------------------------------- #
    def __str__(self) -> str:  # noqa: Dunder
        return json.dumps(self.indexes, indent=2, default=str)
