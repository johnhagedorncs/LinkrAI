#!/usr/bin/env python3
"""
SMS Workflow Simulator - Auto Mode (No User Input Required)

This runs the full SMS workflow automatically with pre-set responses.
Perfect for quick testing!

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

# Import scheduling functions
from scheduling_mcp import call_tool as scheduling_call_tool

async def call_tool(name: str, arguments: dict):
    """Route tool calls to appropriate module."""
    return await scheduling_call_tool(name, arguments)

# Configuration
PATIENT_ID = "5775"
PATIENT_NAME = "Cassie"
PRACTICE_ID = "1959222"
SPECIALTY = "internal medicine"

# Pre-set responses (change these to test different scenarios)
PREFERRED_DAYS = ["Monday", "Wednesday"]
PREFERRED_TIME = "1"  # 1=morning, 2=afternoon, 3=evening, 4=anytime
SELECTED_OPTION = "1"  # Which appointment to book (1, 2, or 3)


def print_sms(message: str):
    """Print an SMS message in a nice format."""
    print("\n" + "="*80)
    print("📱 SMS TO PATIENT")
    print("="*80)
    print(message)
    print("="*80)


def print_user_response(response: str):
    """Print user's response."""
    print(f"\n💬 Patient replies: '{response}'")


async def main():
    """Run the SMS simulator workflow automatically."""

    print("="*80)
    print("🤖 SMS SCHEDULING WORKFLOW - AUTO MODE")
    print("="*80)
    print(f"\n📋 Configuration:")
    print(f"   Patient: {PATIENT_NAME} (ID: {PATIENT_ID})")
    print(f"   Practice: {PRACTICE_ID}")
    print(f"   Specialty: {SPECIALTY}")
    print(f"\n🎯 Pre-set Responses:")
    print(f"   Days: {', '.join(PREFERRED_DAYS)}")
    print(f"   Time: {'Morning' if PREFERRED_TIME == '1' else 'Afternoon' if PREFERRED_TIME == '2' else 'Evening' if PREFERRED_TIME == '3' else 'Anytime'}")
    print(f"   Selection: Option {SELECTED_OPTION}")

    conversation_id = f"auto_conv_{int(datetime.now().timestamp())}"

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

    # Use pre-set response
    days_response = ", ".join(PREFERRED_DAYS)
    print_user_response(days_response)

    preferred_days = PREFERRED_DAYS
    print(f"✅ Parsed days: {preferred_days}")

    # =========================================================================
    # STAGE 2: Ask for preferred time
    # =========================================================================
    print("\n" + "🔵 STAGE 2: Collecting Time Preferences".center(80, "="))

    days_text = ", ".join(preferred_days)
    message_2 = f"""Great! I'll look for appointments on {days_text}.

What time of day works best?

Reply with ONE number:
1 - MORNING (8am-12pm)
2 - AFTERNOON (12pm-5pm)
3 - EVENING (5pm-8pm)
4 - ANYTIME"""

    print_sms(message_2)

    # Use pre-set response
    time_response = PREFERRED_TIME
    print_user_response(time_response)

    # Parse time preference
    time_mappings = {
        "1": ("09:00", "12:00", "morning"),
        "2": ("12:00", "17:00", "afternoon"),
        "3": ("17:00", "20:00", "evening"),
        "4": (None, None, "anytime")
    }

    time_start, time_end, time_label = time_mappings.get(time_response.strip(), (None, None, "anytime"))
    print(f"✅ Selected time: {time_label.upper()}")
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
        return

    data = json.loads(text[json_start:json_end])
    appointment_options = data.get('appointment_options', [])

    if not appointment_options:
        print("\n❌ No appointments available")
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

    # Use pre-set response
    selection_response = SELECTED_OPTION
    print_user_response(selection_response)

    try:
        selection_index = int(selection_response.strip()) - 1
        selected_apt = appointment_options[selection_index]
    except (ValueError, IndexError):
        print(f"\n❌ Invalid selection: {selection_response}")
        return

    print(f"\n✅ Selected:")
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
    print("✅ SMS WORKFLOW COMPLETE!")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   Stages completed: 6/6")
    print(f"   SMS messages: 5")
    print(f"   Appointments found: {len(appointment_options)}")
    print(f"   Appointment booked: {'✓ Yes' if booking_successful else '✗ Failed'}")
    print(f"\n💡 To test with different preferences, edit the variables at the top of this file:")
    print(f"   PREFERRED_DAYS = {PREFERRED_DAYS}")
    print(f"   PREFERRED_TIME = \"{PREFERRED_TIME}\"")
    print(f"   SELECTED_OPTION = \"{SELECTED_OPTION}\"")
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
