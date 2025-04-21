# forest_app/modules/sentiment.py

import json
import logging
# --- MODIFICATION START: Import necessary items ---
from typing import Any # Make sure these are present

# Import the LLM interface AND the necessary models/exceptions
# Assumes llm.py defines SentimentResponseModel and LLMValidationError
try:
    from forest_app.integrations.llm import (
        generate_response,
        SentimentResponseModel, # Import the specific model for sentiment
        LLMValidationError, # Import the specific exception
        # LLMResponseModel can be removed if not needed for fallback logic
    )
except ImportError as import_err:
    logger_init = logging.getLogger(__name__)
    logger_init.error("LLM generate_response or models not found for sentiment engine: %s", import_err)

    # Define a dummy async function if import fails
    async def generate_response(prompt: str, response_model=None) -> Any: # Adjust dummy signature
        logger_init.warning("Using dummy generate_response for SentimentEngine.")
        # Return a default dictionary structure matching SentimentResponseModel if possible
        return {
                "emotional_fingerprint": {},
                "shadow_data": {"active_shadow_tags": [], "shadow_intensity": 0.0},
                "sentiment_flow": "stable",
                "ambivalence_score": 0.0,
                "final_score": 0.0,
            }
    # Define dummy exception if needed
    class LLMValidationError(Exception):
         def __init__(self, message, errors=None, data=None):
              self.data = data
              super().__init__(message)

    # Define dummy SentimentResponseModel if needed for type hints or fallback logic
    class SentimentResponseModel:
        # Add attributes if needed by downstream processing in this file's error handling
        emotional_fingerprint: dict = {}
        shadow_data: dict = {}
        sentiment_flow: str = "unknown"
        ambivalence_score: float = 0.0
        final_score: float = 0.0
        def model_dump(self): # Add model_dump for consistency
             return {
                 "emotional_fingerprint": self.emotional_fingerprint,
                 "shadow_data": self.shadow_data,
                 "sentiment_flow": self.sentiment_flow,
                 "ambivalence_score": self.ambivalence_score,
                 "final_score": self.final_score,
             }
# --- MODIFICATION END ---


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SecretSauceSentimentEngineHybrid:
    """
    Advanced LLM-Driven Sentiment Engine for The Forest OS.
    ... (docstring remains the same) ...
    """

    def __init__(self):
        """Initializes the sentiment engine."""
        self.prompt_modifier = 1.0
        logger.debug("SecretSauceSentimentEngineHybrid initialized.")

    async def analyze_emotional_field(self, text: str, snapshot: dict = None) -> dict:
        """
        Analyzes the emotional field of the input text using LLM, considering snapshot context.

        Args:
            text: The user reflection text to analyze.
            snapshot: Optional dictionary representing the current MemorySnapshot state.

        Returns:
            A dictionary containing the analysis results (emotional_fingerprint, shadow_data, etc.)
            or an error dictionary if parsing fails or validation specific to sentiment fails.
        """
        # Default structure to return on error
        default_error_return = {
             "error": "Sentiment analysis failed",
             "raw": "",
             # Include default keys expected by downstream logic if possible
             "final_score": 0.0,
             "emotional_fingerprint": {},
             "shadow_data": {"active_shadow_tags": [], "shadow_intensity": 0.0},
             "sentiment_flow": "unknown",
             "ambivalence_score": 0.0,
        }

        if not snapshot:
            snapshot = {}
        if not isinstance(text, str) or not text.strip():
            logger.warning("Empty or invalid text provided to analyze_emotional_field.")
            err = default_error_return.copy()
            err["error"] = "Empty input text"
            return err

        # ... (Context assembly logic - assuming correct based on your previous code) ...
        context_parts = []
        context_parts.append(f"Capacity: {snapshot.get('capacity', 0.5)}")
        context_parts.append(f"Shadow Score: {snapshot.get('shadow_score', 0.5)}")
        context_parts.append(f"Magnitude: {snapshot.get('magnitude', 5.0)}")
        dev_index_data = snapshot.get("component_state", {}).get("dev_index", {})
        if dev_index_data: context_parts.append(f"Development Index: {json.dumps(dev_index_data)}")
        archetype_manager_data = snapshot.get("component_state", {}).get("archetype_manager", {})
        active_archetypes = archetype_manager_data.get("active_archetypes", {})
        if active_archetypes:
            active_names = list(active_archetypes.keys())
            context_parts.append(f"Active Archetype(s): {', '.join(active_names)}")
        seed_manager_data = snapshot.get("component_state", {}).get("seed_manager", {})
        seeds = seed_manager_data.get("seeds", [])
        if seeds:
            active_seeds = [s.get("seed_name", "Unknown") for s in seeds if s.get("status") == "active"]
            if active_seeds: context_parts.append(f"Active Seeds: {', '.join(active_seeds)}")
        practical_consequence_data = snapshot.get("component_state", {}).get("practical_consequence", {})
        if practical_consequence_data: context_parts.append(f"Practical Consequence Score: {practical_consequence_data.get('score', 'N/A'):.2f}")
        hardware_config_data = snapshot.get("hardware_config", {})
        if hardware_config_data: context_parts.append(f"Hardware Config: {json.dumps(hardware_config_data)}")
        reflection_context_data = snapshot.get("reflection_context", {})
        if reflection_context_data.get("current_priority") or reflection_context_data.get("recent_insight"):
            context_parts.append(f"Reflection Context: Priority='{reflection_context_data.get('current_priority', '')}', Insight='{reflection_context_data.get('recent_insight', '')}'")
        snapshot_context = "; ".join(filter(None, context_parts))


        # ... (Prompt construction - assuming correct based on your previous code) ...
        prompt = (
             f"You are the Arbiter of The Forest—a poetic, deeply attuned guide tasked with interpreting the "
             f"user's internal emotional landscape. Analyze the following user reflection in light of the provided contextual data. \n\n"
             f'Reflection Text:\n"""\n{text}\n"""\n\n'
             f"Contextual Data (Consider lightly):\n{snapshot_context}\n\n"
             f"Instructions:\n"
             f"1. For each Forest Core Emotional Tag (Stillness, Spark, Courage, Reset, Joy, Clarity, Compassion, Resilience, Depth), assign a score between 0.0 and 1.0 reflecting its resonance in the reflection.\n"
             f"2. Identify any Core Shadow Tags (e.g., Burnout, Avoidance, Bitterness, Rigidity, Shame) present in the text and estimate their intensities (0.0 to 1.0). List them as 'active_shadow_tags' in the 'shadow_data' object.\n"
             f"3. Determine the overall 'sentiment_flow' of the text (improving, worsening, volatile, ambivalent, stable).\n"
             f"4. Calculate an 'ambivalence_score' (0.0 to 1.0) if conflicting signals are present.\n"
             f"5. Compute an overall 'final_score' normalized between -1.0 (very negative) and 1.0 (very positive).\n\n"
             f"Return ONLY a single valid JSON object with keys: 'emotional_fingerprint' (object mapping tags to scores), 'shadow_data' (object with 'active_shadow_tags' list and 'shadow_intensity' float), 'sentiment_flow' (string), 'ambivalence_score' (float), 'final_score' (float).\n\n"
             f"Apply Prompt Modifier Factor: {self.prompt_modifier:.1f}. Adhere strictly to System-Veil Language and the Sanctuary Directive principles in your internal processing, outputting only the requested JSON structure."
         )
        logger.info("Constructed sentiment analysis prompt (length: %d).", len(prompt))

        # --- MODIFICATION START: Call generate_response with specific model ---
        try:
            # Call generate_response and tell it to validate against SentimentResponseModel
            # Ensure SentimentResponseModel was imported correctly above
            validated_sentiment_data = await generate_response(
                prompt,
                response_model=SentimentResponseModel # Pass the correct model type
            )

            # If successful, return the validated data as a dictionary
            # Use .model_dump() for Pydantic v2+ or .dict() for Pydantic v1
            # Ensure the validated object has the method
            if hasattr(validated_sentiment_data, 'model_dump'):
                 result = validated_sentiment_data.model_dump()
                 logger.info("Sentiment analysis successful.")
                 return result
            else:
                 # Should not happen if validation passed and it's a Pydantic model
                 logger.error("Validated sentiment data missing model_dump method.")
                 err = default_error_return.copy()
                 err["error"] = "Internal processing error after validation"
                 return err

        except LLMValidationError as e:
            # Handle the specific validation error from llm.py
            logger.error("Sentiment analysis LLM call failed validation against SentimentResponseModel: %s", e)
            error_result = default_error_return.copy()
            error_result["error"] = "Sentiment validation failed"
            if hasattr(e, 'data'): # Include raw data if available in exception
                 error_result["raw"] = e.data
            return error_result
        except Exception as e:
            # Catch other potential errors from generate_response (timeouts, connection errors, etc.)
            logger.exception("Error during sentiment analysis LLM call or processing: %s", e)
            error_result = default_error_return.copy()
            error_result["error"] = f"Sentiment analysis failed: {e}"
            # Cannot capture raw response here as the error might have occurred before response
            # error_result["raw"] = ""
            return error_result
        # --- MODIFICATION END ---


    def to_dict(self) -> dict:
        """Serializes the engine's state."""
        return {"prompt_modifier": self.prompt_modifier}

    def update_from_dict(self, data: dict):
        """Updates the engine's state from a dictionary."""
        if isinstance(data, dict):
            self.prompt_modifier = data.get("prompt_modifier", self.prompt_modifier)
            logger.debug("SentimentEngine state updated from dict.")
        else:
            logger.warning(
                "Invalid data type provided to SentimentEngine.update_from_dict"
            )