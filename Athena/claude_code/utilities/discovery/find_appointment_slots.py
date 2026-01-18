#!/usr/bin/env python3
"""
Find Appointment Slots - General Purpose Tool

Purpose: Find providers with available appointment slots across any practice/department/provider combination
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from athena_api import AthenaWorkflow, legacy_get
from datetime import datetime, timedelta
import argparse
import json


def find_slots(practice_id, department_ids=None, provider_ids=None,
               start_date=None, end_date=None, exhaustive=False, reason_id="-1",
               prioritize_usual_department=False):
    """
    Find appointment slots based on given criteria.

    Args:
        practice_id: Practice ID to search
        department_ids: List of department IDs (None = search all)
        provider_ids: List of provider IDs (None = search all)
        start_date: Start date (default: tomorrow)
        end_date: End date (default: +90 days)
        exhaustive: If True, test all providers x departments
        reason_id: Reason ID for slot search (default: "-1" for all)
        prioritize_usual_department: If True, search usual department first for each provider

    Returns:
        List of dicts with slot information
    """
    workflow = AthenaWorkflow(practice_id=practice_id)

    # Set date defaults
    if not start_date:
        start_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=90)).strftime("%m/%d/%Y")

    results = []

    # Get all providers if not specified
    if not provider_ids or exhaustive:
        print(f"  Fetching all providers in practice {practice_id}...")
        providers_result = legacy_get("/v1/{practiceid}/providers", params={}, practice_id=practice_id)
        all_providers = providers_result.get("providers", [])
        if not provider_ids:
            provider_ids = [str(p["providerid"]) for p in all_providers if p.get("providerid")]
        print(f"  Found {len(all_providers)} providers")

        # Create provider map for usual department lookup
        provider_map = {str(p["providerid"]): p for p in all_providers}
    else:
        # Fetch provider details for usual department
        providers_result = legacy_get("/v1/{practiceid}/providers", params={}, practice_id=practice_id)
        all_providers = providers_result.get("providers", [])
        provider_map = {str(p["providerid"]): p for p in all_providers}

    # Get all departments if not specified
    if not department_ids or exhaustive:
        print(f"  Fetching all departments in practice {practice_id}...")
        departments_result = legacy_get("/v1/{practiceid}/departments", params={}, practice_id=practice_id)
        all_departments = departments_result.get("departments", [])
        if not department_ids:
            department_ids = [str(d["departmentid"]) for d in all_departments if d.get("departmentid")]
        print(f"  Found {len(all_departments)} departments")

    # Search combinations
    total_combinations = len(provider_ids) * len(department_ids)
    print(f"\n  Searching {total_combinations} provider/department combinations...")
    print(f"  Date range: {start_date} to {end_date}")

    checked = 0
    for provider_id in provider_ids:
        # Get ordered list of departments (usual first if prioritizing)
        departments_to_check = list(department_ids)

        if prioritize_usual_department and provider_id in provider_map:
            usual_dept = provider_map[provider_id].get("usualdepartmentid")
            if usual_dept and str(usual_dept) in departments_to_check:
                # Move usual department to front of list
                departments_to_check.remove(str(usual_dept))
                departments_to_check.insert(0, str(usual_dept))
                print(f"  Provider {provider_id}: Prioritizing usual department {usual_dept}")

        for dept_id in departments_to_check:
            checked += 1
            if checked % 10 == 0:
                print(f"  Progress: {checked}/{total_combinations} combinations checked...")

            try:
                slots = workflow.find_appointment_slots(
                    department_id=dept_id,
                    provider_id=provider_id,
                    start_date=start_date,
                    end_date=end_date,
                    reason_id=reason_id
                )

                if slots:
                    # Calculate date range
                    slot_dates = [s['date'] for s in slots]
                    earliest_date = min(slot_dates)
                    latest_date = max(slot_dates)

                    first_slot = slots[0]
                    results.append({
                        "practice_id": practice_id,
                        "provider_id": provider_id,
                        "department_id": dept_id,
                        "available_slots": len(slots),
                        "slot_date_range": {
                            "earliest": earliest_date,
                            "latest": latest_date
                        },
                        "first_slot_date": first_slot['date'],
                        "first_slot_time": first_slot['starttime'],
                        "appointmenttypeid": str(first_slot['appointmenttypeid']),
                        "appointment_type": first_slot['appointmenttype'],
                        "appointment_id": first_slot['appointmentid']
                    })
            except Exception as e:
                # Silent failure for invalid combinations
                pass

    return results


def find_slots_for_provider_with_usual_priority(practice_id, provider_id,
                                                  start_date=None, end_date=None,
                                                  reason_id="-1"):
    """
    Find appointment slots for a specific provider, prioritizing their usual department.
    Returns the first department with available slots.

    Args:
        practice_id: Practice ID to search
        provider_id: Provider ID to search
        start_date: Start date (default: tomorrow)
        end_date: End date (default: +90 days)
        reason_id: Reason ID for slot search (default: "-1" for all)

    Returns:
        Dict with slot information for first department with slots, or None
    """
    workflow = AthenaWorkflow(practice_id=practice_id)

    # Set date defaults
    if not start_date:
        start_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=90)).strftime("%m/%d/%Y")

    # Get provider details to find usual department
    providers_result = legacy_get("/v1/{practiceid}/providers", params={}, practice_id=practice_id)
    all_providers = providers_result.get("providers", [])
    provider_map = {str(p["providerid"]): p for p in all_providers}

    if provider_id not in provider_map:
        print(f"  ✗ Provider {provider_id} not found")
        return None

    provider = provider_map[provider_id]
    usual_dept = provider.get("usualdepartmentid")

    # Get all departments
    departments_result = legacy_get("/v1/{practiceid}/departments", params={}, practice_id=practice_id)
    all_departments = departments_result.get("departments", [])
    department_ids = [str(d["departmentid"]) for d in all_departments]

    # Create ordered list: usual department first, then others
    departments_to_check = []
    if usual_dept and str(usual_dept) in department_ids:
        departments_to_check.append(str(usual_dept))
        print(f"  Checking usual department {usual_dept} first for provider {provider_id}")

    # Add remaining departments
    other_depts = [d for d in department_ids if d != str(usual_dept)]
    departments_to_check.extend(other_depts)

    # Search until we find slots
    for dept_id in departments_to_check:
        try:
            slots = workflow.find_appointment_slots(
                department_id=dept_id,
                provider_id=provider_id,
                start_date=start_date,
                end_date=end_date,
                reason_id=reason_id
            )

            if slots:
                # Calculate date range
                slot_dates = [s['date'] for s in slots]
                earliest_date = min(slot_dates)
                latest_date = max(slot_dates)

                first_slot = slots[0]

                # Get department name
                dept_name = next((d['name'] for d in all_departments
                                 if str(d['departmentid']) == dept_id), "Unknown")

                result = {
                    "practice_id": practice_id,
                    "provider_id": provider_id,
                    "provider_name": f"{provider.get('firstname', '')} {provider.get('lastname', '')}".strip(),
                    "department_id": dept_id,
                    "department_name": dept_name,
                    "available_slots": len(slots),
                    "slot_date_range": {
                        "earliest": earliest_date,
                        "latest": latest_date
                    },
                    "first_slot_date": first_slot['date'],
                    "first_slot_time": first_slot['starttime'],
                    "appointmenttypeid": str(first_slot['appointmenttypeid']),
                    "appointment_type": first_slot['appointmenttype'],
                    "appointment_id": first_slot['appointmentid'],
                    "searched_usual_dept_first": (dept_id == str(usual_dept))
                }

                if dept_id == str(usual_dept):
                    print(f"  ✓ Found {len(slots)} slots in usual department {dept_id}")
                else:
                    print(f"  ✓ Found {len(slots)} slots in department {dept_id} (not usual dept)")

                return result

        except Exception as e:
            # Silent failure for invalid combinations
            pass

    print(f"  ✗ No slots found for provider {provider_id} in any department")
    return None


def verify_test_cases(test_cases_file):
    """
    Verify specific test cases from JSON file.

    Args:
        test_cases_file: Path to JSON file with test cases

    Returns:
        List of verified test cases
    """
    with open(test_cases_file, 'r') as f:
        test_data = json.load(f)

    test_cases = test_data.get("test_cases", test_data.get("verified_cases", []))

    print(f"\n  Verifying {len(test_cases)} test cases...")

    verified = []
    for i, case in enumerate(test_cases, 1):
        practice_id = case.get("practice_id", "195900")
        provider_id = case["provider_id"]
        dept_id = case["department_id"]

        print(f"\n  Test Case #{i}: Provider {provider_id}, Dept {dept_id}")

        results = find_slots(
            practice_id=practice_id,
            provider_ids=[provider_id],
            department_ids=[dept_id],
            reason_id="-1"
        )

        if results:
            verified.append(results[0])
            print(f"    ✓ Verified: {results[0]['available_slots']} slots available")
        else:
            print(f"    ✗ No slots found")

    return verified


def main():
    parser = argparse.ArgumentParser(
        description="Find appointment slots across practices/departments/providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick search in specific departments
  %(prog)s --practice-id 195900 --department-ids 1,162

  # Exhaustive search of all combinations
  %(prog)s --practice-id 195900 --exhaustive

  # Search specific providers only
  %(prog)s --practice-id 1959222 --provider-ids 121,71

  # Verify test cases from JSON file
  %(prog)s --practice-id 195900 --verify-test-cases test_inputs.json

  # Custom date range with JSON output
  %(prog)s --practice-id 195900 --start-date 11/10/2025 --end-date 11/15/2025 --output-format json
        """
    )

    parser.add_argument('--practice-id', required=True, help='Practice ID to search')
    parser.add_argument('--department-ids', help='Comma-separated department IDs')
    parser.add_argument('--provider-ids', help='Comma-separated provider IDs')
    parser.add_argument('--start-date', help='Start date (MM/DD/YYYY, default: tomorrow)')
    parser.add_argument('--end-date', help='End date (MM/DD/YYYY, default: +90 days)')
    parser.add_argument('--exhaustive', action='store_true', help='Search ALL providers x departments')
    parser.add_argument('--verify-test-cases', help='Verify test cases from JSON file')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--output-format', choices=['txt', 'json', 'both'], default='txt',
                       help='Output format (default: txt)')
    parser.add_argument('--reason-id', default='-1', help='Reason ID for slots (default: -1 = all)')

    args = parser.parse_args()

    print("="*80)
    print("APPOINTMENT SLOT FINDER")
    print("="*80)
    print(f"\nPractice ID: {args.practice_id}")

    # Parse comma-separated IDs
    dept_ids = args.department_ids.split(',') if args.department_ids else None
    provider_ids = args.provider_ids.split(',') if args.provider_ids else None

    # Verify test cases mode
    if args.verify_test_cases:
        print(f"Mode: Verify test cases from {args.verify_test_cases}")
        results = verify_test_cases(args.verify_test_cases)
    else:
        # Normal search mode
        if args.exhaustive:
            print("Mode: Exhaustive search (all providers x departments)")
        elif provider_ids and dept_ids:
            print(f"Mode: Targeted search")
            print(f"  Providers: {', '.join(provider_ids)}")
            print(f"  Departments: {', '.join(dept_ids)}")
        elif provider_ids:
            print(f"Mode: Search specific providers across all departments")
            print(f"  Providers: {', '.join(provider_ids)}")
        elif dept_ids:
            print(f"Mode: Search all providers in specific departments")
            print(f"  Departments: {', '.join(dept_ids)}")
        else:
            print(f"Mode: Search all providers and departments")

        results = find_slots(
            practice_id=args.practice_id,
            department_ids=dept_ids,
            provider_ids=provider_ids,
            start_date=args.start_date,
            end_date=args.end_date,
            exhaustive=args.exhaustive,
            reason_id=args.reason_id
        )

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"\nFound {len(results)} provider/department combinations with available slots\n")

    if results:
        for i, result in enumerate(results, 1):
            print(f"Result #{i}:")
            print(f"  Provider: {result['provider_id']}, Department: {result['department_id']}")
            print(f"  Available Slots: {result['available_slots']}")
            print(f"  First Slot: {result['first_slot_date']} at {result['first_slot_time']}")
            print(f"  Appointment Type: {result['appointment_type']} (ID: {result['appointmenttypeid']})")
            print()

    # Save output
    if args.output or args.output_format in ['json', 'both']:
        output_file = args.output or f"appointment_slots_{args.practice_id}.txt"

        if args.output_format in ['txt', 'both']:
            txt_file = output_file if output_file.endswith('.txt') else output_file + '.txt'
            with open(txt_file, 'w') as f:
                f.write(f"Appointment Slots - Practice {args.practice_id}\n")
                f.write("="*80 + "\n\n")
                for i, result in enumerate(results, 1):
                    f.write(f"Provider {result['provider_id']} (Dept {result['department_id']}):\n")
                    f.write(f"  Available Slots: {result['available_slots']}\n")
                    f.write(f"  First Slot: {result['first_slot_date']} at {result['first_slot_time']}\n")
                    f.write(f"  Appointment Type: {result['appointment_type']}\n")
                    f.write(f"  appointmenttypeid: {result['appointmenttypeid']}\n\n")
            print(f"✓ Saved to {txt_file}")

        if args.output_format in ['json', 'both']:
            json_file = output_file.replace('.txt', '.json') if output_file.endswith('.txt') else output_file + '.json'
            with open(json_file, 'w') as f:
                json.dump({
                    "practice_id": args.practice_id,
                    "search_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "results": results,
                    "total_found": len(results)
                }, f, indent=2)
            print(f"✓ Saved to {json_file}")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()