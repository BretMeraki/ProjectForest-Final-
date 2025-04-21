import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configurable thresholds/tuning constants.
ACTIVATION_THRESHOLD = 0.8  # Minimum weight for an archetype to be considered active.
DOMINANCE_FACTOR = 1.5      # If the top archetype is at least 1.5x the next, use its influence exclusively.

class Archetype:
    """
    Represents a single archetype with defined traits and dynamic context parameters.

    Attributes:
        name: The unique name of the archetype.
        core_trait: The primary characteristic of this archetype.
        emotional_priority: A descriptor indicating emotional focus.
        shadow_expression: How this archetype expresses its shadow aspects.
        transformation_style: The style guiding transformation.
        tag_bias: Tags influencing narrative tone.
        default_weight: Baseline importance weight.
        context_factors: Mapping of context keys to scaling multipliers.
        current_weight: Dynamically updated weight.
    """
    def __init__(
        self,
        name: str,
        core_trait: str,
        emotional_priority: str,
        shadow_expression: str,
        transformation_style: str,
        tag_bias: List[str],
        default_weight: float = 1.0,
        context_factors: Optional[Dict[str, float]] = None,
    ):
        self.name = name
        self.core_trait = core_trait
        self.emotional_priority = emotional_priority
        self.shadow_expression = shadow_expression
        self.transformation_style = transformation_style
        self.tag_bias = tag_bias
        self.default_weight = default_weight
        self.context_factors = context_factors or {}
        self.current_weight = default_weight

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "core_trait": self.core_trait,
            "emotional_priority": self.emotional_priority,
            "shadow_expression": self.shadow_expression,
            "transformation_style": self.transformation_style,
            "tag_bias": self.tag_bias,
            "default_weight": self.default_weight,
            "context_factors": self.context_factors,
            "current_weight": self.current_weight,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Archetype":
        return cls(
            name=data["name"],
            core_trait=data.get("core_trait", ""),
            emotional_priority=data.get("emotional_priority", ""),
            shadow_expression=data.get("shadow_expression", ""),
            transformation_style=data.get("transformation_style", ""),
            tag_bias=data.get("tag_bias", []),
            default_weight=data.get("default_weight", 1.0),
            context_factors=data.get("context_factors"),
        )

    def adjust_weight(self, context: Dict[str, float]) -> None:
        """
        Dynamically adjusts current_weight based on XP, capacity, and shadow_score.
        """
        xp = context.get("xp", 0)
        capacity = context.get("capacity", 0.5)
        shadow = context.get("shadow_score", 0.5)
        defaults = {"xp": 0.001, "capacity": 0.5, "shadow": 0.7}

        new_weight = self.default_weight
        new_weight += xp * self.context_factors.get("xp", defaults["xp"])

        if capacity < 0.4 and "caretaker" in self.name.lower():
            new_weight += self.context_factors.get("capacity", defaults["capacity"])

        if shadow > 0.7 and "healer" in self.name.lower():
            new_weight += self.context_factors.get("shadow", defaults["shadow"])

        self.current_weight = new_weight
        logger.info(
            "Archetype '%s' adjusted weight to %.2f with context %s",
            self.name,
            self.current_weight,
            context
        )

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class ArchetypeManager:
    """
    Manages a collection of archetypes, dynamically selecting and blending them
    based on the MemorySnapshot state.
    """
    def __init__(self):
        self.archetypes: List[Archetype] = []
        self.active_archetypes: Dict[str, Archetype] = {}

    def load_archetypes(self, archetype_list: List[dict]):
        """
        Load archetypes from a list of dicts, initializing both the full list
        and the active set to include all by default.
        """
        self.archetypes = [Archetype.from_dict(item) for item in archetype_list]
        self.active_archetypes = {arch.name: arch for arch in self.archetypes}
        logger.info("Loaded %d archetypes.", len(self.archetypes))

    def set_active_archetype(self, name: str) -> bool:
        """
        Replace the active set with a single archetype matching `name`.
        """
        for arch in self.archetypes:
            if arch.name.lower() == name.lower():
                self.active_archetypes = {arch.name: arch}
                logger.info("Active archetype set to '%s'.", arch.name)
                return True
        logger.warning("Archetype '%s' not found.", name)
        return False

    def update_active_archetypes(self, snapshot: dict):
        """
        Recompute each archetype's weight from snapshot, then select those
        ≥ ACTIVATION_THRESHOLD; fallback to the top one if none qualify.
        """
        xp = snapshot.get("xp", 0)
        capacity = snapshot.get("capacity", 0.5)
        shadow = snapshot.get("shadow_score", 0.5)
        defaults = {"xp": 0.001, "capacity": 0.5, "shadow": 0.7}

        for arch in self.archetypes:
            new_w = arch.default_weight
            new_w += xp * arch.context_factors.get("xp", defaults["xp"])
            if capacity < 0.4 and "caretaker" in arch.name.lower():
                new_w += arch.context_factors.get("capacity", defaults["capacity"])
            if shadow > 0.7 and "healer" in arch.name.lower():
                new_w += arch.context_factors.get("shadow", defaults["shadow"])
            arch.current_weight = new_w
            logger.info("Archetype '%s' updated weight: %.2f", arch.name, arch.current_weight)

        filtered = {
            arch.name: arch
            for arch in self.archetypes
            if arch.current_weight >= ACTIVATION_THRESHOLD
        }
        if filtered:
            self.active_archetypes = filtered
        else:
            top = max(self.archetypes, key=lambda a: a.current_weight)
            self.active_archetypes = {top.name: top}

        logger.info("Active archetypes after update: %s", list(self.active_archetypes.keys()))

    def get_influence(self) -> dict:
        """
        Blend or pick a dominant archetype’s transformation_style and tag_bias.
        """
        if not self.active_archetypes:
            return {"transformation_style": "neutral", "tag_bias": []}

        lst = sorted(self.active_archetypes.values(), key=lambda a: a.current_weight, reverse=True)
        if len(lst) > 1 and lst[0].current_weight >= DOMINANCE_FACTOR * lst[1].current_weight:
            return {
                "transformation_style": lst[0].transformation_style,
                "tag_bias": lst[0].tag_bias,
            }

        style = " / ".join(f"{a.transformation_style} ({a.current_weight:.2f})" for a in lst)
        tags = []
        for a in lst:
            for t in a.tag_bias:
                if t not in tags:
                    tags.append(t)
        return {"transformation_style": style, "tag_bias": tags}

    def to_dict(self) -> dict:
        return {
            "archetypes": [a.to_dict() for a in self.archetypes],
            "active_archetypes": {n: a.to_dict() for n, a in self.active_archetypes.items()},
        }

    def update_from_dict(self, data: dict):
        self.archetypes = [Archetype.from_dict(d) for d in data.get("archetypes", [])]
        self.active_archetypes = {
            n: Archetype.from_dict(d)
            for n, d in data.get("active_archetypes", {}).items()
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)

__all__ = ["Archetype", "ArchetypeManager"]
