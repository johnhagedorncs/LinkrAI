#!/usr/bin/env python3
"""
Test the find_appointment_options_by_specialty tool

This demonstrates the complete workflow:
1. Host agent provides: patient_id + specialty
2. Scheduling agent searches all providers for that specialty
3. Returns top 3 available appointment slots
4. Formatted for messaging agent
"""

from scheduling_mcp import AthenaWorkflow
from datetime import datetime, timedelta
import json


def test_find_options_cardiology():
    """Test finding cardiology appointments"""
    print("="*80)
    print("TEST: Find Appointment Options by Specialty")
    print("="*80)

    # Simulating input from host agent
    patient_id = "60183"
    specialty = "cardiology"

    print(f"\nInput from Host Agent:")
    print(f"  patient_id: {patient_id}")
    print(f"  specialty: {specialty}")

    # Initialize workflow
    workflow = AthenaWorkflow(practice_id="195900")

    # Map specialty to ID
    SPECIALTY_TO_ID = {
        "cardiology": "006",
        "primary care": "001",
        "orthopedics": "010",
        "dermatology": "012",
    }

    specialty_id = SPECIALTY_TO_ID.get(specialty.lower())
    print(f"\nMapped specialty '{specialty}' to ID '{specialty_id}'")

    # Get all providers
    all_providers = workflow.get_providers()
    print(f"Total providers in practice: {len(all_providers)}")

    # Filter by specialty
    specialty_providers = [
        p for p in all_providers
        if p.get("specialtyid") == specialty_id
    ]
    print(f"Providers with {specialty} specialty: {len(specialty_providers)}")

    # Get all departments
    all_departments = workflow.get_departments()
    print(f"Total departments in practice: {len(all_departments)}")

    # Search slots for each provider across all departments
    start_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%m/%d/%Y")

    print(f"\nSearching slots from {start_date} to {end_date}...")
    print(f"Checking {len(specialty_providers)} providers x {len(all_departments)} departments...\n")

    all_slots = []
    for provider in specialty_providers:
        provider_id = provider["providerid"]
        provider_name = f"{provider.get('firstname', '')} {provider.get('lastname', '')}".strip()

        print(f"Provider {provider_id} ({provider_name}):")

        # Try each department for this provider
        found_for_provider = False
        for dept in all_departments:
            dept_id = dept["departmentid"]

            try:
                slots = workflow.find_appointment_slots(
                    department_id=str(dept_id),
                    provider_id=str(provider_id),
                    reason_id="-1",
                    start_date=start_date,
                    end_date=end_date,
                    bypass_checks=True
                )

                if slots:
                    print(f"  ✅ Dept {dept_id} ({dept.get('name', 'Unknown')}): {len(slots)} slots")
                    found_for_provider = True
                    for slot in slots:
                        slot["provider_info"] = {
                            "id": provider_id,
                            "name": provider_name,
                            "specialty": provider.get("specialty", specialty)
                        }
                        slot["department_name"] = dept.get("name", "Unknown")
                        all_slots.append(slot)
            except Exception as e:
                # Silently skip department+provider combos that don't work
                pass

        if not found_for_provider:
            print(f"  ℹ️  No slots found in any department")

    print(f"\nTotal slots found: {len(all_slots)}")

    if not all_slots:
        print("❌ No slots found")
        return

    # Sort by date/time
    all_slots.sort(key=lambda s: (s.get('date', ''), s.get('starttime', '')))

    # Take top 3
    top_3 = all_slots[:3]

    # Format response
    options = []
    for i, slot in enumerate(top_3, 1):
        provider_info = slot.get("provider_info", {})
        options.append({
            "option_number": i,
            "appointment_id": slot.get("appointmentid"),
            "appointmenttypeid": str(slot.get("appointmenttypeid")),
            "date": slot.get("date"),
            "time": slot.get("starttime"),
            "duration_minutes": slot.get("duration"),
            "appointment_type": slot.get("appointmenttype"),
            "provider": {
                "id": provider_info.get("id"),
                "name": provider_info.get("name"),
                "specialty": provider_info.get("specialty")
            },
            "department_id": str(slot.get("departmentid"))
        })

    response_data = {
        "patient_id": patient_id,
        "specialty": specialty,
        "total_slots_found": len(all_slots),
        "appointment_options": options
    }

    # Display results
    print("\n" + "="*80)
    print("TOP 3 APPOINTMENT OPTIONS")
    print("="*80)

    for opt in options:
        print(f"\nOption {opt['option_number']}:")
        print(f"  Provider: {opt['provider']['name']}")
        print(f"  Date: {opt['date']} at {opt['time']}")
        print(f"  Duration: {opt['duration_minutes']} minutes")
        print(f"  Type: {opt['appointment_type']}")
        print(f"  Department: {opt['department_id']}")
        print(f"  Appointment ID: {opt['appointment_id']}")
        print(f"  Appointment Type ID: {opt['appointmenttypeid']}")

    print("\n" + "="*80)
    print("JSON FOR MESSAGING AGENT")
    print("="*80)
    print(json.dumps(response_data, indent=2))

    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_find_options_cardiology()
