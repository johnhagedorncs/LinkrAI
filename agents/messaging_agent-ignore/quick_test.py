#!/usr/bin/env python3
"""Quick interactive test script for messaging agent."""

import asyncio
from messaging_mcp import call_tool


async def demo_workflow():
    """Demonstrate the complete messaging workflow."""

    print("=" * 70)
    print("🧪 MESSAGING AGENT QUICK TEST")
    print("=" * 70)

    # Step 1: Send appointment SMS
    print("\n📤 Step 1: Sending appointment SMS to patient...")
    result = await call_tool('send_appointment_sms', {
        'phone_number': '+11234567890',
        'appointment_slots': [
            {
                'slot_number': 1,
                'date': '2025-11-15',
                'time': '10:00 AM',
                'provider': 'Smith',
                'cost_estimate': '$150'
            },
            {
                'slot_number': 2,
                'date': '2025-11-15',
                'time': '2:00 PM',
                'provider': 'Johnson',
                'cost_estimate': '$150'
            },
            {
                'slot_number': 3,
                'date': '2025-11-16',
                'time': '9:00 AM',
                'provider': 'Williams',
                'cost_estimate': '$150'
            }
        ],
        'cost_estimate': '$150',
        'conversation_id': 'quick_test_demo'
    })
    print(result[0].text)

    # Step 2: Check for response (should be none yet)
    print("\n🔍 Step 2: Checking for user response (should be none yet)...")
    result = await call_tool('check_sms_response', {
        'conversation_id': 'quick_test_demo'
    })
    print(result[0].text)

    # Step 3: Simulate user response
    print("\n👤 Step 3: Simulating user selecting slot 2...")
    result = await call_tool('simulate_user_sms_response', {
        'conversation_id': 'quick_test_demo',
        'response': '2'
    })
    print(result[0].text)

    # Step 4: Check response again (should have response now)
    print("\n✅ Step 4: Checking for user response (should have response now)...")
    result = await call_tool('check_sms_response', {
        'conversation_id': 'quick_test_demo'
    })
    print(result[0].text)

    # Step 5: Get conversation state
    print("\n📊 Step 5: Getting conversation state...")
    result = await call_tool('get_conversation_state', {
        'conversation_id': 'quick_test_demo'
    })
    print(result[0].text)

    print("\n" + "=" * 70)
    print("✅ QUICK TEST COMPLETED!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   - Run 'python sms_simulator.py list' to see all messages")
    print("   - Run 'python test_messaging.py' for full test suite")
    print("   - Run 'python -m messaging_agent' to start the full A2A agent")


if __name__ == "__main__":
    asyncio.run(demo_workflow())