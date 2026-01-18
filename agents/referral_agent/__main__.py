"""Referral Agent - AWS Bedrock powered agent for medical referral management.

This agent uses AWS Bedrock with Claude Haiku 4.5 to handle referral-related
queries and workflows with Athena Health API integration.
"""

import logging
import os
import sys

# Add parent directories to path for imports here
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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

# Import shared Bedrock executor
from shared_bedrock import BedrockExecutor
import referral_mcp


# Load shared .env from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

logging.basicConfig()

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 10004

# Default Bedrock model (inference profile for Claude Haiku 4.5)
DEFAULT_MODEL_ID = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'

# Agent system instruction
AGENT_INSTRUCTION = """You are a medical referral specialist assistant that creates patient referrals using the Athena Health API.

AVAILABLE TOOLS:
1. execute_complete_referral_workflow - Creates referral with diagnosis in ONE STEP (USE THIS FOR ALL REFERRAL REQUESTS)
2. list_patient_diagnoses - Lists patient's diagnoses
3. list_patient_referrals - Lists patient's referrals
4. list_diagnoses - Shows available diagnosis codes
5. list_referral_types - Gets referral types by specialty

WORKFLOW FOR CREATING REFERRALS:
When user requests a referral creation, use execute_complete_referral_workflow tool with:
- patient_lastname: Patient's last name or ID
- diagnosis_key: The diagnosis (e.g., "chest pain", "angina", "shortness of breath")
- specialty: The specialty (e.g., "cardiology", "orthopedics", "neurology")

This ONE tool handles everything: finding patient, adding diagnosis, getting referral type, creating referral.

EXAMPLES:
User: "Create cardiology referral for patient 60182 with chest pain"
You: [Calls execute_complete_referral_workflow with patient_lastname="60182", diagnosis_key="chest pain", specialty="cardiology"]
Result: "✅ Referral created successfully. Order ID: 203829"

User: "Patient needs orthopedics referral for knee pain"
You: [Calls execute_complete_referral_workflow with patient_lastname from context, diagnosis_key="knee pain", specialty="orthopedics"]

CRITICAL RULES:
- For ALL referral creation requests, use execute_complete_referral_workflow
- Do NOT try to break it into multiple steps
- Do NOT use create_referral, add_diagnosis separately - they don't exist anymore
- ONE tool call = complete referral"""


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Start the referral agent with AWS Bedrock backend."""

    # Bedrock configuration from environment
    model_id = os.getenv('BEDROCK_MODEL_ID', DEFAULT_MODEL_ID)
    region_name = os.getenv('AWS_REGION', 'us-east-1')
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    logging.info('Starting Referral Agent with AWS Bedrock')
    logging.info(f'Model: {model_id}')
    logging.info(f'Region: {region_name}')

    # Define agent skill
    skill = AgentSkill(
        id='referral_management',
        name='Manage medical referrals',
        description='Helps create and manage patient referrals to specialists using Athena Health API',
        tags=['referral', 'specialist', 'diagnosis', 'medical orders'],
        examples=[
            'Create a cardiology referral for patient Smith',
            'I need to refer a patient to orthopedics',
            'Add a diagnosis and create a referral',
            'Patient needs to see a neurologist'
        ],
    )

    # Create agent card
    app_url = os.environ.get('APP_URL', f'http://{host}:{port}')

    agent_card = AgentCard(
        name='Referral Agent',
        description='Helps create and manage patient referrals to medical specialists',
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
        mcp_module=referral_mcp,  # Pass MCP module for tool extraction
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
    """Launch the Referral Agent server."""
    main(host, port)


if __name__ == '__main__':
    main()
