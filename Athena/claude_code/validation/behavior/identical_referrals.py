"""
Test creating two IDENTICAL referrals with exact same parameters
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))  # Add root to path
from athena_api import AthenaWorkflow

workflow = AthenaWorkflow(practice_id="195900")

encounter_id = "61456"
order_type_id = "257362"  # cardiologist referral
diagnosis_snomed = "29857009"  # chest pain
provider_note = "EXACT DUPLICATE TEST - Patient needs cardiology evaluation"
reason = "Chest pain evaluation - duplicate test"

print("="*80)
print("TESTING IDENTICAL REFERRAL CREATION")
print("="*80)
print(f"\nEncounter: {encounter_id}")
print(f"Order Type: {order_type_id} (cardiologist referral)")
print(f"Diagnosis SNOMED: {diagnosis_snomed} (chest pain)")
print(f"Provider Note: {provider_note}")

print("\n" + "="*80)
print("CREATING REFERRAL #1")
print("="*80)

try:
    referral1 = workflow.create_referral_order(
        encounter_id,
        order_type_id,
        diagnosis_snomed,
        provider_note=provider_note,
        reason_for_referral=reason
    )
    ref_id_1 = referral1.get("documentid")
    print(f"✓ Referral #1 created: {ref_id_1}")
except Exception as e:
    print(f"✗ Failed to create referral #1: {e}")
    ref_id_1 = None

print("\n" + "="*80)
print("CREATING REFERRAL #2 (IDENTICAL PARAMETERS)")
print("="*80)

try:
    referral2 = workflow.create_referral_order(
        encounter_id,
        order_type_id,
        diagnosis_snomed,
        provider_note=provider_note,
        reason_for_referral=reason
    )
    ref_id_2 = referral2.get("documentid")
    print(f"✓ Referral #2 created: {ref_id_2}")
except Exception as e:
    print(f"✗ Failed to create referral #2: {e}")
    ref_id_2 = None

print("\n" + "="*80)
print("RESULTS")
print("="*80)

if ref_id_1 and ref_id_2:
    if ref_id_1 == ref_id_2:
        print("\n❌ MERGED - Both calls returned the same document ID")
        print(f"   Document ID: {ref_id_1}")
        print("   API reused existing referral instead of creating duplicate")
    else:
        print("\n✅ STACKED - Two different document IDs created")
        print(f"   Referral #1: {ref_id_1}")
        print(f"   Referral #2: {ref_id_2}")
        print("   API allows truly identical referrals to coexist")

        # Verify both exist
        print("\n" + "-"*80)
        print("VERIFYING BOTH REFERRALS EXIST")
        print("-"*80)

        for ref_id in [ref_id_1, ref_id_2]:
            try:
                details = workflow.get_referral_details(encounter_id, ref_id)
                print(f"\nReferral {ref_id}:")
                print(f"  Order Type ID: {details.get('ordertypeid')}")
                print(f"  Status: {details.get('status')}")
                print(f"  Order Type: {details.get('ordertype')}")
            except Exception as e:
                print(f"\nReferral {ref_id}: ERROR - {e}")
elif ref_id_1:
    print("\n⚠️  Only first referral created")
elif ref_id_2:
    print("\n⚠️  Only second referral created")
else:
    print("\n❌ Both referrals failed")