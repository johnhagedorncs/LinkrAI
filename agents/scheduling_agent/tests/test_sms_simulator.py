#!/usr/bin/env python3
"""
SMS Workflow Simulator - Test without real SMS

This simulates the SMS conversation in your terminal.
No real SMS sent - perfect for testing the workflow logic!

Patient: Cassie Test (ID: 5775)
Practice: 1959222 (Internal Medicine)
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import scheduling and messaging functions
from scheduling_mcp import call_tool as scheduling_call_tool

async def call_tool(name: str, arguments: dict):
    """Route tool calls to appropriate module."""
    return await scheduling_call_tool(name, arguments)

# Configuration
PATIENT_ID = "12345"
PATIENT_NAME = "Demo Patient"
YOUR_PHONE = "+15555551234"
PRACTICE_ID = "YOUR_PRACTICE_ID"
SPECIALTY = "internal medicine"


def print_sms(message: str):
    """Print an SMS message in a nice format."""
    print("\n" + "="*80)
    print("📱 SMS TO YOUR PHONE (+15555551234)")
    print("="*80)
    print(message)
    print("="*80)


def get_user_input(prompt: str) -> str:
    """Get user input with a nice prompt."""
    print(f"\n💬 {prompt}")
    response = input("Your reply: ").strip()
    return response


async def main():
    """Run the SMS simulator workflow."""

    print("="*80)
    print("🤖 SMS SCHEDULING WORKFLOW SIMULATOR")
    print("="*80)
    print(f"\n📋 Configuration:")
    print(f"   Patient: {PATIENT_NAME} (ID: {PATIENT_ID})")
    print(f"   Your Phone: {YOUR_PHONE} (simulated)")
    print(f"   Practice: {PRACTICE_ID}")
    print(f"   Specialty: {SPECIALTY}")
    print(f"\n✅ All messages are simulated - no real SMS will be sent!")
    print(f"   You'll see the messages here and type responses in terminal.")

    input("\n👉 Press ENTER to start the conversation...")

    conversation_id = f"sim_conv_{int(datetime.now().timestamp())}"

    # =========================================================================
    # STAGE 1: Ask for preferred days
    # =========================================================================
    print("\n" + "🔵 STAGE 1: Collecting Day Preferences".center(80, "="))

    message_1 = f"""Hi {PATIENT_NAME}! I'm here to help schedule your Internal Medicine appointment.

What days of the week work best for you?

Please reply with day names separated by commas.
Examples:
- Monday, Wednesday
- Tuesday, Thursday, Friday
- ANY (if any day works)"""

    print_sms(message_1)

    # Get your response
    days_response = get_user_input("What days work for you?")

    # Parse days
    if days_response.upper() == "ANY":
        preferred_days = None
        print(f"\n✅ You selected: Any day works")
    else:
        preferred_days = [day.strip() for day in days_response.split(',')]
        print(f"\n✅ Parsed days: {preferred_days}")

    # =========================================================================
    # STAGE 2: Ask for preferred time
    # =========================================================================
    print("\n" + "🔵 STAGE 2: Collecting Time Preferences".center(80, "="))

    if preferred_days:
        days_text = ", ".join(preferred_days)
        message_2 = f"""Great! I'll look for appointments on {days_text}.

What time of day works best?

Reply with ONE number:
1 - MORNING (8am-12pm)
2 - AFTERNOON (12pm-5pm)
3 - EVENING (5pm-8pm)
4 - ANYTIME"""
    else:
        message_2 = """Great! I'll look for appointments on any day.

What time of day works best?

Reply with ONE number:
1 - MORNING (8am-12pm)
2 - AFTERNOON (12pm-5pm)
3 - EVENING (5pm-8pm)
4 - ANYTIME"""

    print_sms(message_2)

    # Get your response
    time_response = get_user_input("What time works best? (1-4)")

    # Parse time preference
    time_mappings = {
        "1": ("09:00", "12:00", "morning"),
        "2": ("12:00", "17:00", "afternoon"),
        "3": ("17:00", "20:00", "evening"),
        "4": (None, None, "anytime")
    }

    time_start, time_end, time_label = time_mappings.get(time_response.strip(), (None, None, "anytime"))
    print(f"\n✅ Selected time: {time_label.upper()}")
    if time_start:
        print(f"   Time range: {time_start} - {time_end}")

    # =========================================================================
    # STAGE 3: Search for appointments with preferences
    # =========================================================================
    print("\n" + "🔵 STAGE 3: Searching for Appointments".center(80, "="))

    search_params = {
        'patient_id': PATIENT_ID,
        'specialty': SPECIALTY,
        'start_date': '01/20/2026',
        'end_date': '02/15/2026'
    }

    if preferred_days:
        search_params['preferred_days'] = preferred_days
    if time_start and time_end:
        search_params['preferred_time_start'] = time_start
        search_params['preferred_time_end'] = time_end

    print(f"\n🔍 Searching Athena Health...")
    print(f"   Patient ID: {PATIENT_ID}")
    print(f"   Specialty: {SPECIALTY}")
    if preferred_days:
        print(f"   Days: {', '.join(preferred_days)}")
    if time_start:
        print(f"   Time: {time_start} - {time_end}")

    # Call the scheduling MCP tool
    print(f"\n⏳ Calling find_appointment_options_by_specialty...")
    find_result = await call_tool('find_appointment_options_by_specialty', search_params)

    # Parse the JSON response
    import json
    text = find_result[0].text
    json_start = text.find('{')
    json_end = text.rfind('}') + 1

    if json_start == -1 or json_end == 0:
        print("\n❌ No appointment data found")
        print_sms("Sorry, we couldn't find any available appointments. Please call our office at 555-0100.")
        return

    data = json.loads(text[json_start:json_end])
    appointment_options = data.get('appointment_options', [])

    if not appointment_options:
        print("\n❌ No appointments available")
        print_sms("Sorry, no appointments match your preferences. Would you like to try different days or times?")
        return

    print(f"\n✅ Found {len(appointment_options)} matching appointments!")

    # =========================================================================
    # STAGE 4: Send appointment options via SMS
    # =========================================================================
    print("\n" + "🔵 STAGE 4: Presenting Options".center(80, "="))

    # Format options for SMS
    options_message = f"Found {len(appointment_options)} available appointments:\n"

    for i, opt in enumerate(appointment_options, 1):
        options_message += f"""
{i}. Dr. {opt['provider']['name']}
   {opt['date']} at {opt['time']}
   {opt['duration_minutes']} min - {opt['appointment_type']}
   Dept {opt['department_id']}"""

    options_message += "\n\nReply with the number (1, 2, or 3)\nOr reply NONE if none work"

    print_sms(options_message)

    # Get your selection
    selection_response = get_user_input("Which appointment do you want? (1-3 or NONE)")

    if selection_response.upper() == "NONE":
        print("\n❌ You declined all options")
        print_sms("No problem! Would you like me to search for different times?")
        return

    try:
        selection_index = int(selection_response.strip()) - 1
        selected_apt = appointment_options[selection_index]
    except (ValueError, IndexError):
        print(f"\n❌ Invalid selection: {selection_response}")
        print_sms("Sorry, I didn't understand. Please reply with 1, 2, or 3.")
        return

    print(f"\n✅ You selected:")
    print(f"   Provider: Dr. {selected_apt['provider']['name']}")
    print(f"   Date: {selected_apt['date']} at {selected_apt['time']}")
    print(f"   Department: {selected_apt['department_id']}")

    # =========================================================================
    # STAGE 5: Book the appointment
    # =========================================================================
    print("\n" + "🔵 STAGE 5: Booking Appointment".center(80, "="))

    booking_message = "Great choice! Booking your appointment now..."
    print_sms(booking_message)

    print(f"\n📝 Calling book_athena_appointment...")
    print(f"   Appointment ID: {selected_apt['appointment_id']}")
    print(f"   Appointment Type ID: {selected_apt['appointmenttypeid']}")

    try:
        book_result = await call_tool('book_athena_appointment', {
            'patient_id': PATIENT_ID,
            'appointment_id': str(selected_apt['appointment_id']),
            'appointmenttype_id': str(selected_apt['appointmenttypeid'])
        })

        booking_text = book_result[0].text.lower()
        booking_successful = "success" in booking_text or "confirmed" in booking_text or "booked" in booking_text

        print(f"\n📋 Booking result:")
        print(book_result[0].text)

    except Exception as e:
        print(f"\n❌ Booking error: {e}")
        booking_successful = False

    # =========================================================================
    # STAGE 6: Send confirmation SMS
    # =========================================================================
    print("\n" + "🔵 STAGE 6: Sending Confirmation".center(80, "="))

    if booking_successful:
        confirmation = f"""✅ Appointment Confirmed!

Dr. {selected_apt['provider']['name']}
{selected_apt['provider']['specialty']}

📅 {selected_apt['date']} at {selected_apt['time']}
⏱️  {selected_apt['duration_minutes']} minutes

📍 Department {selected_apt['department_id']}
💰 Estimated: $50 copay

We'll send a reminder 24 hours before.
Reply HELP for assistance."""
    else:
        confirmation = f"""⚠️ Booking Issue

We had trouble booking your appointment. Our team will call you shortly.

Selected time:
{selected_apt['date']} at {selected_apt['time']}
Dr. {selected_apt['provider']['name']}

Please call us at 555-0100 if you need immediate assistance."""

    print_sms(confirmation)

    # =========================================================================
    # DONE!
    # =========================================================================
    print("\n" + "="*80)
    print("✅ SMS WORKFLOW SIMULATION COMPLETE!")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   Stages completed: 6/6")
    print(f"   SMS messages: 5")
    print(f"   User interactions: 3")
    print(f"   Appointments found: {len(appointment_options)}")
    print(f"   Appointment booked: {'✓ Yes' if booking_successful else '✗ Failed'}")
    print(f"\n💡 This workflow would work the same way with real SMS!")
    print(f"   The only difference is messages go to your phone instead of console.")
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
