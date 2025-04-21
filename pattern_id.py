# forest_app/modules/pattern_id.py

import logging
import re
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

# Consider adding stop-word list or using a library if available later
# from nltk.corpus import stopwords # Example
# STOP_WORDS = set(stopwords.words('english'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PatternIdentificationEngine:
    """
    Analyzes historical snapshot data to identify recurring patterns, cycles,
    or potential triggers affecting the user's state.

    Refined to include:
    - Analysis of recurring keyword co-occurrence in reflections.
    - Task cycle detection potentially linked to HTA nodes.
    - Heuristic-based potential trigger identification correlating recent reflection
      keywords with current snapshot metrics.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initializes the engine. Config includes thresholds and lookback windows.
        """
        self.config = config or {
            "reflection_lookback": 10,
            "task_lookback": 20,
            "min_keyword_occurrence": 3,
            "min_cooccurrence": 2,  # Min times keywords must appear together
            "min_task_cycle_occurrence": 3,
            "high_shadow_threshold": 0.7,
            "low_capacity_threshold": 0.3,
            # Add more config like stop words, common task title patterns etc.
        }
        # Basic stop words (consider expanding or using a library)
        self.stop_words = set(
            [
                "a",
                "an",
                "the",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "it",
                "is",
                "was",
                "am",
                "are",
                "i",
                "me",
                "my",
                "myself",
                "we",
                "our",
                "ours",
                "ourselves",
                "you",
                "your",
                "yours",
                "yourself",
                "yourselves",
                "he",
                "him",
                "his",
                "himself",
                "she",
                "her",
                "hers",
                "herself",
                "it",
                "its",
                "itself",
                "they",
                "them",
                "their",
                "theirs",
                "themselves",
                "what",
                "which",
                "who",
                "whom",
                "this",
                "that",
                "these",
                "those",
                "am",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "having",
                "do",
                "does",
                "did",
                "doing",
                "a",
                "an",
                "the",
                "and",
                "but",
                "if",
                "or",
                "because",
                "as",
                "until",
                "while",
                "of",
                "at",
                "by",
                "for",
                "with",
                "about",
                "against",
                "between",
                "into",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "to",
                "from",
                "up",
                "down",
                "in",
                "out",
                "on",
                "off",
                "over",
                "under",
                "again",
                "further",
                "then",
                "once",
                "here",
                "there",
                "when",
                "where",
                "why",
                "how",
                "all",
                "any",
                "both",
                "each",
                "few",
                "more",
                "most",
                "other",
                "some",
                "such",
                "no",
                "nor",
                "not",
                "only",
                "own",
                "same",
                "so",
                "than",
                "too",
                "very",
                "s",
                "t",
                "can",
                "will",
                "just",
                "don",
                "should",
                "now",
                "d",
                "ll",
                "m",
                "o",
                "re",
                "ve",
                "y",
                "ain",
                "aren",
                "couldn",
                "didn",
                "doesn",
                "hadn",
                "hasn",
                "haven",
                "isn",
                "ma",
                "mightn",
                "mustn",
                "needn",
                "shan",
                "shouldn",
                "wasn",
                "weren",
                "won",
                "wouldn",
                "feel",
                "think",
                "get",
                "go",
                "make",
                "know",
                "try",
                "really",
                "want",
                "need",
                "like",
                "day",
                "time",
                "work",
                "going",
                "still",
                "even",
                "much",
                "bit",
                "today",
                "yesterday",
                "week",
            ]
        )
        logger.info(
            "PatternIdentificationEngine initialized with config: %s", self.config
        )

    def _extract_keywords(self, text: str, num_keywords: int = 7) -> List[str]:
        """Extracts keywords based on frequency, excluding stop words and short words."""
        if not isinstance(text, str):
            return []
        words = re.findall(r"\b\w{3,}\b", text.lower())  # Find words of 3+ chars
        filtered_words = [word for word in words if word not in self.stop_words]
        word_counts = Counter(filtered_words)
        # Return the most common keywords meeting a minimum count maybe?
        return [word for word, count in word_counts.most_common(num_keywords)]

    def analyze_snapshot(self, snapshot_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes snapshot data for patterns.

        Args:
            snapshot_dict: Dictionary representation of MemorySnapshot.
                           Assumes reflection_log contains entries with 'input'.
                           Assumes task_backlog contains task dicts with 'status',
                           'title'/'theme', and potentially 'linked_hta_node_id'.

        Returns:
            Dictionary summarizing detected patterns.
        """
        logger.info("Starting pattern analysis on snapshot.")
        detected_patterns = {
            "recurring_reflection_keywords": [],
            "recurring_keyword_pairs": [],
            "potential_task_cycles": [],
            "potential_triggers": [],
        }
        all_keywords_flat = []  # Store all keywords for trigger analysis later

        # --- 1. Analyze Reflection Log ---
        try:
            reflection_log = snapshot_dict.get("reflection_log", [])
            recent_reflections = reflection_log[-self.config["reflection_lookback"] :]
            recent_reflection_keywords_sets = [
                set(self._extract_keywords(entry.get("input", ""), num_keywords=10))
                for entry in recent_reflections
                if entry.get("input")
            ]

            if recent_reflection_keywords_sets:
                # Find recurring individual keywords
                all_keywords_flat = [
                    kw for kw_set in recent_reflection_keywords_sets for kw in kw_set
                ]
                keyword_counts = Counter(all_keywords_flat)
                min_occurrence = self.config["min_keyword_occurrence"]
                recurring_kws = [
                    kw
                    for kw, count in keyword_counts.items()
                    if count >= min_occurrence
                ]
                # Sort for consistency
                detected_patterns["recurring_reflection_keywords"] = sorted(
                    recurring_kws
                )
                if recurring_kws:
                    logger.info(
                        f"Detected recurring reflection keywords: {recurring_kws}"
                    )

                # Find recurring co-occurring keyword pairs
                pair_counts = Counter()
                for kw_set in recent_reflection_keywords_sets:
                    # Create sorted pairs to count ('a','b') the same as ('b','a')
                    # Ensure kw1 != kw2 implicitly by list slicing start index
                    pairs = {
                        tuple(sorted((kw1, kw2)))
                        for i, kw1 in enumerate(list(kw_set))
                        for kw2 in list(kw_set)[i + 1 :]
                    }
                    pair_counts.update(pairs)

                min_cooccurrence = self.config["min_cooccurrence"]
                # Sort pairs for consistent output
                recurring_pairs = sorted(
                    [
                        list(pair)
                        for pair, count in pair_counts.items()
                        if count >= min_cooccurrence
                    ]
                )
                detected_patterns["recurring_keyword_pairs"] = recurring_pairs
                if recurring_pairs:
                    logger.info(f"Detected recurring keyword pairs: {recurring_pairs}")

                # --- Placeholder: Sentiment Trend Analysis ---
                # If reflection logs included sentiment scores, analyze trend here.
                # Example: Calculate slope of sentiment over recent_reflections.
                # if sentiment_trend < -0.1: # Example threshold for worsening trend
                #     detected_patterns["sentiment_trend"] = "worsening"

        except Exception as e:
            logger.exception(
                f"Error analyzing reflection log patterns: {e}"
            )  # Use exception logging

        # --- 2. Analyze Task Backlog/History for Cycles ---
        try:
            task_backlog = snapshot_dict.get("task_backlog", [])
            # Ensure tasks are dictionaries before proceeding
            recent_tasks = [
                task
                for task in task_backlog[-self.config["task_lookback"] :]
                if isinstance(task, dict)
            ]

            task_patterns = defaultdict(
                lambda: {"skipped": 0, "failed": 0, "overdue": 0, "count": 0}
            )

            for task in recent_tasks:
                # Prioritize HTA Node ID for grouping, fallback to theme
                hta_node_id = task.get(
                    "linked_hta_node_id"
                )  # Assumes this key might exist
                key = (
                    f"hta_node:{hta_node_id}"
                    if hta_node_id
                    else f"theme:{task.get('theme', 'Unknown').lower()}"
                )
                task_patterns[key]["count"] += 1

                status_lower = task.get("status", "").lower()
                if status_lower == "skipped":
                    task_patterns[key]["skipped"] += 1
                elif status_lower == "failed":  # Assuming 'failed' status exists
                    task_patterns[key]["failed"] += 1

                # Check overdue flag set by orchestrator's deadline monitoring
                if task.get("overdue", False):
                    task_patterns[key]["overdue"] += 1

            min_cycle = self.config["min_task_cycle_occurrence"]
            for key, counts in task_patterns.items():
                # Flag if a significant portion of tasks for a key are skipped/failed/overdue
                if counts["skipped"] >= min_cycle:
                    detected_patterns["potential_task_cycles"].append(
                        {"pattern": f"Skipped {key}", "count": counts["skipped"]}
                    )
                if counts["failed"] >= min_cycle:
                    detected_patterns["potential_task_cycles"].append(
                        {"pattern": f"Failed {key}", "count": counts["failed"]}
                    )
                if counts["overdue"] >= min_cycle:
                    detected_patterns["potential_task_cycles"].append(
                        {"pattern": f"Overdue {key}", "count": counts["overdue"]}
                    )

            # Sort for consistency
            detected_patterns["potential_task_cycles"].sort(
                key=lambda x: x.get("pattern")
            )

            if detected_patterns["potential_task_cycles"]:
                logger.info(
                    f"Detected potential task cycles: {detected_patterns['potential_task_cycles']}"
                )
        except Exception as e:
            logger.exception(
                f"Error analyzing task log patterns: {e}"
            )  # Use exception logging

        # --- 3. Analyze Current State for Potential Triggers ---
        # Limited by only having current snapshot; ideally uses historical logs/metrics.
        try:
            shadow_score = snapshot_dict.get("shadow_score", 0.5)
            capacity = snapshot_dict.get("capacity", 0.5)
            # Use keywords from *all* recent reflections analyzed earlier
            recent_keywords_flat_set = set(all_keywords_flat)

            high_shadow_threshold = self.config["high_shadow_threshold"]
            low_capacity_threshold = self.config["low_capacity_threshold"]

            # Example: High shadow potentially linked to recurring stressor keywords
            if shadow_score > high_shadow_threshold:
                stress_keywords = {
                    "deadline",
                    "conflict",
                    "argument",
                    "pressure",
                    "overwhelm",
                    "anxiety",
                    "stress",
                    "failure",
                }
                found_stressors = recent_keywords_flat_set.intersection(stress_keywords)
                if found_stressors:
                    detected_patterns["potential_triggers"].append(
                        f"High shadow ({shadow_score:.2f}) potentially linked to recent mentions of: {sorted(list(found_stressors))}"
                    )

            # Example: Low capacity potentially linked to recurring fatigue keywords
            if capacity < low_capacity_threshold:
                fatigue_keywords = {
                    "tired",
                    "exhausted",
                    "burnout",
                    "drained",
                    "overwhelmed",
                }
                found_fatigue = recent_keywords_flat_set.intersection(fatigue_keywords)
                if found_fatigue:
                    detected_patterns["potential_triggers"].append(
                        f"Low capacity ({capacity:.2f}) potentially linked to recent mentions of: {sorted(list(found_fatigue))}"
                    )

            # Example: Link task cycles to current state
            if detected_patterns["potential_task_cycles"]:
                if shadow_score > high_shadow_threshold:
                    detected_patterns["potential_triggers"].append(
                        f"Task cycles detected while shadow score is high ({shadow_score:.2f}). Consider addressing shadow."
                    )
                if capacity < low_capacity_threshold:
                    detected_patterns["potential_triggers"].append(
                        f"Task cycles detected while capacity is low ({capacity:.2f}). Consider simpler tasks or rest."
                    )

            # --- Placeholder: Correlation with Logged Metrics ---
            # if TaskEventLog/ReflectionEventLog data with metrics were available,
            # more robust correlations could be calculated here.
            # Example: Check if 'skipped' task events correlate with low 'capacity_at_event'.

            # Sort for consistency
            detected_patterns["potential_triggers"].sort()

            if detected_patterns["potential_triggers"]:
                logger.info(
                    f"Detected potential triggers based on current state/recent reflections: {detected_patterns['potential_triggers']}"
                )
        except Exception as e:
            logger.exception(
                f"Error analyzing potential triggers: {e}"
            )  # Use exception logging

        logger.info(
            "Pattern analysis complete. Detected patterns: %s", detected_patterns
        )
        return detected_patterns

    def to_dict(self) -> dict:
        """Serializes the engine's configuration."""
        return {"config": self.config}

    def update_from_dict(self, data: dict):
        """Updates the engine's configuration from a dictionary."""
        if "config" in data:
            config_update = data.get("config", {})
            if isinstance(config_update, dict):
                # Use update for nested dicts if necessary, or just replace
                self.config.update(config_update)
            else:
                logger.warning(
                    "Invalid format for config update in PatternIdentificationEngine."
                )
