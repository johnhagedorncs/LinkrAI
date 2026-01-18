# Twilio SMS Integration Guide

This guide explains how to use Twilio as your SMS provider in the Artera messaging agent.

## Overview

The messaging agent now supports **multiple SMS providers**:

1. **Twilio** (recommended for production) - Full-featured, reliable SMS service
2. **AWS End User Messaging** - Alternative production option
3. **Mock Gateway** - For testing without sending real SMS

The system automatically detects which provider to use based on your environment variables, with **Twilio as the preferred provider** if configured.

## Prerequisites

- Twilio account (sign up at https://www.twilio.com)
- Twilio phone number capable of sending SMS
- Account SID and Auth Token from Twilio console

## Configuration

### Step 1: Get Your Twilio Credentials

1. Log in to your Twilio console: https://console.twilio.com
2. Find your **Account SID** and **Auth Token** on the dashboard
3. Navigate to Phone Numbers → Active numbers
4. Copy your SMS-capable phone number (must be in E.164 format: +1234567890)

### Step 2: Update Environment Variables

Add these variables to your `.env` file:

```bash
# Twilio SMS Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+15555551234
```

**Important:** Replace `your_auth_token_here` with your actual Twilio auth token.

### Step 3: Install Dependencies

```bash
cd A2A-Framework/messaging_agent
pip install -r requirements.txt
```

This installs the `requests` library needed for Twilio API calls.

## Testing the Integration

### Basic Configuration Test

```bash
python test_twilio.py
```

This runs a series of tests:
- ✓ Checks if Twilio credentials are configured
- ✓ Tests TwilioGateway initialization
- ✓ Verifies unified gateway auto-detection

### Send Test SMS

To send an actual test SMS:

```bash
python test_twilio.py --send +19253244134
```

Replace `+19253244134` with your test phone number (must be E.164 format).

**Expected output:**
```
✓ SMS sent successfully!
  Message ID: SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  Status: queued
  Provider: twilio
  Timestamp: 2025-01-13T...
  Price: -0.00750 USD
```

## Usage in Your Application

### Automatic Provider Selection

The messaging agent automatically selects Twilio if configured:

```python
from aws_sms_gateway import create_unified_gateway

# Auto-detect provider (Twilio > AWS > Mock)
gateway = create_unified_gateway()

# Send SMS
result = gateway.send_sms(
    phone_number="+19253244134",
    message="Hello from Artera!",
    conversation_id="conv_123"
)

print(f"Sent via {result['provider']}")  # Should show "twilio"
```

### Force Specific Provider

```python
# Force Twilio
gateway = create_unified_gateway(provider='twilio')

# Force AWS
gateway = create_unified_gateway(provider='aws')

# Force Mock (testing)
gateway = create_unified_gateway(provider='mock')
```

## API Response Format

When sending via Twilio, the response includes:

```python
{
    'message_id': 'SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  # Twilio SID
    'conversation_id': 'conv_123',
    'phone_number': '+19253244134',
    'direction': 'outbound',
    'timestamp': '2025-01-13T12:34:56.789000',
    'status': 'queued',  # or 'sent', 'delivered', 'failed'
    'response': None,
    'response_timestamp': None,
    'provider': 'twilio',
    'twilio_data': {
        'sid': 'SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'account_sid': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'date_created': 'Wed, 07 Jan 2026 23:21:14 +0000',
        'price': '-0.00750',
        'price_unit': 'USD'
    }
}
```

## Message Status Tracking

Check delivery status of a sent message:

```python
from twilio_gateway import TwilioGateway

gateway = TwilioGateway()
status = gateway.get_message_status('SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

print(status['status'])  # queued, sent, delivered, failed, etc.
print(status['error_code'])  # Error code if failed
```

## Receiving SMS (Webhooks)

To receive SMS replies from users, you need to configure a webhook in Twilio:

### Step 1: Set Up Webhook Endpoint

The messaging agent already includes webhook support. Deploy your webhook endpoint and note the URL (e.g., `https://your-domain.com/sms/webhook`).

### Step 2: Configure Twilio Webhook

1. Go to Twilio Console → Phone Numbers → Active numbers
2. Click your SMS-capable number
3. Under "Messaging", find "A MESSAGE COMES IN"
4. Set webhook URL: `https://your-domain.com/sms/webhook`
5. Method: `POST`
6. Save

### Step 3: Test Incoming SMS

When a user replies to your SMS:
1. Twilio sends a POST request to your webhook
2. Webhook looks up the conversation by phone number
3. Response is stored in conversation state
4. Agent can check for response using `check_sms_response` tool

## Pricing

Twilio SMS pricing (as of 2025):
- **Outbound SMS (US):** ~$0.0075 per message
- **Inbound SMS (US):** ~$0.0075 per message
- **Phone number:** ~$1-2/month (local) or ~$2-3/month (toll-free)

Compare to AWS End User Messaging: ~$0.00645 per SMS

## Troubleshooting

### "ValueError: Account SID is required"

**Problem:** Twilio credentials not found in environment.

**Solution:**
1. Check that `.env` file exists in `messaging_agent/` directory
2. Verify `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` are set
3. Make sure you're loading the `.env` file with `python-dotenv`

### "HTTP 401 Unauthorized"

**Problem:** Invalid auth token or account SID.

**Solution:**
1. Verify credentials in Twilio console
2. Regenerate auth token if needed
3. Update `.env` file with correct credentials

### "HTTP 400 Bad Request - Invalid phone number"

**Problem:** Phone number not in E.164 format.

**Solution:**
- Phone numbers must start with `+` and country code
- Correct: `+19253244134`
- Incorrect: `9253244134` or `(925) 324-4134`

### "Phone number not capable of sending SMS"

**Problem:** Your Twilio number doesn't have SMS capabilities.

**Solution:**
1. Go to Twilio Console → Phone Numbers
2. Click your number
3. Check "Capabilities" - SMS should be enabled
4. If not enabled, purchase a new SMS-capable number

## Migration from Mock/AWS to Twilio

If you're currently using Mock or AWS, switching to Twilio is simple:

1. Add Twilio credentials to `.env`:
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_FROM_NUMBER=+1234567890
   ```

2. Restart the messaging agent:
   ```bash
   cd A2A-Framework/messaging_agent
   python -m messaging_agent
   ```

3. Verify Twilio is active:
   ```bash
   python test_twilio.py
   ```

The system automatically prioritizes Twilio if credentials are present. **No code changes required!**

## Security Best Practices

1. **Never commit `.env` to git** - It contains sensitive credentials
2. **Use environment-specific configs** - Different `.env` for dev/staging/prod
3. **Rotate credentials regularly** - Regenerate auth tokens periodically
4. **Validate webhook signatures** - Verify incoming webhooks are from Twilio
5. **Use HTTPS for webhooks** - Twilio requires HTTPS in production

## Support

- **Twilio Docs:** https://www.twilio.com/docs/sms
- **Twilio Support:** https://support.twilio.com
- **Project Issues:** Check the Artera Project repository

## Summary

✅ **Twilio integration complete!**

Your messaging agent now supports:
- Multi-provider SMS (Twilio, AWS, Mock)
- Automatic provider detection
- Production-ready Twilio gateway
- Full two-way SMS support
- Message status tracking
- Webhook integration for incoming messages

To activate Twilio, simply add your credentials to `.env` and restart the agent. The system will automatically detect and use Twilio as the preferred provider.
