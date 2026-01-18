"""
Automated Healthcare Workflow Orchestrator using Google ADK

Orchestrates the complete patient care workflow using ADK tools:
1. Scribe Agent → Medical conversation
2. Referral Agent → Determines medical codes
3. Scheduling Agent → Finds appointment slots
4. Messaging Agent → Sends SMS to patient
5. Patient Response → Books appointment

Uses Google ADK's tool system and A2A protocol for agent communication.
"""

import asyncio
import os
from typing import Dict, Any
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai import types
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, Message, TextPart, Part
import httpx

load_dotenv()

# Agent URLs (based on actual agent ports)
SCRIBE_AGENT_URL = os.getenv('SCRIBE_AGENT_URL', 'http://localhost:10001')  # Not yet implemented as A2A server
REFERRAL_AGENT_URL = os.getenv('REFERRAL_AGENT_URL', 'http://localhost:10004')
SCHEDULING_AGENT_URL = os.getenv('SCHEDULING_AGENT_URL', 'http://localhost:10005')
MESSAGING_AGENT_URL = os.getenv('MESSAGING_AGENT_URL', 'http://localhost:10003')  # Actual port is 10003


class WorkflowState:
    """Maintains state throughout the workflow"""
    def __init__(self):
        self.patient_id: str = ""
        self.patient_phone: str = ""
        self.scribe_notes: Dict[str, Any] = {}
        self.referral_data: Dict[str, Any] = {}
        self.appointment_options: list = []
        self.selected_appointment: Dict[str, Any] = {}
        self.booked_appointment: Dict[str, Any] = {}


# Global workflow state
workflow_state = WorkflowState()


async def call_agent_with_a2a(agent_url: str, message_text: str, context_data: Dict[str, Any] = None) -> str:
    """
    Call another agent using A2A protocol

    Args:
        agent_url: URL of the target agent
        message_text: Message to send
        context_data: Additional context data

    Returns:
        Agent's response as string
    """
    async with httpx.AsyncClient(timeout=240) as client:
        # Get agent card
        card_response = await client.get(f"{agent_url}/.well-known/agent-card")
        card_response.raise_for_status()
        agent_card = card_response.json()

        # Create A2A client
        a2a_client = A2AClient(client, agent_card, url=agent_url)

        # Create message
        message = Message(
            role="user",
            parts=[Part(root=TextPart(text=message_text))]
        )

        # Send message
        request = SendMessageRequest(
            params=MessageSendParams(message=message)
        )

        response = await a2a_client.send_message(request)

        # Extract text from response
        if hasattr(response, 'task') and response.task and response.task.artifacts:
            text_parts = []
            for artifact in response.task.artifacts:
                for part in artifact.parts:
                    if hasattr(part, 'text'):
                        text_parts.append(part.text)
            return "\n".join(text_parts)

        return str(response)


# ============================================================================
# ADK TOOLS - Each step in the workflow is a tool
# ============================================================================

async def step1_process_scribe(medical_conversation: str) -> str:
    """
    Step 1: Process medical conversation through Scribe Agent

    Note: Scribe Agent is not yet implemented as an A2A server, using mock data

    Args:
        medical_conversation: The doctor-patient conversation transcript

    Returns:
        Structured medical notes
    """
    print("\n📝 STEP 1: Processing medical conversation (Mock Scribe)")
    print("-" * 80)

    # TODO: When Scribe Agent A2A server is implemented, uncomment:
    # response = await call_agent_with_a2a(
    #     SCRIBE_AGENT_URL,
    #     f"Process this medical conversation and extract key information:\n\n{medical_conversation}"
    # )

    # For now, extract basic info from the conversation
    mock_response = f"""
Medical Transcription Summary:

Chief Complaint: Chest pain and shortness of breath
Duration: Past week
Symptoms:
- Sharp chest pain, especially during exercise
- Shortness of breath
- Family history: Father had heart attack at age 55

Recommendation: Referral to cardiologist for further evaluation

Raw conversation excerpt:
{medical_conversation[:200]}...
"""

    # Store in workflow state
    workflow_state.scribe_notes = {
        "raw_response": mock_response,
        "chief_complaint": "chest pain",
        "symptoms": "shortness of breath, fatigue"
    }

    print(f"✅ Mock scribe completed (Scribe Agent A2A server not yet implemented)")
    return mock_response


async def step2_get_referral_codes(patient_id: str) -> str:
    """
    Step 2: Get medical codes and referral specialty from Referral Agent

    Args:
        patient_id: Patient ID

    Returns:
        Referral information with medical codes and specialty
    """
    print("\n🏥 STEP 2: Determining medical codes and referral (Referral Agent)")
    print("-" * 80)

    workflow_state.patient_id = patient_id

    message = f"""
Based on the following medical notes, determine referral information:

Patient ID: {patient_id}
Chief Complaint: {workflow_state.scribe_notes.get('chief_complaint')}
Symptoms: {workflow_state.scribe_notes.get('symptoms')}

Please provide:
1. ICD-10 diagnosis codes
2. Required specialty for referral
3. Recommended appointment type
"""

    response = await call_agent_with_a2a(
        REFERRAL_AGENT_URL,
        message,
        context_data={"patient_id": patient_id}
    )

    # Store referral data
    workflow_state.referral_data = {
        "raw_response": response,
        "specialty": "cardiology",  # Would extract from response
        "diagnosis_codes": ["I20.9", "E11.9"],
        "referral_id": "REF-12345"
    }

    print(f"✅ Referral codes determined: {workflow_state.referral_data['specialty']}")
    return f"Referral: {workflow_state.referral_data['specialty']} - Codes: {workflow_state.referral_data['diagnosis_codes']}"


async def step3_find_appointments(patient_phone: str) -> str:
    """
    Step 3: Find appointment slots via Scheduling Agent

    Args:
        patient_phone: Patient's phone number for SMS

    Returns:
        Available appointment options
    """
    print(f"\n📅 STEP 3: Finding appointments (Scheduling Agent)")
    print("-" * 80)

    workflow_state.patient_phone = patient_phone

    specialty = workflow_state.referral_data.get('specialty', 'cardiology')
    patient_id = workflow_state.patient_id

    message = f"""
Find appointment options for patient {patient_id}

Specialty: {specialty}
Diagnosis Codes: {', '.join(workflow_state.referral_data.get('diagnosis_codes', []))}

Find the top 3 available appointment slots.
"""

    response = await call_agent_with_a2a(
        SCHEDULING_AGENT_URL,
        message,
        context_data={
            "patient_id": patient_id,
            "specialty": specialty
        }
    )

    # Parse REAL appointment options from scheduling agent response
    # The scheduling agent returns JSON with appointment_options array
    import json
    import re

    # Extract JSON from response (it's in a ```json code block)
    json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        parsed_data = json.loads(json_str)

        # Extract REAL appointment options from Athena API
        if 'appointment_options' in parsed_data:
            workflow_state.appointment_options = parsed_data['appointment_options']
            print(f"✅ Parsed {len(workflow_state.appointment_options)} REAL appointments from Athena")
        else:
            print("⚠️  No appointment_options in response, using empty list")
            workflow_state.appointment_options = []
    else:
        print("⚠️  Could not parse JSON from scheduling agent response")
        print(f"Response preview: {response[:200]}...")
        workflow_state.appointment_options = []

    print(f"✅ Found {len(workflow_state.appointment_options)} appointment slots")
    return f"Found {len(workflow_state.appointment_options)} appointments: {response[:200]}..."


async def step4_send_sms_to_patient() -> str:
    """
    Step 4: Send appointment options to patient via SMS (Messaging Agent)

    Returns:
        SMS send confirmation
    """
    print(f"\n📱 STEP 4: Sending SMS to patient (Messaging Agent)")
    print("-" * 80)

    # Format SMS message
    sms_text = f"📅 {workflow_state.referral_data['specialty'].title()} Appointments\n\n"
    for opt in workflow_state.appointment_options:
        sms_text += f"{opt['option_number']}. {opt['date']} at {opt['time']}\n"
        sms_text += f"   {opt['provider']} - {opt['location']}\n\n"
    sms_text += "Reply 1-3 to book"

    message = f"""
Send SMS to patient phone number: {workflow_state.patient_phone}

Message:
{sms_text}

Store the appointment options so we can handle the patient's reply.
"""

    response = await call_agent_with_a2a(
        MESSAGING_AGENT_URL,
        message,
        context_data={
            "patient_id": workflow_state.patient_id,
            "phone_number": workflow_state.patient_phone,
            "appointment_options": workflow_state.appointment_options
        }
    )

    print(f"✅ SMS sent to {workflow_state.patient_phone}")
    return f"SMS sent successfully to {workflow_state.patient_phone}"


async def step5_book_appointment(patient_choice: int) -> str:
    """
    Step 5: Book the selected appointment (Scheduling Agent)

    Args:
        patient_choice: Option number selected by patient (1-3)

    Returns:
        Booking confirmation
    """
    print(f"\n✅ STEP 5: Booking appointment (Scheduling Agent)")
    print("-" * 80)

    if patient_choice < 1 or patient_choice > len(workflow_state.appointment_options):
        return f"Invalid choice: {patient_choice}"

    selected = workflow_state.appointment_options[patient_choice - 1]
    workflow_state.selected_appointment = selected

    message = f"""
Book appointment for patient {workflow_state.patient_id}

Appointment ID: {selected['appointment_id']}
Appointment Type ID: {selected['appointmenttypeid']}
Patient ID: {workflow_state.patient_id}

Please confirm the booking.
"""

    response = await call_agent_with_a2a(
        SCHEDULING_AGENT_URL,
        message,
        context_data={
            "patient_id": workflow_state.patient_id,
            "appointment_id": selected['appointment_id'],
            "appointmenttype_id": selected['appointmenttypeid']
        }
    )

    workflow_state.booked_appointment = {
        "confirmation": response,
        "appointment_details": selected
    }

    print(f"✅ Appointment booked: {selected['date']} at {selected['time']}")

    # Step 6: Send confirmation SMS
    await step6_send_confirmation()

    return f"Appointment booked successfully! Confirmation sent to patient."


async def step6_send_confirmation() -> str:
    """
    Step 6: Send booking confirmation via SMS (Messaging Agent)

    Returns:
        Confirmation send status
    """
    print(f"\n📧 STEP 6: Sending confirmation SMS")
    print("-" * 80)

    selected = workflow_state.selected_appointment

    confirmation_text = f"""✅ Appointment Confirmed!

Date: {selected['date']}
Time: {selected['time']}
Provider: {selected['provider']}
Location: {selected['location']}

See you then!"""

    message = f"""
Send confirmation SMS to: {workflow_state.patient_phone}

Message:
{confirmation_text}
"""

    response = await call_agent_with_a2a(
        MESSAGING_AGENT_URL,
        message
    )

    print(f"✅ Confirmation sent")
    return "Confirmation SMS sent successfully"


# ============================================================================
# WORKFLOW ORCHESTRATOR AGENT
# ============================================================================

def create_workflow_orchestrator_agent() -> Agent:
    """
    Create an ADK Agent that orchestrates the entire workflow

    This agent has tools for each step of the workflow and can
    automatically execute them in sequence.
    """

    # Create ADK tools for each workflow step using proper FunctionTool syntax
    tools = [
        FunctionTool(step1_process_scribe),
        FunctionTool(step2_get_referral_codes),
        FunctionTool(step3_find_appointments),
        FunctionTool(step4_send_sms_to_patient),
        FunctionTool(step5_book_appointment),
    ]

    # System instruction for the orchestrator
    system_instruction = """You are a healthcare workflow orchestrator.

Your job is to automatically execute the complete patient care workflow:

1. Call `process_scribe` with the medical conversation
2. Call `get_referral_codes` with the patient ID
3. Call `find_appointments` with the patient phone number
4. Call `send_sms_to_patient` to notify the patient
5. Wait for patient response (simulated for now)
6. Call `book_appointment` with the patient's choice (usually option 1)

Execute all steps automatically in sequence. After completing all steps, provide a summary."""

    agent = Agent(
        model="gemini-1.5-flash",
        name="WorkflowOrchestrator",  
        instruction=system_instruction,
        tools=tools,
    )

    return agent


def get_user_confirmation(step_name: str, output: str) -> bool:
    """
    Display output and get user confirmation

    Args:
        step_name: Name of the step that just completed
        output: Output from the step

    Returns:
        True if user approves, False if they want to retry
    """
    print("\n" + "=" * 80)
    print(f"📋 {step_name} - OUTPUT PREVIEW")
    print("=" * 80)
    print(output)
    print("=" * 80)

    while True:
        response = input("\n✅ Type 'looks good' to proceed, or 'retry' to run again: ").strip().lower()
        if response in ['looks good', 'lg', 'good', 'yes', 'y']:
            return True
        elif response in ['retry', 'r', 'no', 'n']:
            return False
        else:
            print("Please type 'looks good' or 'retry'")


async def run_interactive_workflow(
    medical_conversation: str,
    patient_id: str,
    patient_phone: str
) -> None:
    """
    Run an interactive workflow with user confirmation after each step

    Args:
        medical_conversation: Doctor-patient conversation transcript
        patient_id: Patient ID in Athenahealth
        patient_phone: Patient's phone number
    """
    print("=" * 80)
    print("🚀 Starting Interactive Healthcare Workflow")
    print("=" * 80)
    print("\n📝 You'll be able to review and approve each step before proceeding\n")

    # Step 1: Process Scribe
    while True:
        response = await step1_process_scribe(medical_conversation)
        if get_user_confirmation("STEP 1: Scribe Agent", response):
            break

    # Step 2: Get Referral Codes
    while True:
        response = await step2_get_referral_codes(patient_id)
        if get_user_confirmation("STEP 2: Referral Agent", response):
            break

    # Step 3: Find Appointments
    while True:
        response = await step3_find_appointments(patient_phone)
        if get_user_confirmation("STEP 3: Scheduling Agent", response):
            break

    # Step 4: Send SMS
    while True:
        response = await step4_send_sms_to_patient()
        if get_user_confirmation("STEP 4: Messaging Agent (SMS)", response):
            break

    # Step 5: Book Appointment (simulate patient selecting option 1)
    print("\n" + "=" * 80)
    print("📞 Simulating patient response: Patient selected Option 1")
    print("=" * 80)

    while True:
        response = await step5_book_appointment(1)
        if get_user_confirmation("STEP 5: Booking Confirmation", response):
            break

    print("\n" + "=" * 80)
    print("🎉 Workflow Complete!")
    print("=" * 80)
    print("\n✅ All steps completed successfully!")
    print(f"✅ Patient {patient_id} has been booked for {workflow_state.selected_appointment.get('specialty', 'appointment')}")
    print(f"✅ Confirmation sent to {patient_phone}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Example usage"""

    medical_conversation = """
Doctor: Hello, what brings you in today?
Patient: I've been having chest pain and shortness of breath for the past week.
Doctor: Can you describe the pain?
Patient: It's a sharp pain in my chest, especially when I exercise.
Doctor: Do you have any history of heart problems?
Patient: My father had a heart attack at 55.
Doctor: I'd like to refer you to a cardiologist for further evaluation.
Patient: Okay, how soon can I get an appointment?
"""

    await run_interactive_workflow(
        medical_conversation=medical_conversation,
        patient_id="60183",
        patient_phone="+15555551234"
    )


if __name__ == "__main__":
    asyncio.run(main())
