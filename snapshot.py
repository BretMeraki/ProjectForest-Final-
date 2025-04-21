# forest_app/core/snapshot.py
import json
import logging
from datetime import datetime
# --- Ensure necessary typing imports ---
from typing import Dict, List, Any, Optional

# ---------- import managers / engines ----------
# Assuming these imports are correct based on your project structure
# Note: If these also need state saved/loaded via snapshot, ensure they have
# to_dict/update_from_dict methods.
from forest_app.modules.development_index import FullDevelopmentIndex
from forest_app.modules.archetype import ArchetypeManager
from forest_app.modules.seed import SeedManager
from forest_app.modules.memory import MemorySystem
from forest_app.modules.xp_mastery import XPMastery

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MemorySnapshot:
    """Serializable container for user journey state."""

    def __init__(self) -> None:
        # ---- Core progress & wellbeing gauges ---------------------------
        self.xp: int = 0
        self.shadow_score: float = 0.50  # 0–1 (lower better)
        self.capacity: float = 0.50      # available resources 0–1
        self.magnitude: float = 5.00     # perceived impact 1–10
        self.resistance: float = 0.00    # dynamic 0–1 opposition dial
        self.relationship_index: float = 0.50  # overall relational health

        # ---- Narrative scaffolding --------------------------------------
        self.story_beats: List[Dict[str, Any]] = []  # [{beat_id, text, ts}, …]
        self.totems: List[Dict[str, Any]] = []       # [{totem_id, name, …}, …]

        # ---- Desire & pairing caches ------------------------------------
        self.wants_cache: Dict[str, float] = {}            # {"travel:iceland": 0.8, …}
        self.partner_profiles: Dict[str, Dict[str, Any]] = {}  # mirror profiles

        # ---- Engagement maintenance ------------------------------------
        self.withering_level: float = 0.00  # 0–1 engagement nudge

        # ---- Activation & core pathing ----------------------------------
        self.activated_state: Dict[str, Any] = {
            "activated": False,
            "mode": None,
            "goal_set": False,
        }
        self.core_state: Dict[str, Any] = {}   # e.g. HTA tree
        self.decor_state: Dict[str, Any] = {}  # UI or theme info

        # ---- Path & deadlines -------------------------------------------
        self.current_path: str = "structured"              # structured/hybrid/open
        self.estimated_completion_date: Optional[str] = None # ISO formatted date

        # ---- Managers / engines (ensure these have to_dict/update methods if stateful) ---
        self.dev_index = FullDevelopmentIndex()
        self.archetype_manager = ArchetypeManager()
        self.seed_manager = SeedManager()
        self.memory_system = MemorySystem()
        self.xp_mastery = XPMastery()

        # ---- Hardware & misc -------------------------------------------
        self.hardware_config: Dict[str, Any] = {
            "ram": 0,
            "gpu_vram": 0,
            "cpu": "Unknown",
            "neural_engine": "Unknown",
        }

        # ---- Logs / context --------------------------------------------
        self.reflection_context: Dict[str, Any] = {
            "themes": [],
            "recent_insight": "",
            "current_priority": "",
        }
        self.reflection_log: List[Dict[str, Any]] = []
        self.task_backlog: List[Dict[str, Any]] = []
        self.task_footprints: List[Dict[str, Any]] = []

        # --- ADDED: Attribute for conversation history ---
        # Stores turns as {"role": "user" | "assistant", "content": "text"}
        self.conversation_history: List[Dict[str, str]] = []
        # --- END ADDED ---

        # ---- Component state stubs for every live engine ----------------
        # Note: component_state often stores the serialized dicts from managers/engines
        self.component_state: Dict[str, Any] = {
            "sentiment_engine_calibration": {},
            "metrics_engine": {},
            "seed_manager": {},
            "archetype_manager": {},
            "dev_index": {},
            "memory_system": {},
            "xp_mastery": {},
            "pattern_engine_config": {},
            "emotional_integrity_index": {},
            "desire_engine": {},
            "resistance_engine": {},
            "reward_index": {},
            "last_issued_task_id": None,
            "last_activity_ts": None,
            # "conversation_history" could also be stored here if preferred,
            # but keeping it top-level for easier access seems okay too.
        }

        # ---- Misc meta --------------------------------------------------
        self.template_metadata: Dict[str, Any] = {}
        self.last_ritual_mode: str = "Trail"
        self.timestamp: str = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialise entire snapshot to a dict (JSON‑safe)."""
        # --- Ensure managers/engines have to_dict methods ---
        # --- Or handle cases where they might not ---
        def safe_to_dict(obj):
             if hasattr(obj, 'to_dict') and callable(obj.to_dict):
                 return obj.to_dict()
             logger.warning("Object %s lacks a to_dict method, saving {} instead.", type(obj).__name__)
             return {}

        return {
            # Core gauges
            "xp": self.xp,
            "shadow_score": self.shadow_score,
            "capacity": self.capacity,
            "magnitude": self.magnitude,
            "resistance": self.resistance,
            "relationship_index": self.relationship_index,

            # Narrative
            "story_beats": self.story_beats,
            "totems": self.totems,

            # Desire / pairing
            "wants_cache": self.wants_cache,
            "partner_profiles": self.partner_profiles,

            # Engagement
            "withering_level": self.withering_level,

            # Activation / state
            "activated_state": self.activated_state,
            "core_state": self.core_state,
            "decor_state": self.decor_state,

            # Path & deadlines
            "current_path": self.current_path,
            "estimated_completion_date": self.estimated_completion_date,

            # Engines (Using safe_to_dict wrapper)
            "dev_index": safe_to_dict(self.dev_index),
            "archetype_manager": safe_to_dict(self.archetype_manager),
            "seed_manager": safe_to_dict(self.seed_manager),
            "memory_system": safe_to_dict(self.memory_system),
            "xp_mastery": safe_to_dict(self.xp_mastery),

            # Hardware
            "hardware_config": self.hardware_config,

            # Logs
            "reflection_context": self.reflection_context,
            "reflection_log": self.reflection_log,
            "task_backlog": self.task_backlog,
            "task_footprints": self.task_footprints,

            # --- ADDED: Include conversation history in serialization ---
            "conversation_history": self.conversation_history,
            # --- END ADDED ---

            # Component states (This might duplicate engine state if engines are also serialized above)
            # Consider if component_state should store the *result* of engine.to_dict() instead
            # For now, keeping both as per original structure, but be mindful.
            "component_state": self.component_state,

            # Misc
            "template_metadata": self.template_metadata,
            "last_ritual_mode": self.last_ritual_mode,
            "timestamp": self.timestamp,
        }

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Rehydrate snapshot from dict, preserving unknown fields defensively."""
        if not isinstance(data, dict): # Basic type check
             logger.error("Invalid data passed to update_from_dict: expected dict, got %s", type(data))
             return

        # Simple scalars and lists/dicts
        for attr in [
            "xp", "shadow_score", "capacity", "magnitude", "resistance",
            "relationship_index", "hardware_config", "activated_state",
            "core_state", "decor_state", "reflection_context",
            "reflection_log", "task_backlog", "task_footprints",
            "story_beats", "totems", "wants_cache", "partner_profiles",
            "withering_level", "current_path", "estimated_completion_date",
            "template_metadata", "last_ritual_mode", "timestamp",
            # --- ADDED: Load conversation history ---
            "conversation_history",
            # --- END ADDED ---
        ]:
            if attr in data:
                setattr(self, attr, data[attr])
            # --- ADDED: Ensure conversation_history defaults to list if missing/null ---
            elif attr == "conversation_history":
                 # Set only if the attribute doesn't exist or is None after loop
                 if not hasattr(self, attr) or getattr(self, attr) is None:
                     setattr(self, attr, [])
            # --- END ADDED ---

        # --- Ensure conversation_history is a list after potential loading ---
        if not isinstance(getattr(self, 'conversation_history', []), list):
             logger.warning("Loaded conversation_history is not a list (%s), resetting.", type(self.conversation_history))
             self.conversation_history = []
        # ---

        # Complex managers (using safe update)
        # --- Ensure managers/engines have update_from_dict methods ---
        # --- Or handle cases where they might not ---
        def safe_update_from_dict(engine_attr_name, key_in_data):
             engine = getattr(self, engine_attr_name, None)
             if engine and hasattr(engine, 'update_from_dict') and callable(engine.update_from_dict):
                 engine_data = data.get(key_in_data)
                 if isinstance(engine_data, dict):
                     try:
                         engine.update_from_dict(engine_data)
                     except Exception as e:
                          logger.exception("Error calling update_from_dict for %s: %s", engine_attr_name, e)
                 elif engine_data is not None:
                      logger.warning("Data for %s is not a dict (%s), cannot update.", engine_attr_name, type(engine_data))
             elif key_in_data in data:
                  logger.warning("Engine %s not found or lacks update_from_dict method.", engine_attr_name)

        safe_update_from_dict("dev_index", "dev_index")
        safe_update_from_dict("archetype_manager", "archetype_manager")
        safe_update_from_dict("seed_manager", "seed_manager")
        safe_update_from_dict("memory_system", "memory_system")
        safe_update_from_dict("xp_mastery", "xp_mastery")

        # Component_state blob (Load this last, it might contain overrides or old state)
        loaded_cs = data.get("component_state")
        if isinstance(loaded_cs, dict):
            self.component_state = loaded_cs
        elif loaded_cs is not None:
            logger.warning("Loaded component_state is not a dict (%s), ignoring.", type(loaded_cs))
            # Keep existing self.component_state or default it
            if not hasattr(self, 'component_state') or not isinstance(self.component_state, dict):
                 self.component_state = {}
        # Note: Consider if loading component_state should *also* trigger
        # update_from_dict on the individual managers based on its contents,
        # depending on how _save_component_states in orchestrator works.


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemorySnapshot":
        snap = cls()
        # Ensure data is dict before passing
        if isinstance(data, dict):
            snap.update_from_dict(data)
        else:
             logger.error("Invalid data passed to MemorySnapshot.from_dict: expected dict, got %s", type(data))
             # snap will have default initial values
        return snap

    def __str__(self) -> str:
        try:
            # Use default=str for non-serializable objects like datetime, but handle others potentially
            return json.dumps(self.to_dict(), indent=2, default=str)
        except TypeError as exc:
            logger.error("Snapshot serialisation error: %s", exc)
            # Attempt a basic representation if full serialization fails
            return f"<Snapshot xp={getattr(self, 'xp', 'N/A')} ts={getattr(self, 'timestamp', 'N/A')} ...>"