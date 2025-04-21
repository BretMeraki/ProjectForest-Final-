# forest_app/modules/task_engine.py

"""
TaskEngine: Generates the next actionable task for the user by combining:
  • HTA plan progress (dependencies, priority, resources),
  • Development‐index needs,
  • Identified reflection/pattern insights,
  • Rule‑based magnitude assignment using HTA_MAX_DEPTH_FOR_MAG_NORM.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from forest_app.config.constants import (
    TASK_TIER_BASE_MAGNITUDE,
    TASK_MAGNITUDE_DEPTH_WEIGHT,
    TASK_DEFAULT_MAGNITUDE,
    MAGNITUDE_MIN_VALUE,
    MAGNITUDE_MAX_VALUE,
    HTA_MAX_DEPTH_FOR_MAG_NORM,
    DEV_INDEX_PRIORITY_BOOST,
    PATTERN_PRIORITY_BOOST,
    REFLECTION_PRIORITY_BOOST,
)
from forest_app.modules.snapshot_flow import SnapshotFlowController
from forest_app.modules.pattern_id import PatternIdentificationEngine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ─── HTA Tree / Node Definitions (real or dummy) ─────────────────────────────
try:
    from forest_app.modules.hta_tree import HTATree, HTANode, RESOURCE_MAP
except ImportError:
    logger.warning("HTATree/HTANode not found; using dummy implementations.")
    RESOURCE_MAP = {"low": 0.3, "medium": 0.6, "high": 0.9}

    class HTANode:
        def __init__(self, **kwargs):
            self.id = kwargs.get("id", "dummy_id")
            self.title = kwargs.get("title", "Dummy Node")
            self.description = kwargs.get("description", "")
            self.priority = kwargs.get("priority", 1.0)
            self.status = kwargs.get("status", "pending")
            self.children = []
            self.depends_on = []
            self.estimated_energy = "medium"
            self.estimated_time = "medium"
            self.depth = kwargs.get("depth", 0)

        def dependencies_met(self, node_map: Dict[str, "HTANode"]) -> bool:
            return True

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "title": self.title,
                "description": self.description,
                "priority": self.priority,
                "status": self.status,
                "depth": self.depth,
            }

    class HTATree:
        def __init__(self, root: Optional[HTANode] = None):
            self.root = root

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> "HTATree":
            root = HTANode(**data["root"]) if data.get("root") else None
            return cls(root=root)

        def flatten(self) -> List[HTANode]:
            nodes: List[HTANode] = []
            def _recurse(n: HTANode):
                nodes.append(n)
                for c in n.children:
                    _recurse(c)
            if self.root:
                _recurse(self.root)
            return nodes

# ────────────────────────────────────────────────────────────────────────────────

class TaskEngine:
    """
    Orchestrates HTA‐based task selection, enriches with development and
    pattern insights, assigns magnitude, and returns the next task.
    """

    def __init__(self, task_templates: Optional[Dict[str, Dict[str, str]]] = None):
        self.default_templates = task_templates or {
            "Reflection": {
                "base_title": "Deep Reflection Session",
                "base_description": "A guided session to examine your inner journey.",
            }
        }
        self.flow = SnapshotFlowController(frequency=5)
        self.pattern_engine = PatternIdentificationEngine()

    def _is_dependency_met(self, node: HTANode, node_map: Dict[str, HTANode]) -> bool:
        try:
            return node.dependencies_met(node_map)
        except Exception as e:
            logger.exception("Dependency check failed for %s: %s", node.id, e)
            return False

    def select_and_score_nodes(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Flatten HTA, filter by dependencies and resources, then score each candidate:
          score = 
            node.priority
            + DEV_INDEX_PRIORITY_BOOST * (1 - dev_index for relevant dims)
            + PATTERN_PRIORITY_BOOST * pattern_score
            + REFLECTION_PRIORITY_BOOST * recent_reflection_intensity
        """
        hta_data = snapshot.get("core_state", {}).get("hta_tree", {})
        if not hta_data:
            return []

        tree = HTATree.from_dict(hta_data)
        nodes = tree.flatten()
        node_map = {n.id: n for n in nodes}
        capacity = snapshot.get("capacity", 0.5)

        dev_index = snapshot.get("dev_index", {})
        reflection_intensity = snapshot.get("reflection_context", {}).get("recent_intensity", 0.0)
        pattern_scores = self.pattern_engine.score(snapshot.get("reflection_log", []))

        candidates = []
        for n in nodes:
            if n.status not in ("pending", "active"):
                continue
            if not self._is_dependency_met(n, node_map):
                continue
            energy = RESOURCE_MAP.get(n.estimated_energy, 0.5)
            time_ = RESOURCE_MAP.get(n.estimated_time, 0.5)
            if max(energy, time_) > capacity:
                continue

            score = n.priority
            for dim in getattr(n, "relevant_indexes", []):
                dev_val = dev_index.get(dim, 0.5)
                score += DEV_INDEX_PRIORITY_BOOST * (1 - dev_val)
            score += PATTERN_PRIORITY_BOOST * pattern_scores.get(n.id, 0.0)
            score += REFLECTION_PRIORITY_BOOST * reflection_intensity

            candidates.append({"node": n, "score": score})

        return sorted(candidates, key=lambda x: x["score"], reverse=True)

    def _select_task_based_on_seed(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Choose the top-scoring HTA node, or fallback to a Reflection template.
        """
        scored = self.select_and_score_nodes(snapshot)
        node = scored[0]["node"] if scored else None

        task_id = hashlib.md5(
            f"{snapshot.get('xp',0)}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:8]

        introspective = "Reflect on how this task advances your journey."

        if node:
            base = {
                "id": task_id,
                "title": node.title,
                "description": node.description,
                "tier": snapshot.get("current_tier", "Bud"),
                "metadata": {"hta_depth": getattr(node, "depth", 0)},
                "created_at": datetime.utcnow().isoformat(),
                "introspective_prompt": introspective,
            }
        else:
            tpl = self.default_templates["Reflection"]
            base = {
                "id": task_id,
                "title": tpl["base_title"],
                "description": tpl["base_description"],
                "tier": snapshot.get("current_tier", "Bud"),
                "metadata": {},
                "created_at": datetime.utcnow().isoformat(),
                "introspective_prompt": introspective,
            }
        return base

    def get_next_step(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public API: Return {'base_task': {..., 'magnitude': float}}.
        """
        base_task = self._select_task_based_on_seed(snapshot)

        # ─── Rule‑based magnitude assignment (1–10 scale) ────────────
        mag = TASK_TIER_BASE_MAGNITUDE.get(base_task["tier"], TASK_DEFAULT_MAGNITUDE)
        depth = base_task.get("metadata", {}).get("hta_depth")
        if isinstance(depth, (int, float)):
            norm_depth = min(depth, HTA_MAX_DEPTH_FOR_MAG_NORM) / HTA_MAX_DEPTH_FOR_MAG_NORM
            mag += norm_depth * TASK_MAGNITUDE_DEPTH_WEIGHT

        # clamp to [MAGNITUDE_MIN_VALUE, MAGNITUDE_MAX_VALUE]
        mag = max(MAGNITUDE_MIN_VALUE, min(MAGNITUDE_MAX_VALUE, mag))
        base_task["magnitude"] = mag
        # ─────────────────────────────────────────────────────────────

        return {"base_task": base_task}

