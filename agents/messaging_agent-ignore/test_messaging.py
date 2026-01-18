#!/usr/bin/env python3
"""Test suite for messaging agent functionality.

Tests the SMS messaging tools, state persistence, and mock gateway using the actual MCP tools.
"""

import asyncio
import json
import shutil
from pathlib import Path

# Import from messaging_mcp to use the actual global instances
import messaging_mcp
from messaging_mcp import call_tool


def setup_test_environment():
    """Set up clean test environment."""
    # Ensure directories exist
    messaging_mcp.STATE_DIR.mkdir(exist_ok=True)

    # Clean up the actual message state directory for testing
    for file in messaging_mcp.STATE_DIR.glob("*.json"):
        file.unlink()

    # Clear SMS messages (create if doesn't exist)
    with open(messaging_mcp.SMS_STORAGE_FILE, 'w') as f:
        json.dump([], f)


def cleanup_test_environment():
    """Clean up test environment."""
    # Clean up test data
    if messaging_mcp.STATE_DIR.exists():
        for file in messaging_mcp.STATE_DIR.glob("test_*.json"):
            file.unlink()


async def test_send_appointment_sms():
    """Test sending appointment SMS."""
    print("\n🧪 Test: Send Appointment SMS")

    setup_test_environment()

    # Test data
    appointment_slots = [
        {
            "slot_number": 1,
            "date": "2025-11-15",
            "time": "10:00 AM",
            "provider": "Smith",
            "cost_estimate": "$150"
        },
        {
            "slot_number": 2,
            "date": "2025-11-15",
            "time": "2:00 PM",
            "provider": "Johnson",
            "cost_estimate": "$150"
        },
        {
            "slot_number": 3,
            "date": "2025-11-16",
            "time": "9:00 AM",
            "provider": "Williams",
            "cost_estimate": "$150"
        }
    ]

    arguments = {
        "phone_number": "+11234567890",
        "appointment_slots": appointment_slots,
        "cost_estimate": "$150",
        "conversation_id": "test_conv_001"
    }

    result = await call_tool("send_appointment_sms", arguments)

    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    assert "SMS sent successfully" in result[0].text, "SMS sent message not found"
    assert "test_conv_001" in result[0].text, "Conversation ID not in result"

    # Verify conversation state was saved
    conv_state = messaging_mcp.message_state.load_conversation("test_conv_001")
    assert conv_state is not None, "Conversation state not saved"
    assert conv_state["status"] == "awaiting_response", f"Wrong status: {conv_state['status']}"
    assert len(conv_state["appointment_slots"]) == 3, f"Wrong slot count: {len(conv_state['appointment_slots'])}"

    print("✅ PASSED: SMS sent and state saved correctly")


async def test_simulate_and_check_user_response():
    """Test simulating user response and checking it."""
    print("\n🧪 Test: Simulate and Check User Response")

    setup_test_environment()

    # First send an SMS
    appointment_slots = [
        {"slot_number": 1, "date": "2025-11-15", "time": "10:00 AM", "provider": "Smith"},
        {"slot_number": 2, "date": "2025-11-15", "time": "2:00 PM", "provider": "Johnson"}
    ]

    send_args = {
        "phone_number": "+11234567890",
        "appointment_slots": appointment_slots,
        "conversation_id": "test_conv_002"
    }

    await call_tool("send_appointment_sms", send_args)

    # Simulate user selecting slot 1
    simulate_args = {
        "conversation_id": "test_conv_002",
        "response": "1"
    }

    result = await call_tool("simulate_user_sms_response", simulate_args)
    assert "Simulated user response" in result[0].text, "Simulate response failed"

    # Check the response
    check_args = {
        "conversation_id": "test_conv_002"
    }

    result = await call_tool("check_sms_response", check_args)
    assert "User responded" in result[0].text, "User response not detected"
    assert "slot #1" in result[0].text, "Slot number not found"
    assert "confirmed" in result[0].text.lower(), "Confirmation not found"

    # Verify state was updated
    conv_state = messaging_mcp.message_state.load_conversation("test_conv_002")
    assert conv_state["status"] == "slot_confirmed", f"Wrong status: {conv_state['status']}"
    assert conv_state["selected_slot"]["slot_number"] == 1, "Wrong slot selected"

    print("✅ PASSED: User response simulated and processed correctly")


async def test_user_declines_all_slots():
    """Test user declining all slots."""
    print("\n🧪 Test: User Declines All Slots")

    setup_test_environment()

    # Send SMS
    appointment_slots = [
        {"slot_number": 1, "date": "2025-11-15", "time": "10:00 AM", "provider": "Smith"}
    ]

    send_args = {
        "phone_number": "+11234567890",
        "appointment_slots": appointment_slots,
        "conversation_id": "test_conv_003"
    }

    await call_tool("send_appointment_sms", send_args)

    # User responds with NONE
    simulate_args = {
        "conversation_id": "test_conv_003",
        "response": "NONE"
    }

    await call_tool("simulate_user_sms_response", simulate_args)

    # Check response
    check_args = {"conversation_id": "test_conv_003"}
    result = await call_tool("check_sms_response", check_args)

    assert "declined all slots" in result[0].text.lower(), "Decline message not found"

    # Verify state
    conv_state = messaging_mcp.message_state.load_conversation("test_conv_003")
    assert conv_state["status"] == "slots_declined", f"Wrong status: {conv_state['status']}"

    print("✅ PASSED: User decline handled correctly")


async def test_check_response_before_user_replies():
    """Test checking for response when user hasn't replied yet."""
    print("\n🧪 Test: Check Response Before User Replies")

    setup_test_environment()

    # Send SMS
    send_args = {
        "phone_number": "+11234567890",
        "appointment_slots": [
            {"slot_number": 1, "date": "2025-11-15", "time": "10:00 AM", "provider": "Smith"}
        ],
        "conversation_id": "test_conv_004"
    }

    await call_tool("send_appointment_sms", send_args)

    # Try to check response immediately (before user replies)
    check_args = {"conversation_id": "test_conv_004"}
    result = await call_tool("check_sms_response", check_args)

    assert "No response yet" in result[0].text, "Should report no response"

    print("✅ PASSED: Correctly reports no response")


async def test_get_conversation_state():
    """Test retrieving conversation state."""
    print("\n🧪 Test: Get Conversation State")

    setup_test_environment()

    # Send SMS
    send_args = {
        "phone_number": "+11234567890",
        "appointment_slots": [
            {"slot_number": 1, "date": "2025-11-15", "time": "10:00 AM", "provider": "Smith"}
        ],
        "conversation_id": "test_conv_005"
    }

    await call_tool("send_appointment_sms", send_args)

    # Get conversation state
    get_args = {"conversation_id": "test_conv_005"}
    result = await call_tool("get_conversation_state", get_args)

    assert "Conversation State" in result[0].text, "State header not found"
    assert "test_conv_005" in result[0].text, "Conversation ID not found"
    assert "awaiting_response" in result[0].text, "Status not found"

    print("✅ PASSED: Conversation state retrieved correctly")


async def test_multiple_conversations():
    """Test handling multiple concurrent conversations."""
    print("\n🧪 Test: Multiple Concurrent Conversations")

    setup_test_environment()

    # Send multiple SMS messages
    for i in range(1, 4):
        send_args = {
            "phone_number": f"+1123456789{i}",
            "appointment_slots": [
                {"slot_number": 1, "date": "2025-11-15", "time": "10:00 AM", "provider": "Smith"}
            ],
            "conversation_id": f"test_conv_00{i + 5}"
        }
        await call_tool("send_appointment_sms", send_args)

    # Verify all conversation states exist
    for i in range(1, 4):
        conv_state = messaging_mcp.message_state.load_conversation(f"test_conv_00{i + 5}")
        assert conv_state is not None, f"Conversation test_conv_00{i + 5} not found"

    # Simulate response to second conversation
    simulate_args = {
        "conversation_id": "test_conv_007",
        "response": "1"
    }
    await call_tool("simulate_user_sms_response", simulate_args)

    # Check that only the correct conversation got the response
    check_args = {"conversation_id": "test_conv_007"}
    result = await call_tool("check_sms_response", check_args)
    assert "User responded" in result[0].text, "Response not detected"

    # Other conversations should still be awaiting response
    check_args = {"conversation_id": "test_conv_006"}
    result = await call_tool("check_sms_response", check_args)
    assert "No response yet" in result[0].text, "Should show no response for other conversation"

    print("✅ PASSED: Multiple conversations handled correctly")


async def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("🧪 MESSAGING AGENT TEST SUITE")
    print("=" * 70)

    tests = [
        test_send_appointment_sms,
        test_simulate_and_check_user_response,
        test_user_declines_all_slots,
        test_check_response_before_user_replies,
        test_get_conversation_state,
        test_multiple_conversations,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")

    cleanup_test_environment()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)