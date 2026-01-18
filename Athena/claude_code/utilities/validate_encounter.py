#!/usr/bin/env python3
"""
Validate Encounter - General Purpose Tool

Purpose: Validate encounter data (diagnoses, referrals) and test adding new diagnoses
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from athena_api import AthenaWorkflow, DIAGNOSIS_MAPPINGS
import argparse


def check_diagnoses(workflow, encounter_id):
    """Check all diagnoses on an encounter"""
    print(f"\n{'='*80}")
    print("DIAGNOSES ON ENCOUNTER")
    print(f"{'='*80}\n")

    diagnoses = workflow.get_encounter_diagnoses(encounter_id)
    print(f"Total diagnoses: {len(diagnoses)}\n")

    existing_snomed = set()
    for diag in diagnoses:
        snomed = str(diag.get("snomedcode"))
        icd10 = diag.get("icd10code", "N/A")
        description = diag.get("description", "N/A")
        diag_id = diag.get("diagnosisid")
        existing_snomed.add(snomed)

        print(f"Diagnosis ID: {diag_id}")
        print(f"  SNOMED: {snomed} | ICD-10: {icd10}")
        print(f"  Description: {description}\n")

    # Check against known diagnosis mappings
    if DIAGNOSIS_MAPPINGS:
        print(f"{'='*80}")
        print("CHECKING AGAINST DIAGNOSIS_MAPPINGS")
        print(f"{'='*80}\n")

        new_diagnoses = []
        existing_diagnoses_list = []

        for condition, mapping in DIAGNOSIS_MAPPINGS.items():
            snomed = mapping["snomed"]
            status = "EXISTS" if snomed in existing_snomed else "NEW"

            print(f"{condition.upper()}: {status}")
            print(f"  SNOMED: {snomed} | ICD-10: {mapping['icd10']}")
            print(f"  {mapping['description']}\n")

            if snomed in existing_snomed:
                existing_diagnoses_list.append(condition)
            else:
                new_diagnoses.append(condition)

        if new_diagnoses:
            print(f"\n✅ {len(new_diagnoses)} new diagnoses available to add:")
            for cond in new_diagnoses:
                print(f"  - {cond}")

    return diagnoses


def check_referrals(workflow, encounter_id, referral_ids=None):
    """Check all or specific referrals on an encounter"""
    print(f"\n{'='*80}")
    print("REFERRALS ON ENCOUNTER")
    print(f"{'='*80}\n")

    if referral_ids:
        print(f"Checking specific referral IDs: {', '.join(referral_ids)}\n")
        referrals = []

        for ref_id in referral_ids:
            try:
                details = workflow.get_referral_details(encounter_id, ref_id)
                referrals.append(details)
                print(f"✓ Referral {ref_id}:")
                print(f"  Order Type: {details.get('ordertype')} (ID: {details.get('ordertypeid')})")
                print(f"  Status: {details.get('status')}")
                print(f"  Created: {details.get('createddate', 'N/A')}\n")
            except Exception as e:
                print(f"✗ Referral {ref_id}: {e}\n")

    else:
        print("Note: API doesn't provide list of all referrals endpoint")
        print("Use --referral-ids to check specific referral IDs\n")
        referrals = []

    return referrals


def test_add_diagnosis(workflow, encounter_id, snomed_code, icd10_code, note="Test diagnosis"):
    """Test adding a diagnosis to an encounter"""
    print(f"\n{'='*80}")
    print("TESTING: Add Diagnosis")
    print(f"{'='*80}\n")

    print(f"Encounter: {encounter_id}")
    print(f"SNOMED: {snomed_code}")
    print(f"ICD-10: {icd10_code}")
    print(f"Note: {note}\n")

    try:
        result = workflow.add_diagnosis(encounter_id, snomed_code, icd10_code, note)
        print(f"✅ SUCCESS!")
        print(f"  Diagnosis ID: {result.get('diagnosisid')}")
        print(f"  Description: {result.get('description')}")
        print(f"  SNOMED: {result.get('snomedcode')}")
        return result
    except Exception as e:
        print(f"❌ FAILED: {e}")
        if "already present" in str(e).lower():
            print("\nNote: This diagnosis already exists on the encounter")
        return None


def test_complete_pipeline(workflow, encounter_id, patient_id=None,
                          order_type_id="257362", snomed_code="29857009"):
    """
    Test the complete referral pipeline on an encounter.
    This proves end-to-end workflow: encounter → diagnosis → referral

    Default: Cardiologist referral (257362) for chest pain (29857009)
    """
    print(f"\n{'='*80}")
    print("COMPLETE REFERRAL PIPELINE TEST")
    print(f"{'='*80}\n")

    print(f"Encounter: {encounter_id}")
    if patient_id:
        print(f"Patient: {patient_id}")
    print(f"Order Type: {order_type_id}")
    print(f"Diagnosis SNOMED: {snomed_code}")

    # Step 1: Verify diagnoses on encounter
    print("\n[STEP 1] Verifying existing diagnoses...")
    diagnoses = workflow.get_encounter_diagnoses(encounter_id)
    print(f"  Diagnoses on encounter: {len(diagnoses)}")

    diagnosis_exists = False
    for diag in diagnoses:
        diag_snomed = str(diag.get('snomedcode'))
        print(f"    - Diagnosis {diag.get('diagnosisid')}: {diag.get('description')} (SNOMED: {diag_snomed})")
        if diag_snomed == str(snomed_code):
            diagnosis_exists = True

    if not diagnosis_exists:
        print(f"\n⚠️  Warning: Diagnosis {snomed_code} not found on encounter")
        print("  Referral may still work if diagnosis gets added automatically")

    # Step 2: Create referral order
    print("\n[STEP 2] Creating referral order...")
    try:
        referral_result = workflow.create_referral_order(
            encounter_id,
            order_type_id,
            snomed_code,
            provider_note="Testing complete referral pipeline",
            reason_for_referral="Pipeline test - encounter validation"
        )

        referral_id = referral_result.get("documentid")
        print(f"  ✅ Referral created: {referral_id}")

        # Step 3: Verify referral
        print("\n[STEP 3] Verifying referral...")
        details = workflow.get_referral_details(encounter_id, referral_id)
        print(f"  Referral ID: {referral_id}")
        print(f"  Status: {details.get('status')}")
        print(f"  Order Type: {details.get('ordertype')}")
        print(f"  Order Type ID: {details.get('ordertypeid')}")

        print(f"\n{'='*80}")
        print("✅ COMPLETE PIPELINE SUCCESS!")
        print(f"{'='*80}\n")
        print("Workflow Summary:")
        print(f"  1. Encounter {encounter_id} validated")
        print(f"  2. Diagnoses checked ({len(diagnoses)} found)")
        print(f"  3. Referral created → Referral {referral_id}")
        print("\n✅ End-to-end referral workflow verified!")

        return referral_id

    except Exception as e:
        print(f"  ❌ Referral creation failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n{'='*80}")
        print("❌ PIPELINE FAILED")
        print(f"{'='*80}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Validate encounter data and test diagnosis operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all diagnoses and referrals
  %(prog)s --practice-id 195900 --encounter-id 61456

  # Check only diagnoses
  %(prog)s --practice-id 195900 --encounter-id 61456 --check diagnoses

  # Check specific referrals
  %(prog)s --practice-id 195900 --encounter-id 61456 --check referrals --referral-ids 203645,203732

  # Test adding a diagnosis
  %(prog)s --practice-id 195900 --encounter-id 62020 --add-diagnosis --diagnosis-snomed 29857009 --diagnosis-icd10 R07.9

  # Test complete referral pipeline (THE MOST IMPORTANT TEST)
  %(prog)s --practice-id 195900 --encounter-id 62020 --patient-id 7681 --test-pipeline

  # Test pipeline with custom order type
  %(prog)s --practice-id 195900 --encounter-id 62020 --test-pipeline --order-type-id 257362 --pipeline-snomed 29857009
        """
    )

    parser.add_argument('--practice-id', required=True, help='Practice ID')
    parser.add_argument('--encounter-id', required=True, help='Encounter ID')
    parser.add_argument('--patient-id', help='Patient ID (for pipeline test)')
    parser.add_argument('--check', choices=['diagnoses', 'referrals', 'all'], default='all',
                       help='What to check (default: all)')
    parser.add_argument('--referral-ids', help='Comma-separated referral IDs to check')
    parser.add_argument('--add-diagnosis', action='store_true', help='Test adding a diagnosis')
    parser.add_argument('--diagnosis-snomed', help='SNOMED code for test diagnosis')
    parser.add_argument('--diagnosis-icd10', help='ICD-10 code for test diagnosis')
    parser.add_argument('--diagnosis-note', default='Test diagnosis', help='Note for test diagnosis')
    parser.add_argument('--test-pipeline', action='store_true',
                       help='Test complete referral pipeline (encounter → diagnosis → referral)')
    parser.add_argument('--order-type-id', default='257362',
                       help='Order type ID for pipeline test (default: 257362 - cardiologist)')
    parser.add_argument('--pipeline-snomed', default='29857009',
                       help='SNOMED code for pipeline test (default: 29857009 - chest pain)')

    args = parser.parse_args()

    print("="*80)
    print("ENCOUNTER VALIDATION")
    print("="*80)
    print(f"\nPractice ID: {args.practice_id}")
    print(f"Encounter ID: {args.encounter_id}")

    workflow = AthenaWorkflow(practice_id=args.practice_id)

    # Check diagnoses
    if args.check in ['diagnoses', 'all']:
        check_diagnoses(workflow, args.encounter_id)

    # Check referrals
    if args.check in ['referrals', 'all']:
        referral_ids = args.referral_ids.split(',') if args.referral_ids else None
        check_referrals(workflow, args.encounter_id, referral_ids)

    # Test adding diagnosis
    if args.add_diagnosis:
        if not args.diagnosis_snomed or not args.diagnosis_icd10:
            print("\n❌ Error: --diagnosis-snomed and --diagnosis-icd10 required for --add-diagnosis")
        else:
            test_add_diagnosis(
                workflow,
                args.encounter_id,
                args.diagnosis_snomed,
                args.diagnosis_icd10,
                args.diagnosis_note
            )

    # Test complete pipeline
    if args.test_pipeline:
        test_complete_pipeline(
            workflow,
            args.encounter_id,
            args.patient_id,
            args.order_type_id,
            args.pipeline_snomed
        )

    print("\n" + "="*80)


if __name__ == "__main__":
    main()