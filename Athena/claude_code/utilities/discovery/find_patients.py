#!/usr/bin/env python3
"""
Find Patients - General Purpose Tool

Purpose: Find patients by encounter status (with open encounters, without encounters, or any)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from athena_api import AthenaWorkflow, legacy_get
import argparse


def find_patients(practice_id, department_id="1", encounter_status="any",
                 lastname_patterns=None, limit=20):
    """
    Find patients based on encounter status criteria.

    Args:
        practice_id: Practice ID to search
        department_id: Department ID (default: "1")
        encounter_status: "open", "no-open", "any" (default: "any")
        lastname_patterns: List of lastname patterns to search (default: ["Test", "Sandbox", "Demo", "Sample"])
        limit: Maximum number of patients to check (default: 20)

    Returns:
        List of patient dicts with encounter information
    """
    workflow = AthenaWorkflow(practice_id=practice_id)

    if not lastname_patterns:
        lastname_patterns = ["Test", "Sandbox", "Demo", "Sample"]

    print(f"  Searching for patients matching: {', '.join(lastname_patterns)}")
    print(f"  Practice: {practice_id}, Department: {department_id}")
    print(f"  Encounter filter: {encounter_status}")

    # Gather all patients
    all_patients = []
    for pattern in lastname_patterns:
        try:
            result = legacy_get(
                f"/v1/{{practiceid}}/patients",
                params={"lastname": pattern},
                practice_id=practice_id
            )
            patients = result.get("patients", [])
            all_patients.extend(patients)
        except Exception as e:
            print(f"  ⚠️  Error searching pattern '{pattern}': {e}")

    print(f"  Found {len(all_patients)} patients total")

    # Check each patient's encounter status
    results = []
    checked = 0

    for patient in all_patients[:limit]:
        checked += 1
        patient_id = patient.get("patientid")
        firstname = patient.get("firstname", "")
        lastname = patient.get("lastname", "")

        try:
            encounters = legacy_get(
                f"/v1/{{practiceid}}/chart/{patient_id}/encounters",
                params={"departmentid": department_id},
                practice_id=practice_id
            )

            open_encounters = [e for e in encounters.get("encounters", [])
                             if e.get("status") == "OPEN"]
            all_encounters = encounters.get("encounters", [])

            # Filter based on encounter status
            include = False
            if encounter_status == "any":
                include = True
            elif encounter_status == "open" and open_encounters:
                include = True
            elif encounter_status == "no-open" and not open_encounters:
                include = True

            if include:
                patient_info = {
                    "patient_id": patient_id,
                    "name": f"{firstname} {lastname}",
                    "total_encounters": len(all_encounters),
                    "open_encounters": len(open_encounters)
                }

                if open_encounters:
                    enc = open_encounters[0]
                    patient_info["encounter_id"] = enc.get("encounterid")
                    patient_info["encounter_date"] = enc.get("encounterdate")
                    patient_info["encounter_status"] = enc.get("status")

                results.append(patient_info)

        except Exception as e:
            # Silent failure for patients not in department
            pass

    print(f"  Checked {checked} patients")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Find patients by encounter status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find patients WITH open encounters (referral-ready)
  %(prog)s --practice-id 195900 --encounter-status open

  # Find patients WITHOUT open encounters (clean state for testing)
  %(prog)s --practice-id 195900 --encounter-status no-open

  # Find all patients matching patterns
  %(prog)s --practice-id 195900 --encounter-status any

  # Custom search patterns
  %(prog)s --practice-id 195900 --lastname-patterns "Smith,Johnson,Test" --limit 50

  # Save to file
  %(prog)s --practice-id 195900 --encounter-status open --output viable_patients.txt
        """
    )

    parser.add_argument('--practice-id', required=True, help='Practice ID to search')
    parser.add_argument('--department-id', default='1', help='Department ID (default: 1)')
    parser.add_argument('--encounter-status', choices=['open', 'no-open', 'any'], default='any',
                       help='Filter by encounter status (default: any)')
    parser.add_argument('--lastname-patterns', help='Comma-separated lastname patterns (default: Test,Sandbox,Demo,Sample)')
    parser.add_argument('--limit', type=int, default=20, help='Max patients to check (default: 20)')
    parser.add_argument('--output', help='Output file path (optional)')

    args = parser.parse_args()

    print("="*80)
    print("PATIENT FINDER")
    print("="*80)
    print(f"\nPractice ID: {args.practice_id}")
    print(f"Department ID: {args.department_id}")

    # Parse patterns
    patterns = args.lastname_patterns.split(',') if args.lastname_patterns else None

    print()
    results = find_patients(
        practice_id=args.practice_id,
        department_id=args.department_id,
        encounter_status=args.encounter_status,
        lastname_patterns=patterns,
        limit=args.limit
    )

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"\nFound {len(results)} patients matching criteria\n")

    for i, patient in enumerate(results, 1):
        print(f"Patient #{i}:")
        print(f"  ID: {patient['patient_id']}")
        print(f"  Name: {patient['name']}")
        print(f"  Total Encounters: {patient['total_encounters']}")
        print(f"  Open Encounters: {patient['open_encounters']}")

        if 'encounter_id' in patient:
            print(f"  Active Encounter: {patient['encounter_id']}")
            print(f"    Date: {patient['encounter_date']}")
            print(f"    Status: {patient['encounter_status']}")
        print()

    # Save output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(f"Patients - Practice {args.practice_id} (Encounter Status: {args.encounter_status})\n")
            f.write("="*80 + "\n\n")

            for patient in results:
                f.write(f"Patient ID: {patient['patient_id']}\n")
                f.write(f"  Name: {patient['name']}\n")
                f.write(f"  Total Encounters: {patient['total_encounters']}\n")
                f.write(f"  Open Encounters: {patient['open_encounters']}\n")

                if 'encounter_id' in patient:
                    f.write(f"  Encounter ID: {patient['encounter_id']}\n")
                    f.write(f"  Encounter Date: {patient['encounter_date']}\n")
                f.write("\n")

        print(f"✓ Saved to {args.output}")

    print("="*80)


if __name__ == "__main__":
    main()