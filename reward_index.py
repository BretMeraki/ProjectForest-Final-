# forest_app/modules/reward_index.py

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RewardIndex:
    """
    Tracks the reward-related state, which influences offering generation.

    Attributes:
      - readiness: A float (0.0 to 1.0) representing the current readiness for a reward.
      - generosity: A float (0.0 to 1.0) indicating the evolving generosity level.
      - desire_signal: A float (0.0 to 1.0) capturing the user's expressed desire for reward/intervention.
    """

    def __init__(self):
        self.readiness = 0.5
        self.generosity = 0.5
        self.desire_signal = 0.5

    def to_dict(self) -> dict:
        return {
            "readiness": self.readiness,
            "generosity": self.generosity,
            "desire_signal": self.desire_signal,
        }

    def update_from_dict(self, data: dict):
        self.readiness = data.get("readiness", self.readiness)
        self.generosity = data.get("generosity", self.generosity)
        self.desire_signal = data.get("desire_signal", self.desire_signal)
