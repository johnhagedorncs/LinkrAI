# Messaging Agent

SMS-based messaging agent for healthcare appointment scheduling, built with AWS Bedrock Claude Haiku 4.5 and the A2A Framework.

## Overview

The Messaging Agent handles SMS communication with patients for appointment scheduling. It sends appointment slot options to patients via SMS, waits for their responses (which can take hours or days), and coordinates with the scheduling agent to book confirmed appointments.

## Features

- **SMS Communication**: Send appointment slots to patients via SMS using AWS End User Messaging
- **Persistent State Management**: Conversations persist across sessions, handling multi-day response times
- **Mock SMS Gateway**: Built-in mock SMS service for testing without real SMS infrastructure
- **Production SMS**: AWS End User Messaging integration for real two-way SMS communication
- **Response Processing**: Intelligently parses user responses (slot selection or decline)
- **Multi-Conversation Support**: Handle multiple patient conversations concurrently
- **Scheduling Integration**: Coordinates with scheduling agent to book confirmed appointments
- **HIPAA-Ready**: AWS integration with compliance features for healthcare data

## Architecture

```
┌─────────────────────┐
│  Messaging Agent    │
│  (Bedrock Claude)   │
└──────────┬──────────┘
           │
           │ Uses
           ▼
┌─────────────────────┐
│   Messaging MCP     │
│   Server (Tools)    │
└──────────┬──────────┘
           │
           ├─────────────────┬──────────────────┐
           ▼                 ▼                  ▼
┌──────────────────┐  ┌──────────────┐  ┌────────────────┐
│  Message State   │  │  Mock SMS    │  │  AWS End User  │
│  (JSON Files)    │  │  Gateway     │  │  Messaging SMS │
└──────────────────┘  └──────────────┘  └────────────────┘
```

## Installation

### Prerequisites

```bash
# Python 3.11+
pip install mcp a2a-sdk boto3 uvicorn click python-dotenv
```

### AWS Credentials

Set up AWS credentials for Bedrock access:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

Or create a `.env` file (see `example.env` for template):

```bash
# AWS Credentials (for Bedrock and SMS)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0

# Optional: AWS End User Messaging (for production SMS)
# Leave commented for mock mode (development/testing)
# AWS_SMS_ORIGINATION_NUMBER=+1234567890
```

## Usage

### Starting the Messaging Agent

```bash
cd A2A-Framework/messaging_agent
python -m messaging_agent
```

The agent will start on `http://0.0.0.0:10003` by default.

### Running Tests

```bash
cd A2A-Framework/messaging_agent
python test_messaging.py
```

Expected output:
```
======================================================================
🧪 MESSAGING AGENT TEST SUITE
======================================================================
...
📊 TEST RESULTS: 6 passed, 0 failed out of 6 tests
✅ ALL TESTS PASSED!
```

### Using the SMS Simulator

The messaging agent includes a CLI tool to simulate user SMS responses:

#### View All Messages
```bash
python sms_simulator.py list
```

#### View Specific Conversation
```bash
python sms_simulator.py view test_conv_001
```

#### Simulate User Response
```bash
# User selects slot 1
python sms_simulator.py respond test_conv_001 1

# User declines all slots
python sms_simulator.py respond test_conv_001 NONE
```

#### View Pending Messages
```bash
python sms_simulator.py pending
```

#### Clear All Messages (for testing)
```bash
python sms_simulator.py clear
```

## MCP Tools

The Messaging Agent provides 4 MCP tools:

### 1. send_appointment_sms

Send SMS to a patient with available appointment slots.

**Input:**
```json
{
  "phone_number": "+11234567890",
  "appointment_slots": [
    {
      "slot_number": 1,
      "date": "2025-11-15",
      "time": "10:00 AM",
      "provider": "Smith",
      "cost_estimate": "$150"
    }
  ],
  "cost_estimate": "$150",
  "conversation_id": "conv_123"
}
```

**Output:**
- SMS message ID
- Conversation ID
- Message preview

### 2. check_sms_response

Check if a patient has responded to an SMS.

**Input:**
```json
{
  "conversation_id": "conv_123"
}
```

**Output:**
- User response (if available)
- Selected slot details or decline indication
- Next steps recommendation

### 3. simulate_user_sms_response

Simulate a user SMS response for testing.

**Input:**
```json
{
  "conversation_id": "conv_123",
  "response": "1"  // or "NONE"
}
```

### 4. get_conversation_state

Retrieve the current state of a conversation.

**Input:**
```json
{
  "conversation_id": "conv_123"
}
```

**Output:**
- Conversation status
- Phone number
- Appointment slots
- Selected slot (if any)

## Workflow Example

### Complete Scheduling Flow

1. **Host receives appointment slots from scheduling agent**
   ```json
   {
     "slots": [
       {"slot_number": 1, "date": "2025-11-15", "time": "10:00 AM", "provider": "Smith"},
       {"slot_number": 2, "date": "2025-11-15", "time": "2:00 PM", "provider": "Johnson"},
       {"slot_number": 3, "date": "2025-11-16", "time": "9:00 AM", "provider": "Williams"}
     ],
     "cost_estimate": "$150"
   }
   ```

2. **Messaging agent sends SMS to patient**
   ```
   🏥 Appointment Slots Available

   Estimated Cost: $150

   Available Times:
   1. 2025-11-15 at 10:00 AM - Dr. Smith
   2. 2025-11-15 at 2:00 PM - Dr. Johnson
   3. 2025-11-16 at 9:00 AM - Dr. Williams

   Reply with:
   - Slot number (1, 2, 3) to confirm
   - NONE if no slots work
   ```

3. **Patient responds** (could be hours or days later)
   ```
   User text: "1"
   ```

4. **Messaging agent checks response and processes it**
   - If user selected a slot → coordinate with scheduling agent to book
   - If user said NONE → request more slots from scheduling agent

5. **Booking confirmation** (if slot selected)
   - Messaging agent sends confirmation SMS
   - Scheduling agent books the appointment

## State Persistence

### Why Persistence Matters

Patients may take hours or even days to respond to SMS messages. The messaging agent uses file-based state persistence to ensure:

- Conversations survive agent restarts
- No data loss if the agent goes down
- Multiple agents can share state (with shared filesystem)

### State Storage

**Location:** `messaging_agent/message_state/`

**Conversation State File:** `{conversation_id}.json`
```json
{
  "conversation_id": "conv_123",
  "phone_number": "+11234567890",
  "appointment_slots": [...],
  "cost_estimate": "$150",
  "message_id": "msg_1_conv_123",
  "status": "awaiting_response",
  "created_at": "2025-11-10T10:30:00",
  "last_updated": "2025-11-10T10:30:05"
}
```

**SMS Messages File:** `sms_messages.json`
```json
[
  {
    "message_id": "msg_1_conv_123",
    "conversation_id": "conv_123",
    "phone_number": "+11234567890",
    "message": "...",
    "direction": "outbound",
    "timestamp": "2025-11-10T10:30:00",
    "status": "sent",
    "response": "1",
    "response_timestamp": "2025-11-10T14:20:00"
  }
]
```

## Integration with Scheduling Agent

The messaging agent is designed to work with the scheduling agent:

1. **Receive slots from scheduling agent**
   - Messaging agent gets available appointment slots
   - Formats them for SMS

2. **Send to patient**
   - SMS sent with clear instructions
   - Conversation state saved

3. **Wait for response**
   - Patient takes time to respond
   - Agent periodically checks for response

4. **Process response**
   - If confirmed: call scheduling agent to book
   - If declined: call scheduling agent for more slots

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_REGION` | AWS region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrock model | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `AWS_SMS_ORIGINATION_NUMBER` | Phone number for production SMS | Optional (uses mock if not set) |
| `USE_MOCK_SMS` | Force mock mode | `false` |
| `APP_URL` | Agent URL | `http://0.0.0.0:10003` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `10003` |

### Custom Port

```bash
python -m messaging_agent --port 8080
```

### Custom Host

```bash
python -m messaging_agent --host 127.0.0.1 --port 8080
```

## Testing

### Unit Tests

Run the complete test suite:

```bash
python test_messaging.py
```

### Manual Testing

1. **Start the agent**
   ```bash
   python -m messaging_agent
   ```

2. **Send a test message** (via A2A client or API)
   ```json
   {
     "action": "send_appointment_sms",
     "phone_number": "+11234567890",
     "appointment_slots": [...],
     "conversation_id": "test_001"
   }
   ```

3. **Simulate user response**
   ```bash
   python sms_simulator.py respond test_001 1
   ```

4. **Check response**
   ```json
   {
     "action": "check_sms_response",
     "conversation_id": "test_001"
   }
   ```

## Troubleshooting

### No SMS messages appearing

Check that the `message_state` directory exists:
```bash
ls -la messaging_agent/message_state/
```

If missing, it will be created automatically on first use.

### State not persisting

Ensure write permissions:
```bash
chmod -R 755 messaging_agent/message_state/
```

### AWS Bedrock errors

Verify credentials:
```bash
echo $AWS_ACCESS_KEY_ID
echo $AWS_REGION
```

Test Bedrock access:
```bash
aws bedrock list-foundation-models --region us-east-1
```

## Production SMS Setup

### AWS End User Messaging Integration

The messaging agent includes production-ready AWS End User Messaging (SMS) integration.

**Quick Start:**

1. **Follow the setup guide**: [AWS_END_USER_MESSAGING_SETUP.md](AWS_END_USER_MESSAGING_SETUP.md)
2. **Purchase AWS phone number** (~$1-2/month)
3. **Update `.env`**:
   ```bash
   AWS_SMS_ORIGINATION_NUMBER=+1234567890
   ```
4. **Update code** (2 lines):
   ```python
   # messaging_mcp.py
   from aws_sms_gateway import create_sms_gateway

   # __main__.py
   from aws_sms_webhook import router as sms_router
   ```
5. **Deploy webhook** for incoming SMS

**Features:**
- ✅ Two-way SMS communication
- ✅ Automatic mock/production mode switching
- ✅ HIPAA-compliant ready
- ✅ ~$0.00645 per SMS
- ✅ Integrated with existing AWS credentials

**Documentation:**
- [AWS_END_USER_MESSAGING_SETUP.md](AWS_END_USER_MESSAGING_SETUP.md) - Complete setup guide
- [AWS_END_USER_MESSAGING_MIGRATION.md](AWS_END_USER_MESSAGING_MIGRATION.md) - Technical details
- [NEXT_STEPS.md](NEXT_STEPS.md) - Quick start guide

### State Management at Scale

For production:
- Use database instead of JSON files
- Implement proper indexes on conversation_id
- Add TTL for old conversations
- Use message queue for async processing

### Security

- Encrypt conversation state at rest
- Use IAM roles instead of access keys
- Implement rate limiting
- Validate phone numbers
- Sanitize all inputs

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]