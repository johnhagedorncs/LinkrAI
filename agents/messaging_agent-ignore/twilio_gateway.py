"""Twilio SMS Gateway for real SMS communication.

This module provides a production-ready SMS gateway using Twilio's API
for sending and receiving SMS messages in healthcare applications.
"""

import base64
import json
import logging
import os
from datetime import datetime
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class TwilioGateway:
    """Twilio SMS gateway for sending and receiving messages.

    Supports both Auth Token and API Key authentication:
    - Auth Token: Use TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN
    - API Key: Use TWILIO_ACCOUNT_SID + TWILIO_API_KEY_SID + TWILIO_API_KEY_SECRET
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        api_key_sid: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        """Initialize Twilio SMS gateway.

        Args:
            account_sid: Twilio Account SID (uses env var if not provided)
            auth_token: Twilio Auth Token (uses env var if not provided)
            api_key_sid: Twilio API Key SID (uses env var if not provided)
            api_key_secret: Twilio API Key Secret (uses env var if not provided)
            from_number: Phone number to send from (uses env var if not provided)
        """
        self.account_sid = account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        self.from_number = from_number or os.getenv('TWILIO_FROM_NUMBER')

        # Support both Auth Token and API Key authentication
        self.api_key_sid = api_key_sid or os.getenv('TWILIO_API_KEY_SID')
        self.api_key_secret = api_key_secret or os.getenv('TWILIO_API_KEY_SECRET')
        self.auth_token = auth_token or os.getenv('TWILIO_AUTH_TOKEN')

        if not self.account_sid:
            raise ValueError(
                "Account SID is required. Set TWILIO_ACCOUNT_SID environment variable."
            )

        # Determine authentication method
        if self.api_key_sid and self.api_key_secret:
            # Use API Key authentication (recommended)
            self.auth_username = self.api_key_sid
            self.auth_password = self.api_key_secret
            self.auth_method = "API Key"
            logger.info("Using Twilio API Key authentication")
        elif self.auth_token:
            # Use Auth Token authentication
            self.auth_username = self.account_sid
            self.auth_password = self.auth_token
            self.auth_method = "Auth Token"
            logger.info("Using Twilio Auth Token authentication")
        else:
            raise ValueError(
                "Authentication credentials required. Set either:\n"
                "  - TWILIO_AUTH_TOKEN (for auth token), or\n"
                "  - TWILIO_API_KEY_SID + TWILIO_API_KEY_SECRET (for API key)"
            )

        if not self.from_number:
            raise ValueError(
                "From number is required. Set TWILIO_FROM_NUMBER environment variable."
            )

        # Construct Twilio API base URL
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

        logger.info(
            f"Initialized Twilio SMS gateway "
            f"(From: {self.from_number}, Account: {self.account_sid[:8]}..., "
            f"Auth: {self.auth_method})"
        )

    def send_sms(
        self,
        phone_number: str,
        message: str,
        conversation_id: str,
    ) -> dict:
        """Send SMS message via Twilio.

        Args:
            phone_number: Recipient phone number (E.164 format, e.g., +1234567890)
            message: SMS message content
            conversation_id: Unique conversation identifier

        Returns:
            dict: Message metadata including message_id, status, timestamp

        Raises:
            requests.exceptions.RequestException: If SMS sending fails
        """
        # Validate phone number format
        if not phone_number.startswith('+'):
            logger.warning(f"Phone number {phone_number} doesn't start with '+', adding +1")
            phone_number = f'+1{phone_number}'

        try:
            # Prepare Twilio API request
            url = f"{self.base_url}/Messages.json"

            # Twilio expects form-encoded data
            data = {
                'To': phone_number,
                'From': self.from_number,
                'Body': message,
            }

            # Send request with Basic Auth (uses API Key or Auth Token)
            response = requests.post(
                url,
                data=data,
                auth=HTTPBasicAuth(self.auth_username, self.auth_password),
                timeout=10,
            )

            # Check for errors
            response.raise_for_status()

            # Parse response
            result = response.json()
            message_id = result.get('sid')
            status = result.get('status', 'unknown')

            logger.info(
                f"Successfully sent SMS to {phone_number} "
                f"(Message SID: {message_id}, Status: {status})"
            )

            return {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'phone_number': phone_number,
                'direction': 'outbound',
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'response': None,
                'response_timestamp': None,
                'twilio_data': {
                    'sid': message_id,
                    'account_sid': result.get('account_sid'),
                    'date_created': result.get('date_created'),
                    'price': result.get('price'),
                    'price_unit': result.get('price_unit', 'USD'),
                }
            }

        except requests.exceptions.HTTPError as e:
            # Twilio returns detailed error info in JSON
            try:
                error_data = e.response.json()
                error_code = error_data.get('code')
                error_message = error_data.get('message')
                logger.error(
                    f"Twilio API error (Code {error_code}): {error_message}"
                )
            except:
                logger.error(f"Twilio HTTP error: {e}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending SMS via Twilio: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error sending SMS via Twilio: {e}")
            raise

    def get_message_status(self, message_sid: str) -> dict:
        """Get delivery status for a sent message.

        Args:
            message_sid: Twilio message SID

        Returns:
            dict: Delivery status information including status, error codes, etc.
        """
        try:
            url = f"{self.base_url}/Messages/{message_sid}.json"

            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.auth_username, self.auth_password),
                timeout=10,
            )

            response.raise_for_status()
            result = response.json()

            return {
                'message_id': message_sid,
                'status': result.get('status'),
                'error_code': result.get('error_code'),
                'error_message': result.get('error_message'),
                'date_sent': result.get('date_sent'),
                'date_updated': result.get('date_updated'),
                'price': result.get('price'),
                'price_unit': result.get('price_unit'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching message status: {e}")
            return {
                'message_id': message_sid,
                'status': 'unknown',
                'error': str(e)
            }
