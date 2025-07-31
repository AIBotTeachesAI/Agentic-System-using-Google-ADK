import asyncio
import os # Kept for general use, though specific API key checks are removed
from dotenv import load_dotenv # For loading .env file

# Import necessary ADK components
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as genai_types # Renamed to avoid conflict

# Import your agent
# Ensure your agent_team directory is in PYTHONPATH or adjust path if necessary
from agent_team.agent import root_agent # This is the agent defined in agent_team/agent.py

async def main():
    print("Starting manual agent run...")

    # 0. Load environment variables from .env file
    load_dotenv() 
    # Now, environment variables from your .env file (e.g., GOOGLE_PROJECT_ID, GOOGLE_LOCATION for Vertex AI)
    # should be available via os.environ. ADK/Google client libraries should pick them up.

    # 1. Setup SessionService
    session_service = InMemorySessionService()

    # Define constants for the session
    APP_NAME = "manual_runner_app"
    USER_ID = "test_user_manual"
    SESSION_ID = "manual_session_123"

    # 2. Create a session
    # For InMemorySessionService, create_session appears to be synchronous
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    if session:
        print(f"Session created successfully: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
    else:
        print("Failed to create session.")
        return

    # 3. Setup Runner
    runner = Runner(
        agent=root_agent,         # Your imported agent
        app_name=APP_NAME,
        session_service=session_service
    )
    print(f"Runner created for agent '{runner.agent.name}'.")

    # 4. Interact with the agent
    queries = [
        "What is the weather like in London?",
        "How about Paris?",
        "Tell me the weather in New York"
    ]

    for query in queries:
        print(f"\n>>> User Query: {query}")

        # Prepare the user's message
        content = genai_types.Content(role='user', parts=[genai_types.Part(text=query)])

        final_response_text = "Agent did not produce a final response."

        # Use run_async to get events
        try:
            async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
                # You can inspect all events if you want:
                # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text
                    elif event.actions and event.actions.escalate:
                        final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                    break
            print(f"<<< Agent Response: {final_response_text}")
        except Exception as e:
            print(f"An error occurred during agent interaction: {e}")
            import traceback
            traceback.print_exc()


    # Optional: Inspect session state after interactions
    retrieved_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    
    print(f"\n--- Final Session State for {SESSION_ID} ---")
    if retrieved_session:
        if retrieved_session.state: # Check if the state object itself exists
            # The .state object is an instance of adk.sessions.State (a UserDict).
            # It will print as {} if empty.
            try:
                print(retrieved_session.state.as_dict()) 
            except AttributeError: # Should ideally not happen if state is State object
                print(retrieved_session.state) 
        else:
            # This case might occur if .state is None, which is unusual for a retrieved session
            print("Session state attribute is None or not present.")
    else:
        print(f"Could not retrieve final session object for {SESSION_ID}.")

if __name__ == "__main__":
    # This script assumes that any necessary authentication (e.g., GOOGLE_API_KEY for AI Studio models,
    # or Application Default Credentials for Vertex AI models) is already configured
    # in your environment.
    asyncio.run(main()) 
    
    
"""
sample output

python run_my_agent_manually.py 
Starting manual agent run...
Session created successfully: App='manual_runner_app', User='test_user_manual', Session='manual_session_123'
Runner created for agent 'weather_agent_stateful_coordinator'.

>>> User Query: What is the weather like in London?
--- Tool: get_weather_stateful called for London ---
--- Tool: Reading state 'user_preference_temperature_unit': Celsius ---
--- Tool: Generated report in Celsius. Result: {'status': 'success', 'report': 'The weather in London is cloudy with a temperature of 15°C.'} ---
--- Tool: Updated state 'last_city_checked_stateful': London ---
<<< Agent Response: The weather in London is cloudy with a temperature of 15°C.


>>> User Query: How about Paris?
--- Tool: get_weather_stateful called for Paris ---
--- Tool: Reading state 'user_preference_temperature_unit': Celsius ---
--- Tool: City 'Paris' not found. ---
<<< Agent Response: Sorry, I don't have weather information for 'Paris'.


>>> User Query: Tell me the weather in New York
--- Tool: get_weather_stateful called for New York ---
--- Tool: Reading state 'user_preference_temperature_unit': Celsius ---
--- Tool: Generated report in Celsius. Result: {'status': 'success', 'report': 'The weather in New york is sunny with a temperature of 25°C.'} ---
--- Tool: Updated state 'last_city_checked_stateful': New York ---
<<< Agent Response: The weather in New york is sunny with a temperature of 25°C.


--- Final Session State for manual_session_123 ---
{'last_city_checked_stateful': 'New York', 'last_weather_report': 'The weather in New york is sunny with a temperature of 25°C.\n'}

"""

    