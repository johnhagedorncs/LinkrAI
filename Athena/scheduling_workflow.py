"""
Athena Health Appointment Scheduling Workflow
Orchestrates the appointment booking process
If "Provider ID 121 is not valid" errors update to Athena Specific practiceID
"""

from datetime import datetime, timedelta
from athena_api import AthenaWorkflow, WorkflowResult, legacy_put


def execute_simplified_appointment_workflow(
    patient_lastname: str,
    department_id: str = "162",
    provider_id: str = "121"
) -> WorkflowResult:
    """
    Simplified workflow: Find patient, search slots, and book appointment
    Books using appointmenttypeid (not reasonid) which works reliably for all slots

    Args:
        patient_lastname: Patient's last name
        department_id: Department ID (default: 162 - Kessler)
        provider_id: Provider ID (default: 121 - Epocrates Patient)

    Returns:
        WorkflowResult with patient and appointment IDs
    """
    workflow = AthenaWorkflow()
    result = WorkflowResult()

    print("\n" + "="*80)
    print("ATHENA APPOINTMENT BOOKING WORKFLOW")
    print("="*80)

    try:
        # Step 1: Find patient
        print("\n📋 STEP 1: Find Patient")
        print("-" * 80)
        patient = workflow.find_patient(patient_lastname)
        result.patient_id = patient["patientid"]
        result.add_step(f"Found patient: {patient.get('firstname')} {patient.get('lastname')} (ID: {result.patient_id})")

        # Step 2: Find all available appointment slots
        print("\n📅 STEP 2: Find Available Slots")
        print("-" * 80)
        start_date = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")
        end_date = (datetime.now() + timedelta(days=60)).strftime("%m/%d/%Y")

        slots = workflow.find_appointment_slots(
            department_id=department_id,
            provider_id=provider_id,
            reason_id="-1",  # Get all slots regardless of reason
            start_date=start_date,
            end_date=end_date,
            bypass_checks=True
        )
        result.add_step(f"Found {len(slots)} available slots between {start_date} and {end_date}")

        if slots:
            print(f"   First available: {slots[0].get('date')} at {slots[0].get('starttime')}")
            print(f"   Type: {slots[0].get('appointmenttype')}")

        # Step 3: Book first available slot using its appointmenttypeid
        appointment = None
        if slots:
            print("\n✅ STEP 3: Book Appointment")
            print("-" * 80)
            first_slot = slots[0]
            appointment_type_id = str(first_slot.get('appointmenttypeid'))

            print(f"   Booking slot: {first_slot.get('date')} at {first_slot.get('starttime')}")
            print(f"   Using appointment type ID: {appointment_type_id}")

            # Book with appointmenttypeid (works reliably for all slots)
            data = {
                "patientid": result.patient_id,
                "appointmenttypeid": appointment_type_id,
                "ignoreschedulablepermission": "true"
            }

            appointment_result = legacy_put(
                f"/v1/{{practiceid}}/appointments/{first_slot['appointmentid']}",
                data=data,
                practice_id=workflow.practice_id
            )

            # API returns a list with one appointment object
            if isinstance(appointment_result, list) and len(appointment_result) > 0:
                appointment = appointment_result[0]
            else:
                appointment = appointment_result

            result.appointment_id = appointment.get("appointmentid")
            result.add_step(f"✨ Booked appointment: {appointment.get('date')} at {appointment.get('starttime')}")
        else:
            result.add_error("No available appointment slots found")

        # Success summary
        print("\n" + "="*80)
        if appointment:
            print("✅ WORKFLOW COMPLETED")
            print("="*80)
            print(f"Patient: {patient.get('firstname')} {patient.get('lastname')}")
            print(f"Appointment: {appointment.get('date')} at {appointment.get('starttime')}")
        else:
            print("⚠️  WORKFLOW COMPLETED (No slots available)")
            print("="*80)
            print(f"Patient: {patient.get('firstname')} {patient.get('lastname')}")
            print(f"Appointment: No slots available in date range")

    except Exception as e:
        result.add_error(f"Workflow failed: {str(e)}")
        print("\n" + "="*80)
        print("❌ WORKFLOW FAILED")
        print("="*80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    return result


if __name__ == "__main__":
    # Demo execution
    result = execute_simplified_appointment_workflow(
        patient_lastname="Test",
        department_id="162",
        provider_id="121"
    )

    print("\n" + "="*80)
    print("WORKFLOW RESULT")
    print("="*80)
    import json
    print(json.dumps(result.to_dict(), indent=2))
