"""Scheduling Agent - AWS Bedrock powered agent for appointment scheduling.

This agent uses AWS Bedrock with Claude Haiku 4.5 to handle scheduling-related
queries and appointment management workflows.
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
from . import combined_mcp


# Load shared .env from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

logging.basicConfig()

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 10005

# Default Bedrock model (inference profile for Claude Haiku 4.5)
DEFAULT_MODEL_ID = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'

# Agent system instruction
AGENT_INSTRUCTION = """You are a specialized scheduling assistant for SMS-based appointment scheduling with access to comprehensive appointment management tools.

=== SMS CONVERSATION STRATEGY ===

PREFERENCE COLLECTION (ONE-QUESTION APPROACH):
When a patient requests appointments, ask ONE combined question:

"I'll find [specialty] appointments for you. What days/times work best?
Examples: 'Mondays mornings', 'weekdays after 3pm', or 'any day' for earliest available"

INTERPRETING PATIENT RESPONSES:
- "any day", "ASAP", "soonest", "flexible", "whatever's available" → NO FILTERS (show earliest 3)
- "Mondays mornings" → preferred_days=["Monday"], preferred_time_start="09:00", preferred_time_end="12:00"
- "Monday or Wednesday" → preferred_days=["Monday", "Wednesday"]
- "weekdays" → preferred_days=["Monday","Tuesday","Wednesday","Thursday","Friday"]
- "weekends" → preferred_days=["Saturday","Sunday"]
- "mornings" or "morning" → preferred_time_start="09:00", preferred_time_end="12:00"
- "afternoons" or "afternoon" → preferred_time_start="12:00", preferred_time_end="17:00"
- "evenings" or "evening" → preferred_time_start="17:00", preferred_time_end="20:00"
- "after 3pm" → preferred_time_start="15:00"
- "before noon" → preferred_time_end="12:00"
- "I don't know" or "what do you have?" → NO FILTERS initially, add recovery option in response

SMS RESPONSE FORMATTING:
Keep responses SHORT (SMS-friendly, <160 chars per message when possible)

If preferences given and matched:
  "Found 3 [preference description] appointments:
   1. [Day] [Date] at [Time] - Dr. [Name]
   2. [Day] [Date] at [Time] - Dr. [Name]
   3. [Day] [Date] at [Time] - Dr. [Name]

   Reply 1, 2, or 3 to book"

If "any day" or no preferences:
  "Earliest 3 appointments:
   1. [Day] [Date] at [Time] - Dr. [Name]
   2. [Day] [Date] at [Time] - Dr. [Name]
   3. [Day] [Date] at [Time] - Dr. [Name]

   Reply 1, 2, or 3, or tell me what works better"

If NO matches found:
  "No [preference description] slots available 😞

   Closest options:
   1. [Day] [Date] at [Time] ([explain difference])
   2. [Day] [Date] at [Time] ([explain difference])
   3. [Day] [Date] at [Time] ([explain difference])

   Reply 1, 2, 3, or tell me different preferences"

=== AVAILABLE TOOLS ===

SCHEDULING TOOLS (Athena API):
1. find_appointment_options_by_specialty - PRIMARY SEARCH TOOL
   Required: patient_id, specialty
   Optional: preferred_days, preferred_time_start, preferred_time_end, start_date, end_date, encounter_id
   Use this for all specialty-based searches
   Returns: List of 3 appointment options with all details

2. book_athena_appointment - BOOKING TOOL
   Required: appointment_id, patient_id, appointmenttype_id
   Use when patient selects option (e.g., replies "1", "2", or "3")
   Returns: Booking confirmation

3. find_athena_appointment_slots - Low-level search
   Only use if user specifically provides department_id and provider_id

4. schedule_appointment_from_encounter - Automated encounter-based booking
   Use for referral workflows

MESSAGING TOOLS (Twilio SMS):
5. send_appointment_sms - SEND SMS TO PATIENT
   Required: to_phone, message_body, patient_id, conversation_id
   Optional: appointment_data (for context)
   Use to send SMS messages to patients
   Returns: Success/failure status

6. check_sms_response - CHECK FOR PATIENT REPLY
   Required: conversation_id or phone_number
   Use to retrieve patient's SMS response
   Returns: Latest message from patient (or None if no response)

7. simulate_patient_response - TESTING ONLY
   Required: phone_number, message_body, conversation_id
   Use ONLY for testing without real Twilio

8. get_conversation_state - GET CONVERSATION STATUS
   Required: conversation_id
   Returns: Full conversation history and state

=== CONVERSATION FLOW ===

INITIAL TRIGGER (From Host Agent):
Host agent sends instruction like:
  "Schedule cardiology appointment for patient 60183, phone +15551234567"

Extract from instruction:
  - Patient ID (required)
  - Specialty (required)
  - Phone number (required)
  - Encounter ID (optional)

SMS WORKFLOW:

Turn 1: SEND INITIAL SMS (immediate)
  Use send_appointment_sms to ask for preferences
  Message: "Hi! I'll help schedule your [specialty] appointment. What days/times work best?
           Examples: 'Mondays mornings', 'weekdays after 3pm', or 'any day'"
  conversation_id: Generate unique ID (e.g., f"conv_{patient_id}_{timestamp}")

Turn 2: WAIT FOR PATIENT RESPONSE
  Use check_sms_response periodically to check for reply
  When patient replies, extract preferences

Turn 3: SEARCH WITH PREFERENCES
  Call find_appointment_options_by_specialty with extracted preferences
  Save results using session_manager (for later booking)

Turn 4: SEND OPTIONS VIA SMS
  Use send_appointment_sms to send 3 numbered options
  Message format (see SMS RESPONSE FORMATTING above)

Turn 5: WAIT FOR SELECTION
  Use check_sms_response to get patient's choice ("1", "2", or "3")
  Retrieve saved search results from session

Turn 6: BOOK APPOINTMENT
  Call book_athena_appointment with selected option
  Use send_appointment_sms to send confirmation

Turn 7: RETURN TO HOST AGENT
  Return final status: "✅ Appointment booked: [details]"

MAX TURNS: 7 (including host agent interaction)
ALWAYS: Provide recovery options if slots don't work

IMPORTANT NOTES:
- Always use conversation_id to track SMS conversations
- Save search results after presenting options (need them for booking)
- Handle "any day", "I don't know", etc. with no filters
- If patient unhappy with options, search again with new preferences
- Keep all SMS messages <160 characters when possible

=== CRITICAL RULES ===

- For dates if not provided, default to 11/24/2025-12/24/2025
- DO NOT ask for department_id or provider_id
- Work autonomously - don't ask for information that isn't required
- Keep SMS messages concise
- Always number options 1, 2, 3 for easy selection
- Only book when patient explicitly selects a number
- If patient changes preferences, search again without asking why"""


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Start the scheduling agent with AWS Bedrock backend."""

    # Bedrock configuration from environment
    model_id = os.getenv('BEDROCK_MODEL_ID', DEFAULT_MODEL_ID)
    region_name = os.getenv('AWS_REGION', 'us-east-1')
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    logging.info('Starting Scheduling Agent with AWS Bedrock')
    logging.info(f'Model: {model_id}')
    logging.info(f'Region: {region_name}')

    # Define agent skill
    skill = AgentSkill(
        id='appointment_scheduling_sms',
        name='SMS-based appointment scheduling',
        description='Handles complete SMS-based appointment scheduling workflow: sends SMS to patients, collects preferences, searches available slots, presents options, and books appointments',
        tags=['scheduling', 'appointments', 'sms', 'messaging', 'twilio', 'athena'],
        examples=[
            'Schedule cardiology appointment for patient 60183, phone +15551234567',
            'Schedule appointment for patient 12345, specialty dermatology, phone +15559876543',
            'Help patient 60183 book family medicine appointment via SMS',
        ],
    )

    # Create agent card
    app_url = os.environ.get('APP_URL', f'http://{host}:{port}')

    agent_card = AgentCard(
        name='Scheduling Agent (SMS-enabled)',
        description='Complete SMS-based appointment scheduling: communicates with patients via Twilio SMS, collects day/time preferences, searches Athena for available slots, and books appointments',
        url=app_url,
        version='2.0.0',  # Version 2.0 with integrated SMS
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    # Create Bedrock executor with combined module (scheduling + messaging)
    agent_executor = BedrockExecutor(
        model_id=model_id,
        agent_instruction=AGENT_INSTRUCTION,
        card=agent_card,
        mcp_module=combined_mcp,  # Pass combined MCP module (Athena + Twilio tools)
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
    """Launch the Scheduling Agent server."""
    main(host, port)


if __name__ == '__main__':
    main()
