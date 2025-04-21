# forest_app/core/harmonic_framework.py

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SilentScoring:
    """
    Computes the 'silent' internal scores that reflect the underlying state of the system.

    This class computes detailed scores for key metrics (such as XP, shadow_score, capacity, and magnitude)
    and then aggregates these into a composite silent score.
    """

    def __init__(self):
        # Define weights for each component; these can later be externalized.
        self.weights = {
            "xp": 0.2,
            "shadow_score": 0.3,
            "capacity": 0.2,
            "magnitude": 0.3,
        }

    def compute_detailed_scores(self, snapshot_dict: dict) -> dict:
        """
        Computes detailed silent scores based on selected snapshot fields.
        Returns a dictionary with individual weighted scores.
        """
        detailed = {
            "xp_score": snapshot_dict.get("xp", 0) * self.weights["xp"],
            "shadow_component": snapshot_dict.get("shadow_score", 0)
            * self.weights["shadow_score"],
            "capacity_component": snapshot_dict.get("capacity", 0)
            * self.weights["capacity"],
            "magnitude_component": snapshot_dict.get("magnitude", 0)
            * self.weights["magnitude"],
        }
        logger.info("Computed detailed silent scores: %s", detailed)
        return detailed

    def compute_composite_score(self, snapshot_dict: dict) -> float:
        """
        Aggregates detailed scores into a single composite silent score.
        """
        detailed = self.compute_detailed_scores(snapshot_dict)
        composite = sum(detailed.values())
        logger.info("Composite silent score computed: %.2f", composite)
        return composite


class HarmonicRouting:
    """
    Determines the harmonic theme based on the composite silent score.

    This theme (e.g., "Reflection", "Renewal", "Resilience", or "Transcendence")
    informs the overall tone and complexity of the tasks and narrative.
    """

    def __init__(self):
        # Thresholds for different harmonic themes (can be tuned or externalized).
        self.theme_thresholds = {
            "Reflection": 0.3,
            "Renewal": 0.6,
            "Resilience": 0.8,
            "Transcendence": float("inf"),
        }

    def route_harmony(self, snapshot_dict: dict, detailed_scores: dict = None) -> dict:
        """
        Determines the harmonic theme based on detailed silent scores.

        If the composite score is low, choose a theme like "Reflection"; as the score increases,
        themes transition through "Renewal", "Resilience", up to "Transcendence."
        Returns a dictionary with keys 'theme' and 'routing_score'.
        """
        if not detailed_scores:
            composite = 0.0
        else:
            composite = sum(detailed_scores.values())

        # Determine theme based on composite score.
        if composite < self.theme_thresholds["Reflection"]:
            theme = "Reflection"
        elif composite < self.theme_thresholds["Renewal"]:
            theme = "Renewal"
        elif composite < self.theme_thresholds["Resilience"]:
            theme = "Resilience"
        else:
            theme = "Transcendence"

        routing_info = {"theme": theme, "routing_score": composite}
        logger.info("Harmonic routing determined: %s", routing_info)
        return routing_info
