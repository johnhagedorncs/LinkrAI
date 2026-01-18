"""
FastAPI endpoint for host agent - allows external services to send messages.
Runs alongside the Gradio UI.
"""
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from routing_agent import root_agent as routing_agent

# Initialize FastAPI
app = FastAPI(title="Host Agent API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent setup
APP_NAME = 'routing_app_api'
USER_ID = 'api_user'

SESSION_SERVICE = InMemorySessionService()
ROUTING_AGENT_RUNNER = Runner(
    agent=routing_agent,
    app_name=APP_NAME,
    session_service=SESSION_SERVICE,
)


class ProcessRequest(BaseModel):
    """Request to process text through agent system"""
    text: str
    session_id: str = "default_session"


class AgentAction(BaseModel):
    """An action taken by an agent"""
    agent: str
    action: str
    details: Dict[str, Any]


class ProcessResponse(BaseModel):
    """Response from agent processing"""
    success: bool
    final_response: str
    actions_taken: List[AgentAction]
    tool_calls: List[Dict[str, Any]]
    tool_responses: List[Dict[str, Any]]
    subagent_tool_calls: Dict[str, List[Dict[str, Any]]] = {}


@app.on_event("startup")
async def startup():
    """Create session on startup"""
    await SESSION_SERVICE.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id="default_session"
    )


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Host Agent API",
        "available_agents": ["referral", "scheduling", "messaging"]
    }


@app.post("/api/process", response_model=ProcessResponse)
async def process_message(request: ProcessRequest):
    """
    Process a message through the host agent and return structured results.

    This calls the routing agent which will delegate to specialized agents
    (referral, scheduling, etc.) as needed.
    """
    try:
        # Run the agent
        event_iterator = ROUTING_AGENT_RUNNER.run_async(
            user_id=USER_ID,
            session_id=request.session_id,
            new_message=types.Content(
                role='user',
                parts=[types.Part(text=request.text)]
            ),
        )

        # Collect events
        tool_calls = []
        tool_responses = []
        actions_taken = []
        subagent_tool_calls = {}  # Track tool calls made by each subagent
        final_response = ""

        async for event in event_iterator:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Capture tool calls
                    if part.function_call:
                        tool_call = {
                            "name": part.function_call.name,
                            "args": part.function_call.args if hasattr(part.function_call, 'args') else {}
                        }
                        tool_calls.append(tool_call)

                        # Extract agent info from function arguments
                        agent_name = "host"

                        # Check if this is a send_message call with agent_name in args
                        if part.function_call.name == "send_message" and hasattr(part.function_call, 'args'):
                            args = part.function_call.args or {}
                            target_agent = args.get('agent_name', '')

                            # Map agent card names to simple names
                            if "referral" in target_agent.lower():
                                agent_name = "referral"
                            elif "scheduling" in target_agent.lower():
                                agent_name = "scheduling"
                            elif "messaging" in target_agent.lower():
                                agent_name = "messaging"

                        actions_taken.append(AgentAction(
                            agent=agent_name,
                            action=part.function_call.name,
                            details=tool_call
                        ))

                    # Capture tool responses
                    elif part.function_response:
                        tool_response = {
                            "name": part.function_response.name,
                            "response": part.function_response.response
                        }
                        tool_responses.append(tool_response)

                        # Extract subagent tool calls from Task metadata
                        # When subagents are called via send_message, they return a Task object
                        # containing artifacts with metadata about tool calls they made.
                        # This allows us to track and display the full execution trace.
                        if part.function_response.name == "send_message":
                            response_data = part.function_response.response

                            # Extract Task object from response
                            # Google ADK wraps the Task in: {'result': Task}
                            task = None
                            if isinstance(response_data, dict) and 'result' in response_data:
                                task = response_data['result']
                            elif isinstance(response_data, dict) and 'artifacts' in response_data:
                                task = response_data
                            elif hasattr(response_data, 'artifacts'):
                                task = response_data

                            if task is None:
                                continue

                            # Extract tool calls from Task artifacts metadata
                            if hasattr(task, 'artifacts') and task.artifacts:
                                for artifact in task.artifacts:
                                    if hasattr(artifact, 'metadata') and artifact.metadata:
                                        if 'tool_calls' in artifact.metadata:
                                            # Match response to corresponding send_message call
                                            agent_name = "unknown"
                                            send_message_response_count = sum(1 for tr in tool_responses if tr['name'] == 'send_message')
                                            send_message_call_count = 0
                                            for action in actions_taken:
                                                if action.action == "send_message":
                                                    send_message_call_count += 1
                                                    if send_message_call_count == send_message_response_count:
                                                        agent_name = action.agent
                                                        break

                                            if agent_name not in subagent_tool_calls:
                                                subagent_tool_calls[agent_name] = []
                                            subagent_tool_calls[agent_name].extend(artifact.metadata['tool_calls'])

            # Capture final response
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = ''.join(
                        [p.text for p in event.content.parts if p.text]
                    )
                elif event.actions and event.actions.escalate:
                    final_response = f"Agent escalated: {event.error_message or 'No specific message.'}"
                break

        return ProcessResponse(
            success=True,
            final_response=final_response or "Task completed",
            actions_taken=actions_taken,
            tool_calls=tool_calls,
            tool_responses=tool_responses,
            subagent_tool_calls=subagent_tool_calls
        )

    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)