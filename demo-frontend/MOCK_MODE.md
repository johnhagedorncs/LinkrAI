# Mock Mode Documentation

## Overview

The demo backend now supports **full mock mode** when deployed without credentials. This allows the demo to run end-to-end on Vercel/Render without requiring:
- AWS credentials (S3, Transcribe, Bedrock)
- Athena Health API keys
- Running host agent infrastructure

## What Mock Mode Does

### 1. Audio Transcription Mock
When AWS credentials are not available:
- Audio upload to S3 is skipped (mock S3 URI returned)
- Pre-loaded medical transcript is returned (oncology consultation scenario)
- No actual AWS Transcribe Medical API call

### 2. Agent Processing Mock
When the host agent (port 8084) is not running:
- Mock agent responses are generated automatically
- Simulates the full agent workflow:
  - **Referral Agent**: Creates oncology referral (REF-789456)
  - **Scheduling Agent**: Finds 3 appointment slots
  - **Messaging Agent**: Sends SMS notification
- Response structure matches real agent output exactly

## How It Works

### Backend Changes

1. **Mock Agent Response Function** (`get_mock_agent_response`)
   - Returns realistic agent orchestration data
   - Includes tool calls, tool responses, and subagent details
   - Mimics real host agent behavior

2. **Automatic Fallback**
   - When `httpx.ConnectError` occurs (host agent not available)
   - Automatically switches to mock mode
   - No error shown to user

3. **Health Check Endpoint** (`GET /`)
   - Reports system mode: `"production"` or `"mock"`
   - Shows availability of:
     - AWS services
     - Scribe agent
     - Host agent

## Testing Mock Mode

### Local Testing
```bash
cd demo-frontend/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit: `http://localhost:8000/`

Expected response:
```json
{
  "status": "healthy",
  "service": "Healthcare Agent Demo API",
  "scribe_available": false,
  "aws_available": false,
  "host_agent_available": false,
  "mode": "mock"
}
```

### Deployment (Vercel + Render)

The deployed demo automatically runs in mock mode:
- ✅ No environment variables needed
- ✅ No AWS setup required
- ✅ No agent infrastructure needed
- ✅ Fully functional demo workflow

## Production Mode

To run in **production mode** (with real APIs):

1. Set environment variables:
   ```bash
   AWS_ACCESS_KEY_ID=xxx
   AWS_SECRET_ACCESS_KEY=xxx
   AWS_REGION=us-east-1
   TRANSCRIBE_OUTPUT_BUCKET=your-bucket
   ```

2. Start the host agent:
   ```bash
   python A2A-Framework/host_agent/api_server.py
   ```

3. Backend will automatically detect and use real services

## Mock Data Details

### Scenario: Prostate Cancer Oncology Referral

**Patient ID**: 12345
**Diagnosis**: Gleason 7 adenocarcinoma (PSA 12.4)
**Referral ID**: REF-789456

**Available Appointments**:
- Dr. Sarah Chen - Jan 25, 2026 at 10:00 AM
- Dr. Michael Rodriguez - Jan 26, 2026 at 2:30 PM
- Dr. Emily Thompson - Jan 27, 2026 at 9:00 AM

**SMS Sent**: 555-555-1234 with appointment options

## Benefits

1. **Zero Setup Demo**: Works immediately on Vercel without configuration
2. **Portfolio Ready**: Demonstrates full system capabilities without infrastructure
3. **Cost Effective**: No AWS charges for demo viewers
4. **Secure**: No credentials needed in public deployment
5. **Realistic**: Mock data mirrors real agent behavior exactly

## Future Enhancements

- [ ] Multiple mock scenarios (cardiology, neurology, etc.)
- [ ] Random appointment times for variety
- [ ] Mock error scenarios for testing
- [ ] WebSocket support for real-time updates
