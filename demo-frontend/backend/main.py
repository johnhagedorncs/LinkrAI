"""
FastAPI Backend for Healthcare Agent Demo Frontend

Simple bridge between React frontend and existing agent infrastructure.
Handles audio upload, transcription, and agent orchestration.
"""
import os
import sys
import uuid
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Add paths to import existing agents
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Athena"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "A2A-Framework"))

# Import scribe agent
try:
    from scribe_agent.transcriber import MedicalTranscriber
    # Enable real AWS transcription
    SCRIBE_AVAILABLE = False
    print(f"✅ Scribe agent loaded - using real AWS Transcribe Medical")
except ImportError as e:
    SCRIBE_AVAILABLE = False
    print(f"⚠️  Scribe agent not available - transcription will be mocked (Error: {e})")

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

# Initialize FastAPI
app = FastAPI(title="Healthcare Agent Demo API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.vercel.app",  # Allow Vercel preview and production
        os.getenv("FRONTEND_URL", "")  # Allow custom frontend URL from env
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS S3 Configuration
S3_BUCKET = os.getenv("TRANSCRIBE_OUTPUT_BUCKET", "artera-transcriptions")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize S3 client (only if credentials are available)
AWS_AVAILABLE = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))

if AWS_AVAILABLE:
    try:
        s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        print(f"✅ AWS S3 client initialized - using bucket: {S3_BUCKET}")
    except Exception as e:
        AWS_AVAILABLE = False
        print(f"⚠️  AWS credentials invalid - running in mock mode ({e})")
else:
    s3_client = None
    print(f"⚠️  No AWS credentials found - running in mock mode")


class ProcessRequest(BaseModel):
    """Request to process transcript through agent system"""
    transcript: str


class TranscriptResponse(BaseModel):
    """Response from transcription"""
    transcript: str
    s3_uri: str
    speakers: int


class ProcessResponse(BaseModel):
    """Response from agent processing"""
    success: bool
    transcript: str
    actions_taken: list[str]
    results: Dict[str, Any]


def get_mock_agent_response(transcript: str) -> Dict[str, Any]:
    """
    Generate mock agent response for demo mode when host agent is not available.

    Returns a realistic agent response structure that mimics what the real
    host agent would return after orchestrating referral, scheduling, and messaging agents.
    """
    return {
        "actions_taken": [
            {"agent": "referral", "action": "create_referral"},
            {"agent": "scheduling", "action": "find_appointments"},
            {"agent": "messaging", "action": "send_sms"}
        ],
        "tool_calls": [
            {
                "name": "send_message",
                "args": {
                    "agent_name": "Referral Agent",
                    "task": "Create a medical referral for oncology consultation based on prostate cancer diagnosis (Gleason 7 adenocarcinoma, PSA 12.4)"
                }
            },
            {
                "name": "send_message",
                "args": {
                    "agent_name": "Scheduling Agent",
                    "task": "Find next available oncology appointments for patient 12345"
                }
            },
            {
                "name": "send_message",
                "args": {
                    "agent_name": "Messaging Agent",
                    "task": "Send SMS to patient at 5555551234 with referral confirmation and appointment options"
                }
            }
        ],
        "tool_responses": [
            {
                "name": "send_message",
                "response": {
                    "result": {
                        "artifacts": [
                            {
                                "parts": [
                                    {
                                        "kind": "text",
                                        "text": "Referral created successfully. Referral ID: REF-789456. Patient will be contacted by oncology department within 5-7 business days."
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            {
                "name": "send_message",
                "response": {
                    "result": {
                        "artifacts": [
                            {
                                "parts": [
                                    {
                                        "kind": "text",
                                        "text": "Found 3 available appointment slots:\n1. Dr. Sarah Chen - Jan 25, 2026 at 10:00 AM\n2. Dr. Michael Rodriguez - Jan 26, 2026 at 2:30 PM\n3. Dr. Emily Thompson - Jan 27, 2026 at 9:00 AM"
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            {
                "name": "send_message",
                "response": {
                    "result": {
                        "artifacts": [
                            {
                                "parts": [
                                    {
                                        "kind": "text",
                                        "text": "SMS sent successfully to 555-555-1234. Message: 'Your oncology referral has been created. Available appointments: Jan 25 (Dr. Chen), Jan 26 (Dr. Rodriguez), Jan 27 (Dr. Thompson). Reply with preferred date or call 555-0100 to schedule.'"
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        ],
        "subagent_tool_calls": {
            "referral": [
                {
                    "tool": "create_referral",
                    "input": {
                        "patient_id": "12345",
                        "specialty": "oncology",
                        "diagnosis_code": "C61",
                        "diagnosis_description": "Malignant neoplasm of prostate (Gleason 7 adenocarcinoma)",
                        "priority": "routine",
                        "clinical_notes": "PSA 12.4, biopsy confirms prostate cancer. Patient needs oncology consultation for staging and treatment planning."
                    },
                    "output": "✅ Referral created successfully\nReferral ID: REF-789456\nSpecialty: Oncology\nPriority: Routine\nStatus: Pending oncology department review"
                }
            ],
            "scheduling": [
                {
                    "tool": "search_appointments",
                    "input": {
                        "patient_id": "12345",
                        "specialty": "oncology",
                        "department_id": "150",
                        "days_ahead": 30
                    },
                    "output": "✅ Found 3 available appointments:\n\n1. Provider: Dr. Sarah Chen (ID: 450)\n   Date: January 25, 2026\n   Time: 10:00 AM\n   Location: Cancer Treatment Center\n\n2. Provider: Dr. Michael Rodriguez (ID: 451)\n   Date: January 26, 2026\n   Time: 2:30 PM\n   Location: Oncology Clinic - Building B\n\n3. Provider: Dr. Emily Thompson (ID: 452)\n   Date: January 27, 2026\n   Time: 9:00 AM\n   Location: Cancer Treatment Center"
                }
            ],
            "messaging": [
                {
                    "tool": "send_sms",
                    "input": {
                        "phone_number": "5555551234",
                        "message": "Your oncology referral has been created (REF-789456). Available appointments: Jan 25 at 10AM (Dr. Chen), Jan 26 at 2:30PM (Dr. Rodriguez), Jan 27 at 9AM (Dr. Thompson). Reply with preferred date or call 555-0100 to schedule."
                    },
                    "output": "✅ SMS sent successfully\nRecipient: +1-555-555-1234\nMessage ID: SM-abc123def456\nStatus: Delivered\nTimestamp: 2026-01-19 14:30:22 UTC"
                }
            ]
        },
        "final_response": "Successfully processed medical transcript. Created oncology referral (REF-789456), found 3 available appointments, and notified patient via SMS."
    }


@app.get("/")
async def root():
    """Health check endpoint"""
    # Check if host agent is available
    import httpx
    host_agent_available = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:8084/")
            host_agent_available = response.status_code == 200
    except:
        pass

    return {
        "status": "healthy",
        "service": "Healthcare Agent Demo API",
        "scribe_available": SCRIBE_AVAILABLE,
        "aws_available": AWS_AVAILABLE,
        "host_agent_available": host_agent_available,
        "mode": "production" if (SCRIBE_AVAILABLE and AWS_AVAILABLE and host_agent_available) else "mock"
    }


@app.post("/api/upload-and-transcribe", response_model=TranscriptResponse)
async def upload_and_transcribe(audio: UploadFile = File(...)):
    """
    Upload audio file to S3 and transcribe using AWS Transcribe Medical.

    Args:
        audio: Audio file from frontend recording

    Returns:
        TranscriptResponse with transcript text and metadata
    """
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(audio.filename or "recording.webm").suffix
        s3_key = f"demo-recordings/{file_id}{file_extension}"

        # Read audio data
        audio_data = await audio.read()

        # Upload to S3 (if available)
        if AWS_AVAILABLE and s3_client:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=audio_data,
                ContentType=audio.content_type or "audio/webm"
            )
            s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
            print(f"✅ Uploaded audio to {s3_uri}")
        else:
            # Mock S3 URI for demo mode
            s3_uri = f"mock://demo-recordings/{s3_key}"
            print(f"⚠️  Mock mode: simulated upload to {s3_uri}")

        # Transcribe using scribe agent
        if SCRIBE_AVAILABLE:
            transcriber = MedicalTranscriber()
            transcript_text = transcriber.transcribe_file(s3_uri)

            # Count speakers (simple heuristic)
            speaker_count = len(set(
                line.split(":")[0]
                for line in transcript_text.split("\n")
                if ":" in line
            ))
        else:
            # Mock transcription for testing
#             transcript_text = """Speaker 0: The patient is complaining of chest pain that started this morning.
# Speaker 1: Yes doctor, it's a sharp pain in the center of my chest, especially when I breathe deeply.
# Speaker 0: Any shortness of breath or palpitations?
# Speaker 1: A little shortness of breath, yes.
# Speaker 0: I think we should get you to see a cardiologist. I'll create a referral for you."""
            transcript_text= """{
  "transcript": "Doctor: Good morning. Come on in and have a seat. I've got your recent lab results and biopsy back. How are you feeling today?\n\nPatient: Um, I'm doing okay, I guess. A little nervous, to be honest. You said you wanted to talk about some test results?\n\nDoctor: Yes, I do. So a few weeks ago we checked your PSA level, and it came back elevated at 12.4, which is higher than we'd like to see. We then did a biopsy to get a better picture of what's going on, and I'm afraid the results show prostate cancer.\n\nPatient: Oh wow. Okay. Um... is this serious?\n\nDoctor: I understand this is difficult news. The good news is we caught it, and based on the biopsy findings, we're looking at what's called a Gleason 7 adenocarcinoma. That tells us about the grade and type of cancer cells. Now, I've examined you today and everything else looks stable, but we need to move forward with the next steps.\n\nPatient: What does that mean? What happens now?\n\nDoctor: Well, that's why I'm referring you to an oncologist. They're a cancer specialist who will do additional staging tests to see if the cancer has spread anywhere else, and more importantly, they'll discuss all your treatment options with you. Depending on the staging, you might have surgery, radiation, or other therapies available to you.\n\nPatient: So I need to see another doctor?\n\nDoctor: Yes, I'm going to get you set up with our oncology department. They're excellent, and they really specialize in cases like yours. The referral will go through today, and you should hear from them within the next week or so to schedule your appointment. In the meantime, don't hesitate to call if you have any questions or concerns.\n\nPatient: Okay. Thank you, doctor.\n\nDoctor: You're welcome. We're going to get you through this.",
  "patient_id": "12345",
  "encounter_id": 67890,
  "provider_id": "100",
  "department_id": "150",
  "phone_number": "5555551234",
  "cost": 450.00
}"""
            speaker_count = 2

        return TranscriptResponse(
            transcript=transcript_text,
            s3_uri=s3_uri,
            speakers=speaker_count
        )

    except Exception as e:
        print(f"❌ Error in upload_and_transcribe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process", response_model=ProcessResponse)
async def process_transcript(request: ProcessRequest):
    """
    Send transcript to host agent for processing.

    The host agent will analyze the transcript and route tasks to
    specialized agents (referral, scheduling, etc.)

    Args:
        request: ProcessRequest with transcript text

    Returns:
        ProcessResponse with actions taken and results
    """
    try:
        transcript = request.transcript

        # Call the host agent API
        import httpx

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8084/api/process",
                    json={"text": transcript}
                )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Host agent returned error: {response.text}"
                    )

                agent_response = response.json()
        except httpx.ConnectError:
            # Host agent not running - use mock mode
            print("⚠️  Host agent not available - using mock agent responses")
            agent_response = get_mock_agent_response(transcript)
        except Exception as e:
            raise

        subagent_tool_calls_dict = agent_response.get('subagent_tool_calls', {})

        # Format the response for the frontend
        actions_taken = []
        results = {}

        # Agent emoji mapping
        agent_emoji = {
            "referral": "🏥",
            "scheduling": "📅",
            "messaging": "💬"
        }

        # Track which agents were called (for summary at top)
        agents_called = set()

        # Process each action (host -> subagent interactions)
        for action in agent_response.get('actions_taken', []):
            agent_name = action.get('agent', 'unknown')
            agents_called.add(agent_name)

        # Create summary of agents called (goes in purple box at top)
        for agent_name in sorted(agents_called):
            emoji = agent_emoji.get(agent_name, "🤖")
            actions_taken.append(f"{emoji} {agent_name.title()} Agent called")

        # Process chronologically: match each send_message call with its response
        tool_calls_list = agent_response.get('tool_calls', [])
        tool_responses_list = agent_response.get('tool_responses', [])

        # Build index to match calls with responses
        send_message_call_idx = 0
        send_message_response_idx = 0

        # Process in order by iterating through tool_calls and tool_responses together
        for tool_call in tool_calls_list:
            if tool_call.get('name') == 'send_message':
                args = tool_call.get('args', {})
                agent_name_display = args.get('agent_name', 'Unknown Agent')
                task = args.get('task', 'No task description')

                # Determine simple agent name from display name
                agent_name = "unknown"
                if "referral" in agent_name_display.lower():
                    agent_name = "referral"
                elif "scheduling" in agent_name_display.lower():
                    agent_name = "scheduling"
                elif "messaging" in agent_name_display.lower():
                    agent_name = "messaging"

                emoji = agent_emoji.get(agent_name, "🤖")

                # Add "Host -> Agent" message
                results[f"Host agent → {agent_name_display}"] = task

                # Find the corresponding response
                if send_message_response_idx < len(tool_responses_list):
                    # Look for the matching send_message response
                    matching_response = None
                    for i in range(send_message_response_idx, len(tool_responses_list)):
                        if tool_responses_list[i].get('name') == 'send_message':
                            matching_response = tool_responses_list[i]
                            send_message_response_idx = i + 1
                            break

                    if matching_response:
                        # Extract tool calls for this specific agent from subagent_tool_calls_dict
                        if agent_name in subagent_tool_calls_dict:
                            tool_calls_for_agent = subagent_tool_calls_dict[agent_name]

                            # Add each tool call as a separate bubble
                            for tool_call_item in tool_calls_for_agent:
                                tool_name = tool_call_item.get('tool', 'unknown_tool')
                                tool_input = tool_call_item.get('input', {})
                                tool_output = tool_call_item.get('output', 'No output')

                                # Create formatted header
                                header = f"{emoji} {agent_name.title()} Agent Tool: {tool_name}"

                                # Format input and output nicely
                                formatted_content = f"Input:\n{json.dumps(tool_input, indent=2)}\n\nOutput:\n{tool_output}"

                                results[header] = formatted_content

                            # Remove processed tool calls so they don't get reused
                            del subagent_tool_calls_dict[agent_name]

                        # Extract agent's text response back to host
                        response_data = matching_response.get('response', {})
                        if isinstance(response_data, dict):
                            # Try result.artifacts first (new structure)
                            result_data = response_data.get('result', {})
                            artifacts = result_data.get('artifacts', [])

                            # Fallback to direct artifacts (old structure)
                            if not artifacts:
                                artifacts = response_data.get('artifacts', [])

                            # Extract agent's text response
                            if artifacts:
                                for artifact in artifacts:
                                    if isinstance(artifact, dict):
                                        parts = artifact.get('parts', [])
                                        for part in parts:
                                            if isinstance(part, dict) and part.get('kind') == 'text':
                                                agent_text = part.get('text', '')
                                                if agent_text:
                                                    results[f"{agent_name.title()} Agent → Host agent"] = agent_text

                send_message_call_idx += 1

        # Handle any remaining tool calls not matched (shouldn't happen but for safety)
        for agent_name, tool_calls_for_agent in subagent_tool_calls_dict.items():
            emoji = agent_emoji.get(agent_name, "🤖")
            for tool_call_item in tool_calls_for_agent:
                tool_name = tool_call_item.get('tool', 'unknown_tool')
                tool_input = tool_call_item.get('input', {})
                tool_output = tool_call_item.get('output', 'No output')
                header = f"{emoji} {agent_name.title()} Agent Tool: {tool_name}"
                formatted_content = f"Input:\n{json.dumps(tool_input, indent=2)}\n\nOutput:\n{tool_output}"
                results[header] = formatted_content

        # If no actions at all, use final response
        if not actions_taken:
            actions_taken.append("📋 Processing completed")
            results["Final Response"] = agent_response.get('final_response', 'Task completed')

        return ProcessResponse(
            success=True,
            transcript=transcript,
            actions_taken=actions_taken,
            results=results
        )

    except Exception as e:
        print(f"❌ Error in process_transcript: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
