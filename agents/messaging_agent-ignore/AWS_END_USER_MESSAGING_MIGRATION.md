# Migration to AWS End User Messaging

## Why We're Migrating

**AWS Pinpoint is being deprecated** (end of support: October 2026, no new customers accepted).

**AWS End User Messaging** is the official AWS replacement service for SMS and push notifications.

---

## What Changed

### New Files Created:

1. **`aws_sms_gateway.py`** - Replacement for `pinpoint_gateway.py`
   - Uses `pinpoint-sms-voice-v2` boto3 client (instead of `pinpoint`)
   - Simpler API (no app ID required)
   - Same mock fallback pattern

2. **`aws_sms_webhook.py`** - Replacement for `sms_webhook.py`
   - Updated event structure for AWS End User Messaging
   - Works with EventBridge or SNS
   - Same conversation routing logic

3. **`AWS_END_USER_MESSAGING_SETUP.md`** - New setup guide
   - Step-by-step AWS configuration
   - Phone number purchase instructions
   - SNS topic setup
   - Webhook deployment guide

### Files Updated:

1. **`example.env`** - New environment variables
   ```bash
   # OLD (Pinpoint):
   AWS_PINPOINT_APP_ID=abc123
   AWS_PINPOINT_ORIGINATION_NUMBER=+1234567890

   # NEW (End User Messaging):
   AWS_SMS_ORIGINATION_NUMBER=+1234567890
   # No app ID needed!
   ```

---

## API Differences

### Sending SMS:

**Old (Pinpoint)**:
```python
self.pinpoint = boto3.client('pinpoint')
response = self.pinpoint.send_messages(
    ApplicationId=self.app_id,
    MessageRequest={
        'Addresses': {
            phone_number: {'ChannelType': 'SMS'}
        },
        'MessageConfiguration': {
            'SMSMessage': {
                'Body': message,
                'MessageType': 'TRANSACTIONAL'
            }
        }
    }
)
```

**New (End User Messaging)**:
```python
self.sms_client = boto3.client('pinpoint-sms-voice-v2')
response = self.sms_client.send_text_message(
    DestinationPhoneNumber=phone_number,
    OriginationIdentity=self.origination_number,
    MessageBody=message,
    MessageType='TRANSACTIONAL'
)
```

### Receiving SMS:

**Old (Pinpoint)**:
```json
{
  "Type": "Notification",
  "Message": {
    "originationNumber": "+1234567890",
    "destinationNumber": "+0987654321",
    "messageBody": "User response",
    "inboundMessageId": "..."
  }
}
```

**New (End User Messaging)**:
```json
{
  "version": "0",
  "source": "aws.sms-voice",
  "detail-type": "SMS Inbound Message",
  "detail": {
    "originationPhoneNumber": "+1234567890",
    "destinationPhoneNumber": "+0987654321",
    "messageBody": "User response",
    "messageId": "...",
    "timestamp": "..."
  }
}
```

---

## Migration Steps

### Step 1: Keep Existing Code Working

Good news! The old `pinpoint_gateway.py` and `sms_webhook.py` still work with mock mode:

```python
# messaging_mcp.py still works as-is
from pinpoint_gateway import create_sms_gateway
sms_gateway = create_sms_gateway()  # Auto-uses mock mode
```

### Step 2: Update Code to Use New Gateway (When Ready)

Update `messaging_mcp.py`:

```python
# OLD:
from pinpoint_gateway import create_sms_gateway

# NEW:
from aws_sms_gateway import create_sms_gateway

sms_gateway = create_sms_gateway()  # Same API!
```

Update `__main__.py`:

```python
# OLD:
from sms_webhook import router as sms_router

# NEW:
from aws_sms_webhook import router as sms_router

app.include_router(sms_router)  # Same API!
```

### Step 3: Update Environment Variables

```bash
# .env file changes:

# Remove (Pinpoint):
# AWS_PINPOINT_APP_ID=abc123
# AWS_PINPOINT_REGION=us-east-1

# Add (End User Messaging):
AWS_SMS_ORIGINATION_NUMBER=+1234567890
```

### Step 4: Follow Setup Guide

Follow [AWS_END_USER_MESSAGING_SETUP.md](AWS_END_USER_MESSAGING_SETUP.md) for:
1. Purchasing phone number
2. Configuring two-way SMS
3. Setting up SNS topic
4. Subscribing webhook

---

## Benefits of Migration

✅ **Future-proof**: AWS End User Messaging is actively supported
✅ **Simpler API**: No app ID required, cleaner code
✅ **Same cost**: $0.00645/SMS (unchanged)
✅ **Same features**: Two-way SMS, delivery tracking, HIPAA-ready
✅ **Better integration**: EventBridge support for event-driven architecture
✅ **Backward compatible**: Mock mode still works the same way

---

## Testing After Migration

### Test Mock Mode (No Changes):

```bash
# Should work exactly as before
cd A2A-Framework/messaging_agent
python __main__.py

# Test via host agent Gradio interface
cd ../host_agent
python __main__.py
```

### Test Production Mode (After AWS Setup):

```bash
# Set environment variable
export AWS_SMS_ORIGINATION_NUMBER=+1234567890

# Start messaging agent
python __main__.py

# Send test SMS via Gradio or quick_test.py
```

---

## Rollback Plan

If you encounter issues, you can temporarily rollback:

```python
# messaging_mcp.py
from pinpoint_gateway import create_sms_gateway  # Use old gateway

# .env
AWS_PINPOINT_APP_ID=abc123  # Restore old config
```

---

## Timeline

- **Now**: Both old (Pinpoint) and new (End User Messaging) code coexist
- **Recommended**: Migrate to End User Messaging before setting up production
- **Deadline**: AWS Pinpoint support ends October 2026

---

## Summary

The migration is **low-risk** because:
- ✅ Mock mode still works identically
- ✅ Gateway API is the same (`send_sms()` method)
- ✅ Webhook API is the same (conversation routing unchanged)
- ✅ Environment variables are the only breaking change
- ✅ Can rollback easily if needed

**Recommendation**: Use the new `aws_sms_gateway.py` for all new production setups.

---

## Questions?

- **Setup questions**: See [AWS_END_USER_MESSAGING_SETUP.md](AWS_END_USER_MESSAGING_SETUP.md)
- **API questions**: See [aws_sms_gateway.py](aws_sms_gateway.py) code comments
- **Webhook questions**: See [aws_sms_webhook.py](aws_sms_webhook.py) code comments