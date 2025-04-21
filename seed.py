# forest_app/modules/seed.py

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

# Initialize logger immediately so it's available in the import fallback
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import HTATree and HTANode from our HTA module.
# Ensure this import path is correct for your structure
try:
    from forest_app.modules.hta_tree import HTATree, HTANode
except ImportError:
    logger.warning("HTATree/HTANode not found, using dummy classes for seed.py.")

    class HTANode:
        def __init__(
            self, id: str, title: str, description: str, priority: float, **kwargs
        ):
            self.id = id
            self.title = title
            self.description = description
            self.priority = priority
            self.status = "pending"
            self.children = []
            self.depends_on = []
            self.estimated_energy = "medium"
            self.estimated_time = "medium"
            self.linked_tasks = []

        def to_dict(self):
            return {
                "id": self.id,
                "title": self.title,
                "description": self.description,
                "priority": self.priority,
                "status": self.status,
                "children": [],
                "depends_on": [],
                "estimated_energy": self.estimated_energy,
                "estimated_time": self.estimated_time,
                "linked_tasks": self.linked_tasks,
            }

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

    class HTATree:
        def __init__(self, root: Optional[HTANode] = None):
            self.root = root

        def to_dict(self):
            return {"root": self.root.to_dict() if self.root else {}}

        @classmethod
        def from_dict(cls, data):
            root_data = data.get("root", {})
            root_node = HTANode.from_dict(root_data) if root_data else None
            return cls(root=root_node)

        def flatten(self):
            return [self.root] if self.root else []

        def propagate_status(self):
            pass  # Dummy method


class Seed:
    """
    Represents a symbolic Seed within the Forest system.
    """
    def __init__(
        self,
        seed_name: str,
        seed_domain: str,
        seed_form: Optional[str] = "",
        description: Optional[str] = "",
        emotional_root_tags: Optional[List[str]] = None,
        shadow_trigger: Optional[str] = "",
        associated_archetypes: Optional[List[str]] = None,
        status: str = "active",
        seed_id: Optional[str] = None,
        created_at: Optional[str] = None,
        hta_tree: Optional[dict] = None,
    ):
        self.seed_id = seed_id or str(uuid.uuid4())
        self.seed_name = seed_name
        self.seed_domain = seed_domain
        self.seed_form = seed_form or ""
        self.description = description or ""
        self.emotional_root_tags = emotional_root_tags or []
        self.shadow_trigger = shadow_trigger or ""
        self.associated_archetypes = associated_archetypes or []
        self.status = status
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.hta_tree = hta_tree or {}

    def to_dict(self) -> dict:
        return {
            "seed_id": self.seed_id,
            "seed_name": self.seed_name,
            "seed_domain": self.seed_domain,
            "seed_form": self.seed_form,
            "description": self.description,
            "emotional_root_tags": self.emotional_root_tags,
            "shadow_trigger": self.shadow_trigger,
            "associated_archetypes": self.associated_archetypes,
            "status": self.status,
            "created_at": self.created_at,
            "hta_tree": self.hta_tree,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Seed":
        return cls(
            seed_name=data.get("seed_name", ""),
            seed_domain=data.get("seed_domain", ""),
            seed_form=data.get("seed_form", ""),
            description=data.get("description", ""),
            emotional_root_tags=data.get("emotional_root_tags", []),
            shadow_trigger=data.get("shadow_trigger", ""),
            associated_archetypes=data.get("associated_archetypes", []),
            status=data.get("status", "active"),
            seed_id=data.get("seed_id"),
            created_at=data.get("created_at"),
            hta_tree=data.get("hta_tree"),
        )

    def update_status(self, new_status: str):
        old = self.status
        self.status = new_status
        logger.info("Seed '%s' status: '%s' → '%s'.", self.seed_name, old, new_status)

    def update_description(self, new_description: str):
        self.description = new_description
        logger.info("Seed '%s' description updated.", self.seed_name)

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class SeedManager:
    """
    Manages a collection of Seeds in the Forest system.
    """
    def __init__(self):
        self.seeds: List[Seed] = []

    def add_seed(self, seed: Seed) -> None:
        if any(s.seed_id == seed.seed_id for s in self.seeds):
            logger.warning("Seed with ID %s already exists. Skipping.", seed.seed_id)
            return
        self.seeds.append(seed)
        logger.info("Added seed '%s' (ID: %s).", seed.seed_name, seed.seed_id)

    def remove_seed_by_id(self, seed_id: str) -> bool:
        initial = len(self.seeds)
        self.seeds = [s for s in self.seeds if s.seed_id != seed_id]
        if len(self.seeds) < initial:
            logger.info("Removed seed ID %s.", seed_id)
            return True
        logger.warning("Seed ID %s not found for removal.", seed_id)
        return False

    def get_seed_by_id(self, seed_id: str) -> Optional[Seed]:
        return next((s for s in self.seeds if s.seed_id == seed_id), None)

    def get_all_seeds(self) -> List[Seed]:
        return self.seeds

    def update_seed(self, seed_id: str, **kwargs) -> bool:
        seed = self.get_seed_by_id(seed_id)
        if not seed:
            return False
        fields = []
        for key, val in kwargs.items():
            if hasattr(seed, key):
                setattr(seed, key, val)
                fields.append(key)
            else:
                logger.warning("No attribute '%s' on Seed. Ignored.", key)
        if fields:
            logger.info("Updated seed %s fields: %s.", seed_id, ", ".join(fields))
            return True
        return False

    def plant_seed(
        self,
        raw_intention: str,
        seed_domain: str,
        additional_context: Optional[dict] = None,
    ) -> Seed:
        context = additional_context or {}
        seed_name = f"Seed of {raw_intention[:20].strip().capitalize()}"
        seed_form = context.get("seed_form", "A newly planted seedling.")
        emotional_root_tags = context.get("emotional_root_tags", [])
        shadow_trigger = context.get("shadow_trigger", "")
        associated_archetypes = context.get("associated_archetypes", [])

        new_seed = Seed(
            seed_name=seed_name,
            seed_domain=seed_domain,
            seed_form=seed_form,
            description=raw_intention,
            emotional_root_tags=emotional_root_tags,
            shadow_trigger=shadow_trigger,
            associated_archetypes=associated_archetypes,
            status="active",
        )

        root_node = HTANode(
            id=str(uuid.uuid4()),
            title=new_seed.seed_name,
            description=new_seed.description,
            priority=1.0,
        )
        tree = HTATree(root=root_node)
        new_seed.hta_tree = tree.to_dict()
        logger.info("Initialized HTA tree for '%s'.", new_seed.seed_name)

        self.add_seed(new_seed)
        return new_seed

    def evolve_seed(
        self, seed_id: str, evolution_type: str, new_intention: Optional[str] = None
    ) -> bool:
        seed = self.get_seed_by_id(seed_id)
        if not seed:
            return False

        et = evolution_type.lower()
        if et == "reframe":
            if new_intention:
                seed.description = new_intention
                logger.info("Seed '%s' reframed.", seed.seed_name)
            else:
                logger.warning("Reframe requires new_intention.")
                return False
        elif et == "expansion":
            if new_intention:
                seed.description += f"\nExpanded: {new_intention}"
                logger.info("Seed '%s' expanded.", seed.seed_name)
            else:
                logger.warning("Expansion requires new_intention.")
                return False
        elif et == "transformation":
            seed.update_status("evolved")
            logger.info("Seed '%s' transformed.", seed.seed_name)
        else:
            logger.warning("Unknown evolution '%s'.", evolution_type)
            return False

        try:
            tree = HTATree.from_dict(seed.hta_tree)
            # ... evolution-specific HTA adjustments ...
            seed.hta_tree = tree.to_dict()
            logger.info("HTA tree updated for seed '%s'.", seed.seed_name)
        except Exception as e:
            logger.error("Error updating HTA tree: %s", e)
            return False

        return True

    def get_seed_summary(self) -> str:
        active = [s for s in self.seeds if s.status.lower() == "active"]
        if not active:
            return "No active seeds."
        return " • ".join(f"{s.seed_name} ({s.seed_domain})" for s in active)

    def to_dict(self) -> dict:
        return {"seeds": [s.to_dict() for s in self.seeds]}

    def update_from_dict(self, data: dict):
        seed_list = data.get("seeds", [])
        self.seeds = [Seed.from_dict(d) for d in seed_list]

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
