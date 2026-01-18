"""Messaging Agent - AWS Bedrock powered agent for SMS-based appointment scheduling.

This agent uses AWS Bedrock with Claude Haiku 4.5 to handle SMS communication
with users for appointment scheduling, including sending slots and processing responses.
"""

import logging
import os
import sys

# Add parent directory to path for shared_bedrock import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from shared_bedrock import BedrockExecutor
import messaging_mcp


# Load shared .env from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

logging.basicConfig()

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 10003

# Default Bedrock model (inference profile for Claude Haiku 4.5)
DEFAULT_MODEL_ID = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'

# Agent system instruction
AGENT_INSTRUCTION = """You are a specialized SMS messaging assistant for healthcare appointment scheduling.

Your responsibilities:
1. Send SMS messages to users with available appointment slots
2. Wait for and process user responses
3. Coordinate with the scheduling agent to book confirmed appointments
4. Request additional slots if user declines all options

WORKFLOW:
- When you receive appointment slots and patient contact info, use send_appointment_sms to notify the user
- Use check_sms_response to check if the user has replied
- If user confirms a slot (replies with slot number), coordinate with scheduling agent to book it
- If user says NONE, request more slots from scheduling agent
- Use get_conversation_state to track conversation status

IMPORTANT:
- Always include a conversation_id when sending SMS (use a unique identifier)
- Be patient - users may take hours or days to respond
- Always provide clear instructions to users in SMS messages
- Format appointment information clearly with dates, times, and providers

You have access to tools for:
- Sending appointment SMS with slots
- Checking for user responses
- Simulating responses (for testing)
- Getting conversation state

Work systematically and keep the user informed of progress."""


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Start the messaging agent with AWS Bedrock backend."""

    # Bedrock configuration from environment
    model_id = os.getenv('BEDROCK_MODEL_ID', DEFAULT_MODEL_ID)
    region_name = os.getenv('AWS_REGION', 'us-east-1')
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    logging.info('Starting Messaging Agent with AWS Bedrock')
    logging.info(f'Model: {model_id}')
    logging.info(f'Region: {region_name}')

    # Define agent skill
    skill = AgentSkill(
        id='appointment_messaging',
        name='SMS appointment scheduling',
        description='Sends SMS messages to users with appointment slots and processes their responses',
        tags=['messaging', 'sms', 'appointment', 'scheduling'],
        examples=[
            'Send appointment slots to patient',
            'Check if user responded to appointment SMS',
            'Message patient about available times'
        ],
    )

    # Create agent card
    app_url = os.environ.get('APP_URL', f'http://{host}:{port}')

    agent_card = AgentCard(
        name='Messaging Agent',
        description='Handles SMS communication for appointment scheduling',
        url=app_url,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    # Create Bedrock executor with shared module
    agent_executor = BedrockExecutor(
        model_id=model_id,
        agent_instruction=AGENT_INSTRUCTION,
        card=agent_card,
        mcp_module=messaging_mcp,  # Pass MCP module for tool extraction
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    logging.info(f'Initialized Bedrock executor with model: {model_id}')

    # Create request handler and app
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )

    logging.info(f'Starting server on {host}:{port}')
    uvicorn.run(a2a_app.build(), host=host, port=port)


@click.command()
@click.option('--host', 'host', default=DEFAULT_HOST, help='Host to bind to')
@click.option('--port', 'port', default=DEFAULT_PORT, help='Port to bind to')
def cli(host: str, port: int):
    """Launch the Messaging Agent server."""
    main(host, port)


if __name__ == '__main__':
    main()