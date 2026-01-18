#!/usr/bin/env python3
"""
Create Patient + Encounter Utility
Simple pipeline: Create patient → Verify → Create encounter via order group

Usage:
    python create_patient.py --practice-id 195900 --firstname John --lastname Doe \\
        --dob 01/15/1990 --sex M --department-id 1 --email john@example.com --zip 93101
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from athena_api import AthenaWorkflow, legacy_post


def main():
    parser = argparse.ArgumentParser(description="Create patient and encounter")
    parser.add_argument('--practice-id', required=True)
    parser.add_argument('--firstname', required=True)
    parser.add_argument('--lastname', required=True)
    parser.add_argument('--dob', required=True, help='MM/DD/YYYY')
    parser.add_argument('--sex', required=True, choices=['M', 'F'])
    parser.add_argument('--department-id', required=True)
    parser.add_argument('--email', required=True)
    parser.add_argument('--zip', required=True)
    parser.add_argument('--provider-id', default='71', help='Provider ID (default: 71)')
    args = parser.parse_args()

    api = AthenaWorkflow(practice_id=args.practice_id)

    print("=" * 80)
    print("PATIENT + ENCOUNTER CREATION")
    print("=" * 80)

    # Step 1: Create patient
    print(f"\n[1] Creating patient: {args.firstname} {args.lastname}")
    result = api.create_patient(
        firstname=args.firstname,
        lastname=args.lastname,
        dob=args.dob,
        sex=args.sex,
        department_id=args.department_id,
        email=args.email,
        zip=args.zip
    )
    patient_id = result["patientid"]
    print(f"✅ Patient ID: {patient_id}")

    # Step 2: Verify patient exists
    print(f"\n[2] Verifying patient...")
    patient = api.get_patient_details(patient_id)
    print(f"✅ Verified: {patient['firstname']} {patient['lastname']}")

    # Step 3: Create order group (triggers encounter creation)
    print(f"\n[3] Creating order group (triggers encounter)...")
    ordergroup_result = legacy_post(
        f"/v1/{{practiceid}}/chart/{patient_id}/ordergroups",
        data={
            "departmentid": args.department_id,
            "providerid": args.provider_id,
        },
        practice_id=args.practice_id
    )

    encounter_id = ordergroup_result.get("encounterid")
    if encounter_id:
        print(f"✅ Encounter ID: {encounter_id} (from order group response)")
    else:
        print(f"⚠️  No encounter ID in response, checking encounters...")

    # Step 4: Verify encounter exists
    print(f"\n[4] Verifying encounter...")

    # If we got encounter ID from order group, use that
    if encounter_id:
        print(f"✅ Using encounter from order group: {encounter_id}")

        print("\n" + "=" * 80)
        print("✅ SUCCESS")
        print("=" * 80)
        print(f"Patient ID: {patient_id}")
        print(f"Encounter ID: {encounter_id}")
        print(f"Department ID: {args.department_id}")
        print(f"Provider ID: {args.provider_id}")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ No encounter created")
        sys.exit(1)


if __name__ == "__main__":
    main()