# forest_app/modules/xp_mastery.py

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class XPMastery:
    """
    Handles XP‐based stage computation and generates concrete Mastery Challenges
    as the user approaches each new stage.
    """

    # Define XP stage thresholds and associated concrete Mastery Challenge types.
    XP_STAGES = {
        "Awakening": {
            "min_xp": 0,
            "max_xp": 150,
            "challenge_type": "Naming Desire",
        },
        "Committing": {
            "min_xp": 150,
            "max_xp": 300,
            "challenge_type": "Showing Up",
        },
        "Deepening": {
            "min_xp": 300,
            "max_xp": 450,
            "challenge_type": "Softening Shadow",
        },
        "Harmonizing": {
            "min_xp": 450,
            "max_xp": 600,
            "challenge_type": "Harmonizing Seeds",
        },
        "Becoming": {
            "min_xp": 600,
            "max_xp": float("inf"),
            "challenge_type": "Integration Prompt",
        },
    }

    def __init__(self):
        # Nothing to initialize for now—methods are stateless beyond XP_STAGES
        pass

    # --- Method to serialize state (ADDED) ---
    def to_dict(self) -> dict:
        """
        Serializes the engine's state (currently stateless).
        """
        # Since there's no state in __init__ to save, return empty dict.
        # If state is added later, persist it here.
        return {}
    # --- End Added Method ---

    # --- Method to load state (Optional but good practice) ---
    def update_from_dict(self, data: dict):
        """
        Updates the engine's state from a dictionary (currently stateless).
        """
        # If state is added later, load it here.
        logger.debug("XPMastery state loaded (currently stateless).")
        pass
    # --- End Added Method ---


    def get_current_stage(self, xp: float) -> dict:
        """
        Determines the current XP stage based on total XP.
        Returns a dict with:
          - stage: name
          - challenge_type
          - min_xp
          - max_xp
        """
        for stage, params in self.XP_STAGES.items():
            if params["min_xp"] <= xp < params["max_xp"]:
                return {
                    "stage": stage,
                    "challenge_type": params["challenge_type"],
                    "min_xp": params["min_xp"],
                    "max_xp": params["max_xp"],
                }
        return {
            "stage": "Unknown",
            "challenge_type": "Generic Mastery",
            "min_xp": 0,
            "max_xp": 0,
        }

    def generate_challenge_content(self, xp: float, snapshot: dict) -> dict:
        """
        Generates a concrete Mastery Challenge based on the current XP stage.
        Returns a dict with:
          - stage
          - challenge_type
          - challenge_content: detailed, actionable prompt
          - triggered_at: ISO timestamp
        """
        info = self.get_current_stage(xp)
        ct = info["challenge_type"]

        if ct == "Naming Desire":
            act = (
                "Select one tangible object or action that symbolizes your deepest desire. "
                "Write it on a durable card or journal and place it somewhere visible every day."
            )
        elif ct == "Showing Up":
            act = (
                "Commit to a specific appointment or activity. "
                "Schedule a meeting with someone influential or sign up for a skill-building class."
            )
        elif ct == "Softening Shadow":
            act = (
                "Pick one recurring challenge and take a stress-relieving action. "
                "For example, reach out for counseling, do a relaxation routine, or set a boundary."
            )
        elif ct == "Harmonizing Seeds":
            act = (
                "Link two of your goals with a concrete plan. "
                "Maybe create a vision board or schedule a day combining creative and organizational tasks."
            )
        elif ct == "Integration Prompt":
            act = (
                "Create a tangible artifact of your journey—a manifesto, art piece, or community project—"
                "to showcase your integrated self."
            )
        else:
            act = "Reflect on a concrete step to advance your personal journey."

        content = (
            f"Mastery Challenge for the {info['stage']} Stage:\n"
            f"Your task is '{ct}'.\n"
            f"Concrete action: {act}\n"
            "Focus on a real-world step that impacts you tangibly and document your plan."
        )

        challenge = {
            "stage":          info["stage"],
            "challenge_type": ct,
            "challenge_content": content,
            "triggered_at":   datetime.utcnow().isoformat(),
        }
        logger.info("Generated Mastery Challenge: %s", challenge)
        return challenge

    def check_xp_stage(self, snapshot) -> dict:
        """
        If the user is within 10 XP of the next stage threshold, generate
        and return a Mastery Challenge; otherwise return {}.
        """
        # Ensure snapshot has an 'xp' attribute
        if not hasattr(snapshot, 'xp'):
             logger.warning("Snapshot object missing 'xp' attribute in check_xp_stage.")
             return {}

        current_xp = snapshot.xp
        info = self.get_current_stage(current_xp)
        threshold = 10 # XP_MASTERY_PROXIMITY_THRESHOLD could be used from constants

        # Handle cases where max_xp might be infinity for the last stage
        if info["max_xp"] == float("inf"):
            xp_to_next = float("inf") # Effectively never triggers for the last stage
        else:
            xp_to_next = info["max_xp"] - current_xp

        if 0 <= xp_to_next <= threshold:
            # Ensure snapshot has a to_dict method or handle appropriately
            if hasattr(snapshot, 'to_dict') and callable(snapshot.to_dict):
                 snapshot_dict = snapshot.to_dict()
            else:
                 logger.warning("Snapshot object missing 'to_dict' method in check_xp_stage. Passing empty dict.")
                 snapshot_dict = {}
            return self.generate_challenge_content(current_xp, snapshot_dict)

        logger.info("XP stage not ready for a challenge (need %.2f more XP).", xp_to_next)
        return {}
