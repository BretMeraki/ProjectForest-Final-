"""forest_app/modules/soft_deadline_manager.py

Assigns and manages *soft deadlines* for tasks, driven by the user’s
estimated completion date and journey path (structured, blended, open).

Rules
-----
- **Structured**: Deadlines are distributed **evenly** from *now* to the
  `estimated_completion_date`.
- **Blended**: Same even distribution **plus jitter** of ±20 % to feel
  like flexible guideposts.
- **Open**: **No deadlines** are attached.

The manager writes an ISO‑8601 `soft_deadline` string into each task
(dict) and returns the updated list.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Iterable

from forest_app.core.snapshot import MemorySnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime) -> str:
    """Return an ISO‑8601 string without microseconds."""
    return dt.replace(microsecond=0).isoformat() + "Z"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def schedule_soft_deadlines(
    snapshot: MemorySnapshot,
    tasks: Iterable[Dict[str, Any]],
    *,
    jitter_pct: float = 0.20,
    override_existing: bool = False,
) -> List[Dict[str, Any]]:
    """Assign `soft_deadline` fields to each task in *tasks*.

    Parameters
    ----------
    snapshot : MemorySnapshot
        Provides `current_path` and `estimated_completion_date`.
    tasks : iterable of task dicts
        Each task will be mutated in‑place.
    jitter_pct : float, optional
        Fractional jitter applied in **blended** mode (±20 % default).
    override_existing : bool, optional
        If False (default), tasks that already have `soft_deadline` are
        left untouched.

    Returns
    -------
    list of dict
        Reference to the same task dicts, updated.
    """
    path = getattr(snapshot, "current_path", "structured").lower()
    if path == "open":
        # Ensure no lingering deadlines
        for t in tasks:
            t.pop("soft_deadline", None)
        return list(tasks)

    # Guard: we need an estimated completion date to schedule deadlines.
    if not snapshot.estimated_completion_date:
        raise ValueError(
            "Snapshot missing `estimated_completion_date`; cannot generate soft deadlines."
        )

    end_dt = datetime.fromisoformat(snapshot.estimated_completion_date)
    now = datetime.utcnow()
    if end_dt <= now:
        # Fallback: push end date one week ahead to avoid zero/negative span.
        end_dt = now + timedelta(days=7)

    total_span_sec = (end_dt - now).total_seconds()
    num_tasks = len(list(tasks))
    if num_tasks == 0:
        return list(tasks)

    even_step = total_span_sec / num_tasks

    updated = []
    for idx, task in enumerate(tasks, start=1):
        if not override_existing and task.get("soft_deadline"):
            updated.append(task)
            continue

        # Base offset
        offset_sec = even_step * idx

        # Jitter for blended path
        if path == "blended":
            jitter_range = even_step * jitter_pct
            offset_sec += random.uniform(-jitter_range, jitter_range)
            # Clamp within [0, total_span]
            offset_sec = max(min(offset_sec, total_span_sec), 0)

        deadline_dt = now + timedelta(seconds=offset_sec)
        task["soft_deadline"] = _iso(deadline_dt)
        updated.append(task)

    return updated


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


def schedule_backlog(snapshot: MemorySnapshot, *, override_existing=False) -> None:
    """Assign deadlines to *all* tasks currently in `snapshot.task_backlog`."""
    if not hasattr(snapshot, "task_backlog"):
        return
    schedule_soft_deadlines(
        snapshot, snapshot.task_backlog, override_existing=override_existing
    )


def hours_until_deadline(task: Dict[str, Any]) -> float:
    """Return hours until this task’s soft deadline (or float('inf') if none)."""
    sd = task.get("soft_deadline")
    if not sd:
        return float("inf")
    try:
        return max(
            (datetime.fromisoformat(sd.rstrip("Z")) - datetime.utcnow()).total_seconds()
            / 3600,
            0.0,
        )
    except Exception:
        return float("inf")
