"""Test script for Twilio SMS integration.

Run this to verify Twilio is properly configured and working.
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Load from messaging_agent/.env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Import gateways
from twilio_gateway import TwilioGateway
from aws_sms_gateway import create_unified_gateway

def test_twilio_credentials():
    """Test that Twilio credentials are configured."""
    print("=" * 60)
    print("Testing Twilio Credentials")
    print("=" * 60)

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    api_key_sid = os.getenv('TWILIO_API_KEY_SID')
    api_key_secret = os.getenv('TWILIO_API_KEY_SECRET')
    from_number = os.getenv('TWILIO_FROM_NUMBER')

    print(f"Account SID: {account_sid[:8]}... (found: {bool(account_sid)})")

    # Check for either Auth Token or API Key
    has_auth_token = bool(auth_token)
    has_api_key = bool(api_key_sid and api_key_secret)

    if has_api_key:
        print(f"API Key SID: {api_key_sid[:8]}... (found: True)")
        print(f"API Key Secret: {'*' * 20} (found: True)")
        print(f"Auth Method: API Key (recommended)")
    elif has_auth_token:
        print(f"Auth Token: {'*' * 20} (found: True)")
        print(f"Auth Method: Auth Token")
    else:
        print(f"Auth Token: (found: False)")
        print(f"API Key: (found: False)")

    print(f"From Number: {from_number}")
    print()

    if not account_sid or not from_number:
        print("❌ ERROR: Missing TWILIO_ACCOUNT_SID or TWILIO_FROM_NUMBER")
        return False

    if not has_auth_token and not has_api_key:
        print("❌ ERROR: Missing authentication credentials")
        print("Please set either:")
        print("  - TWILIO_AUTH_TOKEN, or")
        print("  - TWILIO_API_KEY_SID + TWILIO_API_KEY_SECRET")
        return False

    print("✓ All Twilio credentials found")
    return True

def test_twilio_gateway_init():
    """Test TwilioGateway initialization."""
    print("=" * 60)
    print("Testing TwilioGateway Initialization")
    print("=" * 60)

    try:
        gateway = TwilioGateway()
        print(f"✓ TwilioGateway initialized successfully")
        print(f"  Account SID: {gateway.account_sid[:8]}...")
        print(f"  From Number: {gateway.from_number}")
        print(f"  Base URL: {gateway.base_url}")
        return True
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize TwilioGateway: {e}")
        return False

def test_unified_gateway():
    """Test UnifiedMessagingGateway auto-detection."""
    print("=" * 60)
    print("Testing UnifiedMessagingGateway Auto-Detection")
    print("=" * 60)

    try:
        gateway = create_unified_gateway()
        print(f"✓ Unified gateway initialized")
        print(f"  Selected provider: {gateway.provider_name}")

        if gateway.provider_name == 'twilio':
            print("  ✓ Twilio successfully auto-detected as primary provider")
        elif gateway.provider_name == 'aws':
            print("  ⚠ AWS selected (Twilio not configured?)")
        elif gateway.provider_name == 'mock':
            print("  ⚠ Mock mode (no production provider configured)")

        return True
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize unified gateway: {e}")
        return False

def test_send_sms(test_phone: str = None):
    """Test sending an SMS via Twilio.

    Args:
        test_phone: Phone number to send test SMS to (E.164 format)
    """
    if not test_phone:
        print("=" * 60)
        print("Skipping SMS Send Test (no test phone provided)")
        print("=" * 60)
        print("To test SMS sending, run:")
        print("  python test_twilio.py --send +1234567890")
        print()
        return True

    print("=" * 60)
    print(f"Testing SMS Send to {test_phone}")
    print("=" * 60)

    try:
        gateway = create_unified_gateway()

        result = gateway.send_sms(
            phone_number=test_phone,
            message="🏥 Test message from Artera Messaging Agent via Twilio!",
            conversation_id="test_conv_001"
        )

        print(f"✓ SMS sent successfully!")
        print(f"  Message ID: {result.get('message_id')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Provider: {result.get('provider')}")
        print(f"  Timestamp: {result.get('timestamp')}")

        if 'twilio_data' in result:
            print(f"  Price: {result['twilio_data'].get('price')} {result['twilio_data'].get('price_unit')}")

        return True
    except Exception as e:
        print(f"❌ ERROR: Failed to send SMS: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║  TWILIO SMS GATEWAY INTEGRATION TEST                     ║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Check for --send flag
    test_phone = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '--send' and len(sys.argv) > 2:
            test_phone = sys.argv[2]

    tests = [
        ("Credentials Check", test_twilio_credentials),
        ("Gateway Initialization", test_twilio_gateway_init),
        ("Unified Gateway", test_unified_gateway),
    ]

    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
        print()

    # Optional send test
    if test_phone:
        result = test_send_sms(test_phone)
        results.append(("SMS Send Test", result))
        print()

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print()
    all_passed = all(result for _, result in results)

    if all_passed:
        print("🎉 All tests passed! Twilio integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")

    print()

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
