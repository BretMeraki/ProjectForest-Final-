# forest_app/core/orchestrator.py
# =============================================================================
#  ForestOrchestrator  –  unified version (2025‑04‑21)
#  * Includes invisible‑hand Magnitude / Resistance flow
#  * Soft‑deadline & Withering engagement maintenance
#  * Harmonic routing, narrative modes, reward loop, XP mastery
#  * Conversation History in Snapshot/Prompts
#  * Explicit Onboarding Flow (handled in main.py)
#  * Initial HTA Generation (handled in main.py)
#  * HTA Rebalancing on Task Completion (implemented here)
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any # Ensure List is imported

from sqlalchemy.orm import Session  # DB session for logging completions

# ─────────────────────────────── Forest sub‑modules ──────────────────────────
# Assuming these imports are correct based on your project structure
from forest_app.modules.sentiment import SecretSauceSentimentEngineHybrid
from forest_app.modules.practical_consequence import PracticalConsequenceEngine
from forest_app.modules.snapshot_flow import SnapshotFlowController
from forest_app.modules.task_engine import TaskEngine
from forest_app.modules.offering_reward import OfferingRouter
from forest_app.modules.reward_index import RewardIndex
from forest_app.modules.xp_mastery import XPMastery
from forest_app.modules.metrics_specific import MetricsSpecificEngine
from forest_app.modules.seed import SeedManager, Seed # Assuming Seed class is exported
from forest_app.modules.pattern_id import PatternIdentificationEngine
from forest_app.modules.relational import RelationalManager
from forest_app.modules.narrative_modes import NarrativeModesEngine
from forest_app.modules.emotional_integrity import EmotionalIntegrityIndex
from forest_app.modules.soft_deadline_manager import (
    hours_until_deadline,
    schedule_soft_deadlines,
)
from forest_app.modules.resistance_engine import clamp01
# --- ADDED: HTA Imports for Rebalancing ---
# ---

# Logging helpers & LLM Integration (with fallbacks)
try:
    # Assuming loggers and LLM tools are correctly located
    from forest_app.modules.logging_tracking import TaskFootprintLogger, ReflectionLogLogger
    from forest_app.integrations.llm import (
        generate_response,
        LLMResponseModel,
        SentimentResponseModel,
        LLMError,
        LLMResponseFormatError,
        LLMValidationError,
        LLMClientError,
        LLMServerError,
    )
    # --- ADDED: Import HTAResponseModel ---
    from forest_app.modules.hta_models import HTAResponseModel, HTANodeModel
    # ---
except ImportError as import_err:
    logger_init = logging.getLogger(__name__)
    logger_init.warning("Could not import some modules needed by Orchestrator. Using fallbacks. %s", import_err)
    # Define necessary dummy classes/functions if imports fail
    class LLMResponseModel: task: Dict[str, Any] = {}; narrative: str = "LLM offline."
    class SentimentResponseModel: pass
    class HTAResponseModel(BaseModel): hta_root: dict = {}
    class HTANodeModel: pass
    async def generate_response(prompt: str, response_model=None) -> Any:
        dummy = LLMResponseModel(); dummy.task = {"id": "fallback", "title": "Fallback"}; return dummy
    class LLMError(Exception): pass
    class LLMValidationError(LLMError): pass
    class TaskFootprintLogger:
        def __init__(self, db): pass
        def log_task_event(self, *args, **kwargs): pass
    class ReflectionLogLogger:
        def __init__(self, db): pass
        def log_reflection_event(self, *args, **kwargs): pass

# Harmonic framework (with fallback)
try:
    from forest_app.core.harmonic_framework import SilentScoring, HarmonicRouting
except ImportError:
    class SilentScoring:
        def compute_detailed_scores(self, *_): return {}
        def compute_composite_score(self, *_): return 0.0
    HarmonicRouting = None

# Constants import (with fallback)
try:
    from forest_app.config.constants import MAGNITUDE_THRESHOLDS
except ImportError:
     logging.getLogger(__name__).error("MAGNITUDE_THRESHOLDS not found in constants.py! Using fallback.")
     MAGNITUDE_THRESHOLDS = {"Seismic": 9.0, "Profound": 7.0, "Rising": 5.0, "Subtle": 3.0, "Dormant": 1.0}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ═════════════════════════════ Helper utilities ══════════════════════════════

def award_task_xp(task: Dict[str, Any], shadow_score: float) -> int:
    """Return XP for a completed task (plus shadow bonus)."""
    tier = task.get("tier", "Bud")
    base = {"Bud": 10, "Bloom": 20, "Blossom": 30}.get(tier, 10)
    bonus = 5 if (tier != "Bud" and isinstance(shadow_score, (int, float)) and shadow_score > 0.7) else 0
    return base + bonus

def prune_context(snap_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Minimise prompt size while keeping key info."""
    component_state = snap_dict.get("component_state") or {}
    dev_index = component_state.get("dev_index") or {}
    ctx = {
        "xp": snap_dict.get("xp", 0),
        "shadow_score": snap_dict.get("shadow_score", 0.5),
        "capacity": snap_dict.get("capacity", 0.5),
        "magnitude": snap_dict.get("magnitude", 5.0),
        "dev_index": dev_index if dev_index else None,
        "last_ritual_mode": snap_dict.get("last_ritual_mode"),
        "current_path": snap_dict.get("current_path"),
        # Add level/stage from xp_mastery if available
        "xp_stage": component_state.get("xp_mastery", {}).get("current_stage_name"),
    }
    ctx = {k: v for k, v in ctx.items() if v is not None}
    return ctx


def default_task_outcome() -> Dict[str, Any]:
    return {"completed": False, "effort": 0, "feedback": "No recent task outcome."}

def default_relational_interaction() -> Dict[str, Any]:
    return {"support": 0, "conflict": 0, "feedback": "No specific relational data."}

# ═════════════════════════════ ForestOrchestrator ════════════════════════════

class ForestOrchestrator:
    """Top‑level coordinator for the entire Forest flow."""

    # ───────────────────────── 1. INITIALISATION ─────────────────────────────
    def __init__(self, saver: Optional[Any] = None):
        """Initializes all engines and the optional saver callback."""
        self.sentiment_engine = SecretSauceSentimentEngineHybrid()
        self.practical_consequence_engine = PracticalConsequenceEngine()
        self.metrics_engine = MetricsSpecificEngine()
        self.seed_manager = SeedManager() # Holds state loaded via component_state
        self.relational_manager = RelationalManager()
        self.narrative_engine = NarrativeModesEngine()
        self.offering_router = OfferingRouter()
        self.reward_index = RewardIndex()
        self.xp_mastery = XPMastery()
        self.pattern_engine = PatternIdentificationEngine()
        self.emotional_integrity_engine = EmotionalIntegrityIndex()
        self.task_engine = TaskEngine()
        self.flow = SnapshotFlowController(frequency=5)
        self.silent_scorer = SilentScoring()
        self.harmonic_router = HarmonicRouting() if HarmonicRouting else None
        self._saver = saver
        logger.info("ForestOrchestrator initialized with all engines.")

    # ───────────────────────── 2. COMPONENT‑STATE IO ─────────────────────────
    def _load_component_states(self, snap):
        """Safely loads state into each engine from the snapshot's component_state."""
        cs = snap.component_state if isinstance(snap.component_state, dict) else {}
        logger.debug("Loading component states from snapshot's component_state.")
        components_to_load = [
            ("metrics_engine", self.metrics_engine, "metrics_engine"),
            ("seed_manager", self.seed_manager, "seed_manager"), # Make sure SeedManager is loaded
            ("relational_manager", self.relational_manager, "relational_manager"),
            ("sentiment_engine", self.sentiment_engine, "sentiment_engine_calibration"),
            ("practical_consequence", self.practical_consequence_engine, "practical_consequence"),
            ("reward_index", self.reward_index, "reward_index"),
            ("xp_mastery", self.xp_mastery, "xp_mastery"),
            ("pattern_engine", self.pattern_engine, "pattern_engine_config"),
            ("narrative_engine", self.narrative_engine, "narrative_engine_config"),
            ("emotional_integrity", self.emotional_integrity_engine, "emotional_integrity_index"),
            ("archetype_manager", getattr(snap, "archetype_manager", None), "archetype_manager"),
            ("dev_index", getattr(snap, "dev_index", None), "dev_index"),
            ("memory_system", getattr(snap, "memory_system", None), "memory_system"),
        ]
        for name, engine, key in components_to_load:
             if engine and hasattr(engine, 'update_from_dict') and callable(engine.update_from_dict):
                 try:
                     engine_state = cs.get(key, {})
                     if isinstance(engine_state, dict):
                         engine.update_from_dict(engine_state)
                         logger.debug("Loaded state for %s from key '%s'", name, key)
                     else:
                          logger.warning("Invalid state format for %s (key: %s), expected dict, got %s. Skipping load.", name, key, type(engine_state))
                 except Exception as e:
                     logger.exception("Failed to load state for %s using key '%s': %s", name, key, e)
             elif key in cs:
                 logger.warning("State found for key '%s', but engine '%s' is missing or lacks update_from_dict.", key, name)

    def _save_component_states(self, snap):
        """Safely saves state from each engine into the snapshot's component_state."""
        if not hasattr(snap, 'component_state') or not isinstance(snap.component_state, dict):
            snap.component_state = {}
        cs = snap.component_state
        logger.debug("Saving component states into snapshot's component_state.")
        components_to_save = [
            ("sentiment_engine_calibration", getattr(self, 'sentiment_engine', None)),
            ("metrics_engine", getattr(self, 'metrics_engine', None)),
            ("seed_manager", getattr(self, 'seed_manager', None)), # Make sure SeedManager is saved
            ("relational_manager", getattr(self, 'relational_manager', None)),
            ("practical_consequence", getattr(self, 'practical_consequence_engine', None)),
            ("reward_index", getattr(self, 'reward_index', None)),
            ("xp_mastery", getattr(self, 'xp_mastery', None)),
            ("pattern_engine_config", getattr(self, 'pattern_engine', None)),
            ("narrative_engine_config", getattr(self, 'narrative_engine', None)),
            ("emotional_integrity_index", getattr(self, 'emotional_integrity_engine', None)),
            ("archetype_manager", getattr(snap, "archetype_manager", None)),
            ("dev_index", getattr(snap, "dev_index", None)),
            ("memory_system", getattr(snap, "memory_system", None)),
        ]
        for key, engine in components_to_save:
            # Ensure engine is not None before checking attributes
            if engine and hasattr(engine, 'to_dict') and callable(engine.to_dict):
                try:
                    cs[key] = engine.to_dict()
                    logger.debug("Saved state for component '%s'", key)
                except Exception as e:
                    logger.exception("Failed to save state for component '%s': %s", key, e)
            elif engine: # Log if engine exists but lacks to_dict
                 logger.warning("Engine '%s' (key: %s) lacks a to_dict method.", type(engine).__name__, key)

        snap.component_state = cs
        if self._saver:
            try:
                logger.debug("Calling external saver callback.")
                self._saver(snap)
            except Exception as e:
                logger.exception("Error in external saver callback: %s", e)

    # ───────────────────────── 3. UTILITY HELPERS ────────────────────────────
    def get_primary_active_seed(self) -> Optional[Seed]:
        """Retrieves the first active seed from the loaded SeedManager state."""
        # Assumes _load_component_states was called, populating self.seed_manager
        if not hasattr(self.seed_manager, 'get_all_seeds'):
             logger.error("SeedManager missing or not loaded correctly.")
             return None
        try:
            all_seeds = self.seed_manager.get_all_seeds()
            if not isinstance(all_seeds, list):
                 logger.error("SeedManager.get_all_seeds() did not return a list.")
                 return None
            seeds = [
                s for s in all_seeds
                if (isinstance(s, Seed) and getattr(s, 'status', None) == "active")
            ]
            if seeds:
                 logger.debug("Found primary active seed: %s", getattr(seeds[0], 'seed_id', 'N/A'))
                 return seeds[0]
            else:
                 logger.debug("No active seed found in SeedManager.")
                 return None
        except Exception as e:
            logger.exception("Error getting primary active seed: %s", e)
            return None

    # ───────────────────────── 4. WITHERING LOGIC ────────────────────────────
    def _update_withering(self, snap) -> None:
        """Adjusts withering level based on inactivity and deadlines."""
        if not hasattr(snap, 'withering_level'): snap.withering_level = 0.0
        if not hasattr(snap, 'component_state') or not isinstance(snap.component_state, dict): snap.component_state = {}
        if not hasattr(snap, 'task_backlog') or not isinstance(snap.task_backlog, list): snap.task_backlog = []
        current_path = getattr(snap, "current_path", "structured")
        now = datetime.utcnow()
        last_iso = snap.component_state.get("last_activity_ts")
        idle_hours = 0.0
        if last_iso and isinstance(last_iso, str):
             try:
                 last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
                 idle_hours = max(0.0,(now.replace(tzinfo=None) - last_dt.replace(tzinfo=None)).total_seconds() / 3600.0)
             except ValueError: logger.warning("Could not parse last_activity_ts: %s", last_iso)
        elif last_iso is not None: logger.warning("last_activity_ts is not a string: %s", type(last_iso))
        idle_coeff = {"structured": 0.025,"hybrid": 0.015,"open": 0.0}.get(current_path, 0.025)
        idle_penalty = idle_coeff * idle_hours
        overdue_hours = 0.0
        if current_path != "open":
            overdue_list = []
            if isinstance(snap.task_backlog, list):
                 for task in snap.task_backlog:
                     if isinstance(task, dict) and task.get("soft_deadline"):
                         try:
                              overdue = hours_until_deadline(task)
                              if isinstance(overdue, (int, float)) and overdue < 0: overdue_list.append(abs(overdue))
                         except Exception as e: logger.error("Error processing task deadline: %s - Task: %s", e, task.get('id', 'N/A'))
            if overdue_list: overdue_hours = max(overdue_list)
        soft_coeff = {"structured": 0.012,"hybrid": 0.005}.get(current_path, 0.0)
        soft_penalty = soft_coeff * overdue_hours
        current_withering = getattr(snap, 'withering_level', 0.0)
        if not isinstance(current_withering, (int, float)): current_withering = 0.0
        new_level = clamp01(float(current_withering) + idle_penalty + soft_penalty)
        snap.withering_level = clamp01(new_level * 0.98)
        logger.debug("Updated withering level to: %.4f", snap.withering_level)

    # ───────────────────────── 5. REFLECTION WORKFLOW ───────────────────────
    async def process_reflection(self, user_input: str, snap) -> Dict[str, Any]:
        """Processes user reflection, updates state, generates task/narrative."""
        logger.info("Processing reflection for user...")
        if not hasattr(snap, 'component_state') or not isinstance(snap.component_state, dict): snap.component_state = {}
        if not hasattr(snap, 'task_backlog') or not isinstance(snap.task_backlog, list): snap.task_backlog = []
        if not hasattr(snap, 'conversation_history') or not isinstance(snap.conversation_history, list): snap.conversation_history = []

        self._load_component_states(snap)
        self._update_withering(snap)

        # 1 – Sentiment Analysis
        sentiment_result = {"final_score": 0.0}
        try:
            if hasattr(self.sentiment_engine, 'analyze_emotional_field'):
                logger.debug("Calling sentiment engine...")
                # Ensure the correct response model is passed if analyze_emotional_field calls generate_response internally
                # Assuming analyze_emotional_field was updated as discussed previously
                sentiment_analysis_result = await self.sentiment_engine.analyze_emotional_field(
                     user_input, snapshot=snap.to_dict() if hasattr(snap, 'to_dict') else {}
                )
                if isinstance(sentiment_analysis_result, dict): sentiment_result = sentiment_analysis_result
                else: logger.warning("Sentiment engine returned non-dict type: %s", type(sentiment_analysis_result))
            else: logger.error("Sentiment engine or analyze_emotional_field method missing.")
        except Exception as exc: logger.exception("Sentiment analysis step failed: %s", exc)
        score = sentiment_result.get("final_score", 0.0)
        if not isinstance(score, (int, float)): score = 0.0
        logger.debug(f"Sentiment analysis score: {score}")

        # 2 – Quick metric nudges based on sentiment
        current_capacity = getattr(snap, 'capacity', 0.5); snap.capacity = clamp01(float(current_capacity) + 0.05 * score)
        current_shadow = getattr(snap, 'shadow_score', 0.5); snap.shadow_score = clamp01(float(current_shadow) - 0.05 * score)
        logger.debug(f"Metrics nudged: Capacity={snap.capacity:.2f}, Shadow={snap.shadow_score:.2f}")

        # 3 – Practical consequence update
        try:
             if hasattr(self.practical_consequence_engine, 'update_signals_from_reflection'):
                 logger.debug("Calling practical consequence engine...")
                 self.practical_consequence_engine.update_signals_from_reflection(user_input)
             else: logger.error("Practical consequence engine or method missing.")
        except Exception as exc: logger.exception("Practical consequence update step failed: %s", exc)

        # 4 – Task generation
        base_task = {"id": "fallback", "title": "Default Reflection Task", "magnitude": 5.0}
        try:
            logger.debug("Calling task engine...")
            sdict = snap.to_dict() if hasattr(snap, 'to_dict') else {}
            # Ensure HTA from active seed is put into sdict['core_state'] for task engine
            seed = self.get_primary_active_seed() # Uses self.seed_manager loaded from state
            if seed and hasattr(seed, 'hta_tree') and isinstance(seed.hta_tree, dict):
                 sdict.setdefault("core_state", {})["hta_tree"] = seed.hta_tree
                 logger.debug("Found active seed HTA for Task Engine.")
            else:
                 # Ensure core_state exists even without seed HTA
                 sdict.setdefault("core_state", {})["hta_tree"] = snap.core_state.get("hta_tree", {})
                 logger.debug("No active seed HTA found, using snapshot core_state HTA (if any) for Task Engine.")

            if hasattr(self.task_engine, 'get_next_step'):
                task_bundle = self.task_engine.get_next_step(sdict) # TaskEngine needs HTA here
                if isinstance(task_bundle, dict) and "base_task" in task_bundle:
                     potential_task = task_bundle["base_task"]
                     if isinstance(potential_task, dict):
                           potential_task.setdefault('magnitude', 5.0)
                           base_task = potential_task
                           logger.debug(f"Task generated: {base_task.get('id')} - {base_task.get('title')}")
                     else: logger.error("task_engine returned invalid base_task format: %s", type(potential_task))
                else: logger.error("task_engine returned invalid bundle format: %s", task_bundle)
            else: logger.error("Task engine or get_next_step method missing.")
        except Exception as exc: logger.exception("Task engine step failed: %s", exc)

        # 5 – Narrative mode determination
        style = ""
        try:
             logger.debug("Determining narrative mode...")
             if hasattr(self.narrative_engine, 'determine_narrative_mode'):
                 nm = self.narrative_engine.determine_narrative_mode(
                     snap.to_dict() if hasattr(snap, 'to_dict') else {},
                     context={"base_task": base_task}
                 )
                 if isinstance(nm, dict):
                      style = nm.get("style_directive", "")
                      logger.debug(f"Narrative mode determined: {nm.get('mode', 'unknown')}")
                 else: logger.error("Narrative engine returned invalid format: %s", nm)
             else: logger.error("Narrative engine or method missing.")
        except Exception as exc: logger.exception("Narrative mode step failed: %s", exc)

        # --- Prepare conversation history for prompt ---
        conversation_history_text = ""
        history_limit = 6
        try:
            if isinstance(snap.conversation_history, list):
                recent_history = snap.conversation_history[-history_limit:]
                if recent_history:
                    formatted_history = [f"{turn.get('role', 'N/A').capitalize()}: {turn.get('content', '').strip()}"
                                         for turn in recent_history if isinstance(turn, dict)]
                    conversation_history_text = "\n".join(filter(None, formatted_history)) + "\n\n"
                    logger.debug("Prepended conversation history to LLM prompt.")
        except Exception as hist_exc: logger.exception("Error formatting conversation history: %s", hist_exc)

        # 6 – Arbiter LLM Call
        final_task, narrative = base_task, "(fallback: LLM call failed)"

        arb_prompt = (
            f"You are the Arbiter of The Forest—a poetic, deeply attuned guide. Your goal is to provide a short, evocative narrative response and potentially refine the suggested task.\n\n"
            f"Recent Conversation History:\n{conversation_history_text}"
            f"Current Context Summary: {json.dumps(prune_context(snap.to_dict() if hasattr(snap, 'to_dict') else {}))}\n\n"
            f"Suggested Task Blueprint: {json.dumps(base_task)}\n\n"
            f"Narrative Style Directive: {style if style else 'Default poetic style.'}\n\n"
            f"Instructions: Return ONLY a single valid JSON object with required keys 'task' (object, can be same as blueprint or refined) and 'narrative' (string response to user based on input, context, and history)."
        )
        logger.debug("Constructed Arbiter LLM prompt.")

        try:
            logger.debug("Calling Arbiter LLM...")
            arb_out = await generate_response(arb_prompt, response_model=LLMResponseModel) # Use default model
            if isinstance(arb_out, LLMResponseModel):
                 potential_task = arb_out.task
                 if isinstance(potential_task, dict): final_task = potential_task or base_task
                 else: logger.warning("LLM returned invalid 'task' type (%s), using base task.", type(potential_task)); final_task = base_task
                 potential_narrative = arb_out.narrative
                 if isinstance(potential_narrative, str): narrative = potential_narrative
                 else: logger.warning("LLM returned invalid 'narrative' type (%s), using fallback.", type(potential_narrative)); narrative = "(LLM response format error)"
                 logger.info(">>> Successfully received narrative from LLM: %s", narrative[:100] + "...")
            else:
                 logger.error("generate_response returned unexpected type: %s", type(arb_out))
                 narrative = "(Internal processing error after LLM call)"
        except Exception as e:
            logger.warning("LLM error during reflection processing: %s", e)
            narrative = "(offline)"
            logger.info(">>> Using fallback narrative: %s", narrative)

        # --- Append current turn to history ---
        try:
            if not isinstance(snap.conversation_history, list): snap.conversation_history = []
            if isinstance(user_input, str): snap.conversation_history.append({"role": "user", "content": user_input})
            if isinstance(narrative, str): snap.conversation_history.append({"role": "assistant", "content": narrative})
            max_history = 20
            if len(snap.conversation_history) > max_history: snap.conversation_history = snap.conversation_history[-max_history:]
            logger.debug("Appended current turn to conversation history (length: %d).", len(snap.conversation_history))
        except Exception as hist_append_exc: logger.exception("Error appending to conversation history: %s", hist_append_exc)

        # 7 – Soft‑deadline scheduling
        current_path = getattr(snap, "current_path", "structured")
        if not hasattr(snap, 'task_backlog') or not isinstance(snap.task_backlog, list): snap.task_backlog = []
        if current_path != "open":
            try:
                if isinstance(final_task, dict):
                     logger.debug("Scheduling soft deadline...")
                     # Ensure schedule_soft_deadlines is imported and works
                     schedule_soft_deadlines(snap, [final_task], override_existing=False)
                else: logger.error("Cannot schedule deadline, final_task is not a dict.")
            except ValueError as ve: logger.error("Soft-deadline scheduling error: %s", ve)
            except Exception as exc: logger.exception("Unexpected soft‑deadline scheduling error: %s", exc)

        # --- Persist state *after* updating history AND potentially adding task ---
        # Add the generated task to the backlog *before* saving
        if isinstance(final_task, dict) and final_task.get("id"):
             if isinstance(snap.task_backlog, list):
                  snap.task_backlog.append(final_task)
             else:
                  logger.error("task_backlog is not a list, cannot append task.")
        else:
             logger.warning("No valid final_task generated to add to backlog.")

        if not hasattr(snap, 'component_state') or not isinstance(snap.component_state, dict): snap.component_state = {}
        snap.component_state["last_activity_ts"] = datetime.utcnow().isoformat()
        self._save_component_states(snap) # Saves snapshot including conversation_history and updated task_backlog

        # Calculate final response fields
        task_magnitude = final_task.get('magnitude', 5.0)
        if not isinstance(task_magnitude, (int, float)): task_magnitude = 5.0
        mag_desc = ForestOrchestrator.describe_magnitude(float(task_magnitude))

        resonance_info = {"theme": "default", "routing_score": 0.0}
        if self.harmonic_router and hasattr(self.harmonic_router, 'route_harmony'):
            try:
                logger.debug("Calculating harmonic routing...")
                detailed_scores = {}
                if hasattr(self.silent_scorer, 'compute_detailed_scores'):
                     detailed_scores = self.silent_scorer.compute_detailed_scores(snap.to_dict() if hasattr(snap, 'to_dict') else {})
                harmonic_result = self.harmonic_router.route_harmony(
                     snap.to_dict() if hasattr(snap, 'to_dict') else {},
                     detailed_scores if isinstance(detailed_scores, dict) else {}
                )
                if isinstance(harmonic_result, dict):
                     resonance_info = harmonic_result
                     logger.debug("Harmonic routing result: %s", resonance_info)
            except Exception as hr_exc: logger.exception("Error getting harmonic routing: %s", hr_exc)

        # Construct final response payload
        response_payload = {
            "task": final_task if isinstance(final_task, dict) else {},
            "arbiter_response": narrative if isinstance(narrative, str) else "",
            "withering": getattr(snap, 'withering_level', 0.0),
            "magnitude_description": mag_desc if isinstance(mag_desc, str) else "Unknown",
            "resonance_theme": resonance_info.get("theme", "default"),
            "routing_score": resonance_info.get("routing_score", 0.0),
            "offering": None, # Placeholder
            "mastery_challenge": None, # Placeholder
        }
        logger.info(">>> Final narrative being returned in payload: %s", response_payload["arbiter_response"][:100] + "...")
        logger.info("Reflection processing complete.")
        return response_payload


    # ───────────────────────── 6. COMPLETION WORKFLOW ───────────────────────
    async def process_task_completion(
        self,
        task_id: str,
        snap,
        db: Session,
        # success: bool = True # If using success flag passed from main.py
    ) -> Dict[str, Any]:
        """Processes task completion, updates snapshot, logs event, triggers HTA rebalancing."""
        logger.info(f"Processing completion for task {task_id}...")
        # Basic state updates (XP, remove task, logs, etc.)
        if not hasattr(snap, 'task_backlog') or not isinstance(snap.task_backlog, list): snap.task_backlog = []
        if not hasattr(snap, 'xp'): snap.xp = 0
        if not hasattr(snap, 'shadow_score'): snap.shadow_score = 0.5
        if not hasattr(snap, 'withering_level'): snap.withering_level = 0.0
        if not hasattr(snap, 'component_state') or not isinstance(snap.component_state, dict): snap.component_state = {}

        # Find the completed task details *before* removing it
        task = next((t for t in snap.task_backlog if isinstance(t, dict) and t.get("id") == task_id), None)
        if not task:
            logger.warning("Task %s not found in backlog for completion.", task_id)
            return {"error": f"Task {task_id} not found.", "xp_awarded": 0, "withering": getattr(snap, 'withering_level', 0.0)}

        # Get linked HTA node ID *before* removing task
        linked_hta_node_id = task.get("hta_node_id")

        logger.debug("Removing task %s from backlog.", task_id)
        snap.task_backlog = [t for t in snap.task_backlog if isinstance(t, dict) and t.get("id") != task_id]

        # Update XP, Dev Index, etc.
        shadow_score_val = getattr(snap, 'shadow_score', 0.5)
        if not isinstance(shadow_score_val, (int, float)): shadow_score_val = 0.5
        xp_gain = award_task_xp(task, float(shadow_score_val))
        logger.info(f"Awarding {xp_gain} XP for task {task_id}.")
        current_xp = getattr(snap, 'xp', 0)
        if not isinstance(current_xp, (int, float)): current_xp = 0
        snap.xp = float(current_xp) + xp_gain

        if hasattr(snap, "dev_index") and hasattr(snap.dev_index, 'apply_task_effect'):
            try:
                 mult = {"Bud": 1.0, "Bloom": 1.5, "Blossom": 2.0}.get(task.get("tier", "Bud"), 1.0)
                 logger.debug("Applying dev index effect for task completion.")
                 snap.dev_index.apply_task_effect(task.get("relevant_indexes", []), mult, 1.0) # Assuming momentum = 1.0
            except Exception as dev_exc: logger.exception("Error applying dev_index task effect: %s", dev_exc)

        # Log completion event
        try:
            if 'TaskFootprintLogger' in globals():
                 logger.debug("Logging task completion event to DB.")
                 TaskFootprintLogger(db).log_task_event(
                     task_id=task_id, event_type="completed",
                     snapshot=snap.to_dict() if hasattr(snap, 'to_dict') else {},
                     event_metadata={"xp_awarded": xp_gain, "success": True}, # Assuming success=True if this method is called
                 )
        except Exception as log_exc: logger.exception("Task footprint logging error on completion: %s", log_exc)

        # Update withering
        current_withering = getattr(snap, 'withering_level', 0.0)
        if not isinstance(current_withering, (int, float)): current_withering = 0.0
        snap.withering_level = clamp01(float(current_withering) - 0.15)
        logger.debug(f"Withering level reduced to: {snap.withering_level:.4f}")

        # --- ADDED: HTA Rebalancing Logic ---
        # Trigger rebalancing if the completed task was linked to an HTA node
        if linked_hta_node_id:
            logger.info(f"Task completion linked to HTA node {linked_hta_node_id}. Triggering HTA rebalancing.")
            try:
                # 1. Get current HTA state from the active seed
                active_seed = self.get_primary_active_seed() # Assumes SeedManager state is loaded
                if not active_seed or not isinstance(active_seed.hta_tree, dict):
                    raise ValueError("Active seed or its HTA tree not found/valid for rebalancing.")

                current_hta_dict = active_seed.hta_tree
                # Optional: Mark the completed node status within the HTA dict before sending?
                # This requires finding the node by ID and updating its status in the dict.
                # Simpler: Just send the completed ID and let LLM handle status logic.

                # 2. Construct Rebalancing Prompt
                # Placeholder prompt - needs significant refinement!
                hta_rebalancing_prompt = (
                    f"[INST] You are an AI assistant that dynamically adapts a user's Hierarchical Task Analysis (HTA) plan based on their progress and context.\n"
                    f"The user just completed the task linked to HTA node ID: '{linked_hta_node_id}'.\n"
                    f"Their Current HTA Tree Structure:\n{json.dumps(current_hta_dict, indent=2)}\n\n"
                    f"User Context Summary: {json.dumps(prune_context(snap.to_dict()))}\n"
                    f"Current Level/Stage: {self.xp_mastery.get_current_stage(snap.xp)['stage']}\n\n" # Get current stage
                    f"Instructions:\n"
                    f"1. Analyze the impact of completing node '{linked_hta_node_id}'.\n"
                    f"2. Re-evaluate the priorities, statuses (mark completed node, check parents), and relevance of remaining nodes, especially within the current level/branch.\n"
                    f"3. **Serendipity:** Consider if this completion unlocks or suggests any unexpected but relevant new steps or exploration paths. If so, add them as new child nodes with a 'rationale'.\n"
                    f"4. Prune any branches that are now clearly irrelevant due to this completion.\n"
                    f"5. Return ONLY the complete, updated HTA tree structure as a single valid JSON object, adhering to the required schema (root key 'hta_root', nodes with id, title, description, priority, depends_on, children, etc.).\n"
                    f"[/INST]"
                )

                # 3. Call LLM
                logger.debug("Calling LLM for HTA rebalancing...")
                rebalanced_hta_response = await generate_response(hta_rebalancing_prompt, response_model=HTAResponseModel)

                # 4. Update Snapshot if successful
                if hasattr(rebalanced_hta_response, 'hta_root') and isinstance(rebalanced_hta_response.hta_root, HTANodeModel):
                    new_hta_dict = {"root": rebalanced_hta_response.hta_root.model_dump(mode='json')}
                    active_seed.hta_tree = new_hta_dict # Update seed object in memory

                    # Update SeedManager state in component_state
                    if hasattr(self, 'seed_manager') and hasattr(self.seed_manager, 'update_seed'):
                        self.seed_manager.update_seed(active_seed.seed_id, hta_tree=new_hta_dict)
                        snap.component_state["seed_manager"] = self.seed_manager.to_dict()
                    else:
                        logger.error("Cannot update SeedManager state during HTA rebalancing.")

                    # Update core_state for TaskEngine
                    snap.core_state['hta_tree'] = new_hta_dict
                    logger.info("Successfully rebalanced HTA tree after task completion.")
                else:
                    logger.error("Failed to get valid rebalanced HTA structure from LLM.")
                    # Continue without updating HTA

            except Exception as rebal_err:
                logger.exception("Error during HTA rebalancing after task completion: %s", rebal_err)
                # Do not re-raise, allow completion to succeed even if rebalancing fails
        # --- END ADDED: HTA Rebalancing Logic ---

        # Final state save *after* potential rebalancing
        snap.component_state["last_activity_ts"] = datetime.utcnow().isoformat()
        self._save_component_states(snap)

        logger.info(f"Task {task_id} completion processed successfully.")
        # Return original intended data
        return {"xp_awarded": xp_gain, "withering": snap.withering_level}


    # ───────────────────────── 7. CONVENIENCE APIS ──────────────────────────
    def plant_seed(
        self,
        intention: str,
        domain: str,
        addl_ctx: Optional[Dict[str, Any]] = None,
    ) -> Optional[Seed]:
        """Plants a new seed using the SeedManager."""
        logger.info(f"Attempting to plant seed: Intention='{intention}', Domain='{domain}'")
        # Note: This might be redundant if main.py handles seed creation now.
        # Ensure SeedManager instance exists and is loaded
        if not hasattr(self, 'seed_manager') or not hasattr(self.seed_manager, 'plant_seed'):
             logger.error("SeedManager missing or not loaded correctly for plant_seed.")
             return None
        try:
            new_seed = self.seed_manager.plant_seed(intention, domain, addl_ctx)
            if new_seed: logger.info("Seed planted successfully via orchestrator method.")
            else: logger.warning("Seed planting via orchestrator method did not return a seed object.")
            return new_seed
        except Exception as exc:
            logger.exception("Orchestrator plant_seed error: %s", exc)
            return None

    def trigger_seed_evolution(
        self, seed_id: str, evolution: str, new_intention: Optional[str] = None
    ) -> bool:
        """Triggers seed evolution using the SeedManager."""
        logger.info(f"Attempting to evolve seed {seed_id}: Evolution='{evolution}'")
        # Ensure SeedManager instance exists and is loaded
        if not hasattr(self, 'seed_manager') or not hasattr(self.seed_manager, 'evolve_seed'):
             logger.error("SeedManager missing or not loaded correctly for evolve_seed.")
             return False
        try:
            # The evolve_seed method itself needs the AI logic for HTA adjustments
            success = self.seed_manager.evolve_seed(seed_id, evolution, new_intention)
            logger.info(f"Seed {seed_id} evolution attempt result: {success}")
            return success
        except Exception as exc:
            logger.exception("Orchestrator trigger_seed_evolution error: %s", exc)
            return False

    @staticmethod
    def describe_magnitude(value: float) -> str:
        """Describes a magnitude value based on configured thresholds."""
        if 'MAGNITUDE_THRESHOLDS' not in globals() or not isinstance(MAGNITUDE_THRESHOLDS, dict):
             logger.error("MAGNITUDE_THRESHOLDS constant is missing or invalid for describe_magnitude.")
             if value >= 9.0: return "Seismic"
             if value >= 7.0: return "Profound"
             if value >= 5.0: return "Rising"
             if value >= 3.0: return "Subtle"
             return "Dormant"
        try:
             float_value = float(value)
             valid_thresholds = {k: float(v) for k, v in MAGNITUDE_THRESHOLDS.items() if isinstance(v, (int, float))}
             if not valid_thresholds:
                  logger.error("MAGNITUDE_THRESHOLDS contains no valid numeric thresholds.")
                  return "Unknown"
             sorted_thresholds = sorted(valid_thresholds.items(), key=lambda item: item[1], reverse=True)
             for label, thresh in sorted_thresholds:
                 if float_value >= thresh: return label
             return sorted_thresholds[-1][0] if float_value > 0 else "Dormant"
        except Exception as e:
             logger.exception("Error describing magnitude for value %s: %s", value, e)
             return "Unknown"

# ═════════════════════════════════════════════════════════════════════════════