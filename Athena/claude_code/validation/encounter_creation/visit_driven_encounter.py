"""
TEST: Visit-Driven Encounter Creation
Book same-day appointment → Check-in → Encounter opens

Using clean patient without open encounter
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))  # Add root to path
from athena_api import AthenaWorkflow, legacy_get, legacy_post, legacy_put
from datetime import datetime
import time

workflow = AthenaWorkflow(practice_id="195900")

# Find a new clean patient (not 7681, which now has encounter 62020)
print("="*80)
print("FINDING NEW CLEAN PATIENT")
print("="*80)

test_patients = ["7848", "7859", "7955", "8141"]  # From our earlier search

clean_patient = None
for pid in test_patients:
    try:
        encounters = legacy_get(
            f"/v1/{{practiceid}}/chart/{pid}/encounters",
            params={"departmentid": "1"},
            practice_id="195900"
        )
        open_encs = [e for e in encounters.get("encounters", []) if e.get("status") == "OPEN"]

        if not open_encs:
            clean_patient = pid
            print(f"✓ Found clean patient: {pid}")
            break
    except:
        pass

if not clean_patient:
    print("⚠️ No clean patient found, using 7848 anyway")
    clean_patient = "7848"

PATIENT_ID = clean_patient
DEPARTMENT_ID = "1"

print(f"\nUsing Patient: {PATIENT_ID}")

# ============================================================================
# STEP 1: Find TODAY's appointment slots
# ============================================================================
print("\n" + "="*80)
print("VISIT-DRIVEN PIPELINE: Same-Day Appointment")
print("="*80)

today = datetime.now().strftime("%m/%d/%Y")
print(f"\n[STEP 1] Finding appointment slots for TODAY ({today})...")

# Try multiple providers to find today's slots
providers_to_try = [
    ("71", "1"),   # Adam Bricker, Dept 1
    ("1911", "1"), # Bryan Adamczyk, Dept 1
    ("2276", "1"), # Nikhil Jain, Dept 1
    ("325", "21"), # Maurice Johnson, Dept 21
    ("27", "150"), # Elsa Spinka, Dept 150
]

found_slot = None
for provider_id, dept_id in providers_to_try:
    try:
        print(f"  Checking Provider {provider_id}, Department {dept_id}...")
        slots = workflow.find_appointment_slots(
            department_id=dept_id,
            provider_id=provider_id,
            start_date=today,
            end_date=today,
            reason_id="-1"
        )

        if slots:
            found_slot = slots[0]
            found_slot["provider_id"] = provider_id
            found_slot["department_id"] = dept_id
            print(f"  ✓ Found {len(slots)} slots!")
            print(f"  ✓ Using: {found_slot['date']} at {found_slot['starttime']}")
            break
    except Exception as e:
        print(f"  ✗ Error: {e}")

if not found_slot:
    print("\n⚠️  NO SAME-DAY SLOTS AVAILABLE - Creating one...")
    print("\n[STEP 1B] Creating open appointment slot for today...")

    # Use first provider/department from our list
    create_provider_id = "71"
    create_dept_id = "1"
    create_time = "14:00"  # 2:00 PM

    try:
        # First, get valid appointment types for this department
        print(f"  Fetching appointment types for Department {create_dept_id}...")
        appt_types = legacy_get(
            f"/v1/{{practiceid}}/appointmenttypes",
            params={
                "departmentid": create_dept_id
            },
            practice_id="195900"
        )

        if not appt_types or "appointmenttypes" not in appt_types or len(appt_types["appointmenttypes"]) == 0:
            print("  ❌ No appointment types found for this department")
            print("  Response:", appt_types)
            print("\nCannot test visit-driven pipeline without valid appointment type")
            print("\nTo test this pipeline manually:")
            print("1. Wait for business hours when same-day slots exist")
            print("2. Or create appointment via athenaNet UI")
            exit(1)

        # Use the first available appointment type
        appt_type_id = str(appt_types["appointmenttypes"][0]["appointmenttypeid"])
        appt_type_name = appt_types["appointmenttypes"][0].get("name", "Unknown")
        print(f"  ✓ Using appointment type: {appt_type_name} (ID: {appt_type_id})")

        # Create the appointment slot using appointmenttypeid instead of reasonid
        create_result = legacy_post(
            f"/v1/{{practiceid}}/appointments/open",
            data={
                "appointmentdate": today,
                "appointmenttime": create_time,
                "appointmenttypeid": appt_type_id,
                "departmentid": create_dept_id,
                "providerid": create_provider_id
            },
            practice_id="195900"
        )

        print(f"  ✓ Created open appointment slot!")
        print(f"  Response: {create_result}")

        # Extract appointment ID and time from response
        # Response format: {'appointmentids': {'1421693': '14:00'}}
        if "appointmentids" in create_result:
            appt_ids = create_result["appointmentids"]
            if appt_ids:
                appt_id = list(appt_ids.keys())[0]
                appt_time = list(appt_ids.values())[0]

                # Build found_slot object to match expected structure
                found_slot = {
                    "appointmentid": appt_id,
                    "appointmenttypeid": appt_type_id,
                    "date": today,
                    "starttime": appt_time,
                    "provider_id": create_provider_id,
                    "department_id": create_dept_id
                }
                print(f"  ✓ Using newly created appointment: ID {appt_id} at {appt_time}")
            else:
                print("  ❌ No appointment IDs in response")
                exit(1)
        else:
            print("  ❌ Unexpected response format:", create_result)
            exit(1)

    except Exception as e:
        print(f"  ❌ Failed to create appointment slot: {e}")
        print("\nCannot test visit-driven pipeline without today's appointment")
        print("\nTo test this pipeline manually:")
        print("1. Wait for business hours when same-day slots exist")
        print("2. Or create appointment via athenaNet UI")
        exit(1)

# ============================================================================
# STEP 2: Book the appointment
# ============================================================================
print(f"\n[STEP 2] Booking same-day appointment...")

try:
    book_result = legacy_put(
        f"/v1/{{practiceid}}/appointments/{found_slot['appointmentid']}",
        data={
            "patientid": PATIENT_ID,
            "appointmenttypeid": str(found_slot['appointmenttypeid']),
            "ignoreschedulablepermission": "true"
        },
        practice_id="195900"
    )

    # Handle list or dict response
    if isinstance(book_result, list) and len(book_result) > 0:
        appointment_id = book_result[0].get("appointmentid")
    elif isinstance(book_result, dict):
        appointment_id = book_result.get("appointmentid")
    else:
        appointment_id = found_slot['appointmentid']

    print(f"  ✓ Appointment booked: {appointment_id}")
    print(f"    Patient: {PATIENT_ID}")
    print(f"    Provider: {found_slot['provider_id']}")
    print(f"    Department: {found_slot['department_id']}")
    print(f"    Time: {found_slot['date']} at {found_slot['starttime']}")

except Exception as e:
    print(f"  ❌ Booking failed: {e}")
    exit(1)

# ============================================================================
# STEP 3: Check encounters BEFORE check-in
# ============================================================================
print(f"\n[STEP 3] Checking encounters BEFORE check-in...")

encounters_before = legacy_get(
    f"/v1/{{practiceid}}/chart/{PATIENT_ID}/encounters",
    params={"departmentid": found_slot['department_id']},
    practice_id="195900"
)

open_before = [e for e in encounters_before.get("encounters", []) if e.get("status") == "OPEN"]
all_before = encounters_before.get("encounters", [])

print(f"  Total encounters: {len(all_before)}")
print(f"  Open encounters: {len(open_before)}")

if all_before:
    print("  Existing encounters:")
    for enc in all_before[:3]:
        print(f"    - {enc.get('encounterid')}: {enc.get('status')} ({enc.get('encounterdate')})")

# ============================================================================
# STEP 4: Check-in the appointment
# ============================================================================
print(f"\n[STEP 4] Checking in same-day appointment...")
print(f"  Endpoint: POST /v1/{{practiceid}}/appointments/{appointment_id}/checkin")

try:
    checkin_result = legacy_post(
        f"/v1/{{practiceid}}/appointments/{appointment_id}/checkin",
        data={},
        practice_id="195900"
    )

    print(f"  ✅ CHECK-IN SUCCESSFUL!")
    print(f"  Response: {checkin_result}")

except Exception as e:
    print(f"  ❌ Check-in failed: {e}")
    if "not today" in str(e).lower() or "future" in str(e).lower():
        print("  ℹ️  Error suggests appointment is not today")
        print(f"  ℹ️  Appointment date: {found_slot['date']}")
        print(f"  ℹ️  Today's date: {today}")
    elif "insurance" in str(e).lower():
        print("  ℹ️  Check-in blocked by insurance requirement (known sandbox limitation)")
        print("  ℹ️  This is expected in sandbox environment")
    exit(1)

# ============================================================================
# STEP 5: Check encounters AFTER check-in
# ============================================================================
print(f"\n[STEP 5] Checking encounters AFTER check-in...")

# Give system a moment to create encounter
time.sleep(2)

encounters_after = legacy_get(
    f"/v1/{{practiceid}}/chart/{PATIENT_ID}/encounters",
    params={"departmentid": found_slot['department_id']},
    practice_id="195900"
)

open_after = [e for e in encounters_after.get("encounters", []) if e.get("status") == "OPEN"]
all_after = encounters_after.get("encounters", [])

print(f"  Total encounters: {len(all_after)}")
print(f"  Open encounters: {len(open_after)}")

if all_after:
    print("  Current encounters:")
    for enc in all_after[:5]:
        print(f"    - {enc.get('encounterid')}: {enc.get('status')} ({enc.get('encounterdate')}, Type: {enc.get('encountertype', 'N/A')})")

# ============================================================================
# STEP 6: Analyze results
# ============================================================================
print("\n" + "="*80)
print("RESULTS")
print("="*80)

if len(all_after) > len(all_before):
    print("\n✅ NEW ENCOUNTER CREATED!")
    new_encounters = [e for e in all_after if e.get('encounterid') not in [x.get('encounterid') for x in all_before]]

    for enc in new_encounters:
        print(f"\nEncounter ID: {enc.get('encounterid')}")
        print(f"  Status: {enc.get('status')}")
        print(f"  Type: {enc.get('encountertype', 'N/A')}")
        print(f"  Date: {enc.get('encounterdate')}")
        print(f"  Department: {enc.get('departmentid')}")

        # Try to add diagnosis to verify it's a working encounter
        print(f"\n[STEP 7] Testing diagnosis on new encounter...")
        try:
            diag_result = workflow.add_diagnosis(
                str(enc.get('encounterid')),
                "29857009",  # chest pain
                "R07.9",
                note="Test diagnosis on visit-driven encounter"
            )
            print(f"  ✅ Diagnosis added: {diag_result.get('diagnosisid')}")
            print(f"  ✅ Visit-driven encounter is fully functional!")
        except Exception as e:
            print(f"  ⚠️  Could not add diagnosis: {e}")

    print("\n" + "="*80)
    print("✅ VISIT-DRIVEN PIPELINE VERIFIED!")
    print("="*80)
    print("  Book same-day appointment → Check-in → OPEN encounter created")
    print(f"  Patient {PATIENT_ID}: {len(all_before)} → {len(all_after)} encounters")

elif len(open_after) > len(open_before):
    print("\n✅ OPEN ENCOUNTER CREATED (or status changed)")
    print(f"  Open encounters: {len(open_before)} → {len(open_after)}")

    for enc in open_after:
        if enc not in open_before:
            print(f"\nNew/Changed Encounter: {enc.get('encounterid')}")
            print(f"  Status: {enc.get('status')}")
            print(f"  Type: {enc.get('encountertype', 'N/A')}")

else:
    print("\n⚠️ NO NEW ENCOUNTER DETECTED")
    print(f"  Encounters before: {len(all_before)}")
    print(f"  Encounters after: {len(all_after)}")
    print("\nPossible reasons:")
    print("  - Encounter merged with existing")
    print("  - System delay")
    print("  - Check-in didn't trigger encounter creation")

print("\n" + "="*80)
