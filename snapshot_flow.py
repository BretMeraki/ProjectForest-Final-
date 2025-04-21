import json
import logging
from datetime import datetime
from collections import deque
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def load_snapshot_config():
    """
    Load snapshot configuration from an external JSON file.
    If the file is not found or an error occurs, return default configuration.
    """
    config_path = os.path.join("forest_app", "config", "snapshot_config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            logger.info("Loaded snapshot configuration from %s", config_path)
            return config
    except FileNotFoundError as fnf_error:
        logger.warning(
            "Snapshot config file not found at %s: %s. Using default config.",
            config_path,
            fnf_error,
        )
    except Exception as e:
        logger.warning(
            "Error loading snapshot config from %s: %s. Using default config.",
            config_path,
            e,
        )
    return {
        "fields": [
            "xp",
            "shadow_score",
            "capacity",
            "magnitude",
            "top_tags",
            "development_indexes",
            "last_ritual_mode",
        ]
    }


class CallbackTrigger:
    """
    Monitors the number of interactions and triggers a snapshot build once the counter
    reaches a preset frequency.
    """

    def __init__(self, frequency: int = 5):
        self.counter = 0
        self.frequency = frequency
        self.last_snapshot = None

    def register_interaction(self, full_snapshot) -> dict:
        self.counter += 1
        if self.counter >= self.frequency:
            self.counter = 0
            builder = CompressedSnapshotBuilder()
            self.last_snapshot = builder.build(full_snapshot)
            logger.info("Snapshot triggered: %s", self.last_snapshot)
            return self.last_snapshot
        return None

    def force_trigger(self, full_snapshot) -> dict:
        self.counter = 0
        builder = CompressedSnapshotBuilder()
        self.last_snapshot = builder.build(full_snapshot)
        logger.info("Forced snapshot: %s", self.last_snapshot)
        return self.last_snapshot

    def get_last_snapshot(self) -> dict:
        return self.last_snapshot


class SnapshotRotatingSaver:
    """
    Maintains a rolling backup of compressed snapshots in a deque.
    Intended for short-term (in-memory or file-based) backup; distinct from SQLSnapshotSaver.
    """

    def __init__(self, max_snapshots: int = 10):
        self.snapshots = deque(maxlen=max_snapshots)

    def store_snapshot(self, snapshot: dict):
        record = {"timestamp": datetime.utcnow().isoformat(), "snapshot": snapshot}
        self.snapshots.append(record)
        logger.info("Snapshot stored at %s", record["timestamp"])

    def get_latest(self) -> dict:
        return self.snapshots[-1] if self.snapshots else None

    def get_all(self) -> list:
        return list(self.snapshots)

    def export_to_json(self, filepath: str):
        try:
            with open(filepath, "w") as f:
                json.dump(self.get_all(), f, indent=2)
            logger.info("Snapshots exported to %s", filepath)
        except FileNotFoundError as fnf_error:
            logger.error(
                "File not found during export (check '%s'): %s", filepath, fnf_error
            )
        except IOError as io_error:
            logger.error("I/O error during export: %s", io_error)
        except Exception as e:
            logger.error("Unexpected error during export: %s", e)

    def load_from_json(self, filepath: str):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                self.snapshots = deque(data, maxlen=self.snapshots.maxlen)
            logger.info("Snapshots loaded from %s", filepath)
        except FileNotFoundError as fnf_error:
            logger.error(
                "File not found during load (check '%s'): %s", filepath, fnf_error
            )
        except IOError as io_error:
            logger.error("I/O error during load: %s", io_error)
        except Exception as e:
            logger.error("Unexpected error during load: %s", e)


class GPTMemorySync:
    """
    Packages a compressed snapshot into a succinct context string suitable for injection into LLM prompts.
    """

    def __init__(self):
        self.synced_snapshot = None

    def inject_into_context(self, compressed_snapshot: dict) -> str:
        if not compressed_snapshot:
            return "No memory state available."
        context_lines = [
            f"XP: {compressed_snapshot.get('xp')}",
            f"Shadow Score: {compressed_snapshot.get('shadow_score')}",
            f"Capacity: {compressed_snapshot.get('capacity')}",
            f"Magnitude: {compressed_snapshot.get('magnitude')}",
            f"Top Tags: {', '.join(compressed_snapshot.get('top_tags', []))}",
            f"Development Indexes: {json.dumps(compressed_snapshot.get('development_indexes', {}))}",
            f"Last Ritual Mode: {compressed_snapshot.get('last_ritual_mode')}",
        ]
        self.synced_snapshot = compressed_snapshot
        context_string = "\n".join(context_lines)
        logger.info("Injected snapshot context for LLM:\n%s", context_string)
        return context_string


class CompressedSnapshotBuilder:
    """
    Compresses the full MemorySnapshot into a dictionary containing only essential fields.
    The included fields can later be tuned based on prompt testing and configuration.
    """

    def __init__(self):
        self.config = load_snapshot_config()

    def build(self, full_snapshot) -> dict:
        top_tags = (
            sorted(full_snapshot.active_tags.items(), key=lambda x: x[1], reverse=True)
            if hasattr(full_snapshot, "active_tags")
            else []
        )
        compressed = {
            "xp": full_snapshot.xp,
            "shadow_score": full_snapshot.shadow_score,
            "capacity": full_snapshot.capacity,
            "magnitude": full_snapshot.magnitude,
            "current_seed": (
                full_snapshot.seed_manager.to_dict()[0]
                if full_snapshot.seed_manager.to_dict()
                else {"name": "None", "status": "inactive"}
            ),
            "top_tags": [tag for tag, _ in top_tags[:3]] if top_tags else [],
            "development_indexes": full_snapshot.dev_index.to_dict(),
            "last_ritual_mode": full_snapshot.last_ritual_mode,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info("Compressed snapshot built: %s", compressed)
        return compressed


class SnapshotFlowController:
    """
    Coordinates snapshot operations: registering interactions, triggering snapshots,
    storing backups via SnapshotRotatingSaver, and injecting context via GPTMemorySync.
    """

    def __init__(self, frequency: int = 5, max_snapshots: int = 10):
        self.trigger = CallbackTrigger(frequency=frequency)
        self.saver = SnapshotRotatingSaver(max_snapshots=max_snapshots)
        self.memory_sync = GPTMemorySync()

    def register_user_submission(self, full_snapshot) -> dict:
        self.trigger.register_interaction(full_snapshot)
        compressed = self.trigger.get_last_snapshot()
        if compressed:
            self.saver.store_snapshot(compressed)
            context_string = self.memory_sync.inject_into_context(compressed)
            return {
                "synced": True,
                "context_injection": context_string,
                "compressed_snapshot": compressed,
            }
        return {"synced": False, "context_injection": None, "compressed_snapshot": None}

    def get_latest_context(self) -> str:
        latest = self.saver.get_latest()
        if latest:
            return self.memory_sync.inject_into_context(latest["snapshot"])
        return "No recent snapshot available."
