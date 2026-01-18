#!/usr/bin/env python3
"""
Create Unique Schedules for Internal Medicine Providers
Generates appointment slot schedules for Internal Medicine referral consults.

Date Range: January 15, 2026 - February 15, 2026
Geographic Cluster: Greater Boston (South) - Norwood, Dedham, Boston

Usage:
    python create_internal_medicine_schedules.py --practice-id 1959222 --start-date 01/15/2026 --end-date 02/15/2026
    python create_internal_medicine_schedules.py --practice-id 1959222 --start-date 01/15/2026 --end-date 02/15/2026 --dry-run
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from athena_api import legacy_post

# Appointment type for all Internal Medicine referrals
APPOINTMENT_TYPE_ID = '62'  # Consult (30 min)

# Provider schedules with unique characteristics
PROVIDER_SCHEDULES = {
    '67': {  # Chip Ach - Early Bird
        'name': 'Chip Ach',
        'department_id': '155',
        'department_name': 'kate DEPT',
        'location': 'Norwood, MA',
        'schedule_type': 'Full-time (Early Bird)',
        'working_days': ['Monday', 'Tuesday', 'Thursday'],
        'friday_schedule': True,  # Friday has different hours
        'hours': '6:30am - 2:30pm',
        'lunch': '11:00am - 11:30am',
        'time_slots': [
            '06:30', '07:00', '07:30', '08:00', '08:30', '09:00', '09:30',
            '10:00', '10:30', '11:30', '12:00', '12:30', '13:00', '13:30'
        ],
        'friday_slots': [
            '06:30', '07:00', '07:30', '08:00', '08:30', '09:00', '09:30',
            '10:00', '10:30', '11:00', '11:30'
        ]
    },
    '86': {  # Laura Dodge - Standard
        'name': 'Laura Dodge',
        'department_id': '155',
        'department_name': 'kate DEPT',
        'location': 'Norwood, MA',
        'schedule_type': 'Full-time (Standard)',
        'working_days': ['Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        'friday_schedule': False,
        'hours': '9:00am - 5:00pm',
        'lunch': '12:30pm - 1:30pm',
        'time_slots': [
            '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00',
            '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30'
        ]
    },
    '21': {  # Pierce Hawkeye - Standard
        'name': 'Pierce Hawkeye',
        'department_id': '168',
        'department_name': 'Springfield Medical',
        'location': 'Dedham, MA',
        'schedule_type': 'Full-time (Standard)',
        'working_days': ['Monday', 'Tuesday', 'Wednesday', 'Friday'],
        'friday_schedule': False,
        'hours': '8:00am - 4:00pm',
        'lunch': '12:00pm - 12:30pm',
        'time_slots': [
            '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
            '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30'
        ]
    },
    '77': {  # Joshua Parker - Part-time Afternoons
        'name': 'Joshua Parker',
        'department_id': '168',
        'department_name': 'Springfield Medical',
        'location': 'Dedham, MA',
        'schedule_type': 'Part-time (Afternoons)',
        'working_days': ['Tuesday', 'Thursday'],
        'friday_schedule': False,
        'hours': '1:00pm - 5:00pm',
        'lunch': None,
        'time_slots': [
            '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30'
        ]
    },
    '68': {  # Luvenia Smith - Late
        'name': 'Luvenia Smith',
        'department_id': '149',
        'department_name': 'Ortho OP',
        'location': 'Boston, MA (outlier ~15mi)',
        'schedule_type': 'Full-time (Late)',
        'working_days': ['Monday', 'Tuesday', 'Thursday', 'Friday'],
        'friday_schedule': False,
        'hours': '11:00am - 7:00pm',
        'lunch': '2:00pm - 2:30pm',
        'time_slots': [
            '11:00', '11:30', '12:00', '12:30', '13:00', '13:30',
            '14:30', '15:00', '15:30', '16:00', '16:30', '17:00', '17:30', '18:00', '18:30'
        ]
    }
}


def create_slots_for_provider(practice_id, provider_id, department_id, date, times, appointmenttype_id):
    """Create appointment slots for a provider on a specific date"""
    data = {
        "appointmentdate": date,
        "appointmenttime": ','.join(times),
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
        appointment_ids = result.get("appointmentids", {})
        return len(appointment_ids), list(appointment_ids.keys())
    except Exception as e:
        print(f"    ⚠️  Error creating slots: {e}")
        return 0, []


def main():
    parser = argparse.ArgumentParser(description="Create schedules for Internal Medicine providers")
    parser.add_argument('--practice-id', required=True, help='Practice ID')
    parser.add_argument('--start-date', required=True, help='Start date (MM/DD/YYYY)')
    parser.add_argument('--end-date', required=True, help='End date (MM/DD/YYYY)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without actually creating')
    parser.add_argument('--provider', help='Only create for specific provider ID (e.g., 67)')

    args = parser.parse_args()

    print("=" * 80)
    print("INTERNAL MEDICINE SCHEDULE CREATION")
    print("=" * 80)
    print(f"\nPractice ID: {args.practice_id}")
    print(f"Date Range: {args.start_date} to {args.end_date}")
    print(f"Appointment Type: {APPOINTMENT_TYPE_ID} (Consult - 30 min)")
    print(f"Mode: {'DRY RUN (no actual creation)' if args.dry_run else 'LIVE'}")
    if args.provider:
        print(f"Provider Filter: {args.provider} only")

    # Parse dates
    start_date = datetime.strptime(args.start_date, '%m/%d/%Y')
    end_date = datetime.strptime(args.end_date, '%m/%d/%Y')
    num_days = (end_date - start_date).days + 1

    print(f"Total Days: {num_days}")

    grand_total_slots = 0

    # Process each provider
    for provider_id, schedule in PROVIDER_SCHEDULES.items():
        # Skip if filtering by provider
        if args.provider and provider_id != args.provider:
            continue

        print(f"\n{'=' * 80}")
        print(f"PROVIDER [{provider_id}] {schedule['name']}")
        print(f"{'=' * 80}")
        print(f"Department: [{schedule['department_id']}] {schedule['department_name']}")
        print(f"Location: {schedule['location']}")
        print(f"Schedule Type: {schedule['schedule_type']}")
        print(f"Hours: {schedule['hours']}")
        print(f"Lunch: {schedule['lunch'] or 'None'}")
        print(f"Working Days: {', '.join(schedule['working_days'])}")
        if schedule.get('friday_schedule'):
            print(f"Friday (special): AM only - {len(schedule['friday_slots'])} slots")

        total_slots_created = 0
        days_worked = 0

        # Create slots for each day in range
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%m/%d/%Y')
            day_name = current_date.strftime('%A')

            # Check if provider works on this day
            is_friday = day_name == 'Friday'
            works_today = day_name in schedule['working_days'] or (is_friday and schedule.get('friday_schedule'))

            if works_today:
                # Use Friday slots if applicable
                if is_friday and schedule.get('friday_schedule'):
                    time_slots = schedule['friday_slots']
                else:
                    time_slots = schedule['time_slots']

                if not args.dry_run:
                    slots_created, times_created = create_slots_for_provider(
                        args.practice_id,
                        provider_id,
                        schedule['department_id'],
                        date_str,
                        time_slots,
                        APPOINTMENT_TYPE_ID
                    )
                    print(f"  📅 {date_str} ({day_name}): {slots_created} slots created")
                    total_slots_created += slots_created
                else:
                    print(f"  📅 {date_str} ({day_name}): {len(time_slots)} slots (dry run)")
                    total_slots_created += len(time_slots)

                days_worked += 1

            current_date += timedelta(days=1)

        print(f"\n  ✅ Total for {schedule['name']}: {total_slots_created} slots over {days_worked} days")
        grand_total_slots += total_slots_created

    print("\n" + "=" * 80)
    print(f"GRAND TOTAL: {grand_total_slots} slots")
    if args.dry_run:
        print("✅ DRY RUN COMPLETE - No slots actually created")
    else:
        print("✅ SCHEDULE CREATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
