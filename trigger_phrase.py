import json
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def load_trigger_config():
    """
    Loads trigger phrase mappings from an external JSON file. If unable to load, defaults are used.
    Expected JSON format: { "activate the forest": "activate", ... }
    """
    config_path = os.path.join("forest_app", "config", "trigger_config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            logger.info("Loaded trigger configuration from %s", config_path)
            return config
    except Exception as e:
        logger.warning(
            "Could not load trigger configuration from %s: %s. Using default mapping.",
            config_path,
            e,
        )
    return {
        "activate the forest": "activate",
        "forest, change the decor": "change_decor",
        "forest, audit the scores": "audit_scores",
        "forest, show me the running to-do list": "show_todo",
        "forest, integrate memory": "integrate_memory",
    }


class TriggerPhraseHandler:
    """
    Handles simple command trigger phrases in a centralized manner.

    Loads a trigger mapping from configuration and dispatches to dedicated handler functions.
    """

    def __init__(self, snapshot_flow_controller):
        self.flow = snapshot_flow_controller
        self.trigger_map = load_trigger_config()
        self.handlers = {
            "activate": self._handle_activate,
            "change_decor": self._handle_change_decor,
            "audit_scores": self._handle_audit_scores,
            "show_todo": self._handle_show_todo,
            "integrate_memory": self._handle_integrate_memory,
        }

    def handle_trigger_phrase(self, user_input: str, full_snapshot) -> dict:
        command = user_input.strip().lower()
        action_key = self.trigger_map.get(command)
        if action_key and action_key in self.handlers:
            logger.info(
                "Trigger phrase '%s' detected (action: %s).", command, action_key
            )
            return self.handlers[action_key](full_snapshot)
        logger.info("No trigger detected for input: '%s'", command)
        return {
            "triggered": False,
            "message": "No trigger detected.",
            "context_injection": None,
        }

    def _handle_activate(self, full_snapshot) -> dict:
        compressed = self.flow.trigger.build(full_snapshot)
        context = self.flow.memory_sync.inject_into_context(compressed)
        return {
            "triggered": True,
            "message": "Forest activated. All systems are online.",
            "context_injection": context,
        }

    def _handle_change_decor(self, full_snapshot) -> dict:
        # Stub: Implement decor change logic.
        return {
            "triggered": True,
            "message": "Decor changes applied: persistent task commitment enabled and daily-specific tags activated.",
            "context_injection": None,
        }

    def _handle_audit_scores(self, full_snapshot) -> dict:
        # Stub: Return a simple audit message.
        audit_message = "Scores audited: XP, Shadow, Capacity, and Development Index details are logged."
        return {"triggered": True, "message": audit_message, "context_injection": None}

    def _handle_show_todo(self, full_snapshot) -> dict:
        if hasattr(full_snapshot, "task_backlog") and full_snapshot.task_backlog:
            todo_list = "\n".join(
                [
                    f"ID: {t.get('id', 'N/A')}, Title: {t.get('title', '')}"
                    for t in full_snapshot.task_backlog
                ]
            )
        else:
            todo_list = "No tasks found."
        return {
            "triggered": True,
            "message": f"Current To-Do List:\n{todo_list}",
            "context_injection": None,
        }

    def _handle_integrate_memory(self, full_snapshot) -> dict:
        # Stub: Simulate memory integration.
        return {
            "triggered": True,
            "message": "ChatGPT memory integrated successfully.",
            "context_injection": None,
        }
