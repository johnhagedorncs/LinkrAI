# AWS End User Messaging Setup Guide

Complete guide to setting up AWS End User Messaging for production SMS in the messaging agent.

**Note**: AWS End User Messaging is the successor to AWS Pinpoint (which is being deprecated in October 2026).

---

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Phone number for SMS (can purchase through AWS)

---

## Step 1: Access AWS End User Messaging

### Via AWS Console:

1. Go to **AWS End User Messaging Console**: https://console.aws.amazon.com/sms-voice/
2. Click **Manage SMS** to get started with SMS messaging
3. You'll see the SMS configuration dashboard

---

## Step 2: Request Phone Number (Required for Sending)

### Purchase Dedicated Phone Number:

1. In AWS End User Messaging console, go to **Phone numbers**
2. Click **Request phone number**
3. Select:
   - **Country**: United States
   - **Number capabilities**: SMS (select both send and receive)
   - **Number type**:
     - **Toll-free** (easier approval, ~$2/month) OR
     - **10DLC** (long code, better for high volume, requires registration)
4. For **10DLC** (recommended for healthcare):
   - Complete company registration
   - Register use case (Healthcare appointment notifications)
   - Provide sample message content
   - Wait for approval (typically 1-5 business days)
5. **Purchase** the phone number
6. **Copy the phone number** (format: +12345678900) for your `.env` file

**Costs**:
- Toll-free: ~$2/month + $0.00645/SMS
- 10DLC: ~$1-2/month + $0.00645/SMS

---

## Step 3: Configure Phone Number Settings

### Enable Two-Way SMS:

1. Go to **Phone numbers** and select your purchased number
2. Under **Two-way SMS**, enable it
3. Choose delivery method:
   - **EventBridge** (recommended - simpler, direct)
   - **SNS topic** (if you need to fan out to multiple subscribers)
4. If using EventBridge, incoming SMS will be published as events automatically
5. If using SNS, select or create an SNS topic (e.g., `healthcare-incoming-sms`)
6. Save configuration

**Note**: EventBridge is simpler and recommended for single webhook use cases. SNS adds an extra layer but is useful if you need to send incoming SMS to multiple destinations.

---

## Step 4: Set Up Event Destination for Incoming SMS

### Option A: EventBridge (Recommended - Simpler)

No additional setup required! When you enable two-way SMS with EventBridge:
- Events are automatically published to your default event bus
- Event pattern: `source: "aws.sms-voice"`, `detail-type: "SMS Inbound Message"`
- You'll create an EventBridge rule to route to your webhook (Step 5)

### Option B: SNS Topic (If You Need Fan-Out)

Only needed if you want to send incoming SMS to multiple destinations:

```bash
# Create SNS topic for incoming messages
aws sns create-topic --name healthcare-incoming-sms --region us-east-1

# Output will contain TopicArn - save this!
# Example: arn:aws:sns:us-east-1:123456789012:healthcare-incoming-sms
```

Then link it to your phone number:
1. Go to your phone number settings
2. Under **Two-way SMS**, select the SNS topic you just created
3. Save changes

---

## Step 5: Route Events to Your Webhook

### Get Your Webhook URL:

Your webhook will be: `https://your-domain.com/sms/webhook`

**For local testing**, use **ngrok**:

```bash
# Install ngrok
brew install ngrok  # Mac
# or download from ngrok.com

# Start ngrok tunnel (while messaging agent runs on port 10003)
ngrok http 10003

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Your webhook: https://abc123.ngrok.io/sms/webhook
```

### Option A: EventBridge Rule (Recommended)

Create an EventBridge rule to route SMS events to your webhook:

```bash
# Create API Destination for your webhook
aws events create-api-destination \
  --name sms-webhook \
  --invocation-endpoint https://your-domain.com/sms/webhook \
  --http-method POST \
  --region us-east-1

# Create Connection (for auth if needed)
aws events create-connection \
  --name sms-webhook-connection \
  --authorization-type API_KEY \
  --region us-east-1

# Create EventBridge rule
aws events put-rule \
  --name incoming-sms-to-webhook \
  --event-pattern '{
    "source": ["aws.sms-voice"],
    "detail-type": ["SMS Inbound Message"]
  }' \
  --region us-east-1

# Add webhook as target
aws events put-targets \
  --rule incoming-sms-to-webhook \
  --targets "Id"="1","Arn"="arn:aws:events:us-east-1:ACCOUNT:api-destination/sms-webhook" \
  --region us-east-1
```

**Or use AWS Console:**
1. Go to **EventBridge** → **Rules**
2. Click **Create rule**
3. Event pattern:
   - Source: `aws.sms-voice`
   - Detail type: `SMS Inbound Message`
4. Target: **API destination** → Your webhook URL
5. Create rule

### Option B: SNS Subscription (If Using SNS)

Only if you chose SNS in Step 4:

```bash
# Replace with your values
SNS_TOPIC_ARN="arn:aws:sns:us-east-1:123456789012:healthcare-incoming-sms"
WEBHOOK_URL="https://your-domain.com/sms/webhook"

aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol https \
  --notification-endpoint $WEBHOOK_URL \
  --region us-east-1
```

Then confirm subscription:
1. AWS will send a confirmation request to your webhook
2. Check your messaging agent logs for the `SubscribeURL`
3. Visit that URL in your browser to confirm

---

## Step 6: Configure Environment Variables

Update your `.env` file:

```bash
# AWS Credentials (same as Bedrock)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1

# AWS End User Messaging SMS Configuration
AWS_SMS_ORIGINATION_NUMBER=+12345678900  # Your purchased phone number
AWS_SMS_CONFIGURATION_SET=  # Optional: for tracking (can leave empty)

# Use mock SMS for development, real AWS SMS for production
USE_MOCK_SMS=false
```

**Important**: The new gateway uses `AWS_SMS_ORIGINATION_NUMBER` instead of `AWS_PINPOINT_APP_ID`.

---

## Step 7: Update IAM Permissions

Your AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sms-voice:SendTextMessage",
        "sms-voice:DescribePhoneNumbers",
        "sms-voice:DescribeConfigurationSets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Subscribe",
        "sns:Receive"
      ],
      "Resource": "arn:aws:sns:*:*:healthcare-incoming-sms"
    }
  ]
}
```

### Apply via AWS CLI:

```bash
# Save the JSON policy to a file: aws-sms-policy.json

aws iam put-user-policy \
  --user-name your-user \
  --policy-name AWSEndUserMessagingSMSAccess \
  --policy-document file://aws-sms-policy.json
```

---

## Step 8: Update Messaging Agent Code

### Update `messaging_mcp.py`:

Replace the gateway initialization:

```python
# OLD (Pinpoint):
# from pinpoint_gateway import create_sms_gateway

# NEW (AWS End User Messaging):
from aws_sms_gateway import create_sms_gateway

# Gateway auto-detects mode (mock or production)
sms_gateway = create_sms_gateway()
```

### Update `__main__.py`:

Replace webhook router:

```python
# OLD (Pinpoint webhook):
# from sms_webhook import router as sms_router

# NEW (AWS End User Messaging webhook):
from aws_sms_webhook import router as sms_router

# Add webhook routes
app.include_router(sms_router)
```

---

## Step 9: Test the Integration

### Test Sending SMS:

```bash
cd A2A-Framework/messaging_agent

# Ensure .env has AWS_SMS_ORIGINATION_NUMBER set
# Run messaging agent
python __main__.py

# In another terminal, test via host agent Gradio interface
cd ../host_agent
python __main__.py
# Visit http://localhost:7860
```

**Test via Gradio**:
1. Ask: "Send appointment slots to +1YOUR_REAL_NUMBER"
2. Check your phone for the SMS
3. Reply with a slot number (e.g., "1")
4. Ask: "Check if user responded to conversation test_123"

### Test via AWS CLI (Direct):

```bash
# Send test SMS directly via AWS CLI
aws pinpoint-sms-voice-v2 send-text-message \
  --destination-phone-number +11234567890 \
  --origination-identity +10987654321 \
  --message-body "Test message from AWS End User Messaging" \
  --region us-east-1
```

### Test Receiving SMS (Manual):

1. Send SMS to your AWS phone number from your personal phone
2. Check messaging agent logs for incoming webhook
3. Verify response is processed correctly

---

## Step 10: Production Deployment

### Deploy Webhook Publicly:

**Option A: AWS Lambda + API Gateway**
- Deploy webhook as Lambda function
- API Gateway provides HTTPS endpoint
- Lowest cost for low-volume

**Option B: AWS ECS/EC2 with ALB**
- Deploy messaging agent container
- Use Application Load Balancer for HTTPS
- Better for high-volume

**Option C: Your existing infrastructure**
- Ensure HTTPS is enabled
- Configure proper security groups
- Set up monitoring/logging

### Set Up CloudWatch Monitoring:

1. **CloudWatch Logs**: Monitor SMS delivery
2. **CloudWatch Alarms**: Alert on failures
3. **EventBridge Rules**: Track message events

---

## Architecture Comparison

### AWS Pinpoint (Deprecated) vs AWS End User Messaging:

| Feature | Pinpoint | End User Messaging |
|---------|----------|-------------------|
| **API** | `pinpoint.send_messages()` | `pinpoint-sms-voice-v2.send_text_message()` |
| **App ID** | Required | Not required |
| **Phone Number** | Optional (can use pool) | Required for sending |
| **Incoming SMS** | SNS via two-way config | SNS or EventBridge |
| **Cost** | Same ($0.00645/SMS) | Same ($0.00645/SMS) |
| **Status** | Deprecated Oct 2026 | Active, supported |

---

## Cost Estimation

| Item | Cost |
|------|------|
| AWS SMS (US outbound) | $0.00645/message |
| AWS SMS (US inbound) | $0.0075/message |
| Toll-free phone number | $2/month |
| 10DLC phone number | $1-2/month |
| SNS notifications | $0.50/million (~free) |
| **Total (1000 SMS/month)** | **~$8-10/month** |

---

## Troubleshooting

### SMS Not Sending

**Check:**
- ✅ Phone number is purchased and active
- ✅ Phone number has SMS send capability enabled
- ✅ Account spending limit not exceeded
- ✅ Phone number format is E.164 (+1234567890)
- ✅ IAM permissions are correct
- ✅ AWS credentials are valid

**View logs:**
```bash
# Check CloudWatch logs for delivery events
aws logs tail /aws/sms-voice/messages --follow --region us-east-1
```

### SMS Not Receiving

**Check:**
- ✅ Two-way SMS is enabled on phone number
- ✅ SNS topic is configured correctly
- ✅ Webhook is subscribed and confirmed
- ✅ Webhook endpoint is publicly accessible (HTTPS)
- ✅ Check webhook logs for errors

**Test SNS subscription:**
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:healthcare-incoming-sms
```

### Delivery Failures

**Common reasons:**
- Invalid phone number format
- Number is landline (SMS not supported)
- Carrier blocking messages
- Number is on suppression list
- Message content flagged as spam

---

## Security Best Practices

1. ✅ **Use IAM roles** instead of access keys in production
2. ✅ **Enable CloudTrail** for audit logging
3. ✅ **Encrypt sensitive data** with KMS
4. ✅ **Implement rate limiting** on webhook
5. ✅ **Verify SNS signatures** in webhook handler
6. ✅ **Use VPC endpoints** for API calls
7. ✅ **HIPAA BAA** - Sign AWS Business Associate Agreement

---

## HIPAA Compliance

To use AWS End User Messaging for healthcare data:

1. **Sign AWS BAA** (Business Associate Agreement)
   - Contact AWS support or sales
   - Required for HIPAA compliance

2. **Configure encryption**:
   - Enable KMS encryption for all data at rest
   - Use TLS 1.2+ for data in transit

3. **Access controls**:
   - Use IAM with least privilege
   - Enable MFA for all users
   - Log all access via CloudTrail

4. **Audit logging**:
   - Enable CloudTrail
   - Send logs to S3 with encryption
   - Set up alerts for suspicious activity

---

## Migration from Pinpoint

If you previously set up Pinpoint, here's how to migrate:

### Code Changes:

```python
# OLD (pinpoint_gateway.py):
self.pinpoint = boto3.client('pinpoint')
response = self.pinpoint.send_messages(
    ApplicationId=self.app_id,
    MessageRequest={...}
)

# NEW (aws_sms_gateway.py):
self.sms_client = boto3.client('pinpoint-sms-voice-v2')
response = self.sms_client.send_text_message(
    DestinationPhoneNumber=phone_number,
    OriginationIdentity=self.origination_number,
    MessageBody=message
)
```

### Environment Variables:

```bash
# OLD:
AWS_PINPOINT_APP_ID=abc123
AWS_PINPOINT_ORIGINATION_NUMBER=+1234567890

# NEW:
# AWS_PINPOINT_APP_ID is no longer needed
AWS_SMS_ORIGINATION_NUMBER=+1234567890
```

---

## Next Steps

Once AWS End User Messaging is set up:

1. ✅ Update `messaging_mcp.py` to use `aws_sms_gateway`
2. ✅ Update `__main__.py` to use `aws_sms_webhook`
3. ✅ Test thoroughly in development with ngrok
4. ✅ Deploy webhook endpoint with HTTPS
5. ✅ Monitor first few messages carefully
6. ✅ Set up CloudWatch alarms for failures

---

## Support & Resources

- **AWS End User Messaging Docs**: https://docs.aws.amazon.com/sms-voice/
- **API Reference**: https://docs.aws.amazon.com/sms-voice/latest/APIReference/
- **AWS Support**: Open ticket if issues arise
- **Pricing**: https://aws.amazon.com/sns/sms-pricing/

---

## Quick Reference Commands

```bash
# List phone numbers
aws pinpoint-sms-voice-v2 describe-phone-numbers --region us-east-1

# Send test SMS
aws pinpoint-sms-voice-v2 send-text-message \
  --destination-phone-number +11234567890 \
  --origination-identity +10987654321 \
  --message-body "Test message" \
  --region us-east-1

# Check SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:healthcare-incoming-sms

# View CloudWatch logs
aws logs tail /aws/sms-voice/messages --follow --region us-east-1
```

---

## Summary

You now have AWS End User Messaging (the Pinpoint successor) configured for production SMS! This service:

✅ Is actively supported by AWS (not deprecated)
✅ Uses simpler API (no app ID required)
✅ Costs the same as Pinpoint (~$0.00645/SMS)
✅ Supports two-way SMS via SNS/EventBridge
✅ Is HIPAA-compliant ready
✅ Integrates seamlessly with your existing AWS setup

**Ready for production! 🚀**