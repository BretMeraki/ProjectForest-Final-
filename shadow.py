import re
import logging
import math
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ShadowEngine:
    """
    ShadowEngine analyzes text input to detect and quantify shadow-related cues.

    Refinements:
      1. Contextual Weighting: Optionally adjusts lexicon weights based on context.
      2. Pattern Matching: Uses regex to capture common shadow-expressive phrases.
      3. Synergy with Sentiment: Can optionally incorporate a sentiment factor from context.
      4. Refined Normalization: Optionally normalizes by text length rather than a fixed divisor.
    """

    def __init__(self):
        # Base lexicon for single keywords (default weight values)
        self.lexicon = {
            "bitterness": 0.8,
            "avoid": 0.7,
            "burnout": 0.9,
            "rigid": 0.6,
            "shame": 0.7,
            "resent": 0.8,
            "self-hate": 0.9,
            "fearful": 0.6,
            "hopeless": 0.8,
            "despair": 0.9,
            "guilt": 0.7,
        }
        self.negations = {"not", "never", "no"}

        # Additional regex patterns for common shadow phrases
        self.pattern_lexicon = {
            r"\bi can'?t seem to\b": 0.3,
            r"\bstuck (in|on)\b": 0.3,
            r"\bwhat'?s the point\b": 0.4,
        }

        self.last_update = datetime.utcnow().isoformat()

    def _sigmoid(self, x: float, k: float = 1.0) -> float:
        """Optional sigmoid normalization function."""
        return 1 / (1 + math.exp(-k * x))

    def analyze_text(self, text: str, context: dict = None) -> dict:
        """
        Analyzes input text for shadow content using:
          - A basic keyword lexicon.
          - Regex-based pattern matching for common phrases.

        Optionally, uses the 'context' dictionary to adjust weights dynamically.
        Expected context keys:
            - capacity (float): user's current capacity (0.0 to 1.0)
            - sentiment (float): overall negative sentiment score (if available)
            - resonance_theme (str): e.g., "Reset" might reduce certain weights.

        Returns:
            A dict with:
              - 'shadow_score': normalized score (0.0 to 1.0).
              - 'shadow_tags': mapping of detected shadow tags to cumulative weight.
        """
        text_lower = text.lower()
        total_score = 0.0
        tag_scores = {}
        words = text_lower.split()
        skip_next = False

        # Adjust lexicon weights based on context (if provided)
        adjusted_lexicon = self.lexicon.copy()
        if context:
            capacity = context.get("capacity", 0.5)
            resonance_theme = context.get("resonance_theme", "").lower()
            # Example: if capacity is very low, amplify impact of 'burnout', 'hopeless', and 'despair'
            if capacity < 0.3:
                for key in ["burnout", "hopeless", "despair"]:
                    if key in adjusted_lexicon:
                        adjusted_lexicon[key] *= 1.2
            # Example: if resonance_theme is "reset", reduce the impact of "rigid"
            if resonance_theme == "reset":
                if "rigid" in adjusted_lexicon:
                    adjusted_lexicon["rigid"] *= 0.8

        # Process each word for lexicon-based scoring.
        for i, word in enumerate(words):
            if skip_next:
                skip_next = False
                continue
            # Handle simple negation.
            if word in self.negations:
                if i + 1 < len(words):
                    next_word = words[i + 1]
                    if next_word in adjusted_lexicon:
                        score = -adjusted_lexicon[next_word]
                        tag_scores[next_word] = tag_scores.get(next_word, 0) + score
                        total_score += score
                        skip_next = True
                continue
            if word in adjusted_lexicon:
                score = adjusted_lexicon[word]
                tag_scores[word] = tag_scores.get(word, 0) + score
                total_score += score

        # Use regex pattern matching to catch common phrases.
        for pattern, weight in self.pattern_lexicon.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                tag_name = pattern  # using pattern as a key placeholder
                increment = weight * len(matches)
                tag_scores[tag_name] = tag_scores.get(tag_name, 0) + increment
                total_score += increment

        # Optional: Factor in overall negative sentiment from context.
        if context and "sentiment" in context:
            sentiment = context["sentiment"]
            # Assume sentiment is a negative value (e.g., -0.5) if the user is distressed.
            total_score += abs(sentiment) * 0.5

        # Alternative normalization: divide by (number of words + 1) for density.
        normalized_by_length = abs(total_score) / (len(words) + 1)
        # Combine with fixed scaling: for now, choose the higher of the two approaches.
        raw_normalized = max(normalized_by_length, abs(total_score) / 10)
        normalized_shadow = max(0.0, min(1.0, raw_normalized))
        # Optionally, use the sigmoid function instead:
        # normalized_shadow = max(0.0, min(1.0, self._sigmoid(total_score, k=0.5)))

        logger.info(
            "Shadow analysis complete. Raw score: %.2f; Normalized score: %.2f; Tags: %s",
            total_score,
            normalized_shadow,
            tag_scores,
        )
        return {"shadow_score": round(normalized_shadow, 2), "shadow_tags": tag_scores}

    def update_from_text(self, text: str, context: dict = None) -> float:
        """
        Updates the shadow analysis from text (with optional context) and returns the normalized shadow score.
        """
        analysis = self.analyze_text(text, context=context)
        self.last_update = datetime.utcnow().isoformat()
        return analysis["shadow_score"]

    def to_dict(self) -> dict:
        """Serializes the engine's configuration and last update timestamp."""
        return {"lexicon": self.lexicon, "last_update": self.last_update}

    def update_from_dict(self, data: dict):
        """Updates the engine from a dictionary."""
        if "lexicon" in data:
            self.lexicon.update(data["lexicon"])
        self.last_update = data.get("last_update", self.last_update)
