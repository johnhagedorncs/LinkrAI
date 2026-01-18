"""
Athena Health Referral Creation Workflow
Orchestrates the referral order creation process
"""

from athena_api import (
    AthenaWorkflow,
    WorkflowResult,
    DIAGNOSIS_MAPPINGS,
    SPECIALTY_MAPPINGS
)


def execute_complete_referral_workflow(
    patient_lastname: str,
    condition: str,
    specialty: str,
    department_id: str = "1",
    provider_note: str = ""
) -> WorkflowResult:
    """
    Execute referral creation workflow (Patient → Encounter → Diagnosis → Referral Order)
    Stops after referral creation (no insurance check or appointment booking)

    Args:
        patient_lastname: Patient's last name
        condition: Medical condition (e.g., "chest pain")
        specialty: Specialist needed (e.g., "cardiology")
        department_id: Department ID (default: 1)
        provider_note: Optional note from provider

    Returns:
        WorkflowResult with patient, encounter, diagnosis, and referral IDs
    """
    workflow = AthenaWorkflow()
    result = WorkflowResult()

    print("\n" + "="*80)
    print("ATHENA HEALTH REFERRAL CREATION WORKFLOW")
    print("="*80)

    try:
        # ================================================================
        # PHASE 1: PATIENT IDENTIFICATION
        # ================================================================
        print("\n📋 PHASE 1: Patient Identification")
        print("-" * 80)

        # Step 1: Find patient
        patient = workflow.find_patient(patient_lastname)
        result.patient_id = patient["patientid"]
        result.add_step(f"Found patient: {patient.get('firstname')} {patient.get('lastname')} (ID: {result.patient_id})")

        # ================================================================
        # PHASE 2: ENCOUNTER & DIAGNOSIS
        # ================================================================
        print("\n🏥 PHASE 2: Encounter & Diagnosis Management")
        print("-" * 80)

        # Step 2: Get active encounter
        encounter = workflow.get_encounter(result.patient_id, department_id)
        result.encounter_id = encounter["encounterid"]
        result.add_step(f"Found active encounter (ID: {result.encounter_id}, Status: {encounter.get('status')})")

        # Step 3: Map condition to diagnosis codes
        diagnosis_mapping = DIAGNOSIS_MAPPINGS.get(condition.lower())
        if not diagnosis_mapping:
            raise ValueError(f"No diagnosis mapping found for condition: {condition}")
        result.add_step(f"Mapped '{condition}' to SNOMED: {diagnosis_mapping['snomed']}, ICD-10: {diagnosis_mapping['icd10']}")

        # Step 4: Check if diagnosis already exists, add if not
        existing_diagnoses = workflow.get_encounter_diagnoses(result.encounter_id)
        existing_diagnosis = None

        for diag in existing_diagnoses:
            if str(diag.get("snomedcode")) == str(diagnosis_mapping["snomed"]):
                existing_diagnosis = diag
                break

        if existing_diagnosis:
            result.diagnosis_id = existing_diagnosis.get("diagnosisid")
            result.diagnosis_snomed = diagnosis_mapping["snomed"]
            result.add_step(f"Using existing diagnosis (Diagnosis ID: {result.diagnosis_id}, SNOMED: {result.diagnosis_snomed})")
        else:
            diagnosis_result = workflow.add_diagnosis(
                result.encounter_id,
                diagnosis_mapping["snomed"],
                diagnosis_mapping["icd10"],
                note=f"Patient reports {condition}"
            )
            result.diagnosis_id = diagnosis_result.get("diagnosisid")
            result.diagnosis_snomed = diagnosis_mapping["snomed"]
            result.add_step(f"Added new diagnosis to encounter (Diagnosis ID: {result.diagnosis_id})")

        # ================================================================
        # PHASE 3: REFERRAL ORDER CREATION
        # ================================================================
        print("\n📄 PHASE 3: Referral Order Creation")
        print("-" * 80)

        # Step 5: Get referral order types
        specialty_mapping = SPECIALTY_MAPPINGS.get(specialty.lower(), {"searchterm": specialty})
        order_types = workflow.get_referral_order_types(specialty_mapping["searchterm"])

        if not order_types:
            raise ValueError(f"No referral order types found for {specialty}")

        order_type = order_types[0]
        result.add_step(f"Found referral type: {order_type['name']} (ID: {order_type['ordertypeid']})")

        # Step 6: Create referral order
        referral = workflow.create_referral_order(
            result.encounter_id,
            str(order_type["ordertypeid"]),
            result.diagnosis_snomed,
            provider_note=provider_note or f"Patient needs {specialty} evaluation for {condition}",
            reason_for_referral=f"{condition.title()} evaluation"
        )
        result.referral_id = referral.get("documentid")
        result.add_step(f"✨ Created referral order (Order ID: {result.referral_id})")

        # Step 7: Verify referral was created
        referral_details = workflow.get_referral_details(result.encounter_id, result.referral_id)
        result.add_step(f"Verified referral status: {referral_details.get('status')}")

        # ================================================================
        # SUMMARY
        # ================================================================
        print("\n" + "="*80)
        print("✅ REFERRAL WORKFLOW COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"\nPatient: {patient.get('firstname')} {patient.get('lastname')} (ID: {result.patient_id})")
        print(f"Encounter ID: {result.encounter_id}")
        print(f"Diagnosis: {diagnosis_mapping['description']} (SNOMED: {result.diagnosis_snomed})")
        print(f"Referral Order ID: {result.referral_id}")
        print(f"Status: {referral_details.get('status')}")
        print(f"\nTotal Steps Completed: {len(result.steps_completed)}")

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
    result = execute_complete_referral_workflow(
        patient_lastname="Sandboxtest",
        condition="chest pain",
        specialty="cardiology",
        department_id="1",
        provider_note="Patient experiencing intermittent chest pain, needs cardiology evaluation"
    )

    print("\n" + "="*80)
    print("WORKFLOW RESULT")
    print("="*80)
    import json
    print(json.dumps(result.to_dict(), indent=2))
