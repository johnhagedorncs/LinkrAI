"""AWS Bedrock executor for A2A agents using Claude models.

This module provides an AgentExecutor implementation that uses AWS Bedrock's
Converse API with Claude models instead of Google's ADK.

Key Features:
- Automatic tool call tracking in artifact metadata
- Agentic loop for autonomous tool use
- Session management for conversation history
"""

import logging
import boto3
from typing import Optional

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError

from .bedrock_conversions import (
    convert_bedrock_content_to_a2a,
    create_bedrock_message,
)
from .mcp_to_bedrock import create_bedrock_tools_from_mcp


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Constants
DEFAULT_USER_ID = 'self'


class BedrockExecutor(AgentExecutor):
    """An AgentExecutor that uses AWS Bedrock Claude models.

    This executor automatically tracks all tool calls and includes them
    in the artifact metadata for visibility in the host agent.
    """

    def __init__(
        self,
        model_id: str,
        agent_instruction: str,
        card: AgentCard,
        mcp_module,
        region_name: str = 'us-east-1',
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize the Bedrock executor.

        Args:
            model_id: Bedrock model identifier (e.g., 'us.anthropic.claude-haiku-4-5-20251001-v1:0')
            agent_instruction: System prompt/instruction for the agent
            card: Agent card with metadata
            mcp_module: The MCP server module containing tool definitions
            region_name: AWS region name (default: us-east-1)
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
        """
        self.model_id = model_id
        self.agent_instruction = agent_instruction
        self._card = card
        self.mcp_module = mcp_module

        # Initialize Bedrock client
        client_kwargs = {'region_name': region_name}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs['aws_access_key_id'] = aws_access_key_id
            client_kwargs['aws_secret_access_key'] = aws_secret_access_key

        self.bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            **client_kwargs
        )

        # Track conversation history per session
        self._sessions: dict[str, list[dict]] = {}
        # Track active sessions for potential cancellation
        self._active_sessions: set[str] = set()

        # Define tools for Bedrock
        self.tools = self._create_bedrock_tools()

    def _create_bedrock_tools(self) -> list[dict]:
        """Create Bedrock tool definitions from MCP server.

        Returns:
            List of Bedrock toolSpec dictionaries
        """
        logger.info("Extracting tool definitions from MCP server")
        tools = create_bedrock_tools_from_mcp(self.mcp_module)

        if not tools:
            logger.warning("No tools extracted from MCP server, using empty list")

        return tools

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool by calling the MCP module directly.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Dictionary of tool input parameters

        Returns:
            Tool execution result as string
        """
        try:
            logger.info(f'🛠️  [{self._card.name}] Calling {tool_name}')
            logger.debug(f'   Input: {tool_input}')

            # Call the MCP server's call_tool function
            result_contents = await self.mcp_module.call_tool(tool_name, tool_input)

            # Extract text from TextContent objects
            result_text = ' '.join(content.text for content in result_contents)

            logger.debug(f'   Output: {result_text[:200]}{"..." if len(result_text) > 200 else ""}')
            return result_text

        except Exception as e:
            logger.error(f'Error executing tool {tool_name}: {e}', exc_info=True)
            return f"Error executing tool: {str(e)}"

    async def _process_request(
        self,
        parts: list[Part],
        session_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        """Process a request using Bedrock Converse API.

        Args:
            parts: List of A2A Parts from the user message
            session_id: Unique identifier for this conversation session
            task_updater: TaskUpdater for sending status updates
        """
        # Initialize session if needed
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        # Track this session as active
        self._active_sessions.add(session_id)

        try:
            # Convert A2A parts to Bedrock message format
            user_message = create_bedrock_message(parts, role='user')

            # Add to conversation history
            conversation_history = self._sessions[session_id]
            conversation_history.append(user_message)

            # Prepare system prompt
            system_prompts = [{
                'text': self.agent_instruction
            }]

            # Call Bedrock Converse API
            logger.debug(f'Calling Bedrock with model: {self.model_id}')
            logger.debug(f'Session {session_id} has {len(conversation_history)} messages')

            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=conversation_history,
                system=system_prompts,
                toolConfig={'tools': self.tools},
                inferenceConfig={
                    'maxTokens': 4096,
                    'temperature': 1.0,
                }
            )

            # Extract response content
            output_message = response.get('output', {}).get('message', {})
            content_blocks = output_message.get('content', [])

            # Add assistant response to history
            conversation_history.append({
                'role': 'assistant',
                'content': content_blocks
            })

            # Agentic loop - allow agent to use multiple tools autonomously
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            tool_call_history = []  # Track all tool calls for metadata

            while iteration < max_iterations:
                # Check for tool use in current content
                tool_uses = [block for block in content_blocks if 'toolUse' in block]

                if not tool_uses:
                    # No more tools to execute, break out of loop
                    logger.debug(f"No tool uses found in iteration {iteration}, finishing")
                    break

                iteration += 1
                logger.info(f"Tool execution iteration {iteration}: {len(tool_uses)} tool(s) to execute")

                # Execute all tools in this turn
                tool_results = []
                for tool_block in tool_uses:
                    tool_use = tool_block['toolUse']
                    tool_name = tool_use.get('name')
                    tool_input = tool_use.get('input', {})
                    tool_id = tool_use.get('toolUseId')

                    # Execute the tool
                    tool_output = await self._execute_tool(tool_name, tool_input)

                    # 🔥 Track this tool call
                    tool_call_history.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "output": tool_output[:500]  # Truncate output for metadata size
                    })

                    tool_results.append({
                        'toolResult': {
                            'toolUseId': tool_id,
                            'content': [{'text': tool_output}]
                        }
                    })

                # Add tool results to conversation
                conversation_history.append({
                    'role': 'user',
                    'content': tool_results
                })

                # Get next response - agent may use more tools or finish
                logger.debug(f'Getting response after tool execution (iteration {iteration})')
                next_response = self.bedrock_client.converse(
                    modelId=self.model_id,
                    messages=conversation_history,
                    system=system_prompts,
                    toolConfig={'tools': self.tools},
                    inferenceConfig={
                        'maxTokens': 4096,
                        'temperature': 1.0,
                    }
                )

                next_output = next_response.get('output', {}).get('message', {})
                content_blocks = next_output.get('content', [])

                conversation_history.append({
                    'role': 'assistant',
                    'content': content_blocks
                })

            # Convert final response to A2A Parts
            response_parts = []
            for block in content_blocks:
                if 'text' in block:
                    response_parts.append(convert_bedrock_content_to_a2a(block))

            # 🔥 Add artifact with metadata containing tool call history
            logger.debug(f'Yielding final response with {len(tool_call_history)} tool calls tracked')
            await task_updater.add_artifact(
                response_parts,
                metadata={"tool_calls": tool_call_history}  # Include tool call history
            )
            await task_updater.update_status(
                TaskState.completed, final=True
            )

            # Log usage metrics
            usage = response.get('usage', {})
            logger.info(
                f"Bedrock usage - Input tokens: {usage.get('inputTokens')}, "
                f"Output tokens: {usage.get('outputTokens')}, "
                f"Total: {usage.get('totalTokens')}"
            )

        except Exception as e:
            logger.error(f'Bedrock API error: {str(e)}', exc_info=True)
            # Send error back to user
            error_part = Part(root=TextPart(
                text=f"Error communicating with AI service: {str(e)}"
            ))
            await task_updater.add_artifact([error_part])
            await task_updater.update_status(
                TaskState.failed, final=True
            )
        finally:
            # Remove from active sessions when done
            self._active_sessions.discard(session_id)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        """Execute the agent task using Bedrock.

        This method is called by the A2A server when a new task is received.

        Args:
            context: Request context containing message and task information
            event_queue: Queue for sending events back to the client
        """
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        # Notify that the task is submitted
        if not context.current_task:
            await updater.update_status(TaskState.submitted)

        await updater.update_status(TaskState.working)

        # Process the request
        await self._process_request(
            context.message.parts,
            context.context_id,
            updater,
        )

        logger.debug('[bedrock] execute exiting')

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """Cancel the execution for the given context.

        Args:
            context: Request context for the task to cancel
            event_queue: Queue for sending events back to the client

        Raises:
            ServerError: Always raises with UnsupportedOperationError
        """
        session_id = context.context_id

        if session_id in self._active_sessions:
            logger.info(f'Cancellation requested for active session: {session_id}')
            self._active_sessions.discard(session_id)
            # Clean up session history
            if session_id in self._sessions:
                del self._sessions[session_id]
        else:
            logger.debug(f'Cancellation requested for inactive session: {session_id}')

        raise ServerError(error=UnsupportedOperationError())

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session.

        Args:
            session_id: The session ID to clear
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f'Cleared session history: {session_id}')
