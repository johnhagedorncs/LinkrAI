#!/usr/bin/env python3
"""
Fetch ALL specialties from Athena and build comprehensive mapping
"""

from scheduling_mcp import AthenaWorkflow
import json
from collections import defaultdict


def get_all_specialties():
    """Get all unique specialties from Athena providers"""
    print("=" * 80)
    print("FETCHING ALL SPECIALTIES FROM ATHENA")
    print("=" * 80)

    workflow = AthenaWorkflow(practice_id="195900")

    # Get all providers
    print("\n📋 Fetching all providers...")
    all_providers = workflow.get_providers()
    print(f"✅ Found {len(all_providers)} providers")

    # Extract unique specialties
    specialty_map = defaultdict(list)

    for provider in all_providers:
        specialty_id = provider.get("specialtyid")
        specialty_name = provider.get("specialty")
        provider_name = f"{provider.get('firstname', '')} {provider.get('lastname', '')}".strip()

        if specialty_id and specialty_name:
            # Convert to string for consistent sorting
            specialty_id_str = str(specialty_id).zfill(3)  # Pad to 3 digits: "6" -> "006"
            specialty_map[specialty_id_str].append({
                "name": specialty_name,
                "provider_example": provider_name
            })

    # Deduplicate and format
    print("\n" + "=" * 80)
    print("ALL UNIQUE SPECIALTIES IN YOUR PRACTICE")
    print("=" * 80)

    unique_specialties = {}
    for specialty_id, entries in sorted(specialty_map.items()):
        # Get the most common name for this ID
        specialty_name = entries[0]["name"]
        provider_example = entries[0]["provider_example"]
        unique_specialties[specialty_id] = {
            "name": specialty_name,
            "count": len(entries),
            "example_provider": provider_example
        }

        print(f"\nID: {specialty_id:4s} | {specialty_name}")
        print(f"  Providers: {len(entries)}")
        print(f"  Example: {provider_example}")

    # Generate Python mapping code
    print("\n" + "=" * 80)
    print("PYTHON CODE FOR SPECIALTY_TO_ID MAPPING")
    print("=" * 80)
    print("\nSPECIALTY_TO_ID = {")

    for specialty_id, info in sorted(unique_specialties.items(), key=lambda x: x[1]["name"].lower()):
        specialty_name_lower = info["name"].lower()
        print(f'    "{specialty_name_lower}": "{specialty_id}",')

    print("}")

    # Generate reverse mapping (ID to Name)
    print("\n" + "=" * 80)
    print("REVERSE MAPPING: SPECIALTY_ID_TO_NAME")
    print("=" * 80)
    print("\nSPECIALTY_ID_TO_NAME = {")

    for specialty_id, info in sorted(unique_specialties.items()):
        print(f'    "{specialty_id}": "{info["name"]}",')

    print("}")

    # Save to JSON
    output_file = "athena_specialties.json"
    with open(output_file, "w") as f:
        json.dump({
            "total_providers": len(all_providers),
            "total_specialties": len(unique_specialties),
            "specialties": unique_specialties,
            "specialty_to_id": {info["name"].lower(): specialty_id for specialty_id, info in unique_specialties.items()}
        }, f, indent=2)

    print(f"\n✅ Saved detailed mapping to: {output_file}")
    print(f"\n📊 Summary: {len(unique_specialties)} unique specialties found")


if __name__ == "__main__":
    get_all_specialties()
