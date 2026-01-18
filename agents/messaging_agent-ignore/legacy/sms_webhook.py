"""SMS Webhook Handler for receiving incoming messages from AWS Pinpoint.

This module provides a webhook endpoint that receives incoming SMS messages
from AWS Pinpoint (via SNS) and processes them automatically.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse

from messaging_mcp import message_state, sms_gateway

logger = logging.getLogger(__name__)

# Create router for webhook endpoints
router = APIRouter(prefix="/sms", tags=["sms"])


@router.post("/webhook")
async def receive_sms_webhook(request: Request):
    """Webhook endpoint to receive incoming SMS from AWS Pinpoint via SNS.

    AWS Pinpoint sends incoming SMS messages to an SNS topic, which then
    triggers this webhook with the message details.

    Expected payload structure (from SNS):
    {
        "Type": "Notification",
        "MessageId": "...",
        "Message": "{...}",  # JSON string with actual SMS data
        ...
    }

    The nested Message contains:
    {
        "originationNumber": "+1234567890",
        "destinationNumber": "+0987654321",
        "messageBody": "User's response text",
        "inboundMessageId": "...",
        "messageKeyword": "..."
    }
    """
    try:
        # Parse request body
        body = await request.body()
        data = json.loads(body)

        # Handle SNS subscription confirmation
        if data.get('Type') == 'SubscriptionConfirmation':
            return await handle_sns_subscription(data)

        # Handle SNS notification (actual SMS message)
        if data.get('Type') == 'Notification':
            return await handle_incoming_sms(data)

        logger.warning(f"Unknown SNS message type: {data.get('Type')}")
        return Response(status_code=200)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook request: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    except Exception as e:
        logger.error(f"Error processing SMS webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_sns_subscription(data: dict) -> PlainTextResponse:
    """Handle SNS subscription confirmation.

    When you first subscribe your webhook to an SNS topic, AWS sends a
    confirmation message. You need to visit the SubscribeURL to confirm.
    """
    subscribe_url = data.get('SubscribeURL')

    if subscribe_url:
        logger.info(f"SNS Subscription confirmation received")
        logger.info(f"Visit this URL to confirm: {subscribe_url}")

        # In production, you might want to automatically confirm by visiting the URL
        # For now, we'll just log it and return success
        return PlainTextResponse(
            "SNS subscription confirmation received. Check logs for confirmation URL.",
            status_code=200
        )

    logger.error("SNS subscription confirmation missing SubscribeURL")
    raise HTTPException(status_code=400, detail="Missing SubscribeURL")


async def handle_incoming_sms(data: dict) -> Response:
    """Process incoming SMS message from AWS Pinpoint.

    Args:
        data: SNS notification containing SMS data

    Returns:
        HTTP response
    """
    try:
        # Extract the nested Message field (contains actual SMS data)
        message_str = data.get('Message', '{}')
        message_data = json.loads(message_str)

        # Extract SMS details
        from_number = message_data.get('originationNumber')
        to_number = message_data.get('destinationNumber')
        message_body = message_data.get('messageBody', '').strip()
        message_id = message_data.get('inboundMessageId')

        logger.info(
            f"Received SMS: From={from_number}, To={to_number}, "
            f"Body='{message_body}', ID={message_id}"
        )

        if not from_number or not message_body:
            logger.error("Missing required fields in incoming SMS")
            return Response(status_code=400)

        # Find active conversation for this phone number
        conversation = message_state.find_conversation_by_phone(from_number)

        if not conversation:
            logger.warning(f"No active conversation found for phone number: {from_number}")

            # You could optionally create a new conversation or send an error message
            return Response(
                content=json.dumps({
                    "status": "no_active_conversation",
                    "phone_number": from_number
                }),
                status_code=200
            )

        conversation_id = conversation['conversation_id']

        # Store the user's response
        if hasattr(sms_gateway, 'simulate_user_response'):
            # Mock gateway - use simulate method
            success = sms_gateway.simulate_user_response(conversation_id, message_body)
        else:
            # Real gateway - manually update conversation state
            success = store_user_response(conversation_id, message_body, from_number)

        if success:
            logger.info(
                f"Successfully stored response for conversation {conversation_id}: '{message_body}'"
            )

            return Response(
                content=json.dumps({
                    "status": "success",
                    "conversation_id": conversation_id,
                    "response": message_body
                }),
                status_code=200
            )
        else:
            logger.error(f"Failed to store response for conversation {conversation_id}")
            return Response(status_code=500)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse nested Message JSON: {e}")
        return Response(status_code=400)

    except Exception as e:
        logger.error(f"Error handling incoming SMS: {e}", exc_info=True)
        return Response(status_code=500)


def store_user_response(conversation_id: str, response: str, phone_number: str) -> bool:
    """Store user response in conversation state.

    Args:
        conversation_id: Conversation identifier
        response: User's SMS response text
        phone_number: User's phone number

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load conversation
        conversation = message_state.load_conversation(conversation_id)

        if not conversation:
            logger.error(f"Conversation {conversation_id} not found")
            return False

        # Update conversation with response
        conversation['user_response'] = response
        conversation['response_timestamp'] = datetime.now().isoformat()
        conversation['status'] = 'response_received'

        # Parse response to determine action
        response_upper = response.upper().strip()

        # Check if user selected a slot number
        try:
            slot_number = int(response_upper)
            # Find selected slot
            selected_slot = None
            for slot in conversation.get('appointment_slots', []):
                if slot.get('slot_number') == slot_number:
                    selected_slot = slot
                    break

            if selected_slot:
                conversation['status'] = 'slot_confirmed'
                conversation['selected_slot'] = selected_slot
                logger.info(f"User selected slot {slot_number} in conversation {conversation_id}")

        except ValueError:
            # Not a number, check for keywords
            if response_upper == 'NONE':
                conversation['status'] = 'slots_declined'
                logger.info(f"User declined all slots in conversation {conversation_id}")

        # Save updated conversation
        message_state.save_conversation(conversation_id, conversation)

        return True

    except Exception as e:
        logger.error(f"Error storing user response: {e}", exc_info=True)
        return False


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for webhook."""
    return {
        "status": "healthy",
        "service": "sms-webhook",
        "timestamp": datetime.now().isoformat()
    }
