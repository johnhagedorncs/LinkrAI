"""
Test: Can API prevent duplicate diagnoses?
Test if the same diagnosis (SNOMED code) can be added multiple times to an encounter

Expected: API should reject duplicate diagnoses
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from athena_api import AthenaWorkflow

workflow = AthenaWorkflow(practice_id="195900")

# Use encounter 62020 (Patient 7681) - TEMP encounter
encounter_id = "62020"
patient_id = "7681"

# Test diagnosis: Chest pain (SNOMED: 29857009, ICD-10: R07.9)
test_snomed = "29857009"
test_icd10 = "R07.9"
test_description = "Chest pain"

print("="*80)
print("TEST: Identical Diagnosis Behavior")
print("="*80)
print(f"\nEncounter: {encounter_id}")
print(f"Patient: {patient_id}")
print(f"Test Diagnosis: {test_description}")
print(f"  SNOMED: {test_snomed}")
print(f"  ICD-10: {test_icd10}")

# Step 1: Check existing diagnoses
print("\n[STEP 1] Checking existing diagnoses...")
diagnoses = workflow.get_encounter_diagnoses(encounter_id)
print(f"  Current diagnoses on encounter: {len(diagnoses)}")

existing_snomed_codes = set()
diagnosis_exists = False

for diag in diagnoses:
    snomed = str(diag.get('snomedcode'))
    existing_snomed_codes.add(snomed)
    print(f"    - Diagnosis {diag.get('diagnosisid')}: {diag.get('description')} (SNOMED: {snomed})")

    if snomed == test_snomed:
        diagnosis_exists = True
        existing_diagnosis_id = diag.get('diagnosisid')

if diagnosis_exists:
    print(f"\n✓ Diagnosis {test_snomed} already exists (ID: {existing_diagnosis_id})")
else:
    print(f"\n⚠️  Diagnosis {test_snomed} does not exist yet")
    print("  Adding it first...")

    try:
        result = workflow.add_diagnosis(
            encounter_id,
            test_snomed,
            test_icd10,
            note="First instance - for duplicate test"
        )
        print(f"  ✓ Added diagnosis: {result.get('diagnosisid')}")
        existing_diagnosis_id = result.get('diagnosisid')
        diagnosis_exists = True
    except Exception as e:
        print(f"  ❌ Failed to add first diagnosis: {e}")
        print("\nCannot proceed with duplicate test")
        exit(1)

# Step 2: Attempt to add the SAME diagnosis again
print("\n[STEP 2] Attempting to add IDENTICAL diagnosis again...")
print(f"  Diagnosis: {test_description} (SNOMED: {test_snomed})")

try:
    result = workflow.add_diagnosis(
        encounter_id,
        test_snomed,
        test_icd10,
        note="Second instance - testing duplicate prevention"
    )

    new_diagnosis_id = result.get('diagnosisid')
    print(f"  ✓ Diagnosis added: {new_diagnosis_id}")

    # Check if it's the same ID or a new one
    if new_diagnosis_id == existing_diagnosis_id:
        print("\n⚠️  API returned SAME diagnosis ID")
        print(f"    Original ID: {existing_diagnosis_id}")
        print(f"    New ID: {new_diagnosis_id}")
        print("\n✅ RESULT: API prevents duplicates by returning existing diagnosis")
    else:
        print("\n⚠️  API created NEW diagnosis with different ID!")
        print(f"    Original ID: {existing_diagnosis_id}")
        print(f"    New ID: {new_diagnosis_id}")
        print("\n❌ RESULT: API allows duplicate diagnoses (stacking behavior)")

except Exception as e:
    error_msg = str(e)
    print(f"  ❌ Add diagnosis failed: {error_msg}")

    if "already present" in error_msg.lower() or "duplicate" in error_msg.lower():
        print("\n✅ RESULT: API explicitly prevents duplicate diagnoses")
        print("  Error message indicates duplicate detection")
    elif "exists" in error_msg.lower():
        print("\n✅ RESULT: API prevents duplicate diagnoses")
        print("  Error message indicates diagnosis already exists")
    else:
        print("\n⚠️  RESULT: Failed for unknown reason")
        print("  Not a duplicate prevention error")

# Step 3: Verify final state
print("\n[STEP 3] Verifying final diagnosis state...")
diagnoses_after = workflow.get_encounter_diagnoses(encounter_id)
print(f"  Total diagnoses after test: {len(diagnoses_after)}")

count_test_diagnosis = 0
for diag in diagnoses_after:
    if str(diag.get('snomedcode')) == test_snomed:
        count_test_diagnosis += 1
        print(f"    - Diagnosis {diag.get('diagnosisid')}: {diag.get('description')} (SNOMED: {diag.get('snomedcode')})")

print(f"\n  Instances of SNOMED {test_snomed}: {count_test_diagnosis}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if count_test_diagnosis == 1:
    print("\n✅ API prevents duplicate diagnoses")
    print(f"  Only 1 instance of SNOMED {test_snomed} exists")
    print("  Behavior: Duplicate prevention enforced")
elif count_test_diagnosis > 1:
    print("\n⚠️  API allows duplicate diagnoses!")
    print(f"  Found {count_test_diagnosis} instances of SNOMED {test_snomed}")
    print("  Behavior: Diagnoses can stack (like referrals)")
else:
    print("\n❓ Unexpected state")
    print(f"  Expected at least 1 instance, found {count_test_diagnosis}")

print("\n" + "="*80)
