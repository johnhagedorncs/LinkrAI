# Testing the Scheduling Agent

This guide covers how to test the scheduling agent's SMS chatbot functionality with preference filtering.

## Quick Start

### Option 1: Run Automated Tests

```bash
cd A2A-Framework/scheduling_agent
uv run python test_scheduling_agent.py
```

This will run 6 test cases covering:
1. No preferences ("any day")
2. Monday mornings
3. Weekday afternoons
4. After 3pm (any day)
5. Weekends
6. Different specialty (family medicine)

### Option 2: Start the Agent Server

```bash
cd A2A-Framework/scheduling_agent
uv run python -m scheduling_agent
```

The server will start on `http://0.0.0.0:10005`

### Option 3: Test with curl

Start the server first, then send test requests:

```bash
# Test 1: Find appointments without preferences (any day)
curl -X POST http://localhost:10005/agent/task \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Find cardiology appointments for patient 60183. Any day works."
  }'

# Test 2: Find appointments for Monday mornings
curl -X POST http://localhost:10005/agent/task \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Find cardiology appointments for patient 60183. I prefer Monday mornings."
  }'

# Test 3: Find appointments for weekday afternoons
curl -X POST http://localhost:10005/agent/task \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Find cardiology appointments for patient 60183. I prefer weekdays after noon."
  }'
```

## Testing the SMS Conversation Flow

To test the full SMS chatbot conversation flow:

### Step 1: Start the Scheduling Agent
```bash
cd A2A-Framework/scheduling_agent
uv run python -m scheduling_agent
```

### Step 2: Start the Messaging Agent
```bash
cd A2A-Framework/messaging_agent
uv run python -m messaging_agent
```

### Step 3: Send Test SMS Messages

You can use the Twilio test script:

```bash
cd A2A-Framework/messaging_agent
uv run python test_twilio.py
```

**Note**: You need a valid `TWILIO_AUTH_TOKEN` in your `.env` file. Get it from https://console.twilio.com

### Example SMS Conversation Flow

**Message 1 (Patient):**
```
Need cardiology for patient 60183
```

**Message 2 (Agent):**
```
I'll find cardiology appointments for you. What days/times work best?
Examples: 'Mondays mornings', 'weekdays after 3pm', or 'any day'
```

**Message 3 (Patient):**
```
Monday mornings
```

**Message 4 (Agent):**
```
Found 3 Monday morning appointments:
1. Mon 11/25 at 09:00 - Dr. Smith
2. Mon 12/02 at 10:30 - Dr. Jones
3. Mon 12/09 at 09:15 - Dr. Williams

Reply 1, 2, or 3 to book
```

**Message 5 (Patient):**
```
1
```

**Message 6 (Agent):**
```
✅ Booked! Mon 11/25 at 09:00 with Dr. Smith
```

## Testing Preference Interpretation

The agent should interpret these patient responses correctly:

| Patient Says | Should Filter For |
|-------------|------------------|
| "any day" | No filters (earliest 3) |
| "ASAP" | No filters (earliest 3) |
| "Monday mornings" | Monday, 9am-12pm |
| "Monday or Wednesday" | Monday OR Wednesday |
| "weekdays" | Mon-Fri |
| "weekends" | Sat-Sun |
| "mornings" | 9am-12pm |
| "afternoons" | 12pm-5pm |
| "evenings" | 5pm-8pm |
| "after 3pm" | After 3pm (any day) |
| "before noon" | Before 12pm (any day) |

## Checking Logs

The scheduling agent logs detailed information about preference filtering:

```bash
# Start with verbose logging
cd A2A-Framework/scheduling_agent
LOG_LEVEL=DEBUG uv run python -m scheduling_agent
```

Look for log messages like:
```
INFO:scheduling-mcp-server:Finding appointment options: patient=60183, specialty=cardiology
INFO:scheduling-mcp-server:  Preferred days: ['Monday']
INFO:scheduling-mcp-server:  Preferred time range: 09:00 - 12:00
INFO:scheduling-mcp-server:Filtered 47 slots down to 12 matching preferences
```

## Troubleshooting

### Issue: No appointments found
- Check date range (defaults to 11/24/2025 - 12/24/2025)
- Try a different specialty
- Check Athena API credentials in `.env`

### Issue: Filtering not working
- Check log messages for "Filtered X slots down to Y"
- Verify preference parameters are being passed correctly
- Try with no preferences first ("any day") to verify slots exist

### Issue: Import errors
- Make sure dependencies are installed: `uv pip install -r requirements.txt`
- Or use `uv run` which handles dependencies automatically

### Issue: Twilio auth error
- Update `TWILIO_AUTH_TOKEN` in `.env` file
- Get token from https://console.twilio.com
- Or use Mock Mode: set `USE_MOCK_MODE=true` in `.env`

## Available Specialties

The agent currently supports these specialties:
- Cardiology
- Family Medicine
- Internal Medicine
- Pediatric Medicine
- Orthopedic Surgery
- Allergy/Immunology
- Cardiac Surgery
- And 10 more (see `athena_specialties.json`)

## Test Patient IDs

Use these patient IDs for testing:
- `60183` - Primary test patient
- Check Athena sandbox for more test patients

## Expected Behavior

### ✅ Success Cases
- Agent asks for preferences in one combined question
- Agent correctly interprets natural language ("Monday mornings" → filters applied)
- Agent shows exactly 3 options
- Agent numbers options 1, 2, 3 for easy selection
- Agent falls back to earliest slots if no matches

### ❌ Failure Cases to Avoid
- Don't ask multiple questions (ask day AND time separately)
- Don't ask for department_id or provider_id
- Don't show more than 3 options
- Don't fail if no exact matches (show closest options)

## Next Steps

After testing the scheduling agent:
1. Test the full A2A integration (messaging agent → scheduling agent)
2. Test on mobile device with real SMS
3. Test edge cases (no slots available, invalid specialty, etc.)
4. Monitor conversation turn count (should complete in ≤6 messages)
