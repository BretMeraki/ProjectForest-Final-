# forest_app/persistence/models.py

import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from datetime import datetime

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()


# --- Existing MemorySnapshotModel ---
# (Ensure this matches your latest definition if it changed)
class MemorySnapshotModel(Base):
    __tablename__ = "memory_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)  # Assuming user_id is required
    snapshot_data = Column(JSON, nullable=False)  # Store the main snapshot blob
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )  # Add updated_at

    def __repr__(self):
        return f"<MemorySnapshotModel(id={self.id}, user_id={self.user_id}, updated_at={self.updated_at})>"


# --- NEW: Task Event Log Model ---
class TaskEventLog(Base):
    """SQLAlchemy model for logging task-related events."""

    __tablename__ = "task_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    # Link to the user if applicable (e.g., via snapshot or user management)
    # user_id = Column(String, index=True, nullable=False)
    task_id = Column(String, index=True, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # e.g., created, started, completed, skipped, deadline_missed
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    linked_hta_node_id = Column(String, index=True, nullable=True)

    # Contextual fields at the time of the event
    capacity_at_event = Column(Float, nullable=True)
    shadow_score_at_event = Column(Float, nullable=True)
    active_seed_name = Column(String, nullable=True)
    active_archetype_name = Column(String, nullable=True)

    # Optional: Store additional event-specific details as JSON
    event_metadata = Column(
        JSON, nullable=True
    )  # e.g., {"effort": 0.8, "feedback": "Difficult but rewarding"}

    def __repr__(self):
        return f"<TaskEventLog(id={self.id}, task_id={self.task_id}, event='{self.event_type}')>"


# --- NEW: Reflection Event Log Model ---
class ReflectionEventLog(Base):
    """SQLAlchemy model for logging reflection-related events."""

    __tablename__ = "reflection_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    # user_id = Column(String, index=True, nullable=False)
    # Unique ID for the reflection event (could be hash of input + timestamp)
    reflection_id = Column(String, index=True, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # e.g., processed, sentiment_analyzed, triggered_hta_update
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    linked_hta_node_id = Column(String, index=True, nullable=True)

    # Contextual fields at the time of the event
    sentiment_score = Column(Float, nullable=True)
    capacity_at_event = Column(Float, nullable=True)
    shadow_score_at_event = Column(Float, nullable=True)
    active_seed_name = Column(String, nullable=True)
    active_archetype_name = Column(String, nullable=True)

    # Optional: Store additional event-specific details as JSON
    event_metadata = Column(
        JSON, nullable=True
    )  # e.g., {"themes_detected": ["growth", "fear"]}

    def __repr__(self):
        return f"<ReflectionEventLog(id={self.id}, reflection_id={self.reflection_id}, event='{self.event_type}')>"


# You can add other models here as needed (e.g., User, Task, etc.)
