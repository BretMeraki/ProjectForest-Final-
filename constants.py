# forest_app/config/constants.py

"""
Centralized configuration of all quantitative and qualitative parameters
used throughout Forest OS.
"""

import os

# ━━━━━━━━━━━━━━━━━━━━━━━━━━ PATH & ENV CONFIG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "sqlite:///./forest.db"
)
# RATIONALE: Allow easy override for different environments.

ARCHETYPES_FILE = os.getenv(
    "ARCHETYPES_FILE",
    os.path.join(os.path.dirname(__file__), "archetypes.json")
)
# RATIONALE: Centralizes path to archetype definitions.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ PATH DEFINITIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCHEDULER_PATHS = ("structured", "blended", "open")
# RATIONALE: Keys for deadline scheduling modes.

WITHERING_PATHS  = ("structured", "blended", "open")
# RATIONALE: Same modes govern withering logic for consistency.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ DEADLINE SCHEDULING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JITTER_PCT_DEFAULT     = 0.20
# RATIONALE: 20% timing variation keeps deadlines flexible yet meaningful.

DEADLINE_FALLBACK_DAYS = 7
# RATIONALE: One-week default planning horizon when none specified.

SECONDS_PER_HOUR       = 3600
# RATIONALE: Standard conversion factor.

# ━━━━━━━━━━━━━━━━━━━━━━━━━ SNAPSHOT DEFAULTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEFAULT_INITIAL_SHADOW_SCORE       = 0.50
# RATIONALE: Neutral midpoint, to be adjusted via NLP reflection.

DEFAULT_INITIAL_CAPACITY           = 0.50
# RATIONALE: Starts users in a balanced resource state.

DEFAULT_INITIAL_MAGNITUDE          = 5.00
# RATIONALE: Midpoint on a 1–10 scale before any real inputs.

DEFAULT_INITIAL_RELATIONSHIP_INDEX = 0.50
# RATIONALE: Balanced relational health as a starting point.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━ WITHERING / ENGAGEMENT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WITHERING_IDLE_COEFF = {
    "structured": 0.025,  # ~2.5% per‑day decay for structured users.
    "blended":   0.015,   # Gentler decay for blended mode.
    "open":      0.0,     # No decay for freeform mode.
}
WITHERING_OVERDUE_COEFF = {
    "structured": 0.012,  # 1.2% per‑day penalty for missed deadlines.
    "blended":   0.005,   # Reduced pressure in blended.
}
WITHERING_DECAY_FACTOR      = 0.98
# RATIONALE: Prevent runaway penalty accumulation.

WITHERING_COMPLETION_RELIEF = 0.15
# RATIONALE: Completion reduces withering by 15%, rewarding action.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ XP & SCORING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
XP_BASE = {
    "Bud":     10,
    "Bloom":   20,
    "Blossom": 30,
}
# RATIONALE: Tiered rewards scale with task complexity.

XP_SHADOW_BONUS_THRESHOLD      = 0.7
# RATIONALE: Incentivize tackling strong shadow aspects when shadow_score > 70%.

XP_SHADOW_BONUS                = 5
# RATIONALE: Modest bonus to reinforce challenging emotional tasks.

XP_MASTERY_PROXIMITY_THRESHOLD = 10
# RATIONALE: Trigger mastery activities near level‑up XP.

# ━━━━━━━━━━━━━━━━━━━━━━━━━ REFLECTION NUDGES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFLECTION_CAPACITY_NUDGE_BASE = 0.05
REFLECTION_SHADOW_NUDGE_BASE   = 0.05
# RATIONALE: 5% per‑reflection capacity boost and shadow reduction.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━ HARMONIC & MAGNITUDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAGNITUDE_MIN_VALUE               = 1.0
# RATIONALE: Minimum possible magnitude.

MAGNITUDE_MAX_VALUE               = 10.0
# RATIONALE: Maximum possible magnitude.

MAGNITUDE_NEUTRAL_VALUE           = 5.0
# RATIONALE: Midpoint for default/fallback use.

TASK_TIER_BASE_MAGNITUDE = {
    "Bud":     2.0,
    "Bloom":   5.0,
    "Blossom": 9.0,
}
# RATIONALE: Base difficulty per task tier.

TASK_MAGNITUDE_DEPTH_WEIGHT   = 1.0
# RATIONALE: Weight for normalized HTA depth (max adds +1.0).

TASK_DEFAULT_MAGNITUDE        = MAGNITUDE_NEUTRAL_VALUE
# RATIONALE: Fallback if no tier mapping exists.

MAG_COMPLETION_SMOOTHING_ALPHA   = 0.3
# RATIONALE: Blend 30% of task magnitude into user magnitude on completion.

HIGH_MAGNITUDE_THRESHOLD         = 9.0
# RATIONALE: Above this, tasks are “seismic” and merit extra boost.

HIGH_MAG_COMPLETION_BOOST        = 0.5
# RATIONALE: Extra magnitude added when completing high‑mag tasks.

LLM_AMBITION_MAGNITUDE_THRESHOLD = 8.0
# RATIONALE: Above this, LLM prompts should request boundary‑pushing tasks.

HTA_MAX_DEPTH_FOR_MAG_NORM = 5
# RATIONALE: Maximum HTA depth considered for normalizing magnitude contribution.

MAGNITUDE_THRESHOLDS = {
    "Seismic": 9.0,
    "Profound": 7.0,
    "Rising": 5.0,
    "Subtle": 3.0,
    "Dormant": 1.0  # Threshold for the lowest level
}
# RATIONALE: Thresholds for describing magnitude levels used in Orchestrator.

# ━━━━━━━━━━━━━━━━━━━━━━━━━ MODULE-SPECIFIC PARAMETERS ━━━━━━━━━━━━━━━━━━━━━━━━
DEV_INDEX_BASE_BOOST_FACTOR          = 0.02
# RATIONALE: 2% per‑task progress for development indices.

# --- Added/Verified constants needed by TaskEngine ---
# NOTE: Check if task_engine.py should import DEV_INDEX_BASE_BOOST_FACTOR instead of this PRIORITY version.
DEV_INDEX_PRIORITY_BOOST = 0.1  # Placeholder: Boost for tasks targeting low dev index dimensions
PATTERN_PRIORITY_BOOST = 0.1   # Placeholder: Boost for tasks addressing identified patterns
REFLECTION_PRIORITY_BOOST = 0.05 # Placeholder: Boost based on recent reflection intensity
# --- End Added/Verified ---


ARCHETYPE_CARETAKER_BOOST_LOW_CAP_THRESHOLD  = 0.4
# RATIONALE: Boost “Caretaker” archetype below 40% capacity.

ARCHETYPE_HEALER_BOOST_HIGH_SHADOW_THRESHOLD = 0.7
# RATIONALE: Boost “Healer” archetype above 70% shadow.

NARRATIVE_GENTLE_SAFETY_LOW_CAP_TRIGGER      = 0.2
# RATIONALE: Trigger Gentle Safety narrative when capacity < 20%.

NARRATIVE_GENTLE_SAFETY_HIGH_SHADOW_TRIGGER  = 0.8
# RATIONALE: And shadow > 80%.

NARRATIVE_DIRECT_SUPPORT_HIGH_CONSEQUENCE_TRIGGER = 0.8
# RATIONALE: Trigger Direct Support narrative at high practical impact.

EMO_INTEGRITY_INITIAL_SCORE          = 5.0
EMO_INTEGRITY_SCALING_FACTOR         = 2.0
EMO_INTEGRITY_SCORE_RANGE            = (0.0, 10.0)
EMO_INTEGRITY_LLM_DELTA_RANGE        = (-0.5, 0.5)
# RATIONALE: Settings for Emotional Integrity Index.

METRICS_MOMENTUM_ALPHA               = 0.3
# RATIONALE: EWMA smoothing factor for momentum.

PRACTICAL_CONSEQUENCE_TONE_THRESHOLDS = {
    "High Impact":     0.8,
    "Moderate Impact": 0.6,
    "Low Impact":      0.4,
}
PRACTICAL_CONSEQUENCE_DEADLINE_PENALTY = 0.05
# RATIONALE: Tone buckets and penalty for consequences.

RELATIONAL_DEFAULT_CONNECTION_SCORE  = 5.0
RELATIONAL_CONNECTION_SCORE_RANGE    = (0.0, 10.0)
RELATIONAL_REPAIR_THRESHOLDS         = {
    "Cautious": 3.0,
    "Gentle":   7.0,
}
# RATIONALE: Defaults and thresholds for relational health.

OFFERING_DEFAULT_NUM_SUGGESTIONS     = 3
OFFERING_TOP_N_DESIRES               = 2
DESIRE_REINFORCEMENT_FACTOR          = 0.1
# RATIONALE: Parameters for reward/offering logic.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━ ENUMS & KEY LISTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE_EMOTIONAL_TAGS = (
    "Stillness", "Spark", "Courage", "Reset", "Joy", "Clarity",
    "Compassion", "Resilience", "Depth"
)
CORE_SHADOW_TAGS = (
    "Pride", "Arrogance", "Anger", "Impulsivity", "Self-Doubt"
)
# RATIONALE: Canonical tags for Sentiment & Shadow engines.

ALLOWED_TASK_STATUSES = (
    "pending", "active", "completed", "skipped", "failed", "pruned"
)
# RATIONALE: Valid task lifecycle states.

DEV_INDEX_KEYS = (
    "happiness", "career", "health", "financial", "relationship",
    "executive_functioning", "social_life", "charisma", "entrepreneurship",
    "family_planning", "generational_wealth", "adhd_risk", "odd_risk",
    "homeownership", "dream_location",
)
# RATIONALE: Growth dimensions tracked by the system.

ORCHESTRATOR_HEARTBEAT_SEC = int(os.getenv("ORCHESTRATOR_HEARTBEAT_SEC", "60"))
# RATIONALE: Interval for background heartbeat loop.