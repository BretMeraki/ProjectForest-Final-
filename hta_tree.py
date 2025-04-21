#############################################
# File: forest_app/modules/hta_tree.py
#############################################

import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Define a simple RESOURCE_MAP for resource filtering thresholds.
RESOURCE_MAP = {"low": 0.3, "medium": 0.6, "high": 0.9}


class HTANode:
    """
    Represents a node in a Hierarchical Task Analysis (HTA) tree.

    Attributes:
        id: Unique identifier for the node.
        title: The title or short description of the HTA step.
        description: Longer explanation of what this step involves.
        status: Current status, e.g., "pending", "active", "completed", or "pruned".
        priority: A numerical value indicating importance (higher means more important).
        depends_on: A list of IDs of nodes that must be completed before this one.
        estimated_energy: A string (e.g., "low", "medium", "high") representing energy cost.
        estimated_time: A string (e.g., "low", "medium", "high") representing time cost.
        children: A list of child HTANode objects.
        linked_tasks: A list of task IDs linked to this node.
    """

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        priority: float,
        depends_on: Optional[List[str]] = None,
        estimated_energy: str = "medium",
        estimated_time: str = "medium",
        children: Optional[List["HTANode"]] = None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.status = "pending"  # Default status.
        self.priority = priority
        self.depends_on = depends_on if depends_on is not None else []
        self.estimated_energy = estimated_energy
        self.estimated_time = estimated_time
        self.children = children if children is not None else []
        self.linked_tasks: List[str] = []

    def link_task(self, task_id: str):
        """Links a task ID with this node."""
        if task_id not in self.linked_tasks:
            self.linked_tasks.append(task_id)
            logger.info("Linked task '%s' to HTA node '%s'.", task_id, self.title)

    def update_status(self, new_status: str):
        """Update the status of this node and (optionally) trigger propagation."""
        old_status = self.status
        self.status = new_status
        logger.info(
            "HTA node '%s' status changed from '%s' to '%s'.",
            self.title,
            old_status,
            new_status,
        )

    def mark_completed(self):
        """Marks this node as completed."""
        self.update_status("completed")

    def propagate_status(self):
        """
        Propagate status changes upward within the tree.
        If all children of this node are completed or pruned, mark this node as completed.
        (Requires external invocation by HTATree.)
        """
        logger.info("Propagating status for HTA node '%s'.", self.title)
        # Placeholder for actual propagation logic; HTATree.propagate_status handles full tree.

    def adjust_priority_by_context(self, context: dict):
        """
        Dynamically adjust node priority based on context.
        For example, if the user's capacity is high, increase this node's priority.
        """
        capacity = context.get("capacity", 0.5)
        old_priority = self.priority
        # A simple heuristic: increase by a factor proportional to (capacity - 0.5)
        self.priority *= 1 + (capacity - 0.5)
        logger.info(
            "Adjusted priority for node '%s' from %.2f to %.2f based on capacity %.2f",
            self.title,
            old_priority,
            self.priority,
            capacity,
        )

    def prune_if_unnecessary(self, condition: bool):
        """
        Mark this node as pruned if the provided condition is true.
        """
        if condition:
            old_status = self.status
            self.status = "pruned"
            logger.info(
                "Node '%s' pruned: status changed from '%s' to 'pruned'.",
                self.title,
                old_status,
            )

    def dependencies_met(self, node_map: Dict[str, "HTANode"]) -> bool:
        """
        Checks whether this node's dependencies are met.
        """
        for dep_id in self.depends_on:
            dep_node = node_map.get(dep_id)
            if dep_node is None or dep_node.status.lower() != "completed":
                logger.info(
                    "Dependencies for node '%s' not met: Dependency '%s' has status '%s'.",
                    self.title,
                    dep_id,
                    dep_node.status if dep_node else "Not Found",
                )
                return False
        return True

    def to_dict(self) -> dict:
        """Serializes the HTANode to a dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "estimated_energy": self.estimated_energy,
            "estimated_time": self.estimated_time,
            "children": [child.to_dict() for child in self.children],
            "linked_tasks": self.linked_tasks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HTANode":
        """Reconstructs an HTANode from a dictionary."""
        children_data = data.get("children", [])
        children = [cls.from_dict(child_data) for child_data in children_data]
        node = cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", 0),
            depends_on=data.get("depends_on", []),
            estimated_energy=data.get("estimated_energy", "medium"),
            estimated_time=data.get("estimated_time", "medium"),
            children=children,
        )
        node.status = data.get("status", "pending")
        node.linked_tasks = data.get("linked_tasks", [])
        return node


class HTATree:
    """
    Represents the entire HTA tree, centered on a root node.
    """

    def __init__(self, root: Optional[HTANode] = None):
        self.root = root

    def to_dict(self) -> dict:
        """Serializes the HTATree to a dictionary."""
        return {"root": self.root.to_dict() if self.root else {}}

    @classmethod
    def from_dict(cls, data: dict) -> "HTATree":
        """Reconstructs the HTATree from a dictionary; expects a 'root' key."""
        root_data = data.get("root", {})
        root_node = HTANode.from_dict(root_data) if root_data else None
        return cls(root=root_node)

    def flatten(self) -> List[HTANode]:
        """Flattens the tree to a list of all HTANode objects."""
        if not self.root:
            return []

        def _flatten(node: HTANode) -> List[HTANode]:
            nodes = [node]
            for child in node.children:
                nodes.extend(_flatten(child))
            return nodes

        return _flatten(self.root)

    def propagate_status(self):
        """
        Recursively propagates status upward: if all children of a node
        are completed or pruned, mark the node as completed.
        """
        if not self.root:
            return

        def _propagate(node: HTANode) -> bool:
            if not node.children:
                return node.status.lower() in ["completed", "pruned"]
            all_done = all(_propagate(child) for child in node.children)
            if all_done and node.status.lower() not in ["completed", "pruned"]:
                old = node.status
                node.status = "completed"
                logger.info(
                    "Propagated status: Node '%s' changed from '%s' to 'completed'.",
                    node.title,
                    old,
                )
            return node.status.lower() in ["completed", "pruned"]

        _propagate(self.root)

    def find_node_by_id(self, node_id: str) -> Optional[HTANode]:
        """
        Searches the tree for a node with the given id.
        """
        if not self.root:
            return None

        def _find(node: HTANode) -> Optional[HTANode]:
            if node.id == node_id:
                return node
            for child in node.children:
                found = _find(child)
                if found:
                    return found
            return None

        return _find(self.root)

    def add_node(self, parent_id: str, new_node: HTANode) -> bool:
        """
        Adds a new node as a child to the node with the given parent_id.
        """
        parent = self.find_node_by_id(parent_id)
        if parent:
            parent.children.append(new_node)
            logger.info(
                "Added node '%s' as a child of '%s'.", new_node.title, parent.title
            )
            return True
        logger.warning("Parent node with id '%s' not found.", parent_id)
        return False

    def remove_node(self, node_id: str) -> bool:
        """
        Removes the node with the specified id from the tree.
        """
        if not self.root or self.root.id == node_id:
            logger.warning("Cannot remove the root node or tree is empty.")
            return False

        def _remove(parent: HTANode, target_id: str) -> bool:
            for idx, child in enumerate(parent.children):
                if child.id == target_id:
                    del parent.children[idx]
                    logger.info(
                        "Removed node with id '%s' from parent '%s'.",
                        target_id,
                        parent.title,
                    )
                    return True
                if _remove(child, target_id):
                    return True
            return False

        return _remove(self.root, node_id)


#############################################
# End of hta_tree.py
#############################################
