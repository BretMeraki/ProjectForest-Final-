# forest_app/main.py

import logging
import uuid
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Core components
from forest_app.core.orchestrator import ForestOrchestrator, prune_context
from forest_app.core.snapshot import MemorySnapshot

# Persistence components
from forest_app.persistence.database import get_db
from forest_app.persistence.repository import MemorySnapshotRepository
# --- ADDED: Import the missing SQLAlchemy model ---
from forest_app.persistence.models import MemorySnapshotModel
# --- END ADDED ---


# Logging
try:
    from forest_app.modules.logging_tracking import TaskFootprintLogger, ReflectionLogLogger
except ImportError:
    logging.warning("Loggers not found, using dummy classes for main.py")
    class TaskFootprintLogger:
        def __init__(self, db): pass
        def log_task_event(self, *args, **kwargs): pass
    class ReflectionLogLogger:
        def __init__(self, db): pass
        def log_reflection_event(self, *args, **kwargs): pass

# LLM/HTA/Seed components (ensure imports are correct)
try:
    from forest_app.integrations.llm import generate_response, LLMResponseModel, SentimentResponseModel, LLMValidationError, LLMError
    from forest_app.modules.hta_models import HTAResponseModel, HTANodeModel
    from forest_app.modules.seed import Seed
    from forest_app.modules.hta_tree import HTANode, HTATree
except ImportError as import_err:
     logging.getLogger(__name__).critical("Failed to import core LLM/HTA/Seed components: %s", import_err)
     raise RuntimeError("Core component import failed") from import_err

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Forest OS API", version="1.4")


# --- Pydantic models ---
class RichCommandResponse(BaseModel):
    task: dict
    offering: Optional[dict] = None
    mastery_challenge: Optional[dict] = None
    magnitude_description: str
    arbiter_response: str
    resonance_theme: str
    routing_score: float
    onboarding_status: Optional[str] = None

class CommandRequest(BaseModel):
    command: str
    user_id: str

class TaskCompletionRequest(BaseModel):
    user_id: str
    task_id: str
    success: bool

class SetGoalRequest(BaseModel):
    user_id: str
    goal_intention: str = Field(..., description="The user's initial goal or intention text.")

class AddContextRequest(BaseModel):
    user_id: str
    context_reflection: str = Field(..., description="User's reflection providing context for the goal.")

class OnboardingResponse(BaseModel):
    user_id: str
    status: str = Field(..., description="Current onboarding status.")
    message: str
    refined_goal: Optional[str] = Field(None, description="The AI-refined goal description (after set_goal).")
    first_task: Optional[dict] = None


# Single orchestrator instance
try:
    orchestrator = ForestOrchestrator()
    if not hasattr(orchestrator, 'seed_manager'):
         raise AttributeError("Orchestrator instance does not have 'seed_manager' attribute.")
except Exception as e:
     logger.exception("Failed to initialize ForestOrchestrator: %s", e)
     raise RuntimeError("Could not initialize ForestOrchestrator") from e


# --- Helper function for saving snapshot ---
# Note: Type hint uses the imported MemorySnapshotModel now
def save_snapshot(repo: MemorySnapshotRepository, user_id: str, snapshot: MemorySnapshot, stored_model: Optional[MemorySnapshotModel]):
    """Helper to save snapshot, creating or updating as needed."""
    updated_data = snapshot.to_dict()
    new_or_updated_model = None
    if stored_model and hasattr(stored_model, 'id'):
        repo.update_snapshot(stored_model, updated_data)
        logger.info("Updated snapshot for user %s (ID: %s)", user_id, stored_model.id)
        new_or_updated_model = stored_model
    else:
        new_model = repo.create_snapshot(user_id, updated_data)
        logger.info("Saved initial snapshot for user %s (ID: %s)", user_id, new_model.id)
        new_or_updated_model = new_model
    return new_or_updated_model


# --- Onboarding Endpoint 1: Set Goal ---
@app.post("/onboarding/set_goal", response_model=OnboardingResponse)
async def set_goal_endpoint(request: SetGoalRequest, db: Session = Depends(get_db)):
    """
    Handles the first step of onboarding: setting the primary goal ('North Star').
    Refines the goal using LLM and initializes the HTA root.
    """
    user_id = request.user_id
    repo = MemorySnapshotRepository(db)
    stored = repo.get_latest_snapshot(user_id)
    snapshot = MemorySnapshot.from_dict(stored.snapshot_data) if stored else MemorySnapshot()
    snapshot_to_save = stored

    if snapshot.activated_state.get("goal_set"):
         logger.warning("User %s attempted to set goal when already set.", user_id)
         return OnboardingResponse(user_id=user_id, status="Goal Already Set", message="Goal already set. Use /onboarding/add_context or /command.")

    logger.info("Onboarding Step 1 for %s: Refining goal '%s'", user_id, request.goal_intention)
    try:
        # 1. Refine Goal via LLM
        goal_refinement_prompt = (
             f"A user wants to embark on a personal growth journey.\n"
             f"Their initial stated intention is: \"{request.goal_intention}\"\n"
             f"Refine this into a concise, motivating 'North Star' goal suitable as a title "
             f"for their journey (max 10 words) and a slightly longer description (1-2 sentences).\n"
             f"Return ONLY JSON: {{\"task\": {{\"title\": \"North Star Title\"}}, \"narrative\": \"Refined Description\"}}"
        )
        refined_goal_response = await generate_response(goal_refinement_prompt, response_model=LLMResponseModel)
        refined_title = refined_goal_response.task.get("title", request.goal_intention[:50])
        refined_description = refined_goal_response.narrative

        # 2. Create Seed and Root HTA Node in Snapshot
        seed_manager = orchestrator.seed_manager
        new_seed = Seed(
            seed_name=refined_title, description=refined_description, seed_domain="User Goal"
        )
        root_node = HTANode(
            id=str(uuid.uuid4()), title=new_seed.seed_name,
            description=new_seed.description, priority=1.0
        )
        initial_tree = HTATree(root=root_node)
        new_seed.hta_tree = initial_tree.to_dict()

        seed_manager.add_seed(new_seed)
        snapshot.component_state["seed_manager"] = seed_manager.to_dict()
        snapshot.core_state = {'hta_tree': new_seed.hta_tree}

        # 3. Update Activation State
        snapshot.activated_state["goal_set"] = True

        # 4. Save Snapshot
        snapshot_to_save = save_snapshot(repo, user_id, snapshot, snapshot_to_save) # Update snapshot_to_save if created

        logger.info("Onboarding Step 1 complete for %s. Goal set.", user_id)
        return OnboardingResponse(
            user_id=user_id, status="Goal Set",
            message="Your North Star goal has been set. Now, please provide initial context via /onboarding/add_context.",
            refined_goal=f"{refined_title}: {refined_description}"
        )

    except Exception as e:
        logger.exception("Error during /onboarding/set_goal for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to set goal: {e}")


# --- Onboarding Endpoint 2: Add Context & Generate HTA ---
@app.post("/onboarding/add_context", response_model=OnboardingResponse)
async def add_context_endpoint(request: AddContextRequest, db: Session = Depends(get_db)):
    """
    Handles the second step of onboarding: adding context and generating the HTA skeleton.
    Marks the user as fully activated.
    """
    user_id = request.user_id
    repo = MemorySnapshotRepository(db)
    stored = repo.get_latest_snapshot(user_id)

    if not stored:
        raise HTTPException(status_code=404, detail="Snapshot not found. Please set goal first via /onboarding/set_goal.")

    snapshot = MemorySnapshot.from_dict(stored.snapshot_data)

    if not snapshot.activated_state.get("goal_set"):
        raise HTTPException(status_code=400, detail="Goal not set yet. Please use /onboarding/set_goal first.")
    if snapshot.activated_state.get("activated"):
        return OnboardingResponse(user_id=user_id, status="Already Activated", message="Onboarding already complete. Use /command.")

    logger.info("Onboarding Step 2 for %s: Adding context and generating HTA.", user_id)
    try:
        # 1. Retrieve Refined Goal & Root Node ID
        seed_manager = SeedManager() # Create manager instance
        seed_manager.update_from_dict(snapshot.component_state.get("seed_manager", {})) # Load state
        current_seeds = seed_manager.get_all_seeds()
        if not current_seeds: raise ValueError("No seed found in snapshot state.")
        active_seed = current_seeds[0]
        current_hta = HTATree.from_dict(active_seed.hta_tree)
        if not current_hta.root: raise ValueError("HTA root node not found in seed.")

        refined_title = current_hta.root.title
        refined_description = current_hta.root.description
        root_node_id = current_hta.root.id

        # 2. Generate HTA Skeleton via LLM
        initial_context = prune_context(snapshot.to_dict())
        # --- Placeholder Prompt for HTA Skeleton ---
        hta_skeleton_prompt = (
            f"[INST] You are an AI assistant creating an initial plan (Hierarchical Task Analysis tree) for a user's personal growth goal. The user's goal is the root node.\n"
            f"Root Goal: {json.dumps({'id': root_node_id, 'title': refined_title, 'description': refined_description})}\n"
            f"User's Initial Context Reflection:\n{request.context_reflection}\n"
            f"User Context Summary: {json.dumps(initial_context)}\n"
            f"Current Level/Stage: Awakening (Initial)\n\n"
            f"Instructions:\n"
            f"1. Generate the first level of child nodes (2-4 logical steps or phases) branching directly from the root goal.\n"
            f"2. For each child node, provide these keys: 'id' (unique placeholder like 'node_L1_1', 'node_L1_2', etc.), 'title' (concise), 'description' (1-2 sentences), 'priority' (float 0.0-1.0, higher is more important initially), 'depends_on' (list, should contain only the root node ID '{root_node_id}' for this first level), 'estimated_energy' ('low'/'medium'/'high'), 'estimated_time' ('low'/'medium'/'high').\n"
            f"3. **Serendipity:** Include one child node focused on 'Exploration' or 'Curiosity' relevant to the goal (e.g., 'Explore related ideas', 'Mind Map Possibilities'). Give this a moderate priority.\n"
            f"4. Ensure the output is ONLY a single valid JSON object representing the root node, containing its original details plus the generated children in its 'children' list. Adhere strictly to the required schema.\n"
            f"[/INST]\n"
            f"{{\"hta_root\": {{\"id\": \"{root_node_id}\", \"title\": \"{refined_title}\", \"description\": \"{refined_description}\", \"priority\": 1.0, \"depends_on\": [], \"estimated_energy\": \"medium\", \"estimated_time\": \"medium\", \"children\": [ /* LLM generates children here */ ] }}}}"
        )
        # --- End Placeholder Prompt ---

        logger.debug("Sending HTA Skeleton Prompt to LLM...")
        hta_response = await generate_response(hta_skeleton_prompt, response_model=HTAResponseModel)
        logger.info("Received HTA Skeleton response from LLM.")

        # 3. Update Seed's HTA Tree in Snapshot
        if hasattr(hta_response, 'hta_root') and isinstance(hta_response.hta_root, HTANodeModel):
            if hta_response.hta_root.id != root_node_id:
                 logger.warning("LLM changed the root node ID. Resetting to original ID.")
                 hta_response.hta_root.id = root_node_id
            new_hta_dict = {"root": hta_response.hta_root.model_dump(mode='json')}
            active_seed.hta_tree = new_hta_dict
            seed_manager.update_seed(active_seed.seed_id, hta_tree=new_hta_dict)
            snapshot.component_state["seed_manager"] = seed_manager.to_dict()
            snapshot.core_state['hta_tree'] = new_hta_dict
            logger.info("Successfully updated seed HTA with generated skeleton for user %s.", user_id)
        else:
            logger.error("Failed to get valid HTA structure from LLM for user %s.", user_id)
            raise ValueError("Failed to generate HTA skeleton from LLM.")

        # 4. Mark as Activated
        snapshot.activated_state["activated"] = True

        # 5. Save Snapshot
        snapshot_to_save = save_snapshot(repo, user_id, snapshot, stored)

        # 6. Prepare Response
        first_task_from_hta = {}
        try:
            orchestrator._load_component_states(snapshot)
            if snapshot.core_state.get('hta_tree'):
                task_result = orchestrator.task_engine.get_next_step(snapshot.to_dict())
                first_task_from_hta = task_result.get("base_task", {})
        except Exception as task_e:
            logger.exception("Error getting first task after onboarding for user %s: %s", user_id, task_e)

        logger.info("Onboarding Step 2 complete for %s. User activated.", user_id)
        return OnboardingResponse(
            user_id=user_id, status="Activated",
            message="Onboarding complete! Your initial path is set.",
            refined_goal=f"{refined_title}: {refined_description}",
            first_task=first_task_from_hta if first_task_from_hta else None
        )

    except HTTPException: raise
    except Exception as e:
        logger.exception("Error during /onboarding/add_context for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to add context: {e}")


# --- MODIFIED /command Endpoint ---
@app.post("/command", response_model=RichCommandResponse)
async def command_endpoint(request: CommandRequest, db: Session = Depends(get_db)):
    """
    Processes user reflection IF onboarding is complete.
    Otherwise, directs user to onboarding endpoints.
    """
    user_id = request.user_id
    repo = MemorySnapshotRepository(db)
    stored = repo.get_latest_snapshot(user_id)

    # Onboarding Check
    if not stored:
         raise HTTPException(status_code=403, detail="Onboarding not started. Use /onboarding/set_goal.")

    snapshot = MemorySnapshot.from_dict(stored.snapshot_data)
    is_activated = snapshot.activated_state.get("activated", False)
    goal_is_set = snapshot.activated_state.get("goal_set", False)

    if not is_activated:
        if goal_is_set:
             raise HTTPException(status_code=403, detail="Onboarding incomplete. Use /onboarding/add_context.")
        else:
             raise HTTPException(status_code=403, detail="Onboarding not complete. Use /onboarding/set_goal first.")
    # --- END ONBOARDING CHECK ---

    # REGULAR PROCESSING
    try:
        logger.info("User %s is onboarded. Processing command as reflection.", user_id)
        orchestrator._load_component_states(snapshot)

        reflection_id = str(uuid.uuid4())
        result_dict = await orchestrator.process_reflection(request.command, snapshot)

        final_response = RichCommandResponse(**result_dict, onboarding_status="Completed")
        logger.info("Reflection processed for user %s", user_id)

        # Logging
        snapshot_dict = snapshot.to_dict()
        reflection_logger = ReflectionLogLogger(db)
        reflection_logger.log_reflection_event(
            reflection_id=reflection_id, event_type="processed",
            snapshot=snapshot_dict, event_metadata={"input_length": len(request.command)}
        )
        final_task = final_response.task
        if final_task and final_task.get("id"):
            task_logger = TaskFootprintLogger(db)
            task_logger.log_task_event(
                task_id=final_task["id"], event_type="generated",
                snapshot=snapshot_dict, event_metadata={"title": final_task.get("title")}
            )
            if isinstance(snapshot.component_state, dict):
                 snapshot.component_state["last_issued_task_id"] = final_task["id"]

        # Persist updated snapshot
        save_snapshot(repo, user_id, snapshot, stored)

        return final_response

    except HTTPException: raise
    except Exception as e:
        logger.exception("Error during /command processing for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- MODIFIED /complete_task Endpoint ---
@app.post("/complete_task")
async def complete_task_endpoint(
    request: TaskCompletionRequest, db: Session = Depends(get_db)
):
    """
    Handles a task completion event, checking for activation status first.
    """
    user_id = request.user_id
    repo = MemorySnapshotRepository(db)
    stored = repo.get_latest_snapshot(user_id)

    if not stored:
        raise HTTPException(status_code=404, detail=f"No snapshot found for user {user_id}.")

    snapshot = MemorySnapshot.from_dict(stored.snapshot_data)

    # ONBOARDING CHECK
    is_activated = snapshot.activated_state.get("activated", False)
    if not is_activated:
         logger.warning("User %s attempted task completion before onboarding.", user_id)
         raise HTTPException(status_code=403, detail="User onboarding not complete.")
    # END CHECK

    try:
        orchestrator._load_component_states(snapshot)

        # Call orchestrator method
        # Note: Removed 'success' flag assuming orchestrator doesn't need it directly
        completion_result = await orchestrator.process_task_completion(
            task_id=request.task_id,
            snapshot=snapshot,
            db=db
        )
        logger.info("Processed completion for task %s (user %s)", request.task_id, user_id)

        # Logging
        snapshot_dict = snapshot.to_dict()
        task_logger = TaskFootprintLogger(db)
        task_logger.log_task_event(
            task_id=request.task_id, event_type="completed",
            snapshot=snapshot_dict, event_metadata={"success": request.success} # Log success from request
        )

        # Persist updated snapshot using helper
        save_snapshot(repo, user_id, snapshot, stored)
        logger.info("Snapshot updated after completing task %s", request.task_id)

        return {"detail": "Task completion processed", "result": completion_result}

    except HTTPException: raise
    except Exception as e:
        logger.exception("Error in /complete_task for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Optional: Add explicit DB init call here if needed on startup
    # try:
    #     from forest_app.persistence import init_db
    #     init_db()
    #     logger.info("Database initialized check complete.")
    # except Exception as db_init_e:
    #     logger.exception("Error during database initialization check: %s", db_init_e)

    uvicorn.run("forest_app.main:app", host="0.0.0.0", port=8000, reload=True)