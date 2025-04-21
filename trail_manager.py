import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TrailEvent:
    """
    Represents a single event in a trail, such as a bench, lightning event, wonder, or wild path.

    Attributes:
        event_type (str): The type of event (e.g., "bench", "lightning", "wonder", "wild_path", "reflection").
        description (str): A descriptive, often poetic, description of the event.
        metadata (dict): Additional metadata for classification and visual cues (e.g., object_class, visual_theme).
        timestamp (str): The UTC timestamp when the event was recorded (ISO format).
    """

    def __init__(
        self,
        event_type: str,
        description: str,
        metadata: Dict[str, Any] = None,
        object_class: str = None,
    ):
        self.event_type = event_type
        self.description = description
        # Initialize metadata; if object_class is provided, add it under a reserved key.
        self.metadata = metadata.copy() if metadata else {}
        if object_class:
            self.metadata["object_class"] = object_class
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "description": self.description,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrailEvent":
        event = cls(
            event_type=data.get("event_type", "unknown"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            object_class=data.get("metadata", {}).get("object_class"),
        )
        event.timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        return event


class Trail:
    """
    Represents an entire trail in the Forest system, a series of events that together represent the user's journey.

    Attributes:
        trail_id (str): Unique identifier for the trail.
        trail_type (str): The type of trail (e.g., "bench", "lightning", "wonder", "wild_path", "composite").
        description (str): High-level description of the trail.
        events (List[TrailEvent]): List of events along the trail.
        created_at (str): Timestamp when the trail was created.
        updated_at (str): Timestamp when the trail was last updated.
    """

    def __init__(self, trail_id: str, trail_type: str, description: str):
        self.trail_id = trail_id
        self.trail_type = trail_type
        self.description = description
        self.events: List[TrailEvent] = []
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at

    def add_event(self, event: TrailEvent):
        self.events.append(event)
        self.updated_at = datetime.utcnow().isoformat()
        logger.info("Added event to trail '%s': %s", self.trail_id, event.to_dict())

    def update_event(self, index: int, new_event: TrailEvent):
        if 0 <= index < len(self.events):
            self.events[index] = new_event
            self.updated_at = datetime.utcnow().isoformat()
            logger.info(
                "Updated event at index %d for trail '%s'.", index, self.trail_id
            )
        else:
            logger.warning(
                "Attempted to update nonexistent event index %d for trail '%s'.",
                index,
                self.trail_id,
            )

    def to_dict(self) -> dict:
        return {
            "trail_id": self.trail_id,
            "trail_type": self.trail_type,
            "description": self.description,
            "events": [event.to_dict() for event in self.events],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trail":
        trail = cls(
            trail_id=data.get("trail_id", ""),
            trail_type=data.get("trail_type", ""),
            description=data.get("description", ""),
        )
        trail.created_at = data.get("created_at", datetime.utcnow().isoformat())
        trail.updated_at = data.get("updated_at", trail.created_at)
        trail.events = [
            TrailEvent.from_dict(event_data) for event_data in data.get("events", [])
        ]
        return trail


class TrailManager:
    """
    Manages trails (journey paths) within the Forest system.

    Responsibilities include creating new trails, adding events (such as benches,
    lightning events, wonder events, wild paths), updating trails, and retrieving summaries.
    """

    def __init__(self):
        self.trails: Dict[str, Trail] = {}  # Maps trail_id to Trail objects.

    def create_trail(self, trail_type: str, description: str) -> Trail:
        """
        Creates a new trail with a unique identifier.
        """
        import hashlib

        trail_id = hashlib.md5(
            f"{description}-{datetime.utcnow()}".encode("utf-8")
        ).hexdigest()[:8]
        trail = Trail(trail_id=trail_id, trail_type=trail_type, description=description)
        self.trails[trail_id] = trail
        logger.info("Created new trail '%s' of type '%s'.", trail_id, trail_type)
        return trail

    def add_bench(
        self,
        trail_id: str,
        bench_description: str,
        metadata: Dict[str, Any] = None,
        object_class: str = None,
    ) -> bool:
        """
        Adds a bench event (a reflective pause) to the specified trail.
        """
        trail = self.trails.get(trail_id)
        if trail:
            event = TrailEvent(
                event_type="bench",
                description=bench_description,
                metadata=metadata,
                object_class=object_class,
            )
            trail.add_event(event)
            return True
        else:
            logger.warning("Attempted to add bench to unknown trail '%s'.", trail_id)
            return False

    def add_lightning_event(
        self,
        trail_id: str,
        event_description: str,
        metadata: Dict[str, Any] = None,
        object_class: str = None,
    ) -> bool:
        """
        Adds a lightning event (a quick, energizing action) to the specified trail.
        """
        trail = self.trails.get(trail_id)
        if trail:
            event = TrailEvent(
                event_type="lightning",
                description=event_description,
                metadata=metadata,
                object_class=object_class,
            )
            trail.add_event(event)
            return True
        else:
            logger.warning(
                "Attempted to add lightning event to unknown trail '%s'.", trail_id
            )
            return False

    def add_wonder_event(
        self,
        trail_id: str,
        event_description: str,
        metadata: Dict[str, Any] = None,
        object_class: str = None,
    ) -> bool:
        """
        Adds a wonder event (a moment of insight or magical surprise) to the specified trail.
        """
        trail = self.trails.get(trail_id)
        if trail:
            event = TrailEvent(
                event_type="wonder",
                description=event_description,
                metadata=metadata,
                object_class=object_class,
            )
            trail.add_event(event)
            return True
        else:
            logger.warning(
                "Attempted to add wonder event to unknown trail '%s'.", trail_id
            )
            return False

    def add_wild_path(
        self,
        trail_id: str,
        path_description: str,
        metadata: Dict[str, Any] = None,
        object_class: str = None,
    ) -> bool:
        """
        Adds a wild path event (an exploratory or unplanned branch) to the specified trail.
        """
        trail = self.trails.get(trail_id)
        if trail:
            event = TrailEvent(
                event_type="wild_path",
                description=path_description,
                metadata=metadata,
                object_class=object_class,
            )
            trail.add_event(event)
            return True
        else:
            logger.warning(
                "Attempted to add wild path to unknown trail '%s'.", trail_id
            )
            return False

    def get_trail_summary(self, trail_id: str) -> dict:
        """
        Returns a summary dictionary for the specified trail.
        """
        trail = self.trails.get(trail_id)
        if trail:
            summary = trail.to_dict()
            logger.info("Retrieved summary for trail '%s'.", trail_id)
            return summary
        else:
            logger.warning("No trail found with id '%s'.", trail_id)
            return {}

    def to_dict(self) -> dict:
        """
        Serializes all trails managed by the TrailManager.
        """
        return {trail_id: trail.to_dict() for trail_id, trail in self.trails.items()}

    def update_from_dict(self, data: dict):
        """
        Rehydrates the TrailManager from a dictionary of trails.
        """
        trails_data = data.get("trails", {})
        for trail_id, tdata in trails_data.items():
            self.trails[trail_id] = Trail.from_dict(tdata)
