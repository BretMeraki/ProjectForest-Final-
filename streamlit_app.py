# streamlit_app.py
import streamlit as st
import requests
import uuid
import json # Import json for handling potential errors

# --- Configuration ---
# Make sure your FastAPI backend (main.py) is running!
# Adjust this URL if your backend runs on a different address or port.
BACKEND_URL = "http://localhost:8000"
COMMAND_ENDPOINT = f"{BACKEND_URL}/command"
SET_GOAL_ENDPOINT = f"{BACKEND_URL}/onboarding/set_goal"
ADD_CONTEXT_ENDPOINT = f"{BACKEND_URL}/onboarding/add_context"

# --- Initialize Session State ---
# Use session state to store user ID, messages, and onboarding status
if "user_id" not in st.session_state:
    # Generate a random UUID as user_id for this session.
    # In a real app, use proper authentication.
    st.session_state.user_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    # Store chat history: list of {"role": "user" | "assistant", "content": "..."}
    st.session_state.messages = []

if "onboarding_status" not in st.session_state:
    # Possible statuses: "NeedsGoal", "NeedsContext", "Completed"
    st.session_state.onboarding_status = "NeedsGoal"
    # Add initial welcome message only if message history is empty
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Welcome to Forest OS! To begin, please share the primary goal or intention you wish to cultivate."
        })

# --- Helper Function to Call Backend ---
def call_forest_api(endpoint: str, user_id: str, payload_data: dict):
    """Sends data to the Forest OS backend API."""
    payload = {"user_id": user_id, **payload_data}
    try:
        response = requests.post(endpoint, json=payload, timeout=60) # Add timeout
        # Check for specific HTTP errors indicating onboarding state issues
        if response.status_code == 403:
             try:
                 detail = response.json().get("detail", "Access denied. Check onboarding status.")
                 return {"error": f"API Access Error (403): {detail}"}
             except json.JSONDecodeError:
                  return {"error": "API Access Error (403): Permission denied. Ensure onboarding is complete."}
        elif response.status_code == 404: # e.g., user not found during task completion if implemented
             try:
                 detail = response.json().get("detail", "Resource not found.")
                 return {"error": f"API Error (404): {detail}"}
             except json.JSONDecodeError:
                  return {"error": "API Error (404): Resource not found."}

        response.raise_for_status() # Raise HTTPError for other bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.Timeout:
        st.error("API Connection Error: The request timed out.")
        return {"error": "API request timed out."}
    except requests.exceptions.ConnectionError as e:
        st.error(f"API Connection Error: Could not connect to the backend at {endpoint}. Is it running?")
        return {"error": f"Could not connect to backend: {e}"}
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {e}")
        return {"error": f"API request failed: {e}"}
    except json.JSONDecodeError:
        # This can happen if the server returns non-JSON error page (e.g., HTML error)
        st.error(f"API Error: Invalid response format received from {endpoint}. Check backend logs.")
        return {"error": "Invalid response format from backend."}

# --- App Display ---
st.title(" Forest OS ")

# Display User ID for reference/debugging
st.caption(f"Session User ID: {st.session_state.user_id}")

# Display chat messages from history in a container
# Set height to manage screen real estate
message_container = st.container(height=600, border=False)
with message_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"]) # Use markdown for potential formatting

# --- Input Handling using st.chat_input ---
# The prompt variable will contain the user's input when they press Enter
if prompt := st.chat_input("Enter your reflection or command..."):
    # 1. Add user message to chat history immediately
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Display user message in chat message container (rerun will handle this)

    # 3. Determine which API endpoint to call based on onboarding status
    response_data = None
    endpoint_to_call = None
    payload = {}
    is_onboarding_step = False

    if st.session_state.onboarding_status == "NeedsGoal":
        endpoint_to_call = SET_GOAL_ENDPOINT
        payload = {"goal_intention": prompt}
        is_onboarding_step = True
    elif st.session_state.onboarding_status == "NeedsContext":
        endpoint_to_call = ADD_CONTEXT_ENDPOINT
        payload = {"context_reflection": prompt}
        is_onboarding_step = True
    elif st.session_state.onboarding_status == "Completed":
        endpoint_to_call = COMMAND_ENDPOINT
        payload = {"command": prompt}
    else:
         st.error("Internal Error: Unknown onboarding state.")

    # 4. Call the appropriate API if an endpoint is determined
    api_error = False
    if endpoint_to_call:
        with st.spinner("Processing..."): # Provide feedback during API call
            response_data = call_forest_api(endpoint_to_call, st.session_state.user_id, payload)
            if response_data is None or response_data.get("error"):
                api_error = True
                # Display error message if call failed
                error_msg = response_data.get("error", "An unknown API error occurred.") if response_data else "API call failed. Check connection."
                st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Error: {error_msg}"})


    # 5. Process the response if no API error occurred
    if not api_error and response_data:
        assistant_response_content = "Sorry, I received an unexpected response." # Default fallback

        # Handle successful onboarding responses
        if endpoint_to_call == SET_GOAL_ENDPOINT:
            if response_data.get("status") == "Goal Set":
                assistant_response_content = response_data.get("message", "Goal set! Now, please provide some initial context about where you are regarding this goal.")
                st.session_state.onboarding_status = "NeedsContext" # Move to next state
                if response_data.get("refined_goal"):
                     assistant_response_content += f"\n\n*Refined Goal:* {response_data['refined_goal']}"
            else: # Handle potential error status from endpoint
                 assistant_response_content = f"⚠️ Onboarding Issue: {response_data.get('message', 'Failed to set goal.')}"

        elif endpoint_to_call == ADD_CONTEXT_ENDPOINT:
             if response_data.get("status") == "Activated":
                 assistant_response_content = response_data.get("message", "Onboarding complete! Your journey begins.")
                 st.session_state.onboarding_status = "Completed" # Final state
                 if response_data.get("first_task") and response_data["first_task"].get("title"):
                      task = response_data["first_task"]
                      assistant_response_content += f"\n\n*Your first step:* **{task['title']}**\n> {task.get('description', '')}"
             else: # Handle potential error status from endpoint
                  assistant_response_content = f"⚠️ Onboarding Issue: {response_data.get('message', 'Failed to add context.')}"

        # Handle regular command responses
        elif endpoint_to_call == COMMAND_ENDPOINT:
            assistant_response_content = response_data.get("arbiter_response")
            if not assistant_response_content:
                assistant_response_content = "..." # Use ellipsis if response is empty
            # Optionally display other info
            # theme = response_data.get('resonance_theme')
            # mag_desc = response_data.get('magnitude_description')
            # if theme or mag_desc:
            #     assistant_response_content += f"\n\n*(Resonance: {theme}, Magnitude: {mag_desc})*"

        else: # Fallback for unrecognized successful response structure
             assistant_response_content = f"Received response: {str(response_data)[:200]}..." # Show snippet

        # Add successful assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": assistant_response_content})

    # 6. Rerun the script to update the display including the new messages
    st.rerun()