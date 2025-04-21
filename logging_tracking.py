# forest_app/modules/logging_tracking.py

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

# Import repositories for logging events
from forest_app.persistence.repository import (
    TaskEventLogRepository,
    ReflectionEventLogRepository,
)

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Attempt to import the real HTANode class for type hints/linking logic
try:
    from forest_app.modules.hta_tree import HTANode
except ImportError:
    logger.warning("HTANode not found, using dummy class for logging_tracking.py.")

    class HTANode:
        def __init__(self, title="Unknown", id=None):
            self.title = title
            self.id = id

        def link_task(self, task_id):
            pass

        def link_reflection(self, reflection_id):
            pass


class TaskFootprintLogger:
    """
    Logs detailed task events with context directly to the database.
    Requires a database session to operate.
    """

    def __init__(self, db: Session):
        self.repo = TaskEventLogRepository(db)

    def log_task_event(
        self,
        task_id: str,
        event_type: str,
        snapshot: Dict[str, Any],
        hta_node: Optional[HTANode] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Logs a task event with context extracted from the snapshot.
        """
        # Extract context
        capacity = snapshot.get("capacity")
        shadow_score = snapshot.get("shadow_score")
        active_seed = snapshot.get("seed_context", {})
        active_archetype = snapshot.get("archetype_manager", {}).get(
            "active_archetype", {}
        )

        log_data = {
            "task_id": task_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow(),
            "linked_hta_node_id": getattr(hta_node, "id", None) if hta_node else None,
            "capacity_at_event": capacity,
            "shadow_score_at_event": shadow_score,
            "active_seed_name": active_seed.get("seed_name") if active_seed else None,
            "active_archetype_name": (
                active_archetype.get("name") if active_archetype else None
            ),
            "event_metadata": event_metadata or {},
        }

        try:
            self.repo.create_log(log_data)
            # Log HTA linking separately if provided
            if hta_node:
                logger.info(
                    "Task event '%s' linked to HTA node ID '%s'.",
                    task_id,
                    hta_node.id,
                )
        except Exception as e:
            logger.error("Failed to log task event for task %s: %s", task_id, e)


class ReflectionLogLogger:
    """
    Logs detailed reflection events with context directly to the database.
    Requires a database session to operate.
    """

    def __init__(self, db: Session):
        self.repo = ReflectionEventLogRepository(db)

    def log_reflection_event(
        self,
        reflection_id: str,
        event_type: str,
        snapshot: Dict[str, Any],
        hta_node: Optional[HTANode] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Logs a reflection event with context extracted from the snapshot.
        """
        # Extract context
        sentiment_score = (
            snapshot.get("component_state", {})
            .get("metrics_engine", {})
            .get("last_sentiment", None)
        )
        capacity = snapshot.get("capacity")
        shadow_score = snapshot.get("shadow_score")
        active_seed = snapshot.get("seed_context", {})
        active_archetype = snapshot.get("archetype_manager", {}).get(
            "active_archetype", {}
        )

        log_data = {
            "reflection_id": reflection_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow(),
            "linked_hta_node_id": getattr(hta_node, "id", None) if hta_node else None,
            "sentiment_score": sentiment_score,
            "capacity_at_event": capacity,
            "shadow_score_at_event": shadow_score,
            "active_seed_name": active_seed.get("seed_name") if active_seed else None,
            "active_archetype_name": (
                active_archetype.get("name") if active_archetype else None
            ),
            "event_metadata": event_metadata or {},
        }

        try:
            self.repo.create_log(log_data)
            if hta_node:
                logger.info(
                    "Reflection event '%s' linked to HTA node ID '%s'.",
                    reflection_id,
                    hta_node.id,
                )
        except Exception as e:
            logger.error("Failed to log reflection event for %s: %s", reflection_id, e)
