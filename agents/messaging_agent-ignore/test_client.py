#!/usr/bin/env python3
"""Simple test client to interact with the messaging agent via A2A protocol."""

import asyncio
import json
from a2a.client import A2AClient
from a2a.types import TextPart, Part, Message


async def test_messaging_agent():
    """Test the messaging agent with a sample request."""

    print("=" * 70)
    print("🧪 TESTING MESSAGING AGENT VIA A2A PROTOCOL")
    print("=" * 70)

    # Create A2A client
    agent_url = "http://localhost:10003"
    client = A2AClient(agent_url)

    print(f"\n📡 Connecting to agent at: {agent_url}")

    # Test 1: Send appointment slots to a patient
    print("\n" + "=" * 70)
    print("Test 1: Send Appointment SMS")
    print("=" * 70)

    message_text = """
    Please send appointment slots to patient at phone +11234567890.

    Available slots:
    1. November 15, 2025 at 10:00 AM with Dr. Smith
    2. November 15, 2025 at 2:00 PM with Dr. Johnson
    3. November 16, 2025 at 9:00 AM with Dr. Williams

    Cost estimate: $150

    Use conversation ID: client_test_001
    """

    message = Message(
        parts=[Part(root=TextPart(text=message_text.strip()))]
    )

    print(f"\n📤 Sending message to agent...")
    print(f"Message: {message_text.strip()}")

    try:
        # Send the task
        response_stream = client.send_task(message)

        print("\n📥 Agent response:")
        print("-" * 70)

        # Collect all responses
        async for event in response_stream:
            if hasattr(event, 'artifact') and event.artifact:
                for part in event.artifact.parts:
                    if hasattr(part.root, 'text'):
                        print(part.root.text)

        print("-" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Give user time to simulate response
    print("\n" + "=" * 70)
    print("💡 NEXT STEP: Simulate User Response")
    print("=" * 70)
    print("\nIn another terminal, run:")
    print("  python sms_simulator.py respond client_test_001 1")
    print("\nOr wait 5 seconds and we'll simulate it for you...")

    await asyncio.sleep(5)

    # Simulate user response
    print("\n🤖 Simulating user response (selecting slot 1)...")
    from messaging_mcp import call_tool
    await call_tool('simulate_user_sms_response', {
        'conversation_id': 'client_test_001',
        'response': '1'
    })

    # Test 2: Check for user response
    print("\n" + "=" * 70)
    print("Test 2: Check User Response")
    print("=" * 70)

    check_message = Message(
        parts=[Part(root=TextPart(text="Check if user responded to conversation client_test_001"))]
    )

    print(f"\n📤 Asking agent to check for response...")

    try:
        response_stream = client.send_task(check_message)

        print("\n📥 Agent response:")
        print("-" * 70)

        async for event in response_stream:
            if hasattr(event, 'artifact') and event.artifact:
                for part in event.artifact.parts:
                    if hasattr(part.root, 'text'):
                        print(part.root.text)

        print("-" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED")
    print("=" * 70)
    print("\n💡 View all messages: python sms_simulator.py list")


if __name__ == "__main__":
    asyncio.run(test_messaging_agent())