"""AWS Pinpoint SMS Gateway for real SMS communication.

This module provides a production-ready SMS gateway using AWS Pinpoint
for sending and receiving SMS messages in healthcare applications.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class PinpointGateway:
    """AWS Pinpoint SMS gateway for sending and receiving messages."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        region_name: str = 'us-east-1',
        origination_number: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize AWS Pinpoint gateway.

        Args:
            app_id: AWS Pinpoint application ID
            region_name: AWS region (default: us-east-1)
            origination_number: Phone number to send from (optional)
            aws_access_key_id: AWS access key (uses env var if not provided)
            aws_secret_access_key: AWS secret key (uses env var if not provided)
        """
        self.app_id = app_id or os.getenv('AWS_PINPOINT_APP_ID')
        self.region_name = region_name
        self.origination_number = origination_number or os.getenv(
            'AWS_PINPOINT_ORIGINATION_NUMBER'
        )

        if not self.app_id:
            raise ValueError(
                "AWS Pinpoint App ID is required. Set AWS_PINPOINT_APP_ID environment variable."
            )

        # Initialize Pinpoint client
        client_kwargs = {'region_name': region_name}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs['aws_access_key_id'] = aws_access_key_id
            client_kwargs['aws_secret_access_key'] = aws_secret_access_key

        self.pinpoint = boto3.client('pinpoint', **client_kwargs)
        logger.info(f"Initialized AWS Pinpoint gateway (App ID: {self.app_id}, Region: {region_name})")

    def send_sms(
        self,
        phone_number: str,
        message: str,
        conversation_id: str,
        message_type: str = 'TRANSACTIONAL'
    ) -> dict:
        """Send SMS message via AWS Pinpoint.

        Args:
            phone_number: Recipient phone number (E.164 format, e.g., +1234567890)
            message: SMS message content
            conversation_id: Unique conversation identifier
            message_type: TRANSACTIONAL or PROMOTIONAL (default: TRANSACTIONAL)

        Returns:
            dict: Message metadata including message_id, status, timestamp

        Raises:
            ClientError: If SMS sending fails
        """
        # Validate phone number format
        if not phone_number.startswith('+'):
            logger.warning(f"Phone number {phone_number} doesn't start with '+', adding +1")
            phone_number = f'+1{phone_number}'

        try:
            # Prepare message request
            message_request = {
                'Addresses': {
                    phone_number: {
                        'ChannelType': 'SMS'
                    }
                },
                'MessageConfiguration': {
                    'SMSMessage': {
                        'Body': message,
                        'MessageType': message_type
                    }
                }
            }

            # Add origination number if configured
            if self.origination_number:
                message_request['MessageConfiguration']['SMSMessage']['OriginationNumber'] = (
                    self.origination_number
                )

            # Send message via Pinpoint
            response = self.pinpoint.send_messages(
                ApplicationId=self.app_id,
                MessageRequest=message_request
            )

            # Extract result
            result = response['MessageResponse']['Result'][phone_number]

            if result['DeliveryStatus'] == 'SUCCESSFUL':
                logger.info(
                    f"Successfully sent SMS to {phone_number} (Message ID: {result['MessageId']})"
                )

                return {
                    'message_id': result['MessageId'],
                    'conversation_id': conversation_id,
                    'phone_number': phone_number,
                    'direction': 'outbound',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'sent',
                    'delivery_status': result['DeliveryStatus'],
                    'status_code': result['StatusCode'],
                    'response': None,
                    'response_timestamp': None,
                }
            else:
                logger.error(
                    f"Failed to send SMS to {phone_number}: {result.get('StatusMessage')}"
                )
                raise ClientError(
                    {'Error': {'Message': result.get('StatusMessage', 'Unknown error')}},
                    'send_messages'
                )

        except ClientError as e:
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Pinpoint error sending SMS: {error_message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            raise

    def get_sms_delivery_status(self, message_id: str) -> dict:
        """Get delivery status for a sent message.

        Args:
            message_id: AWS Pinpoint message ID

        Returns:
            dict: Delivery status information

        Note:
            This requires CloudWatch Logs or Kinesis stream setup for detailed tracking.
        """
        # Note: Pinpoint doesn't have a direct API to query message status by ID
        # You'd need to set up CloudWatch Events or Kinesis stream for delivery tracking
        logger.warning(
            "Direct message status query not available. "
            "Set up CloudWatch Events or Kinesis for delivery tracking."
        )

        return {
            'message_id': message_id,
            'status': 'unknown',
            'note': 'Configure CloudWatch Events for delivery tracking'
        }


class PinpointGatewayWithFallback:
    """Pinpoint gateway with automatic fallback to mock for development.

    This allows seamless switching between production (Pinpoint) and
    development (Mock) modes based on configuration.
    """

    def __init__(self, use_mock: bool = False):
        """Initialize gateway with optional mock fallback.

        Args:
            use_mock: If True, use mock gateway instead of real Pinpoint
        """
        self.use_mock = use_mock or not os.getenv('AWS_PINPOINT_APP_ID')

        if self.use_mock:
            logger.warning("AWS Pinpoint not configured, using Mock SMS Gateway")
            from messaging_mcp import MockSMSGateway
            self.gateway = MockSMSGateway()
        else:
            logger.info("Using AWS Pinpoint SMS Gateway")
            self.gateway = PinpointGateway()

    def send_sms(self, phone_number: str, message: str, conversation_id: str) -> dict:
        """Send SMS (delegates to real or mock gateway)."""
        return self.gateway.send_sms(phone_number, message, conversation_id)


# Factory function for easy integration
def create_sms_gateway(use_mock: bool = False) -> PinpointGatewayWithFallback:
    """Create SMS gateway (Pinpoint or Mock based on configuration).

    Args:
        use_mock: Force mock mode (default: auto-detect from env vars)

    Returns:
        SMS gateway instance
    """
    return PinpointGatewayWithFallback(use_mock=use_mock)
