# pylint: disable=logging-fstring-interpolation
import asyncio
import json
import os
import uuid

from typing import Any

import httpx

from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from remote_agent_connection import (
    RemoteAgentConnections,
    TaskUpdateCallback,
)
from bedrock_adapter import create_bedrock_model


# Load shared .env from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))


def convert_part(part: Part, tool_context: ToolContext):
    """Convert a part to text. Only text parts are supported."""
    if part.type == 'text':
        return part.text

    return f'Unknown type: {part.type}'


def convert_parts(parts: list[Part], tool_context: ToolContext):
    """Convert parts to text."""
    rval = []
    for p in parts:
        rval.append(convert_part(p, tool_context))
    return rval


def create_send_message_payload(
    text: str, task_id: str | None = None, context_id: str | None = None
) -> dict[str, Any]:
    """Helper function to create the payload for sending a task."""
    payload: dict[str, Any] = {
        'message': {
            'role': 'user',
            'parts': [{'type': 'text', 'text': text}],
            'messageId': uuid.uuid4().hex,
        },
    }

    if task_id:
        payload['message']['taskId'] = task_id

    if context_id:
        payload['message']['contextId'] = context_id
    return payload


class RoutingAgent:
    """The Routing agent.

    This is the agent responsible for choosing which remote seller agents to send
    tasks to and coordinate their work.
    """

    def __init__(
        self,
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''

    async def _async_init_components(
        self, remote_agent_addresses: list[str]
    ) -> None:
        """Asynchronous part of initialization."""
        # Use a single httpx.AsyncClient for all card resolutions for efficiency
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(
                    client, address
                )  # Constructor is sync
                try:
                    card = (
                        await card_resolver.get_agent_card()
                    )  # get_agent_card is async

                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                except httpx.ConnectError as e:
                    print(
                        f'ERROR: Failed to get agent card from {address}: {e}'
                    )
                except Exception as e:  # Catch other potential errors
                    print(
                        f'ERROR: Failed to initialize connection for {address}: {e}'
                    )

        agent_info = []
        for agent_detail_dict in self.list_remote_agents():
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents = '\n'.join(agent_info)

    @classmethod
    async def create(
        cls,
        remote_agent_addresses: list[str],
        task_callback: TaskUpdateCallback | None = None,
    ) -> 'RoutingAgent':
        """Create and asynchronously initialize an instance of the RoutingAgent."""
        instance = cls(task_callback)
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        """Create an instance of the RoutingAgent."""
        return Agent(
            model=create_bedrock_model('us.anthropic.claude-haiku-4-5-20251001-v1:0'),
            name='Routing_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                'This Routing agent orchestrates the decomposition of user requests for billing issues, medical referrals, or appointment scheduling'
            ),
            tools=[
                self.send_message,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        """Generate the root instruction for the RoutingAgent."""
        current_agent = self.check_active_agent(context)
        return f"""
        **Role:** You are an expert Routing Delegator. Your primary function is to accurately delegate user inquiries regarding billing issues, prescription issues, medical referrals, and appointment scheduling to the appropriate specialized remote agents.

        **Core Directives:**

        * **Task Delegation:** Utilize the `send_message` function to assign actionable tasks to remote agents.
        * **Workflow Orchestration:** When users request complete workflows (e.g., "create referral and schedule appointment"), coordinate multiple agents sequentially. First complete the referral creation with the Referral Agent, then use the result to schedule an appointment with the Scheduling Agent.
        * **Contextual Awareness for Remote Agents:** If a remote agent repeatedly requests user confirmation, assume it lacks access to the full conversation history. In such cases, enrich the task description with all necessary contextual information relevant to that specific agent.
        * **Autonomous Agent Engagement:** Never seek user permission before engaging with remote agents. If multiple agents are required to fulfill a request, connect with them directly without requesting user preference or confirmation.
        * **Transparent Communication:** Always present the complete and detailed response from the remote agent to the user.
        * **User Confirmation Relay:** If a remote agent asks for confirmation, and the user has not already provided it, relay this confirmation request to the user.
        * **Focused Information Sharing:** Provide remote agents with only relevant contextual information. Avoid extraneous details.
        * **No Redundant Confirmations:** Do not ask remote agents for confirmation of information or actions.
        * **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions. If information is insufficient, request clarification from the user.
        * **Prioritize Recent Interaction:** Focus primarily on the most recent parts of the conversation when processing requests.
        * **Active Agent Prioritization:** If an active agent is already engaged, route subsequent related requests to that agent using the appropriate task update tool.
        * **Sequential Workflow Execution:** For referral + scheduling workflows:
          1. Send complete referral details (patient_id, encounter_id, specialty, diagnosis, clinical_note) to Referral Agent
          2. Wait for referral creation confirmation
          3. Send scheduling request (patient_id, provider_id, department_id, date range) to Scheduling Agent
          4. Present combined workflow results to user

        **Agent Roster:**

        * Available Healthcare Agents: `{self.agents}`
        * Currently Active Agent: `{current_agent['active_agent']}`
                """

    def check_active_agent(self, context: ReadonlyContext):
        state = context.state
        if (
            'session_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'active_agent' in state
        ):
            return {'active_agent': f'{state["active_agent"]}'}
        return {'active_agent': 'None'}

    def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
            state['session_active'] = True

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.cards:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            print(f'Found agent card: {card.model_dump(exclude_none=True)}')
            print('=' * 100)
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to remote seller agent."""
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')

        state = tool_context.state
        state['active_agent'] = agent_name
        client = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f'Client not available for {agent_name}')

        # --- Keep per-remote-agent session ids in state so we can reuse them ---
        sessions = state.setdefault('agent_sessions', {})   # {agent_name: {task_id, context_id}}
        session = sessions.get(agent_name, {})

        # Reuse only if they already exist (i.e., NOT first turn)
        task_id = session.get('task_id')
        context_id = session.get('context_id')

        # Always a fresh message id
        input_meta = state.get('input_message_metadata') or {}
        message_id = input_meta.get('message_id') or str(uuid.uuid4())

        payload = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': task}],
                'messageId': message_id,
            },
        }

        # Attach ids ONLY if we already have them (continuation). For first turn, omit both.
        if task_id:
            payload['message']['taskId'] = task_id
        if context_id:
            payload['message']['contextId'] = context_id

        message_request = SendMessageRequest(
            id=message_id,
            params=MessageSendParams.model_validate(payload),
        )

        send_response: SendMessageResponse = await client.send_message(message_request=message_request)
        print('send_response', send_response.model_dump_json(exclude_none=True, indent=2))
        print("test")

        if not isinstance(send_response.root, SendMessageSuccessResponse):
            print('received non-success response. Aborting get task ')
            return None

        if not isinstance(send_response.root.result, Task):
            print('received non-task response. Aborting get task ')
            return None

        remote_task: Task = send_response.root.result

        # If this task is already completed, don’t store IDs (forces new session next query)
        if remote_task.status.state == "completed":
            sessions.pop(agent_name, None)
        else:
            sessions[agent_name] = {
                "task_id": remote_task.id,
                "context_id": remote_task.context_id,
            }

        return remote_task


def _get_initialized_routing_agent_sync() -> Agent:
    """Synchronously creates and initializes the RoutingAgent."""

    async def _async_main() -> Agent:
        routing_agent_instance = await RoutingAgent.create(
            remote_agent_addresses=[
                os.getenv('REFERRAL_AGENT_URL', 'http://localhost:10004'),
                os.getenv('SCHEDULING_AGENT_URL', 'http://localhost:10003'),
            ]
        )
        return routing_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if 'asyncio.run() cannot be called from a running event loop' in str(e):
            print(
                f'Warning: Could not initialize RoutingAgent with asyncio.run(): {e}. '
                'This can happen if an event loop is already running (e.g., in Jupyter). '
                'Consider initializing RoutingAgent within an async function in your application.'
            )
        raise


root_agent = _get_initialized_routing_agent_sync()
