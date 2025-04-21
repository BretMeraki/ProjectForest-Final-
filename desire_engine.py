# forest_app/modules/desire_engine.py

import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from forest_app.integrations.llm import generate_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DesireEngine:
    """
    Tracks and manages the user's long‑term wants and needs ("desires").
    Uses an LLM to extract and update key desires from free‑form input,
    and persists a cache of accepted wants to inform reward suggestions.
    """

    def __init__(self):
        # Each entry: {"want": str, "timestamp": ISO8601}
        self.wants_cache: List[Dict[str, Any]] = []

    def update_from_dict(self, data: Dict[str, Any]):
        """
        Rehydrate state from snapshot.component_state['desire_engine'].
        """
        cache = data.get("wants_cache")
        if isinstance(cache, list):
            self.wants_cache = cache
        logger.debug("DesireEngine state loaded: %d wants", len(self.wants_cache))

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize state for persistence.
        """
        return {"wants_cache": self.wants_cache}

    def add_want(self, want_text: str) -> Dict[str, Any]:
        """
        Manually record a new want/need.
        Returns the record added.
        """
        record = {
            "want": want_text.strip(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.wants_cache.append(record)
        logger.info("Added new want: %r", want_text)
        return record

    def get_all_wants(self) -> List[str]:
        """
        Retrieve the list of all recorded wants (texts only).
        """
        return [entry["want"] for entry in self.wants_cache]

    async def infer_wants(self, user_text: str, max_wants: int = 5) -> List[str]:
        """
        Uses the LLM to extract up to `max_wants` key desires from free-form input.
        Appends any *new* wants to the wants_cache and returns the full list of extracted wants.
        """
        prompt = (
            "You are an assistant that extracts the user's key wants or needs "
            "from a free-form statement. Respond with a JSON array of distinct "
            f"up to {max_wants} concise phrases.\n\n"
            f"User input:\n\"\"\"\n{user_text}\n\"\"\"\n\n"
            "Output only valid JSON."
        )
        try:
            raw = await generate_response(prompt)
            # If generate_response returns a model with .response or .response_text:
            raw_text = getattr(raw, "response", None) or str(raw)
            wants_list = json.loads(raw_text)
            if not isinstance(wants_list, list):
                raise ValueError("LLM did not return a JSON list")
        except Exception as e:
            logger.warning("DesireEngine inference failed: %s", e)
            wants_list = []

        new_wants = []
        for want in wants_list:
            if isinstance(want, str) and want.strip():
                normalized = want.strip()
                if normalized not in self.get_all_wants():
                    self.add_want(normalized)
                    new_wants.append(normalized)

        logger.info("Inferred %d new wants", len(new_wants))
        return new_wants

    def clear_wants(self):
        """
        Remove all recorded wants.
        """
        count = len(self.wants_cache)
        self.wants_cache.clear()
        logger.info("Cleared %d wants from cache", count)