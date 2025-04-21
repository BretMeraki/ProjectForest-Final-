# forest_app/modules/practical_consequence.py

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PracticalConsequenceEngine:
    """
    This engine computes a practical consequence score reflecting real-world pressures.
    It now incorporates the effect of missed deadlines (only when current path is 'structured').
    """

    def __init__(self, calibration=None):
        self.calibration = calibration or {
            "base_weight": 1.0,
            "time_weight": 0.25,
            "energy_weight": 0.25,
            "money_weight": 0.20,
            "relational_weight": 0.15,
            "safety_weight": 0.15,
        }
        self.last_update = datetime.utcnow().isoformat()
        self.score = 0.5

    def update_signals_from_reflection(self, reflection: str):
        reflection_lower = reflection.lower()
        adjustments = {
            "time": 0.0,
            "energy": 0.0,
            "money": 0.0,
            "relational": 0.0,
            "safety": 0.0,
        }
        # Example heuristics
        if "rush" in reflection_lower or "deadline" in reflection_lower:
            adjustments["time"] += 0.1
        if "delay" in reflection_lower or "waiting" in reflection_lower:
            adjustments["time"] -= 0.05
        if "tired" in reflection_lower or "exhausted" in reflection_lower:
            adjustments["energy"] += 0.1
        if "energized" in reflection_lower or "motivated" in reflection_lower:
            adjustments["energy"] -= 0.05
        if "money" in reflection_lower or "debt" in reflection_lower:
            adjustments["money"] += 0.1
        if "affluent" in reflection_lower or "wealth" in reflection_lower:
            adjustments["money"] -= 0.05
        if (
            "lonely" in reflection_lower
            or "isolated" in reflection_lower
            or "argument" in reflection_lower
        ):
            adjustments["relational"] += 0.1
        if "supported" in reflection_lower or "connected" in reflection_lower:
            adjustments["relational"] -= 0.05
        if "unsafe" in reflection_lower or "fear" in reflection_lower:
            adjustments["safety"] += 0.1
        if "secure" in reflection_lower or "protected" in reflection_lower:
            adjustments["safety"] -= 0.05

        total_adjustment = (
            self.calibration["time_weight"] * adjustments["time"]
            + self.calibration["energy_weight"] * adjustments["energy"]
            + self.calibration["money_weight"] * adjustments["money"]
            + self.calibration["relational_weight"] * adjustments["relational"]
            + self.calibration["safety_weight"] * adjustments["safety"]
        )
        # Update consequence score, clamped between 0 and 1.
        self.score = max(
            0.0,
            min(1.0, self.score + self.calibration["base_weight"] * total_adjustment),
        )
        logger.info(
            "Practical consequence signals updated: %s (adjustments: %s)",
            self.score,
            adjustments,
        )
        self.last_update = datetime.utcnow().isoformat()

    def compute_consequence(self) -> float:
        return round(self.score, 2)

    def get_consequence_level(self) -> str:
        if self.score >= 0.8:
            return "High Impact"
        elif self.score >= 0.6:
            return "Moderate Impact"
        elif self.score >= 0.4:
            return "Low Impact"
        else:
            return "Minimal Impact"

    def get_task_difficulty_multiplier(self) -> float:
        multiplier = 1.0 + (1.0 - self.score) * 0.5
        return round(multiplier, 2)

    def get_tone_modifier(self) -> dict:
        if self.score >= 0.8:
            tone = {"empathy": 1.2, "encouragement": 0.8}
        elif self.score >= 0.6:
            tone = {"empathy": 1.1, "encouragement": 0.9}
        elif self.score >= 0.4:
            tone = {"empathy": 1.0, "encouragement": 1.0}
        else:
            tone = {"empathy": 0.9, "encouragement": 1.1}
        return tone

    def update_with_deadline_penalties(self, snapshot: dict):
        """
        This function increases the practical consequence score when deadlines are missed.
        It applies only if the current path is 'structured'.
        """
        if snapshot.get("current_path") == "structured":
            # For each missed deadline, we could increase the consequence by a fixed factor.
            # Here we assume that update_signals_from_reflection already handles general signals;
            # we add an extra penalty.
            penalty = 0.05  # Example penalty per missed deadline
            # This function can be called from the orchestrator when a deadline is missed.
            self.score = min(1.0, self.score + penalty)
            logger.info(
                "Practical consequence score increased due to missed deadline. New score: %s",
                self.score,
            )

    def to_dict(self):
        return {
            "calibration": self.calibration,
            "score": self.score,
            "last_update": self.last_update,
        }

    def update_from_dict(self, data: dict):
        if "calibration" in data:
            self.calibration.update(data["calibration"])
        self.score = data.get("score", self.score)
        self.last_update = data.get("last_update", self.last_update)
