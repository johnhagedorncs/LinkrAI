# A2A Pipeline Test Data Generator

## Overview

This utility generates complete test data for the A2A (Agent-to-Agent) pipeline workflow. It creates:
- Patient records (or reuses existing ones)
- Open encounters (without diagnosis attached)
- Random specialty → diagnosis → clinical note combinations
- Provider selection with available appointment slots
- Complete pipeline input payloads ready to feed into the agent workflow

## Files

### Main Scripts
- **`create_model_input.py`** - Main orchestrator script that generates complete test data
- **`create_patient.py`** - Patient creation utility
- **`create_appointment_slot.py`** - Appointment slot creation utility

### Data Files
- **`data/specialty_templates.json`** - Specialty → Diagnosis → Clinical Note mappings
- **`data/reusable_data.json`** - Storage for reusable patients, encounters, and department-provider pairs

### Discovery Scripts
- **`../discovery/find_appointment_slots.py`** - Modified to prioritize usual department and return date ranges

## Features

### Smart Workflow
1. **Random Specialty Selection** - Chooses from 9 medical specialties
2. **Diagnosis Mapping** - Each specialty has 5 predefined diagnoses with clinical notes
3. **Patient Management** - Creates new patients or reuses existing ones
4. **Open Encounter Creation** - Creates encounters WITHOUT diagnosis (agent adds it)
5. **Provider Discovery** - Finds providers by specialty, prioritizes usual department
6. **Slot Management** - Searches for existing slots or creates new ones
7. **Complete Output** - Generates JSON payload ready for agent pipeline

### Data Reusability
- Stores created patients in `reusable_data.json`
- Tracks encounters with metadata
- Caches department-provider pairs with slot availability
- Enables faster subsequent test data generation

## Usage

### Prerequisites
```bash
# Install Python dependencies
pip install python-dotenv requests

# Set up Athena API credentials in .env file
ATHENA_CLIENT_ID=your_client_id
ATHENA_CLIENT_SECRET=your_client_secret
ATHENA_BASE_URL=https://api.preview.platform.athenahealth.com
ATHENA_PRACTICE_ID=195900
```

### Basic Commands

```bash
# Generate completely random test data
python3 create_model_input.py --practice-id 195900 --random

# Specify a specialty (random diagnosis within specialty)
python3 create_model_input.py --practice-id 195900 --specialty cardiology

# Reuse existing patient from reusable_data.json
python3 create_model_input.py --practice-id 195900 --reuse-patient

# Force create new appointment slots even if slots exist
python3 create_model_input.py --practice-id 195900 --force-create-slots

# Dry run (show what would be created without creating)
python3 create_model_input.py --practice-id 195900 --dry-run --random

# Save output to file
python3 create_model_input.py --practice-id 195900 --random --output test_data.json
```

## Output Format

The script generates a complete pipeline input payload:

```json
{
  "pipeline_input": {
    "patient_id": "60183",
    "encounter_id": "12345",
    "specialty": "cardiology",
    "diagnosis": "chest pain",
    "clinical_note": "Patient reports intermittent chest discomfort on exertion. EKG shows non-specific changes."
  },
  "appointment_context": {
    "provider_id": "71",
    "provider_name": "Dr. Smith",
    "department_id": "162",
    "department_name": "Cardiology Clinic",
    "slots_available": true,
    "slot_date_range": {
      "earliest": "11/18/2025",
      "latest": "11/22/2025"
    },
    "created_new_slots": false
  },
  "metadata": {
    "created_at": "2025-11-17T10:45:00Z",
    "practice_id": "195900",
    "encounter_status": "open",
    "note": "Encounter created without diagnosis - agent will add diagnosis from pipeline_input"
  }
}
```

## Workflow Integration

### Agent Pipeline Flow
1. **Input** - Use the `pipeline_input` section to feed into Referral Agent
2. **Referral Agent** - Reads diagnosis and adds it to the open encounter
3. **Referral Agent** - Creates referral order for the specialty
4. **Scheduling Agent** - Uses `appointment_context` to find/book appointments
5. **Messaging Agent** - Sends appointment confirmation to patient

### Key Design Decisions
- **Open Encounters** - Created without diagnosis so agent can add it (tests full workflow)
- **Date Ranges** - Slots stored as date ranges (earliest/latest) not individual slots
- **Usual Department Priority** - Provider's usual department searched first
- **Reusable Data** - Patients and dept-provider pairs cached for efficiency

## Available Specialties

1. **Cardiology** (ID: 006) - chest pain, hypertension, arrhythmia, heart murmur, shortness of breath
2. **Dermatology** (ID: 012) - suspicious mole, severe acne, psoriasis, chronic rash, skin lesion
3. **Orthopedics** (ID: 010) - knee pain, lower back pain, shoulder impingement, hip pain, ankle sprain
4. **Primary Care** (ID: 001) - annual physical, diabetes management, fatigue, weight management, medication refill
5. **Internal Medicine** (ID: 002) - abdominal pain, anemia, thyroid disorder, joint pain, chronic cough
6. **Psychiatry** (ID: 015) - depression, anxiety, insomnia, ADHD, bipolar disorder
7. **Neurology** (ID: 016) - headaches, tremor, numbness, dizziness, seizure
8. **Oncology** (ID: 020) - abnormal mammogram, lymphadenopathy, abnormal blood counts, weight loss, prostate cancer
9. **Pediatrics** (ID: 003) - developmental delay, asthma, failure to thrive, ADHD evaluation, recurrent infections

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'dotenv'**
   ```bash
   pip install python-dotenv requests
   ```

2. **No providers found for specialty**
   - Check that practice has providers with that specialty
   - Verify specialty_id mapping in specialty_templates.json

3. **No appointment slots available**
   - Use `--force-create-slots` to create new slots
   - Check date range (default: next 30 days)

4. **Import errors**
   - Ensure you're running from the project root directory
   - Check that athena_api.py is in the Athena/ directory

## Development

### Adding New Specialties
Edit `data/specialty_templates.json`:
```json
"new_specialty": {
  "specialty_id": "XXX",
  "diagnoses": {
    "diagnosis_name": "Clinical note describing the condition and referral reason."
  }
}
```

### Modifying Slot Creation
Edit the `create_appointment_slots()` function in `create_model_input.py`:
- Change `num_days` for more days
- Modify `slot_times` array for different time slots
- Adjust `duration` and `appointmenttypeid` as needed

## Testing

```bash
# Test with dry run first
python3 create_model_input.py --dry-run --random

# Test specific specialty
python3 create_model_input.py --specialty cardiology --dry-run

# Create real test data
python3 create_model_input.py --practice-id 195900 --random
```

## Notes

- **Encounter Status**: Encounters are created as "open" without diagnosis
- **Agent Responsibility**: Referral agent adds diagnosis from pipeline_input
- **Slot Search**: Prioritizes provider's usual department, then searches all departments
- **Data Persistence**: All created data stored in reusable_data.json for future runs
- **Randomization**: Uses Python's random module with predefined templates for consistency
