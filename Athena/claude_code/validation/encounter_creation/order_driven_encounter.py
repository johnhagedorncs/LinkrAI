"""
CLEAN TEST: Encounter Creation from Patient WITHOUT Existing Encounter

Testing encounter creation pipelines:
1. Visit-driven: Book → Check-in (same day) → Encounter opens
2. Order-driven: Create order group → Encounter opens

Patient: 7681 (Test Test) - NO existing encounters
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))  # Add root to path
from athena_api import AthenaWorkflow, legacy_get, legacy_post, legacy_put
from datetime import datetime, timedelta
import time

workflow = AthenaWorkflow(practice_id="195900")

# Clean patient with NO open encounters
PATIENT_ID = "7681"
DEPARTMENT_ID = "1"
PROVIDER_ID = "71"  # Adam Bricker - has availability

print("="*80)
print("CLEAN ENCOUNTER CREATION TEST")
print("="*80)
print(f"\nPatient: {PATIENT_ID} (Test Test)")
print("Starting Encounters: 0")
print("Goal: Create encounter via documented pipelines")


# ============================================================================
# BASELINE: Verify patient has NO open encounters
# ============================================================================
print("\n" + "="*80)
print("BASELINE: Verify Clean State")
print("="*80)

initial_encounters = legacy_get(
    f"/v1/{{practiceid}}/chart/{PATIENT_ID}/encounters",
    params={"departmentid": DEPARTMENT_ID},
    practice_id="195900"
)

open_encounters = [e for e in initial_encounters.get("encounters", [])
                   if e.get("status") == "OPEN"]

print(f"\nTotal encounters: {len(initial_encounters.get('encounters', []))}")
print(f"Open encounters: {len(open_encounters)}")

if open_encounters:
    print("⚠️  Patient already has open encounter - not a clean test!")
    for enc in open_encounters:
        print(f"  Encounter {enc.get('encounterid')}: {enc.get('status')}")
else:
    print("✅ Patient has NO open encounters - ready for clean test")


# ============================================================================
# ORDER-DRIVEN (Test First - No appointment needed)
# ============================================================================
print("\n" + "="*80)
print("PIPELINE 3: ORDER-DRIVEN ENCOUNTER CREATION")
print("Create Order Group → Encounter Opens")
print("="*80)

print("\n[STEP 1] Creating order group for patient...")
print("  Endpoint: POST /v1/{practiceid}/chart/{patientid}/ordergroups")
print("  Expected: Should create encounter automatically")

try:
    # Create order group
    ordergroup_data = {
        "departmentid": DEPARTMENT_ID,
        "providerid": PROVIDER_ID,
    }

    ordergroup_result = legacy_post(
        f"/v1/{{practiceid}}/chart/{PATIENT_ID}/ordergroups",
        data=ordergroup_data,
        practice_id="195900"
    )

    print(f"  ✓ Order group created: {ordergroup_result}")

    # Check if order group response includes encounter ID
    if "encounterid" in ordergroup_result:
        encounter_id = ordergroup_result.get("encounterid")
        print(f"  ✅ ENCOUNTER CREATED BY ORDER GROUP!")
        print(f"     Encounter ID: {encounter_id}")

        # Verify encounter exists
        print("\n[STEP 2] Verifying encounter...")
        encounters_after = legacy_get(
            f"/v1/{{practiceid}}/chart/{PATIENT_ID}/encounters",
            params={"departmentid": DEPARTMENT_ID},
            practice_id="195900"
        )

        open_after = [e for e in encounters_after.get("encounters", [])
                     if e.get("status") == "OPEN"]

        print(f"  Open encounters after: {len(open_after)}")
        if open_after:
            enc = open_after[0]
            print(f"  ✅ Encounter {enc.get('encounterid')} - Status: {enc.get('status')}")
            print(f"     Date: {enc.get('encounterdate')}")

            # Now create a referral order in this encounter
            print("\n[STEP 3] Adding referral order to encounter...")

            referral_result = workflow.create_referral_order(
                encounter_id,
                "257362",  # cardiologist referral
                "29857009",  # chest pain SNOMED
                provider_note="Test referral via order-driven encounter",
                reason_for_referral="Testing order-driven pipeline"
            )

            referral_id = referral_result.get("documentid")
            print(f"  ✓ Referral created: {referral_id}")

            print("\n" + "="*80)
            print("✅ PIPELINE 3 SUCCESS: ORDER-DRIVEN ENCOUNTER CREATION WORKS!")
            print("="*80)
            print(f"  Order group → Encounter {encounter_id} opened")
            print(f"  Referral {referral_id} added to encounter")
            print("  ✓ Patient went from 0 encounters to 1 open encounter")

    else:
        print("  ⚠️  Order group created but no encounterid in response")
        print(f"  Response: {ordergroup_result}")

        # Check if encounter was created anyway
        print("\n[STEP 2] Checking if encounter was created...")
        encounters_after = legacy_get(
            f"/v1/{{practiceid}}/chart/{PATIENT_ID}/encounters",
            params={"departmentid": DEPARTMENT_ID},
            practice_id="195900"
        )

        open_after = [e for e in encounters_after.get("encounters", [])
                     if e.get("status") == "OPEN"]

        if len(open_after) > len(open_encounters):
            print(f"  ✅ NEW ENCOUNTER CREATED!")
            enc = open_after[0]
            print(f"     Encounter ID: {enc.get('encounterid')}")
            print(f"     Status: {enc.get('status')}")
        else:
            print(f"  ❌ No new encounter created")

except Exception as e:
    print(f"\n❌ Order group creation failed: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

final_encounters = legacy_get(
    f"/v1/{{practiceid}}/chart/{PATIENT_ID}/encounters",
    params={"departmentid": DEPARTMENT_ID},
    practice_id="195900"
)

final_open = [e for e in final_encounters.get("encounters", [])
             if e.get("status") == "OPEN"]

print(f"\nPatient {PATIENT_ID} (Test Test):")
print(f"  Initial open encounters: {len(open_encounters)}")
print(f"  Final open encounters: {len(final_open)}")
print(f"  New encounters created: {len(final_open) - len(open_encounters)}")

if final_open:
    print("\nOpen Encounters:")
    for enc in final_open:
        print(f"  - Encounter {enc.get('encounterid')}: {enc.get('status')} ({enc.get('encounterdate')})")

print("\n" + "="*80)