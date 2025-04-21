# forest_app/modules/financial_readiness.py

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from forest_app.integrations.llm import generate_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _clamp01(x: float) -> float:
    """Clamp a float to the 0.0–1.0 range."""
    return max(0.0, min(1.0, x))


class FinancialReadinessEngine:
    """
    Assesses and tracks the user's financial readiness level (0.0–1.0).
    Uses an LLM to perform an initial baseline assessment and to adjust
    readiness based on subsequent reflections or context updates.
    """

    def __init__(self):
        # Readiness on a 0.0 (not ready) to 1.0 (fully ready) scale.
        self.readiness: float = 0.5
        self.last_update: str = datetime.utcnow().isoformat()

    def update_from_dict(self, data: Dict[str, Any]):
        """
        Rehydrate engine state from snapshot.component_state.
        """
        try:
            r = data.get("readiness")
            if isinstance(r, (int, float)):
                self.readiness = _clamp01(float(r))
            lu = data.get("last_update")
            if isinstance(lu, str):
                self.last_update = lu
            logger.debug("Loaded FinancialReadinessEngine state: readiness=%.2f", self.readiness)
        except Exception as e:
            logger.error("Error loading FinancialReadinessEngine state: %s", e)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize engine state for persistence.
        """
        return {
            "readiness": self.readiness,
            "last_update": self.last_update
        }

    async def assess_baseline(self, description: str) -> float:
        """
        Perform an initial baseline assessment of financial readiness from
        a free-form description of the user's current situation.
        Returns the new readiness (0.0–1.0) and updates internal state.
        """
        prompt = (
            "You are an objective assistant that evaluates a user's financial readiness "
            "for pursuing meaningful goals, on a scale from 0.0 (not ready) to 1.0 (fully ready). "
            "Based on the following description, respond with a JSON object:\n\n"
            f"{{\"readiness\": <float between 0.0 and 1.0>}}\n\n"
            f"User description:\n\"\"\"\n{description}\n\"\"\"\n\n"
            "Output only valid JSON."
        )

        try:
            raw = await generate_response(prompt)
            text = getattr(raw, "response", None) or str(raw)
            data = json.loads(text)
            r = data.get("readiness")
            if not isinstance(r, (int, float)):
                raise ValueError("Invalid readiness value")
            self.readiness = _clamp01(float(r))
        except Exception as e:
            logger.warning("Baseline financial readiness assessment failed: %s", e)
            # fallback: keep previous readiness
        finally:
            self.last_update = datetime.utcnow().isoformat()
            logger.info("Baseline readiness set to %.2f", self.readiness)
            return self.readiness

    async def analyze_reflection(self, reflection: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Adjust the current readiness based on a new user reflection or contextual update.
        The LLM should return a delta (positive or negative) to apply to the current readiness:
        { "delta": <float> }. The new readiness = clamp(old + delta).
        """
        context = context or {}
        prompt = (
            "You are an assistant analyzing how a user's new financial reflections "
            "should adjust their financial readiness (0.0–1.0). "
            "Based on the reflection and optional context, respond with a JSON object:\n\n"
            "{\n  \"delta\": <float, positive or negative>\n}\n\n"
            "User reflection:\n\"\"\"\n"
            f"{reflection}\n\"\"\"\n\n"
            "Context (if any):\n"
            f"{json.dumps(context, indent=2)}\n\n"
            "Output only valid JSON."
        )

        try:
            raw = await generate_response(prompt)
            text = getattr(raw, "response", None) or str(raw)
            data = json.loads(text)
            delta = data.get("delta", 0.0)
            if not isinstance(delta, (int, float)):
                raise ValueError("Invalid delta value")
            self.readiness = _clamp01(self.readiness + float(delta))
        except Exception as e:
            logger.warning("Financial readiness reflection analysis failed: %s", e)
            # fallback: no change
        finally:
            self.last_update = datetime.utcnow().isoformat()
            logger.info("Adjusted readiness to %.2f", self.readiness)
            return self.readiness