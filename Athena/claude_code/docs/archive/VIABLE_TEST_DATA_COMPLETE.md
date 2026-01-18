================================================================================
ATHENA HEALTH - COMPLETE VIABLE TEST DATA
================================================================================
Generated: November 5, 2025
Purpose: Agent workflow testing (Referral + Scheduling)

This file consolidates all viable test data across both practices:
- Practice 195900: Referral patients + Scheduling providers (FULL PIPELINE)
- Practice 1959222: Scheduling providers only

================================================================================


################################################################################
# PRACTICE 195900 (Sandbox) - FULL PIPELINE TESTING
################################################################################

This practice supports BOTH referral creation AND appointment scheduling.
Use this practice to test the complete end-to-end workflow.

================================================================================
SECTION 1: REFERRAL PATIENTS (Practice 195900)
================================================================================

These patients have OPEN ENCOUNTERS and can be used for referral creation.

Patient ID: 60183
  Name: Gary Sandboxtest
  Encounter ID: 61456
  Department: 1
  Encounter Date: 07/22/2025

Patient ID: 60184
  Name: Dorrie Sandboxtest
  Encounter ID: 61457
  Department: 1
  Encounter Date: 07/22/2025

Patient ID: 60181
  Name: Anna Sandbox-Test
  Encounter ID: 61984
  Department: 1
  Encounter Date: 10/14/2025

Patient ID: 60182
  Name: Rebecca Sandbox-Test
  Encounter ID: 61455
  Department: 1
  Encounter Date: 07/22/2025

Patient ID: 7923
  Name: Tra Test
  Encounter ID: 59477
  Department: 1
  Encounter Date: 02/06/2024

Quick Reference:
  Patient IDs: 60183, 60184, 60181, 60182, 7923
  Search Names: "Sandboxtest", "Sandbox-Test", "Test"

================================================================================
SECTION 2: SCHEDULING PROVIDERS (Practice 195900)
================================================================================

These providers have OPEN APPOINTMENT SLOTS. Can be combined with referral
patients above for full pipeline testing.

Provider 1911 (Bryan Adamczyk):
  Department: 1
  Available Slots: 47
  First Slot: 11/07/2025 at 09:00
  Appointment Type: Sick Visit
  appointmenttypeid: 622
  reasonid: ["-1"]
  Booking: provider_id="1911", department_id="1", appointmenttypeid="622"

Provider 71 (Adam Bricker):
  Department: 1
  Available Slots: 194
  First Slot: 11/07/2025 at 08:15
  Appointment Type: Sick Visit
  appointmenttypeid: 622
  reasonid: ["-1"]
  Booking: provider_id="71", department_id="1", appointmenttypeid="622"

Provider 1 (Camille Cartwright):
  Department: 1
  Available Slots: 1
  First Slot: 12/01/2025 at 16:17
  Appointment Type: Cardiology
  appointmenttypeid: 182
  reasonid: ["-1"]
  Booking: provider_id="1", department_id="1", appointmenttypeid="182"

Provider 325 (Maurice Johnson):
  Department: 21
  Available Slots: 108
  First Slot: 11/07/2025 at 09:00
  Appointment Type: 15 minute slot
  appointmenttypeid: 926
  reasonid: ["-1"]
  Booking: provider_id="325", department_id="21", appointmenttypeid="926"

Provider 2276 (Nikhil Jain):
  Department: 1
  Available Slots: 52
  First Slot: 11/07/2025 at 09:00
  Appointment Type: PHYSICAL EXAM
  appointmenttypeid: 4
  reasonid: ["-1"]
  Booking: provider_id="2276", department_id="1", appointmenttypeid="4"

Provider 27 (Elsa Spinka):
  Department: 150
  Available Slots: 563
  First Slot: 11/07/2025 at 08:00
  Appointment Type: Any 15
  appointmenttypeid: 82
  reasonid: ["-1"]
  Booking: provider_id="27", department_id="150", appointmenttypeid="82"

Provider 2116 (Brian Test):
  Department: 21
  Available Slots: 108
  First Slot: 11/07/2025 at 09:00
  Appointment Type: 15 minute slot
  appointmenttypeid: 926
  reasonid: ["-1"]
  Booking: provider_id="2116", department_id="21", appointmenttypeid="926"

Provider 166 (Rowland Wehner):
  Department 1:
  Available Slots: 4
  First Slot: 12/12/2025 at 11:00
  appointmenttype: "NewPatientVisit"
  appointmenttypeid: 1708
  reasonid: ["-1"]
  Booking: provider_id="166", department_id="1", appointmenttypeid="1708"



Quick Reference (Practice 195900):
  Provider:Department pairs: 1911:1, 71:1, 1:1, 325:21, 2276:1, 27:150, 2116:21, 166:1

================================================================================
FULL PIPELINE EXAMPLE (Practice 195900)
================================================================================

Step 1 - Create Referral:
  execute_complete_referral_workflow(
      patient_lastname="Sandboxtest",  # Use patient 60183, 60184, 60181, or 60182
      condition="chest pain",
      specialty="cardiology",
      department_id="1",
      provider_note="Urgent evaluation needed"
  )

Step 2 - Book Appointment (Same Patient):
  execute_simplified_appointment_workflow(
      patient_lastname="Sandboxtest",  # Same patient from Step 1
      department_id="1",               # Use provider 71 (194 slots)
      provider_id="71"
  )

Expected Result:
  - Referral created with ID (e.g., 203645)
  - Diagnosis added to encounter
  - Appointment booked using appointmenttypeid=622
  - Full pipeline complete in same practice!


################################################################################
# PRACTICE 1959222 - SCHEDULING ONLY
################################################################################

This practice is used for scheduling appointments only (no referral patients).

================================================================================
SECTION 3: SCHEDULING PROVIDERS (Practice 1959222)
================================================================================

Provider 121 (Provider 121):
  Department: 162
  Available Slots: 1000
  First Slot: 11/07/2025 at 08:00
  Appointment Type: Any 30
  appointmenttypeid: 522
  reasonid: ["-1"]
  Booking: provider_id="121", department_id="162", appointmenttypeid="522"
  ⭐ MOST SLOTS OVERALL (1000 slots!)

Quick Reference (Practice 1959222):
  Provider:Department pairs: 121:162
  Patient for testing: 5775 (Cassie Test)

================================================================================
SCHEDULING EXAMPLE (Practice 1959222)
================================================================================

execute_simplified_appointment_workflow(
    patient_lastname="Test",         # Patient 5775 (Cassie Test)
    department_id="162",
    provider_id="121"
)


################################################################################
# BOOKING API REFERENCE
################################################################################

To book an appointment, you need 3 pieces of information:

1. appointmentid - From the slot object (used in URL path)
2. appointmenttypeid - From the slot object (sent in request body)
3. patientid - The patient you're booking for

API Call:
  PUT /v1/{practiceid}/appointments/{appointmentid}
  Body: {
      "patientid": "60183",
      "appointmenttypeid": "622",
      "ignoreschedulablepermission": "true"
  }

Note: reasonid is NOT used for booking - it's only used to filter slots
during search. All slots above have reasonid=["-1"] meaning they accept
any visit reason.


################################################################################
# DATA FRESHNESS
################################################################################

Slot Counts: As of 11/06/2025
Encounter Dates: Range from 02/06/2024 to 10/14/2025
Search Window: 1-90 days from current date


################################################################################
# END OF DOCUMENT
################################################################################
