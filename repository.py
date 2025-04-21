# forest_app/persistence/repository.py

import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any, List

# Import your ORM models
from .models import MemorySnapshotModel, TaskEventLog, ReflectionEventLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# --- MemorySnapshotRepository ---
class MemorySnapshotRepository:
    """Repository for managing MemorySnapshot persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_snapshot(
        self, user_id: str, snapshot_data: dict
    ) -> Optional[MemorySnapshotModel]:
        """Creates and persists a new MemorySnapshot."""
        if not user_id:
            logger.error("User ID is required to create a snapshot.")
            return None

        model = MemorySnapshotModel(user_id=user_id, snapshot_data=snapshot_data)
        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            logger.info("Created snapshot for user %s with id %s", user_id, model.id)
            return model
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error creating snapshot for user %s: %s", user_id, e)
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Unexpected error creating snapshot for user %s: %s", user_id, e
            )
            raise

    def get_latest_snapshot(self, user_id: str) -> Optional[MemorySnapshotModel]:
        """Retrieves the latest MemorySnapshot for the specified user."""
        try:
            return (
                self.db.query(MemorySnapshotModel)
                .filter(MemorySnapshotModel.user_id == user_id)
                .order_by(MemorySnapshotModel.updated_at.desc())
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(
                "Database error retrieving latest snapshot for user %s: %s", user_id, e
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error retrieving latest snapshot for user %s: %s",
                user_id,
                e,
            )
            raise

    def update_snapshot(
        self, snapshot_model: MemorySnapshotModel, new_data: dict
    ) -> Optional[MemorySnapshotModel]:
        """Updates an existing MemorySnapshot with new snapshot data."""
        if not snapshot_model:
            logger.warning("Attempted to update a non-existent snapshot model.")
            return None

        snapshot_model.snapshot_data = new_data
        try:
            self.db.commit()
            self.db.refresh(snapshot_model)
            logger.info(
                "Updated snapshot id %s for user %s",
                snapshot_model.id,
                snapshot_model.user_id,
            )
            return snapshot_model
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Database error updating snapshot id %s: %s", snapshot_model.id, e
            )
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Unexpected error updating snapshot id %s: %s", snapshot_model.id, e
            )
            raise

    def delete_snapshot(self, snapshot_model: MemorySnapshotModel):
        """Deletes an existing MemorySnapshot from the database."""
        if not snapshot_model:
            logger.warning("Attempted to delete a non-existent snapshot model.")
            return

        snapshot_id = snapshot_model.id
        try:
            self.db.delete(snapshot_model)
            self.db.commit()
            logger.info("Deleted snapshot id %s", snapshot_id)
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting snapshot id %s: %s", snapshot_id, e)
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("Unexpected error deleting snapshot id %s: %s", snapshot_id, e)
            raise


# --- TaskEventLogRepository ---
class TaskEventLogRepository:
    """Repository for managing TaskEventLog persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_log(self, log_data: Dict[str, Any]) -> Optional[TaskEventLog]:
        """Creates a new task event log entry in the database."""
        if not log_data.get("task_id") or not log_data.get("event_type"):
            logger.error("Task ID and Event Type are required for Task Event Log.")
            return None

        log_entry = TaskEventLog(**log_data)
        try:
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            logger.info(
                "Created Task Event Log entry ID %s for task %s",
                log_entry.id,
                log_entry.task_id,
            )
            return log_entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Database error creating task event log for task %s: %s",
                log_data.get("task_id"),
                e,
            )
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Unexpected error creating task event log for task %s: %s",
                log_data.get("task_id"),
                e,
            )
            raise

    def get_logs_for_task(self, task_id: str) -> List[TaskEventLog]:
        """Retrieves all log entries for a specific task."""
        try:
            return (
                self.db.query(TaskEventLog)
                .filter(TaskEventLog.task_id == task_id)
                .order_by(TaskEventLog.timestamp.asc())
                .all()
            )
        except SQLAlchemyError as e:
            logger.error("Database error retrieving logs for task %s: %s", task_id, e)
            raise
        except Exception as e:
            logger.error("Unexpected error retrieving logs for task %s: %s", task_id, e)
            raise


# --- ReflectionEventLogRepository ---
class ReflectionEventLogRepository:
    """Repository for managing ReflectionEventLog persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_log(self, log_data: Dict[str, Any]) -> Optional[ReflectionEventLog]:
        """Creates a new reflection event log entry in the database."""
        if not log_data.get("reflection_id") or not log_data.get("event_type"):
            logger.error(
                "Reflection ID and Event Type are required for Reflection Event Log."
            )
            return None

        log_entry = ReflectionEventLog(**log_data)
        try:
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            logger.info(
                "Created Reflection Event Log entry ID %s for reflection %s",
                log_entry.id,
                log_entry.reflection_id,
            )
            return log_entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Database error creating reflection event log for reflection %s: %s",
                log_data.get("reflection_id"),
                e,
            )
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Unexpected error creating reflection event log for reflection %s: %s",
                log_data.get("reflection_id"),
                e,
            )
            raise

    def get_logs_for_reflection(self, reflection_id: str) -> List[ReflectionEventLog]:
        """Retrieves all log entries for a specific reflection event."""
        try:
            return (
                self.db.query(ReflectionEventLog)
                .filter(ReflectionEventLog.reflection_id == reflection_id)
                .order_by(ReflectionEventLog.timestamp.asc())
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(
                "Database error retrieving logs for reflection %s: %s", reflection_id, e
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error retrieving logs for reflection %s: %s",
                reflection_id,
                e,
            )
            raise
