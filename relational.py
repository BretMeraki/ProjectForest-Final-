import json
import logging
import re
from typing import Optional, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Attempt to import the LLM integration; provide a dummy fallback if unavailable
try:
    from forest_app.integrations.llm import generate_response
except ImportError:
    logger.error("LLM integration 'generate_response' not found. Dynamic methods will fail.")

    async def generate_response(prompt: str) -> str:
        logger.warning("Using dummy generate_response. LLM calls disabled.")
        if "Relational Repair Request" in prompt:
            return json.dumps({
                "repair_action": "Default fallback action.",
                "tone": "Gentle",
                "scale": "Medium",
            })
        elif "Relational Profile Update Request" in prompt:
            return json.dumps({"score_delta": 0.0, "tag_updates": {}})
        elif "Relational Deepening Suggestion Request" in prompt:
            return json.dumps({
                "deepening_suggestion": "Default deepening suggestion.",
                "tone": "supportive",
            })
        else:
            return "{}"


class Profile:
    """Represents a profile for relational tracking within the Forest system."""

    def __init__(self, name: str):
        self.name: str = name
        self.emotional_tags: Dict[str, float] = {}
        self.love_language: str = "Words of Affirmation"
        self.last_gifted: Optional[str] = None
        self.connection_score: float = 5.0

    def update_emotional_tags(self, new_tags: dict):
        """Updates emotional tags with provided deltas, clamping between 0 and 10."""
        if not isinstance(new_tags, dict):
            logger.warning("Invalid type for new_tags: %s", type(new_tags))
            return
        for tag, value in new_tags.items():
            try:
                current = self.emotional_tags.get(tag, 0.0)
                delta = float(value)
                updated = max(0.0, min(10.0, current + delta))
                self.emotional_tags[tag] = round(updated, 2)
            except (ValueError, TypeError):
                logger.warning("Invalid value for tag '%s': %s", tag, value)
        logger.info("Profile '%s' emotional_tags updated to %s", self.name, self.emotional_tags)

    def update_connection_score(self, delta: float):
        """Updates connection score by a delta, clamping between 0 and 10."""
        try:
            delta_float = float(delta)
            old = self.connection_score
            self.connection_score = max(0.0, min(10.0, self.connection_score + delta_float))
            logger.info("Profile '%s' connection_score: %.2f → %.2f", self.name, old, self.connection_score)
        except (ValueError, TypeError):
            logger.warning("Invalid delta for connection_score: %s", delta)

    def update_love_language(self, new_love_language: str):
        """Updates the profile's love language if valid."""
        if isinstance(new_love_language, str) and new_love_language:
            old = self.love_language
            self.love_language = new_love_language
            logger.info("Profile '%s' love_language: '%s' → '%s'", self.name, old, self.love_language)
        else:
            logger.warning("Invalid love_language provided: %s", new_love_language)

    def to_dict(self) -> dict:
        """Serializes Profile state to a dict."""
        return {
            "name": self.name,
            "emotional_tags": self.emotional_tags,
            "love_language": self.love_language,
            "last_gifted": self.last_gifted,
            "connection_score": self.connection_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Creates Profile instance from a dict."""
        if not isinstance(data, dict):
            logger.error("Invalid data for Profile.from_dict: %s", type(data))
            return cls("Unknown_Error")
        profile = cls(data.get("name", "Unknown"))
        profile.emotional_tags = data.get("emotional_tags", {})
        profile.love_language = data.get("love_language", "Words of Affirmation")
        profile.last_gifted = data.get("last_gifted")
        profile.connection_score = data.get("connection_score", 5.0)
        # Validate types
        if not isinstance(profile.emotional_tags, dict):
            profile.emotional_tags = {}
        if not isinstance(profile.love_language, str):
            profile.love_language = "Words of Affirmation"
        if not isinstance(profile.connection_score, (int, float)):
            profile.connection_score = 5.0
        return profile


class RelationalRepairEngine:
    """Handles generation of repair actions for relationships."""

    def generate_repair_action(self, profile: Profile, context: str = "") -> dict:
        """Generates a static fallback repair action based on profile state."""
        if not isinstance(profile, Profile):
            logger.error("Invalid profile in generate_repair_action.")
            return {}

        # Determine dominant tag
        dominant_tag = max(profile.emotional_tags.items(), key=lambda kv: kv[1], default=("compassion", 0.0))[0]
        score = profile.connection_score
        if score < 3.0:
            tone = "Cautious"
            action = f"Write an unsent letter expressing {dominant_tag} in reflection."
        elif score < 7.0:
            tone = "Gentle"
            action = f"Send a brief, heartfelt note focusing on {dominant_tag}."
        else:
            tone = "Open"
            action = f"Reach out for a conversation inspired by {dominant_tag}."

        result = {
            "recipient": profile.name,
            "tone": tone,
            "repair_action": action,
            "emotional_tag": dominant_tag,
            "context_hint": context,
        }
        logger.info("Static repair action for '%s': %s", profile.name, result)
        return result

    async def generate_dynamic_repair_action(
        self, profile: Profile, snapshot: dict, context: str = ""
    ) -> dict:
        """Generates a dynamic repair action using the LLM."""
        if not isinstance(profile, Profile):
            logger.error("Invalid profile in generate_dynamic_repair_action.")
            return {}

        pruned = {
            "xp": snapshot.get("xp"),
            "capacity": snapshot.get("capacity"),
            "shadow_score": snapshot.get("shadow_score"),
            "relationship_metrics": snapshot.get("relationship_metrics"),
        }
        prompt = (
            f"Relational Repair Request:\n"
            f"Profile: {json.dumps(profile.to_dict())}\n"
            f"Context: {json.dumps(pruned)}\n"
            f"Love language: '{profile.love_language}', connection_score: {profile.connection_score:.1f}\n"
            f"Output JSON with keys 'repair_action', 'tone', 'scale'."
        )
        try:
            raw = (await generate_response(prompt)).strip()
            data = json.loads(raw)
            repair_action = data.get("repair_action", "")
            tone = data.get("tone", "Gentle")
            scale = data.get("scale", "Medium")
            if tone not in ["Cautious", "Gentle", "Open"]:
                tone = "Gentle"
            if scale not in ["Small", "Medium", "Large"]:
                scale = "Medium"
        except Exception as e:
            logger.warning("Dynamic repair action failed: %s", e)
            return self.generate_repair_action(profile, context)

        result = {
            "recipient": profile.name,
            "tone": tone,
            "repair_action": repair_action,
            "scale": scale,
            "context_hint": context,
        }
        logger.info("Dynamic repair action for '%s': %s", profile.name, result)
        return result


class RelationalManager:
    """Manages relational profiles and interactions."""

    def __init__(self):
        self.profiles: Dict[str, Profile] = {}

    def add_or_update_profile(self, profile_data: dict) -> Optional[Profile]:
        """Adds or updates a profile from provided data."""
        if not isinstance(profile_data, dict):
            logger.error("Invalid profile_data type: %s", type(profile_data))
            return None
        name = profile_data.get("name", "").strip()
        if not name:
            logger.error("Empty profile name.")
            return None

        if name in self.profiles:
            profile = self.profiles[name]
            profile.update_emotional_tags(profile_data.get("emotional_tags", {}))
            if "love_language" in profile_data:
                profile.update_love_language(profile_data["love_language"])
            if "connection_score_delta" in profile_data:
                profile.update_connection_score(profile_data["connection_score_delta"])
        else:
            try:
                profile = Profile.from_dict(profile_data)
                if profile.name == "Unknown" and name:
                    profile.name = name
                self.profiles[name] = profile
            except Exception as e:
                logger.error("Failed to create Profile: %s", e)
                return None

        logger.info("Profile '%s' added/updated.", name)
        return profile

    def get_profile(self, name: str) -> Optional[Profile]:
        """Retrieves a profile by name."""
        return self.profiles.get(name)

    def analyze_reflection_for_interactions(self, reflection_text: str) -> dict:
        """Heuristically analyzes text for relational interaction signals."""
        default_signals = {
            "support": 0.0,
            "conflict": 0.0,
            "feedback": "No significant relational signals detected.",
        }
        if not reflection_text or not isinstance(reflection_text, str):
            return default_signals

        text = reflection_text.lower()
        support_kw = ["support", "helped", "appreciated", "cared", "kind"]
        conflict_kw = ["argued", "conflict", "hurt", "ignored", "criticized"]

        support_score = sum(0.1 for w in support_kw if re.search(rf"\b{w}\b", text))
        conflict_score = sum(-0.1 for w in conflict_kw if re.search(rf"\b{w}\b", text))

        signals = {
            "support": round(support_score, 2),
            "conflict": round(conflict_score, 2),
            "feedback": ""
        }
        if signals["support"] > 0 and signals["conflict"] == 0:
            signals["feedback"] = "Positive relational signals detected."
        elif signals["conflict"] < 0 and signals["support"] == 0:
            signals["feedback"] = "Negative relational signals detected."
        elif signals["support"] > 0 and signals["conflict"] < 0:
            signals["feedback"] = "Mixed relational signals detected."
        else:
            signals["feedback"] = default_signals["feedback"]

        logger.info("Relational signals: %s", signals)
        return signals

    async def infer_profile_updates(self, profile_name: str, reflection_text: str) -> dict:
        """Uses LLM to infer profile updates from reflection."""
        profile = self.get_profile(profile_name)
        if not profile:
            logger.warning("Profile '%s' not found.", profile_name)
            return {}

        prompt = (
            f"Relational Profile Update Request:\n"
            f"Profile: {json.dumps(profile.to_dict())}\n"
            f"Reflection: {reflection_text}\n"
            f"Output JSON with 'score_delta', 'tag_updates', optional 'love_language'."
        )
        try:
            raw = (await generate_response(prompt)).strip()
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("LLM returned non-dict")
        except Exception as e:
            logger.warning("Profile inference failed: %s", e)
            data = {"score_delta": 0.0, "tag_updates": {}}

        profile.update_connection_score(data.get("score_delta", 0.0))
        profile.update_emotional_tags(data.get("tag_updates", {}))
        if "love_language" in data:
            profile.update_love_language(data["love_language"])

        logger.info("Profile '%s' inferred updates: %s", profile_name, data)
        return data

    async def generate_repair_for_profile(self, name: str, snapshot: dict, context: str = "") -> dict:
        """Generates a repair action, dynamic if possible."""
        profile = self.get_profile(name)
        if not profile:
            logger.warning("Profile '%s' not found for repair.", name)
            return {}
        engine = RelationalRepairEngine()
        return await engine.generate_dynamic_repair_action(profile, snapshot, context)

    async def generate_deepening_suggestion(self, name: str, snapshot: dict, context: str = "") -> dict:
        """Generates a relationship deepening suggestion via LLM."""
        profile = self.get_profile(name)
        if not profile:
            logger.warning("Profile '%s' not found for deepening.", name)
            return {}

        extra_ctx = {
            "emotional_tags": profile.emotional_tags,
            "connection_score": profile.connection_score,
        }
        prompt = (
            f"Relational Deepening Suggestion Request:\n"
            f"Profile: {json.dumps(profile.to_dict())}\n"
            f"Extra Context: {json.dumps(extra_ctx)}\n"
            f"Output JSON with 'deepening_suggestion' and 'tone'."
        )
        try:
            raw = (await generate_response(prompt)).strip()
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("LLM returned non-dict")
        except Exception as e:
            logger.warning("Deepening suggestion failed: %s", e)
            data = {
                "deepening_suggestion": "Set aside dedicated time for meaningful connection.",
                "tone": "gentle",
            }

        logger.info("Deepening suggestion for '%s': %s", name, data)
        return data

    def to_dict(self) -> dict:
        """Serializes all profiles to a dict."""
        return {"profiles": {n: p.to_dict() for n, p in self.profiles.items()}}

    def update_from_dict(self, data: dict):
        """Rehydrates manager state from a dict."""
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            logger.warning("Invalid profiles data in update_from_dict.")
            return
        self.profiles.clear()
        for name, pd in profiles.items():
            try:
                prof = Profile.from_dict(pd)
                if prof.name == "Unknown" and name:
                    prof.name = name
                self.profiles[name] = prof
            except Exception as e:
                logger.error("Failed to load profile '%s': %s", name, e)
        logger.debug("RelationalManager state updated from dict.")