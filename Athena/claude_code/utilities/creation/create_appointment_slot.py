#!/usr/bin/env python3
"""
Create Appointment Slot Utility
Creates new appointment slots for a provider/department at specific date/time

Usage:
    python create_appointment_slot.py --practice-id 195900 --provider-id 27 \\
        --department-id 150 --date 11/15/2025 --time 09:00,09:15,09:30 --appointmenttype-id 82
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from athena_api import legacy_post

def main():
    parser = argparse.ArgumentParser(description="Create appointment slots")
    parser.add_argument('--practice-id', required=True, help='Practice ID')
    parser.add_argument('--provider-id', required=True, help='Provider ID')
    parser.add_argument('--department-id', required=True, help='Department ID')
    parser.add_argument('--date', required=True, help='Appointment date (MM/DD/YYYY)')
    parser.add_argument('--time', required=True, help='Appointment time(s) in HH:MM format, comma-separated (e.g., 09:00,09:15,09:30)')
    parser.add_argument('--appointmenttype-id', required=True, help='Appointment type ID')
    args = parser.parse_args()

    print("=" * 80)
    print("APPOINTMENT SLOT CREATION")
    print("=" * 80)

    # Prepare data for slot creation
    times = [t.strip() for t in args.time.split(',')]

    print(f"\n[1] Creating appointment slots...")
    print(f"    Provider: {args.provider_id}")
    print(f"    Department: {args.department_id}")
    print(f"    Date: {args.date}")
    print(f"    Times: {', '.join(times)}")
    print(f"    Appointment Type ID: {args.appointmenttype_id}")

    data = {
        "appointmentdate": args.date,
        "appointmenttime": ','.join(times),
        "appointmenttypeid": args.appointmenttype_id,
        "departmentid": args.department_id,
        "providerid": args.provider_id
    }

    result = legacy_post(
        "/v1/{practiceid}/appointments/open",
        data=data,
        practice_id=args.practice_id
    )

    # API returns appointmentids hash
    appointment_ids = result.get("appointmentids", {})

    if appointment_ids:
        print(f"\n✅ Created {len(appointment_ids)} appointment slot(s):")
        for time, appt_id in appointment_ids.items():
            print(f"    {time} → Appointment ID: {appt_id}")
    else:
        print("⚠️  No appointment IDs returned")

    print("\n" + "=" * 80)
    print("✅ SUCCESS")
    print("=" * 80)
    print(f"Provider: {args.provider_id}")
    print(f"Department: {args.department_id}")
    print(f"Date: {args.date}")
    print(f"Slots Created: {len(appointment_ids)}")
    print("=" * 80)

if __name__ == "__main__":
    main()