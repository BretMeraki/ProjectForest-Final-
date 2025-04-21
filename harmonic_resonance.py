# forest_app/modules/harmonic_resonance.py

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HarmonicResonanceEngine:
    """
    HarmonicResonanceEngine computes an internal resonance score that reflects the
    overall balance (or internal harmony) of the system. It utilizes core metrics from
    the MemorySnapshot (e.g., capacity, shadow score, magnitude) and can be later extended to
    incorporate additional factors from development indexes, memory echoes, and archetype influence.

    The computed resonance score (normalized between 0.0 and 1.0) is then used to determine
    a dominant theme, which can drive system actions (e.g., task generation, narrative tone adjustments).

    For example, a higher capacity combined with a lower shadow score should yield a high resonance
    (favoring a theme like "Renewal" or "Resilience"), while high shadow or low capacity may result in
    a lower score (suggesting a need to "Reset" or adopt a "Reflection" approach).

    The engine exposes a compute_resonance() method, along with simple serialization methods.
    """

    def __init__(self, config: dict = None):
        # Optional configuration; default weights can be provided here.
        # These weights can be tuned: how much each metric contributes to overall resonance.
        self.config = config or {
            "capacity_weight": 0.4,
            "shadow_weight": 0.4,  # Shadow will be subtracted (i.e., lower shadow is better).
            "magnitude_weight": 0.2,  # Lower magnitude (closer to 1) is better.
        }
        self.last_computed = None

    def compute_resonance(self, snapshot: dict) -> dict:
        """
        Computes a composite resonance score based on key metrics from the snapshot.

        Expected snapshot keys include:
          - capacity: a value between 0.0 and 1.0 (higher means more available resources).
          - shadow_score: a value between 0.0 and 1.0 (lower is more harmonious).
          - magnitude: a value typically between 1.0 and 10.0 (lower magnitude may indicate gentler change).

        The resonance score is computed as a weighted combination of these inputs.
        Based on the score, a dominant theme is selected.

        Returns:
          A dictionary with keys:
            - "theme": A textual description (e.g., "Renewal", "Resilience", "Reflection", "Reset").
            - "resonance_score": A normalized float (0.0 to 1.0).
        """
        capacity = snapshot.get("capacity", 0.5)  # Expectation: 0.0 (low) to 1.0 (high)
        shadow = snapshot.get("shadow_score", 0.5)  # Lower is better
        magnitude = snapshot.get(
            "magnitude", 5.0
        )  # 1.0 (small change) to 10.0 (large change)

        # Normalize magnitude so that a lower magnitude contributes positively.
        # For instance, if we assume magnitude 1 is best and 10 worst, we can compute:
        normalized_magnitude = (
            10 - magnitude
        ) / 9  # Gives ~1.0 when magnitude is 1, ~0 when magnitude is 10

        # Compute each weighted component.
        capacity_component = self.config["capacity_weight"] * capacity
        shadow_component = self.config["shadow_weight"] * (1.0 - shadow)
        magnitude_component = self.config["magnitude_weight"] * normalized_magnitude

        # Composite resonance is the sum of weighted components.
        resonance_score = capacity_component + shadow_component + magnitude_component
        resonance_score = round(max(0.0, min(1.0, resonance_score)), 2)
        self.last_computed = datetime.utcnow().isoformat()

        # Determine a theme based on thresholds.
        if resonance_score >= 0.75:
            theme = "Renewal"
        elif resonance_score >= 0.5:
            theme = "Resilience"
        elif resonance_score >= 0.25:
            theme = "Reflection"
        else:
            theme = "Reset"

        logger.info("Computed resonance: score=%s, theme=%s", resonance_score, theme)
        return {"theme": theme, "resonance_score": resonance_score}

    def to_dict(self) -> dict:
        """
        Serializes the engine's configuration and last computed timestamp.
        """
        return {"config": self.config, "last_computed": self.last_computed}

    def update_from_dict(self, data: dict):
        if "config" in data:
            self.config.update(data["config"])
        self.last_computed = data.get("last_computed", self.last_computed)
