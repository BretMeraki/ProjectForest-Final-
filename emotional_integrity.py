# forest_app/modules/emotional_integrity.py

import logging
import json
import re  # Import regex for robust JSON extraction
from datetime import datetime
from typing import Optional, Dict

# Import LLM integration safely
try:
    from forest_app.integrations.llm import generate_response
except ImportError:
    logger = logging.getLogger(__name__)  # Define logger here if import fails
    logger.error(
        "LLM integration 'generate_response' not found. EmotionalIntegrityIndex will use defaults."
    )

    # Define a dummy async function if import fails
    async def generate_response(prompt: str) -> str:
        logger.warning("Using dummy generate_response for EmotionalIntegrityIndex.")
        # Return default deltas
        return json.dumps(
            {"kindness_delta": 0.0, "respect_delta": 0.0, "consideration_delta": 0.0}
        )


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class EmotionalIntegrityIndex:
    """
    Tracks and assesses indicators of emotional integrity based on user input using LLM analysis.

    Analyzes reflections to gauge kindness, respect, and consideration. Maintains scores
    for these components (0-10 scale) and an overall index.
    """

    def __init__(self):
        # Initialize scores (0-10 scale, 5 is neutral baseline)
        self.kindness_score: float = 5.0
        self.respect_score: float = 5.0
        self.consideration_score: float = 5.0
        self.overall_index: float = 5.0
        self.last_update: str = datetime.utcnow().isoformat()
        logger.info("EmotionalIntegrityIndex initialized.")

    def _calculate_overall_index(self):
        """Calculates the overall index as a simple average of component scores."""
        scores = [self.kindness_score, self.respect_score, self.consideration_score]
        # Ensure division by zero doesn't occur if scores list is somehow empty
        self.overall_index = round(sum(scores) / len(scores), 2) if scores else 5.0

    async def analyze_reflection(
        self, reflection_text: str, context: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Analyzes reflection text using an LLM to assess emotional integrity indicators.

        Args:
            reflection_text: The user's reflection input.
            context: Optional additional context from the snapshot (e.g., shadow score, capacity).

        Returns:
            A dictionary containing calculated deltas for component scores (e.g.,
            {"kindness_delta": 0.1, "respect_delta": -0.2, "consideration_delta": 0.0}).
            Returns empty dict if analysis fails or text is empty.
        """
        if not isinstance(reflection_text, str) or not reflection_text.strip():
            logger.warning("Empty or invalid reflection text provided for analysis.")
            return {}

        logger.info("Analyzing reflection for emotional integrity via LLM...")
        context = context or {}
        # Prepare context string for LLM, including only relevant parts
        context_summary = json.dumps(
            {
                "shadow_score": context.get("shadow_score"),
                "capacity": context.get("capacity"),
                "active_seed_domain": context.get("seed_context", {}).get(
                    "seed_domain"
                ),  # Example context
                "active_archetype_trait": context.get("archetype_manager", {})
                .get("active_archetype", {})
                .get("core_trait"),  # Example context
            },
            indent=2,
            default=str,
        )  # Use default=str for non-serializable types if any

        # Define the LLM prompt for emotional integrity analysis
        prompt = (
            f"You are an objective analyzer assessing emotional integrity indicators in text.\n"
            f"Analyze the following reflection text based on the user's general context:\n\n"
            f'REFLECTION:\n"""\n{reflection_text}\n"""\n\n'
            f"USER CONTEXT (Consider lightly):\n{context_summary}\n\n"
            f"INSTRUCTION:\n"
            f"Carefully evaluate the reflection for expressions of:\n"
            f"1. Kindness: Towards self OR others (empathy, compassion, gentleness, self-care, gratitude, positive framing).\n"
            f"2. Respect: For self OR others OR boundaries (acknowledging limits, avoiding blame/insults, politeness, validating others' views).\n"
            f"3. Consideration: Of different perspectives OR impacts on others (thoughtfulness, awareness of consequences, acknowledging complexity).\n"
            f"Assign a delta score between -0.5 (strong negative indicators, e.g., harsh self-criticism, blaming, dismissiveness) and +0.5 (strong positive indicators, e.g., expressed gratitude, empathy, boundary setting) for each dimension. A score of 0.0 indicates neutrality or absence of strong signals.\n"
            f"Base the score PRIMARILY on the text's expressed content and tone.\n"
            f"Return ONLY a valid JSON object containing these three delta scores with keys exactly as specified: 'kindness_delta', 'respect_delta', 'consideration_delta'.\n"
            f'Example: {{"kindness_delta": 0.1, "respect_delta": -0.2, "consideration_delta": 0.0}}'
        )

        try:
            logger.debug("Sending prompt to LLM for emotional integrity analysis.")
            response_raw = (await generate_response(prompt)).strip()
            # Attempt to extract JSON even if there's surrounding text
            match = re.search(r"\{.*\}", response_raw, re.DOTALL)
            if match:
                json_str = match.group(0)
                response_data = json.loads(json_str)
            else:
                # If no JSON object found, attempt to parse the whole string
                # This might fail if there's leading/trailing text, handled by except block
                response_data = json.loads(response_raw)

            if not isinstance(response_data, dict):
                raise ValueError("LLM response was not a valid JSON object.")

            # Validate and extract deltas, clamping them to the expected range [-0.5, 0.5]
            # Default to 0.0 if key is missing or value is invalid
            kindness_delta = 0.0
            respect_delta = 0.0
            consideration_delta = 0.0
            try:
                kindness_delta = max(
                    -0.5, min(0.5, float(response_data.get("kindness_delta", 0.0)))
                )
            except (ValueError, TypeError):
                logger.warning("Invalid kindness_delta received.")
            try:
                respect_delta = max(
                    -0.5, min(0.5, float(response_data.get("respect_delta", 0.0)))
                )
            except (ValueError, TypeError):
                logger.warning("Invalid respect_delta received.")
            try:
                consideration_delta = max(
                    -0.5, min(0.5, float(response_data.get("consideration_delta", 0.0)))
                )
            except (ValueError, TypeError):
                logger.warning("Invalid consideration_delta received.")

            deltas = {
                "kindness_delta": kindness_delta,
                "respect_delta": respect_delta,
                "consideration_delta": consideration_delta,
            }
            logger.info("Emotional integrity analysis complete. Deltas: %s", deltas)
            return deltas

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Error parsing LLM response for emotional integrity: %s. Raw: %s",
                e,
                response_raw[:200],
            )
            return {}  # Return empty deltas on failure
        except Exception as e:
            logger.exception(
                "Unexpected error during emotional integrity analysis: %s", e
            )
            return {}

    def apply_updates(self, deltas: Dict[str, float]):
        """Applies calculated deltas to the component scores (0-10) and updates the overall index."""
        if not isinstance(deltas, dict) or not deltas:
            logger.debug(
                "No valid deltas provided to apply_updates for EmotionalIntegrityIndex."
            )
            return

        # Apply deltas with clamping (0-10)
        # Scaling factor determines how much impact a single reflection has (tune this)
        # Example: delta range is -0.5 to +0.5. Scale factor of 2 means max change per reflection is +/- 1.0 point.
        scaling_factor = 2.0
        self.kindness_score = max(
            0.0,
            min(
                10.0,
                self.kindness_score
                + deltas.get("kindness_delta", 0.0) * scaling_factor,
            ),
        )
        self.respect_score = max(
            0.0,
            min(
                10.0,
                self.respect_score + deltas.get("respect_delta", 0.0) * scaling_factor,
            ),
        )
        self.consideration_score = max(
            0.0,
            min(
                10.0,
                self.consideration_score
                + deltas.get("consideration_delta", 0.0) * scaling_factor,
            ),
        )

        self._calculate_overall_index()  # Recalculate overall index
        self.last_update = datetime.utcnow().isoformat()
        logger.info(
            "Emotional Integrity Index updated: Overall=%.2f (K:%.1f, R:%.1f, C:%.1f)",
            self.overall_index,
            self.kindness_score,
            self.respect_score,
            self.consideration_score,
        )

    def get_index(self) -> dict:
        """Returns the current state of the index."""
        return {
            "kindness_score": round(self.kindness_score, 2),
            "respect_score": round(self.respect_score, 2),
            "consideration_score": round(self.consideration_score, 2),
            "overall_index": round(self.overall_index, 2),
            "last_update": self.last_update,
        }

    def to_dict(self) -> dict:
        """Serializes the engine's state."""
        # Simple implementation, same as get_index for now
        return self.get_index()

    def update_from_dict(self, data: dict):
        """Updates the engine's state from a dictionary."""
        if not isinstance(data, dict):
            logger.warning(
                "Invalid data type provided to EmotionalIntegrityIndex.update_from_dict"
            )
            return
        self.kindness_score = data.get("kindness_score", self.kindness_score)
        self.respect_score = data.get("respect_score", self.respect_score)
        self.consideration_score = data.get(
            "consideration_score", self.consideration_score
        )
        # Recalculate overall index after loading components
        self._calculate_overall_index()
        self.last_update = data.get("last_update", self.last_update)
        logger.debug("EmotionalIntegrityIndex state updated from dict.")
