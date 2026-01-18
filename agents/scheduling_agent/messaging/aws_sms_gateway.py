"""AWS End User Messaging SMS Gateway for real SMS communication.

This module provides a production-ready SMS gateway using AWS End User Messaging
(the successor to AWS Pinpoint) for sending and receiving SMS messages in healthcare applications.

AWS End User Messaging uses the pinpoint-sms-voice-v2 API.
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


class AWSEndUserMessagingGateway:
    """AWS End User Messaging SMS gateway for sending and receiving messages."""

    def __init__(
        self,
        origination_number: Optional[str] = None,
        region_name: str = 'us-east-1',
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        configuration_set_name: Optional[str] = None,
    ):
        """Initialize AWS End User Messaging SMS gateway.

        Args:
            origination_number: Phone number to send from (required for sending)
            region_name: AWS region (default: us-east-1)
            aws_access_key_id: AWS access key (uses env var if not provided)
            aws_secret_access_key: AWS secret key (uses env var if not provided)
            configuration_set_name: Optional configuration set for tracking
        """
        self.region_name = region_name
        self.origination_number = origination_number or os.getenv(
            'AWS_SMS_ORIGINATION_NUMBER'
        )
        self.configuration_set_name = configuration_set_name or os.getenv(
            'AWS_SMS_CONFIGURATION_SET'
        )

        if not self.origination_number:
            raise ValueError(
                "Origination number is required. Set AWS_SMS_ORIGINATION_NUMBER environment variable."
            )

        # Initialize SMS client (pinpoint-sms-voice-v2)
        client_kwargs = {'region_name': region_name}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs['aws_access_key_id'] = aws_access_key_id
            client_kwargs['aws_secret_access_key'] = aws_secret_access_key

        self.sms_client = boto3.client('pinpoint-sms-voice-v2', **client_kwargs)
        logger.info(
            f"Initialized AWS End User Messaging SMS gateway "
            f"(From: {self.origination_number}, Region: {region_name})"
        )

    def send_sms(
        self,
        phone_number: str,
        message: str,
        conversation_id: str,
        message_type: str = 'TRANSACTIONAL'
    ) -> dict:
        """Send SMS message via AWS End User Messaging.

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
            # Prepare send request for pinpoint-sms-voice-v2
            send_params = {
                'DestinationPhoneNumber': phone_number,
                'OriginationIdentity': self.origination_number,
                'MessageBody': message,
                'MessageType': message_type,
            }

            # Add configuration set if configured (for tracking)
            if self.configuration_set_name:
                send_params['ConfigurationSetName'] = self.configuration_set_name

            # Add context data for tracking
            send_params['Context'] = {
                'conversation_id': conversation_id,
                'timestamp': datetime.now().isoformat()
            }

            # Send message via AWS End User Messaging
            response = self.sms_client.send_text_message(**send_params)

            message_id = response.get('MessageId')

            logger.info(
                f"Successfully sent SMS to {phone_number} (Message ID: {message_id})"
            )

            return {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'phone_number': phone_number,
                'direction': 'outbound',
                'timestamp': datetime.now().isoformat(),
                'status': 'sent',
                'response': None,
                'response_timestamp': None,
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS SMS error ({error_code}): {error_message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            raise

    def get_sms_delivery_status(self, message_id: str) -> dict:
        """Get delivery status for a sent message.

        Args:
            message_id: AWS message ID

        Returns:
            dict: Delivery status information

        Note:
            Delivery events are typically received via EventBridge or SNS.
            This method is a placeholder for future implementation.
        """
        logger.warning(
            "Direct message status query not implemented. "
            "Use EventBridge or SNS for delivery event tracking."
        )

        return {
            'message_id': message_id,
            'status': 'unknown',
            'note': 'Configure EventBridge or SNS for delivery tracking'
        }


class AWSMessagingGatewayWithFallback:
    """AWS End User Messaging gateway with automatic fallback to mock for development.

    This allows seamless switching between production (AWS SMS) and
    development (Mock) modes based on configuration.
    """

    def __init__(self, use_mock: bool = False):
        """Initialize gateway with optional mock fallback.

        Args:
            use_mock: If True, use mock gateway instead of real AWS SMS
        """
        self.use_mock = use_mock or not os.getenv('AWS_SMS_ORIGINATION_NUMBER')

        if self.use_mock:
            logger.warning("AWS SMS not configured, using Mock SMS Gateway")
            from messaging_mcp import MockSMSGateway
            self.gateway = MockSMSGateway()
        else:
            logger.info("Using AWS End User Messaging SMS Gateway")
            self.gateway = AWSEndUserMessagingGateway()

    def send_sms(self, phone_number: str, message: str, conversation_id: str) -> dict:
        """Send SMS (delegates to real or mock gateway)."""
        return self.gateway.send_sms(phone_number, message, conversation_id)


class UnifiedMessagingGateway:
    """Unified messaging gateway that supports multiple SMS providers.

    Supports:
    - Twilio (default if configured)
    - AWS End User Messaging
    - Mock (development/testing)

    Priority order: Twilio > AWS > Mock
    """

    def __init__(self, provider: Optional[str] = None, use_mock: bool = False):
        """Initialize unified messaging gateway.

        Args:
            provider: Specific provider to use ('twilio', 'aws', or 'mock')
                     If None, auto-detects based on environment variables
            use_mock: Force mock mode (overrides provider selection)
        """
        self.provider_name = provider

        if use_mock:
            logger.info("Using Mock SMS Gateway (forced)")
            from messaging_mcp import MockSMSGateway
            self.gateway = MockSMSGateway()
            self.provider_name = 'mock'
        elif provider == 'twilio' or (not provider and os.getenv('TWILIO_ACCOUNT_SID')):
            try:
                logger.info("Using Twilio SMS Gateway")
                from twilio_gateway import TwilioGateway
                self.gateway = TwilioGateway()
                self.provider_name = 'twilio'
            except (ImportError, ValueError) as e:
                logger.warning(f"Twilio initialization failed: {e}, falling back to AWS")
                self._init_aws_or_mock()
        elif provider == 'aws' or (not provider and os.getenv('AWS_SMS_ORIGINATION_NUMBER')):
            self._init_aws_or_mock()
        else:
            logger.warning("No SMS provider configured, using Mock SMS Gateway")
            from messaging_mcp import MockSMSGateway
            self.gateway = MockSMSGateway()
            self.provider_name = 'mock'

    def _init_aws_or_mock(self):
        """Initialize AWS gateway or fall back to mock."""
        try:
            logger.info("Using AWS End User Messaging SMS Gateway")
            self.gateway = AWSEndUserMessagingGateway()
            self.provider_name = 'aws'
        except ValueError as e:
            logger.warning(f"AWS initialization failed: {e}, using Mock SMS Gateway")
            from messaging_mcp import MockSMSGateway
            self.gateway = MockSMSGateway()
            self.provider_name = 'mock'

    def send_sms(self, phone_number: str, message: str, conversation_id: str) -> dict:
        """Send SMS (delegates to configured provider)."""
        result = self.gateway.send_sms(phone_number, message, conversation_id)
        result['provider'] = self.provider_name
        return result


# Factory functions for easy integration
def create_sms_gateway(use_mock: bool = False) -> AWSMessagingGatewayWithFallback:
    """Create SMS gateway (AWS End User Messaging or Mock based on configuration).

    Args:
        use_mock: Force mock mode (default: auto-detect from env vars)

    Returns:
        SMS gateway instance

    Note: This is the legacy factory. Use create_unified_gateway for multi-provider support.
    """
    return AWSMessagingGatewayWithFallback(use_mock=use_mock)


def create_unified_gateway(provider: Optional[str] = None, use_mock: bool = False) -> UnifiedMessagingGateway:
    """Create unified SMS gateway with multi-provider support.

    Args:
        provider: Specific provider ('twilio', 'aws', 'mock') or None for auto-detect
        use_mock: Force mock mode (overrides provider)

    Returns:
        Unified SMS gateway instance

    Examples:
        # Auto-detect based on environment variables (Twilio > AWS > Mock)
        gateway = create_unified_gateway()

        # Force specific provider
        gateway = create_unified_gateway(provider='twilio')

        # Force mock mode for testing
        gateway = create_unified_gateway(use_mock=True)
    """
    return UnifiedMessagingGateway(provider=provider, use_mock=use_mock)
