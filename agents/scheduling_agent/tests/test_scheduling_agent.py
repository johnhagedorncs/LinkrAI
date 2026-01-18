"""Test script for Scheduling Agent with preference filtering.

This script tests the scheduling agent's ability to:
1. Find appointments by specialty
2. Filter by preferred days and times
3. Handle "any day" requests (no filtering)
4. Fall back gracefully when no matches found
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the MCP server module
from scheduling_agent import scheduling_mcp


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


async def test_find_appointments_no_preferences():
    """Test 1: Find appointments without any preferences (any day)."""
    print_section("TEST 1: Find Appointments - No Preferences (Any Day)")

    arguments = {
        "patient_id": "60183",
        "specialty": "cardiology",
        "start_date": "11/24/2025",
        "end_date": "12/24/2025"
    }

    print(f"Request: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should return earliest 3 available appointments\n")

    result = await scheduling_mcp.call_tool(
        "find_appointment_options_by_specialty",
        arguments
    )

    print(f"Result: {json.dumps(result, indent=2, default=str)}")
    return result


async def test_find_appointments_monday_mornings():
    """Test 2: Find appointments for Monday mornings."""
    print_section("TEST 2: Find Appointments - Monday Mornings")

    arguments = {
        "patient_id": "60183",
        "specialty": "cardiology",
        "preferred_days": ["Monday"],
        "preferred_time_start": "09:00",
        "preferred_time_end": "12:00",
        "start_date": "11/24/2025",
        "end_date": "12/24/2025"
    }

    print(f"Request: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should return only Monday appointments between 9am-12pm\n")

    result = await scheduling_mcp.call_tool(
        "find_appointment_options_by_specialty",
        arguments
    )

    print(f"Result: {json.dumps(result, indent=2, default=str)}")
    return result


async def test_find_appointments_weekdays_afternoon():
    """Test 3: Find appointments for weekday afternoons."""
    print_section("TEST 3: Find Appointments - Weekday Afternoons")

    arguments = {
        "patient_id": "60183",
        "specialty": "cardiology",
        "preferred_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "preferred_time_start": "12:00",
        "preferred_time_end": "17:00",
        "start_date": "11/24/2025",
        "end_date": "12/24/2025"
    }

    print(f"Request: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should return weekday appointments between 12pm-5pm\n")

    result = await scheduling_mcp.call_tool(
        "find_appointment_options_by_specialty",
        arguments
    )

    print(f"Result: {json.dumps(result, indent=2, default=str)}")
    return result


async def test_find_appointments_after_3pm():
    """Test 4: Find appointments after 3pm (any day)."""
    print_section("TEST 4: Find Appointments - After 3pm")

    arguments = {
        "patient_id": "60183",
        "specialty": "cardiology",
        "preferred_time_start": "15:00",
        "start_date": "11/24/2025",
        "end_date": "12/24/2025"
    }

    print(f"Request: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should return appointments after 3pm on any day\n")

    result = await scheduling_mcp.call_tool(
        "find_appointment_options_by_specialty",
        arguments
    )

    print(f"Result: {json.dumps(result, indent=2, default=str)}")
    return result


async def test_find_appointments_weekends():
    """Test 5: Find appointments on weekends."""
    print_section("TEST 5: Find Appointments - Weekends")

    arguments = {
        "patient_id": "60183",
        "specialty": "cardiology",
        "preferred_days": ["Saturday", "Sunday"],
        "start_date": "11/24/2025",
        "end_date": "12/24/2025"
    }

    print(f"Request: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should return weekend appointments or fall back to earliest if none available\n")

    result = await scheduling_mcp.call_tool(
        "find_appointment_options_by_specialty",
        arguments
    )

    print(f"Result: {json.dumps(result, indent=2, default=str)}")
    return result


async def test_different_specialty():
    """Test 6: Find appointments for different specialty."""
    print_section("TEST 6: Find Appointments - Family Medicine, Mornings")

    arguments = {
        "patient_id": "60183",
        "specialty": "family medicine",
        "preferred_time_start": "09:00",
        "preferred_time_end": "12:00",
        "start_date": "11/24/2025",
        "end_date": "12/24/2025"
    }

    print(f"Request: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should return morning appointments for family medicine providers\n")

    result = await scheduling_mcp.call_tool(
        "find_appointment_options_by_specialty",
        arguments
    )

    print(f"Result: {json.dumps(result, indent=2, default=str)}")
    return result


async def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*60)
    print("  SCHEDULING AGENT TEST SUITE")
    print("  Testing SMS Chatbot with Preference Filtering")
    print("="*60)

    tests = [
        test_find_appointments_no_preferences,
        test_find_appointments_monday_mornings,
        test_find_appointments_weekdays_afternoon,
        test_find_appointments_after_3pm,
        test_find_appointments_weekends,
        test_different_specialty
    ]

    results = []
    for test_func in tests:
        try:
            result = await test_func()
            results.append({
                "test": test_func.__name__,
                "status": "PASSED" if result else "FAILED",
                "result": result
            })
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            results.append({
                "test": test_func.__name__,
                "status": "ERROR",
                "error": str(e)
            })

    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Errors: {errors}")
    print()

    for result in results:
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        print(f"{status_icon} {result['test']}: {result['status']}")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    print("\n🧪 Starting Scheduling Agent Tests...\n")
    asyncio.run(run_all_tests())