#!/usr/bin/env python3
"""
Create Model Input - Complete A2A Pipeline Test Data Generator

Purpose: Generate complete test data for the A2A pipeline workflow:
- Creates patient (or reuses existing)
- Creates open encounter (no diagnosis attached)
- Selects random specialty → random diagnosis → predefined note
- Finds provider with available slots (prioritizing usual department)
- Creates appointment slots if none exist
- Outputs complete pipeline input payload

The output is ready to feed into: Referral Agent → Scheduling Agent → Messaging Agent
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Import from athena_api (located in /Athena directory)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from athena_api import AthenaWorkflow, legacy_get, legacy_post, legacy_put

from datetime import datetime, timedelta
import argparse
import json
import random
import string

# Import discovery utilities
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "discovery")))
from find_appointment_slots import find_slots_for_provider_with_usual_priority

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
TEMPLATES_FILE = os.path.join(DATA_DIR, "specialty_templates.json")
PATIENT_DATA_FILE = os.path.join(DATA_DIR, "patient_data.json")


def load_templates():
    """Load specialty templates"""
    with open(TEMPLATES_FILE, 'r') as f:
        return json.load(f)


def load_patient_data():
    """Load patient data (pipeline outputs)"""
    if os.path.exists(PATIENT_DATA_FILE):
        with open(PATIENT_DATA_FILE, 'r') as f:
            data = json.load(f)
            # Handle old format (with patients/encounters arrays) or new format (pipeline_runs array)
            if "pipeline_runs" not in data:
                # Convert old format or initialize new format
                return {"pipeline_runs": []}
            return data
    return {"pipeline_runs": []}


def save_patient_data(data):
    """Save patient data"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PATIENT_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def append_pipeline_run(pipeline_output):
    """Append a new pipeline run to patient data"""
    data = load_patient_data()

    # Add pipeline output to the runs array
    data["pipeline_runs"].append(pipeline_output)

    # Save back to file
    save_patient_data(data)


def generate_random_patient_data():
    """Generate random patient demographics"""
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
                   "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]

    # Random DOB between 1940-2000
    year = random.randint(1940, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)

    # Random phone number
    phone = f"805{random.randint(1000000, 9999999)}"

    # Random email
    firstname = random.choice(first_names).lower()
    lastname = random.choice(last_names).lower()
    email = f"{firstname}.{lastname}{random.randint(100, 999)}@example.com"

    # Random zip code (California)
    zip_codes = ["93101", "93103", "93105", "93106", "93108", "93110", "93111", "93117"]

    return {
        "firstname": firstname.title(),
        "lastname": lastname.title(),
        "dob": f"{month:02d}/{day:02d}/{year}",
        "phone": phone,
        "email": email,
        "zip": random.choice(zip_codes),
        "sex": random.choice(["M", "F"])
    }


def create_patient(practice_id, patient_data=None, department_id="1"):
    """
    Create a patient in Athena using the working API workflow.

    Args:
        practice_id: Practice ID
        patient_data: Optional dict with patient info (firstname, lastname, dob, etc.)
        department_id: Department ID for patient registration

    Returns:
        Patient ID string and patient data dict
    """
    if not patient_data:
        patient_data = generate_random_patient_data()

    # Use the working AthenaWorkflow API
    api = AthenaWorkflow(practice_id=practice_id)

    result = api.create_patient(
        firstname=patient_data["firstname"],
        lastname=patient_data["lastname"],
        dob=patient_data["dob"],
        sex=patient_data.get("sex", "M"),
        department_id=department_id,
        email=patient_data.get("email", f"{patient_data['firstname'].lower()}@example.com"),
        zip=patient_data.get("zip", "93101")
    )

    patient_id = result["patientid"]

    print(f"  ✓ Created patient {patient_id}: {patient_data['firstname']} {patient_data['lastname']}")

    return patient_id, patient_data


def create_encounter_via_ordergroup(practice_id, patient_id, department_id="1", provider_id="71"):
    """
    Create encounter via order group - using the proven working method.

    This method is proven to work from create_patient.py.

    Args:
        practice_id: Practice ID
        patient_id: Patient ID
        department_id: Department ID (default: "1")
        provider_id: Provider ID (default: "71")

    Returns:
        Encounter ID string
    """
    print(f"  Creating encounter via order group...")

    # Use the exact method from create_patient.py that we know works
    ordergroup_result = legacy_post(
        f"/v1/{{practiceid}}/chart/{patient_id}/ordergroups",
        data={
            "departmentid": department_id,
            "providerid": provider_id,
        },
        practice_id=practice_id
    )

    encounter_id = ordergroup_result.get("encounterid")

    if encounter_id:
        print(f"  ✓ Created encounter {encounter_id} via order group")
        return encounter_id
    else:
        print(f"  ✗ No encounter ID in order group response")
        raise Exception("Failed to create encounter via order group")


def select_random_specialty_and_diagnosis(templates, practice_id=None):
    """
    Select random specialty and diagnosis, optionally filtering by practice.

    Args:
        templates: Specialty templates dict
        practice_id: Optional practice ID to filter specialties

    Returns:
        Tuple of (specialty, specialty_id, diagnosis, snomed_code, clinical_note)
    """
    # Filter specialties by practice if specified
    available_specialties = list(templates.keys())

    if practice_id:
        available_specialties = [
            spec for spec in available_specialties
            if practice_id in templates[spec].get("practices", [])
        ]

        if not available_specialties:
            raise ValueError(f"No specialties available for practice {practice_id}")

    specialty = random.choice(available_specialties)
    specialty_data = templates[specialty]
    specialty_id = specialty_data["specialty_id"]

    diagnoses = specialty_data["diagnoses"]
    diagnosis = random.choice(list(diagnoses.keys()))
    diagnosis_data = diagnoses[diagnosis]

    snomed_code = diagnosis_data["snomed_code"]
    clinical_note = diagnosis_data["clinical_note"]

    return specialty, specialty_id, diagnosis, snomed_code, clinical_note


def get_providers_by_specialty(practice_id, specialty_id):
    """Get all providers for a given specialty"""
    providers_result = legacy_get("/v1/{practiceid}/providers", params={}, practice_id=practice_id)
    all_providers = providers_result.get("providers", [])

    specialty_providers = [p for p in all_providers if p.get("specialtyid") == specialty_id]

    return specialty_providers


def create_appointment_slots(practice_id, department_id, provider_id, appointmenttype_id="82", num_days=3):
    """
    Create appointment slots using the working method from create_appointment_slot.py.

    Args:
        practice_id: Practice ID
        department_id: Department ID
        provider_id: Provider ID
        appointmenttype_id: Appointment type ID (default: "82")
        num_days: Number of days to create slots for

    Returns:
        List of created appointment slot info
    """
    created_slots = []
    start_date = datetime.now() + timedelta(days=1)

    for day_offset in range(num_days):
        slot_date = start_date + timedelta(days=day_offset)
        date_str = slot_date.strftime("%m/%d/%Y")

        # Create slots at multiple times per day
        slot_times = ["09:00", "09:15", "09:30", "10:00", "10:15", "10:30"]

        # Use the exact method from create_appointment_slot.py that we know works
        data = {
            "appointmentdate": date_str,
            "appointmenttime": ','.join(slot_times),
            "appointmenttypeid": appointmenttype_id,
            "departmentid": department_id,
            "providerid": provider_id
        }

        try:
            result = legacy_post(
                "/v1/{practiceid}/appointments/open",
                data=data,
                practice_id=practice_id
            )

            # API returns appointmentids hash: {"09:00": "123", "09:15": "124", ...}
            appointment_ids = result.get("appointmentids", {})

            for time, appt_id in appointment_ids.items():
                created_slots.append({
                    "date": date_str,
                    "time": time,
                    "appointment_id": appt_id
                })

            print(f"  ✓ Created {len(appointment_ids)} slots for {date_str}")

        except Exception as e:
            print(f"  ⚠ Failed to create slots on {date_str}: {str(e)}")

    return created_slots


def main():
    parser = argparse.ArgumentParser(
        description="Generate complete A2A pipeline test data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate completely random test data
  %(prog)s --practice-id 195900 --random

  # Specify a specialty (random diagnosis within specialty)
  %(prog)s --practice-id 195900 --specialty cardiology

  # Reuse existing patient
  %(prog)s --practice-id 195900 --reuse-patient

  # Specify Primary Care specialty
  %(prog)s --practice-id 1959222 --specialty "Primary Care"

  # Force create new appointment slots even if slots exist
  %(prog)s --practice-id 195900 --force-create-slots

  # Dry run (don't create anything, just show what would be created)
  %(prog)s --practice-id 195900 --dry-run
        """
    )

    parser.add_argument('--practice-id', default='195900', help='Practice ID (default: 195900)')
    parser.add_argument('--random', action='store_true', help='Generate fully random data')
    parser.add_argument('--specialty', help='Specify specialty (random diagnosis within specialty)')
    parser.add_argument('--reuse-patient', action='store_true', help='Reuse existing patient from reusable_data.json')
    parser.add_argument('--force-create-slots', action='store_true', help='Force create new slots even if slots exist')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would be created without creating')
    parser.add_argument('--output', help='Save output to file')

    args = parser.parse_args()

    print("="*80)
    print("A2A PIPELINE TEST DATA GENERATOR")
    print("="*80)
    print(f"\nPractice ID: {args.practice_id}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    # Load templates
    templates = load_templates()

    # Step 1: Select specialty and diagnosis
    print("Step 1: Selecting Specialty and Diagnosis")
    print("-" * 80)

    if args.specialty:
        if args.specialty not in templates:
            print(f"  ✗ Unknown specialty: {args.specialty}")
            print(f"  Available: {', '.join(templates.keys())}")
            return

        specialty = args.specialty
        specialty_data = templates[specialty]

        # Validate specialty has providers in this practice
        practices = specialty_data.get("practices", [])
        if args.practice_id not in practices:
            print(f"  ✗ Specialty '{specialty}' has no providers in practice {args.practice_id}")
            print(f"  Available practices for {specialty}: {', '.join(practices)}")
            return

        specialty_id = specialty_data["specialty_id"]
        diagnoses = specialty_data["diagnoses"]
        diagnosis = random.choice(list(diagnoses.keys()))
        diagnosis_data = diagnoses[diagnosis]
        snomed_code = diagnosis_data["snomed_code"]
        clinical_note = diagnosis_data["clinical_note"]
    else:
        specialty, specialty_id, diagnosis, snomed_code, clinical_note = select_random_specialty_and_diagnosis(
            templates, practice_id=args.practice_id
        )

    print(f"  Specialty: {specialty} (ID: {specialty_id})")
    print(f"  Diagnosis: {diagnosis}")
    print(f"  SNOMED Code: {snomed_code}")
    print(f"  Clinical Note: {clinical_note[:80]}...")
    print()

    # Step 2: Create or reuse patient
    print("Step 2: Patient Creation/Reuse")
    print("-" * 80)

    # For reuse patient, load existing data to check for patients
    if args.reuse_patient:
        existing_data = load_patient_data()
        # Look for patients in pipeline_runs
        existing_patients = []
        for run in existing_data.get("pipeline_runs", []):
            if "pipeline_input" in run and "patient_id" in run["pipeline_input"]:
                existing_patients.append({
                    "patient_id": run["pipeline_input"]["patient_id"],
                    "specialty": run["pipeline_input"].get("specialty", "unknown"),
                    "created_at": run.get("metadata", {}).get("created_at", "")
                })

        if existing_patients:
            patient_entry = random.choice(existing_patients)
            patient_id = patient_entry["patient_id"]
            print(f"  ↻ Reusing existing patient {patient_id} (from previous {patient_entry['specialty']} run)")
        else:
            print(f"  ⚠ No existing patients found, creating new patient...")
            if args.dry_run:
                patient_data = generate_random_patient_data()
                patient_id = "DRY_RUN_PATIENT_ID"
                print(f"  [DRY RUN] Would create patient: {patient_data['firstname']} {patient_data['lastname']}")
            else:
                patient_id, patient_data = create_patient(args.practice_id)
    else:
        if args.dry_run:
            patient_data = generate_random_patient_data()
            patient_id = "DRY_RUN_PATIENT_ID"
            print(f"  [DRY RUN] Would create patient: {patient_data['firstname']} {patient_data['lastname']}")
        else:
            patient_id, patient_data = create_patient(args.practice_id)
    print()

    # Step 3: Create encounter via order group
    print("Step 3: Creating Encounter")
    print("-" * 80)

    if args.dry_run:
        encounter_id = "DRY_RUN_ENCOUNTER_ID"
        print(f"  [DRY RUN] Would create encounter for patient {patient_id}")
    else:
        encounter_id = create_encounter_via_ordergroup(args.practice_id, patient_id)
    print()

    # Step 4: Find providers by specialty
    print(f"Step 4: Finding Providers for {specialty}")
    print("-" * 80)

    if args.dry_run:
        print(f"  [DRY RUN] Would search for providers with specialty {specialty}")
        provider_id = "DRY_RUN_PROVIDER_ID"
        provider_name = "Dr. Dry Run"
    else:
        providers = get_providers_by_specialty(args.practice_id, specialty_id)

        if not providers:
            print(f"  ✗ No providers found for specialty {specialty} (ID: {specialty_id})")
            return

        print(f"  Found {len(providers)} providers with specialty {specialty}")

        # Select random provider
        provider = random.choice(providers)
        provider_id = str(provider["providerid"])
        provider_name = f"{provider.get('firstname', '')} {provider.get('lastname', '')}".strip()

        print(f"  ✓ Selected provider {provider_id}: {provider_name}")
    print()

    # Step 5: Search for existing appointment slots
    print("Step 5: Searching for Appointment Slots")
    print("-" * 80)

    slots_found = None
    created_new_slots = False

    if not args.force_create_slots:
        if args.dry_run:
            print(f"  [DRY RUN] Would search for slots for provider {provider_id}")
        else:
            slots_found = find_slots_for_provider_with_usual_priority(
                practice_id=args.practice_id,
                provider_id=provider_id,
                start_date=(datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y"),
                end_date=(datetime.now() + timedelta(days=30)).strftime("%m/%d/%Y")
            )

    # Step 6: Create slots if needed
    if not slots_found and not args.dry_run:
        print("\n  No existing slots found. Creating new appointment slots...")
        print("-" * 80)

        # Choose random department
        departments_result = legacy_get("/v1/{practiceid}/departments", params={}, practice_id=args.practice_id)
        all_departments = departments_result.get("departments", [])
        random_dept = random.choice(all_departments)
        department_id = str(random_dept["departmentid"])
        department_name = random_dept.get("name", "Unknown")

        print(f"  Selected department {department_id}: {department_name}")

        created_slots = create_appointment_slots(
            practice_id=args.practice_id,
            department_id=department_id,
            provider_id=provider_id,
            appointmenttype_id="82",
            num_days=3
        )

        if created_slots:
            print(f"  ✓ Created {len(created_slots)} appointment slots")

            # Calculate date range
            slot_dates = [s["date"] for s in created_slots]
            earliest_date = min(slot_dates)
            latest_date = max(slot_dates)

            slots_found = {
                "practice_id": args.practice_id,
                "provider_id": provider_id,
                "provider_name": provider_name,
                "department_id": department_id,
                "department_name": department_name,
                "available_slots": len(created_slots),
                "slot_date_range": {
                    "earliest": earliest_date,
                    "latest": latest_date
                },
                "created_new_slots": True
            }

            created_new_slots = True
    elif slots_found:
        print(f"  ✓ Found existing slots")
        print(f"    Department: {slots_found['department_id']} - {slots_found['department_name']}")
        print(f"    Available Slots: {slots_found['available_slots']}")
        print(f"    Date Range: {slots_found['slot_date_range']['earliest']} to {slots_found['slot_date_range']['latest']}")

    print()

    # Step 7: Generate output payload
    print("Step 7: Generating Pipeline Input Payload")
    print("="*80)

    output_payload = {
        "pipeline_input": {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "specialty": specialty,
            "diagnosis": diagnosis,
            "snomed_code": snomed_code,
            "clinical_note": clinical_note
        },
        "appointment_context": {
            "provider_id": slots_found["provider_id"] if slots_found else provider_id,
            "provider_name": slots_found["provider_name"] if slots_found else provider_name,
            "department_id": slots_found["department_id"] if slots_found else "UNKNOWN",
            "department_name": slots_found.get("department_name", "UNKNOWN") if slots_found else "UNKNOWN",
            "slots_available": bool(slots_found),
            "slot_date_range": slots_found["slot_date_range"] if slots_found else None,
            "created_new_slots": created_new_slots
        },
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "practice_id": args.practice_id,
            "encounter_status": "open",
            "note": "Encounter created without diagnosis - agent will add diagnosis from pipeline_input"
        }
    }

    print("\n" + json.dumps(output_payload, indent=2))
    print("\n" + "="*80)

    # Append to patient_data.json (unless dry run)
    if not args.dry_run:
        append_pipeline_run(output_payload)
        print(f"\n✓ Appended to {PATIENT_DATA_FILE}")

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output_payload, f, indent=2)
        print(f"✓ Saved payload to {args.output}")

    print("\n✓ Complete! Pipeline input ready.")
    print("\nNext Steps:")
    print("  1. Copy the pipeline_input section to feed into Referral Agent")
    print("  2. Agent will add diagnosis to the open encounter")
    print("  3. Agent will create referral order")
    print("  4. Agent will schedule appointment using appointment_context")


if __name__ == "__main__":
    main()
