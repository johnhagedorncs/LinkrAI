# Specialty Provider Availability by Practice

This document tracks which specialties have available providers in each practice.

## Practice 195900

| Specialty | Specialty ID | Provider Count | Status |
|-----------|--------------|----------------|--------|
| Cardiology | 006 | 7 | ✅ Available |
| Oncology | 020 | 1 | ✅ Available |
| Pediatrics | 003 | 2 | ✅ Available |
| Dermatology | 012 | 0 | ❌ Not Available |
| Orthopedics | 010 | 0 | ❌ Not Available |
| Primary Care | 001 | 0 | ❌ Not Available |
| Internal Medicine | 002 | 0 | ❌ Not Available |
| Psychiatry | 015 | 0 | ❌ Not Available |
| Neurology | 016 | 0 | ❌ Not Available |

**Supported Specialties:** `cardiology`, `oncology`, `pediatrics`

## Practice 1959222

| Specialty | Specialty ID | Provider Count | Status |
|-----------|--------------|----------------|--------|
| Cardiology | 006 | 2 | ✅ Available |
| Dermatology | 012 | 1 | ✅ Available |
| Primary Care | 001 | 3 | ✅ Available |
| Internal Medicine | 002 | 1 | ✅ Available |
| Pediatrics | 003 | 4 | ✅ Available |
| Orthopedics | 010 | 0 | ❌ Not Available |
| Psychiatry | 015 | 0 | ❌ Not Available |
| Neurology | 016 | 0 | ❌ Not Available |
| Oncology | 020 | 0 | ❌ Not Available |

**Supported Specialties:** `cardiology`, `dermatology`, `primary care`, `internal medicine`, `pediatrics`

## Both Practices (Universal)

These specialties work across both practices:

- ✅ **Cardiology** - 7 providers in 195900, 2 in 1959222
- ✅ **Pediatrics** - 2 providers in 195900, 4 in 1959222

## Usage in create_model_input.py

The script automatically filters specialties based on practice ID:

```bash
# Practice 195900 - will randomly select from: cardiology, oncology, pediatrics
python3 create_model_input.py --practice-id 195900 --random

# Practice 1959222 - will randomly select from: cardiology, dermatology, primary care, internal medicine, pediatrics
python3 create_model_input.py --practice-id 1959222 --random

# Force specific specialty (validates practice has providers)
python3 create_model_input.py --practice-id 195900 --specialty cardiology

# This will fail with helpful error message:
python3 create_model_input.py --practice-id 195900 --specialty dermatology
# Error: Specialty 'dermatology' has no providers in practice 195900
# Available practices for dermatology: 1959222
```

## Template Structure

The `specialty_templates.json` file includes a `practices` array for each specialty:

```json
{
  "cardiology": {
    "specialty_id": "006",
    "practices": ["195900", "1959222"],  // Available in both
    "diagnoses": { ... }
  },
  "dermatology": {
    "specialty_id": "012",
    "practices": ["1959222"],  // Only in 1959222
    "diagnoses": { ... }
  }
}
```

## Updating This List

To check current provider availability:

```bash
python3 -c "
import sys, os
sys.path.insert(0, os.path.abspath('../../..'))
from athena_api import legacy_get

practice_id = '195900'  # or '1959222'
result = legacy_get('/v1/{practiceid}/providers', params={}, practice_id=practice_id)
providers = result.get('providers', [])

specialty_counts = {}
for p in providers:
    spec_id = p.get('specialtyid', 'unknown')
    specialty_counts[spec_id] = specialty_counts.get(spec_id, 0) + 1

for spec_id, count in sorted(specialty_counts.items()):
    print(f'Specialty {spec_id}: {count} providers')
"
```

## Last Updated

2025-11-17

**Note:** Provider availability may change over time. Run the verification script above to get current data.
