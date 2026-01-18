# Scheduling Agent v2.0

SMS-enabled appointment scheduling agent with integrated Athena Health and Twilio messaging.

## Overview

The scheduling agent handles complete SMS-based appointment workflows. It combines Athena Health API for appointment management with Twilio SMS for patient communication.

## Quick Start

```bash
cd A2A-Framework/scheduling_agent

# Install dependencies
uv pip install -r requirements.txt

# Start the agent
uv run python -m scheduling_agent
```

Server runs on http://0.0.0.0:10005

## Architecture

```
scheduling_agent/
├── __main__.py              Main entry point
├── combined_mcp.py          Exposes 8 tools (4 Athena + 4 Twilio)
├── scheduling_mcp.py        Athena API tools
├── messaging/               Twilio SMS tools
│   ├── messaging_mcp.py
│   ├── session_manager.py   Stores search results
│   └── message_state/
└── tests/
```

## Workflow

1. Receives instruction from host agent
2. Sends SMS asking for patient preferences
3. Waits for patient response
4. Searches Athena with preference filters
5. Sends 3 appointment options via SMS
6. Waits for patient selection (1, 2, or 3)
7. Books appointment in Athena
8. Sends confirmation SMS
9. Returns status to host agent

## Available Tools

**Scheduling (4):**
- find_appointment_options_by_specialty
- book_athena_appointment
- find_athena_appointment_slots
- schedule_appointment_from_encounter

**Messaging (4):**
- send_appointment_sms
- check_sms_response
- simulate_patient_response
- get_conversation_state

## Configuration

Required environment variables in `.env`:

```bash
# AWS Bedrock
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Athena Health
ATHENA_API_KEY=your_key
ATHENA_API_SECRET=your_secret
ATHENA_PRACTICE_ID=195900

# Twilio
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+15551234567

# Testing mode
USE_MOCK_MODE=true
```

## Testing

Run unit tests:
```bash
uv run python tests/test_scheduling_agent.py
```

Run end-to-end workflow test:
```bash
uv run python tests/test_epic_workflow.py
```

Test with host agent:
```bash
curl -X POST http://localhost:10005/agent/task \
  -H "Content-Type: application/json" \
  -d '{"instruction": "Schedule cardiology for patient 60183, phone +15551234567"}'
```

## Epic Status

- Epic 1: SMS Preference Collection - Complete
- Epic 2: Intelligent Filtered Search - Complete
- Epic 3: SMS-Optimized Presentation - Complete
- Epic 4: Booking & Confirmation - Complete
- Epic 5: Integration Testing - In Progress

## Troubleshooting

**Module not found errors:**
```bash
cd A2A-Framework/scheduling_agent
uv run python -m scheduling_agent
```

**Twilio auth errors:**
Set `USE_MOCK_MODE=true` in `.env` for testing without Twilio credentials.

**No appointments found:**
Check date range defaults to 11/24/2025 - 12/24/2025 in agent configuration.

## Migration from v1.0

Version 1.0 used two separate agents (messaging_agent on port 10003, scheduling_agent on port 10005) connected via A2A protocol.

Version 2.0 merges both into a unified agent on port 10005 with direct tool access and built-in session management.
