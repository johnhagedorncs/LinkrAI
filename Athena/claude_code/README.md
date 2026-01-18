# Athena Health API Test Tools

**Last Updated:** November 7, 2025
**Total Scripts:** 7 (3 general-purpose utilities + 4 validation tests)

---

## Directory Structure

```
claude_code/
├── utilities/
│   ├── discovery/
│   │   ├── find_appointment_slots.py
│   │   └── find_patients.py
│   └── validate_encounter.py
│
└── validation/
    ├── behavior/
    │   ├── identical_diagnosis.py
    │   └── identical_referrals.py
    └── encounter_creation/
        ├── order_driven_encounter.py
        └── visit_driven_encounter.py
```

---

## 🟢 General-Purpose Utilities

### `utilities/discovery/find_appointment_slots.py`

**Purpose:** Find available appointment slots across any practice/department/provider combination

**Inputs:**
- `--practice-id` (required) - Practice ID to search
- `--department-ids` (optional) - Comma-separated department IDs
- `--provider-ids` (optional) - Comma-separated provider IDs
- `--start-date` (optional) - Start date (mm/dd/yyyy), default: today
- `--end-date` (optional) - End date (mm/dd/yyyy), default: +7 days
- `--exhaustive` (flag) - Search all provider x department combinations
- `--output-format` (optional) - Output format: txt/json/both (default: txt)
- `--verify-test-cases` (optional) - Path to JSON file with test cases to verify

**Outputs:**
- Console: List of available slots with provider, department, date, time
- Optional file: JSON or TXT format with slot details
- Returns: Slot count and availability summary

**Functionality:**
- Searches for open appointment slots using Athena API
- Supports targeted search (specific providers/departments) or exhaustive search
- Cross-references multiple providers and departments
- Validates test case inputs against available slots
- Exports results for later use

**Example:**
```bash
python3 utilities/discovery/find_appointment_slots.py \
  --practice-id 195900 --provider-ids 71 --department-ids 1
```

---

### `utilities/discovery/find_patients.py`

**Purpose:** Find patients by encounter status (with/without open encounters)

**Inputs:**
- `--practice-id` (required) - Practice ID to search
- `--encounter-status` (optional) - Filter: open/no-open/any (default: any)
- `--lastname-patterns` (optional) - Comma-separated lastname patterns (default: Test,Sandbox,Demo,Sample)
- `--limit` (optional) - Max patients to check (default: 20)
- `--department-id` (optional) - Department ID (default: 1)
- `--output` (optional) - Save results to file path

**Outputs:**
- Console: List of patients with IDs, names, DOB, encounter status
- Optional file: Patient details saved to specified path
- Returns: Patient count by encounter status

**Functionality:**
- Searches patient database by lastname patterns
- Filters patients by encounter status (open/none/any)
- Useful for finding test patients in specific states
- Supports both discovery use cases:
  - Finding patients WITH encounters (referral-ready)
  - Finding patients WITHOUT encounters (clean state for testing)

**Example:**
```bash
python3 utilities/discovery/find_patients.py \
  --practice-id 195900 --encounter-status no-open --limit 10
```

---

### `utilities/validate_encounter.py`

**Purpose:** Validate encounter data (diagnoses, referrals) and test operations

**Inputs:**
- `--practice-id` (required) - Practice ID
- `--encounter-id` (required) - Encounter ID to validate
- `--patient-id` (optional) - Patient ID (for pipeline test)
- `--check` (optional) - What to check: diagnoses/referrals/all (default: all)
- `--referral-ids` (optional) - Comma-separated referral IDs to check
- `--add-diagnosis` (flag) - Test adding a diagnosis
- `--diagnosis-snomed` (optional) - SNOMED code for test diagnosis
- `--diagnosis-icd10` (optional) - ICD-10 code for test diagnosis
- `--diagnosis-note` (optional) - Note for test diagnosis (default: "Test diagnosis")
- `--test-pipeline` (flag) - Test complete referral pipeline
- `--order-type-id` (optional) - Order type ID for pipeline (default: 257362)
- `--pipeline-snomed` (optional) - SNOMED for pipeline (default: 29857009)

**Outputs:**
- Console: Detailed encounter validation report
- Diagnosis list with SNOMED/ICD-10 codes
- Referral details and status
- Test results (diagnosis addition, pipeline execution)
- Success/failure status for each operation

**Functionality:**
- **Check diagnoses:** Lists all diagnoses on encounter with codes
- **Check referrals:** Validates specific referral IDs
- **Add diagnosis:** Tests adding new diagnosis to encounter
- **Pipeline test:** Complete end-to-end workflow (encounter → diagnosis → referral)
- Cross-references against DIAGNOSIS_MAPPINGS
- Identifies which diagnoses are new vs. existing
- Verifies encounter is functional for orders

**Example:**
```bash
# Validate encounter
python3 utilities/validate_encounter.py \
  --practice-id 195900 --encounter-id 61456

# Test complete pipeline (MOST IMPORTANT)
python3 utilities/validate_encounter.py \
  --practice-id 195900 --encounter-id 62020 --patient-id 7681 --test-pipeline
```

---

## 🔴 Validation Tests (Proof Scripts)

### `validation/behavior/identical_diagnosis.py`

**Purpose:** Test if API prevents duplicate diagnoses on same encounter

**Inputs:** None (hardcoded: Encounter 62020, Patient 7681, SNOMED 29857009)

**Outputs:**
- Console: Step-by-step test execution
- API behavior report (allows duplicates vs. prevents)
- Final count of diagnosis instances

**Functionality:**
- Checks existing diagnoses on encounter
- Adds diagnosis if not present
- Attempts to add IDENTICAL diagnosis again
- Analyzes API response:
  - Error = duplicate prevention
  - Same ID = deduplication
  - New ID = stacking allowed
- Verifies final state with instance count

**Expected Result:** API should prevent duplicate diagnoses (reject with error)

**Example:**
```bash
python3 validation/behavior/identical_diagnosis.py
```

---

### `validation/behavior/identical_referrals.py`

**Purpose:** Test if API prevents duplicate referrals on same encounter

**Inputs:** None (hardcoded: Encounter 61456, Patient 60183)

**Outputs:**
- Console: Step-by-step test execution
- API behavior report (allows duplicates vs. prevents)
- Final count of referral instances

**Functionality:**
- Creates first referral order (cardiologist)
- Immediately creates IDENTICAL second referral
- Checks if both referrals were created
- Verifies referral IDs are different
- Proves API allows duplicate referrals (stacking behavior)

**Expected Result:** API allows duplicate referrals (both created successfully)

**Example:**
```bash
python3 validation/behavior/identical_referrals.py
```

---

### `validation/encounter_creation/order_driven_encounter.py`

**Purpose:** Test order-driven encounter creation (POST /ordergroups)

**Inputs:** None (hardcoded: Patient 7681)

**Outputs:**
- Console: Step-by-step encounter creation process
- Encounter ID created (TEMP status, ORDERSONLY type)
- Order group details
- Success/failure status

**Functionality:**
- Finds clean patient (no open encounters)
- Creates referral order group
- **Proves:** API automatically creates TEMP encounter
- Verifies encounter was created
- Shows encounter details (status, type, date)
- Documents order-driven workflow

**Expected Result:** Encounter created automatically via order group

**Example:**
```bash
python3 validation/encounter_creation/order_driven_encounter.py
```

---

### `validation/encounter_creation/visit_driven_encounter.py`

**Purpose:** Test visit-driven encounter creation (book appointment → check-in)

**Inputs:** None (hardcoded test patients)

**Outputs:**
- Console: Step-by-step visit-driven workflow
- Appointment creation/booking status
- Check-in attempt results
- Encounter creation verification
- Error messages (if blocked)

**Functionality:**
- Finds clean patient (no open encounters)
- Searches for today's appointment slots
- **If no slots:** Creates open appointment slot via API
- Books appointment for patient
- Attempts check-in
- Verifies if encounter was created
- **Known limitation:** Check-in blocked by insurance requirement in sandbox

**Expected Result:** Check-in likely fails due to insurance requirement (sandbox limitation)

**Example:**
```bash
python3 validation/encounter_creation/visit_driven_encounter.py
```

---

## 📊 Script Statistics

| Category | Scripts | Purpose |
|----------|---------|---------|
| **Discovery Utilities** | 2 | Find test data (appointments, patients) |
| **Validation Utility** | 1 | Validate encounters, test operations |
| **Behavior Tests** | 2 | Prove API duplicate handling |
| **Encounter Tests** | 2 | Prove encounter creation workflows |
| **TOTAL** | **7** | Complete test coverage |

---

## 🔑 Key Findings Documented

### Encounter Creation
- ✅ **Order-driven works:** POST /ordergroups creates TEMP encounter automatically
- ⚠️ **Visit-driven blocked:** POST /checkin requires insurance (sandbox limitation)

### Duplicate Behavior
- ✅ **Diagnoses:** API prevents duplicates (same SNOMED rejected)
- ✅ **Referrals:** API allows duplicates (stacking behavior)

### Encounter Types
- ✅ **TEMP encounters:** Fully functional for diagnoses and referrals
- ✅ **ORDERSONLY encounters:** Created automatically via order groups

---

## 📚 Documentation Files

### In `claude_code/docs/`
- [`athena_api.md`](docs/athena_api.md) - **Complete API reference** for `athena_api.py`
  - All 18 methods documented with inputs/outputs
  - Real examples with sample responses
  - Common workflows and error handling
  - API endpoint mappings

---

### `docs/REFERRAL_ORDER_TYPES.md`

**Purpose:** Complete catalog of all 347 referral order types by specialty

**Content:**
- Order type IDs organized by specialty (cardiology, orthopedics, etc.)
- Order type names and descriptions
- Specialty groupings
- Most commonly used order types

**Use Case:** Looking up valid order type IDs for referral creation

**Example Entries:**
- `257362` - Cardiologist referral
- `257363` - Orthopedic referral
- `257364` - Dermatology referral

---

## 📁 Archive Documentation

The `docs/archive/` folder contains reference documentation that was used during API exploration and development. These files are preserved for historical reference and lookup.

### `docs/archive/ATHENA_API_WORKFLOW.md`

**Purpose:** High-level API workflow overview and architecture documentation

**Content:**
- Complete referral workflow diagrams
- API endpoint mappings
- Request/response examples
- Authentication flow
- Error handling patterns

**Use Case:** Understanding overall API architecture and workflow design

---

### `docs/archive/MCP_TOOL_TEST_INPUTS.md`

**Purpose:** Test input specifications for MCP (Model Context Protocol) tools

**Content:**
- Validated test inputs for MCP tool testing
- Patient IDs, encounter IDs, order type IDs
- Known working combinations
- Expected outcomes for each test case

**Use Case:** Reference for testing MCP tool integrations with valid sandbox data

---

### `docs/archive/VIABLE_TEST_DATA_COMPLETE.md`

**Purpose:** Comprehensive collection of validated test data in sandbox environment

**Content:**
- Patient IDs with known states (with/without encounters)
- Provider IDs with availability
- Department IDs and configurations
- Encounter IDs with various statuses (TEMP, OPEN, CLOSED)
- Diagnosis IDs and SNOMED codes
- Referral IDs for testing

**Use Case:** Quick lookup of known-good test data for script development

**Example Entries:**
- Patient 7681: Clean state (no encounters)
- Patient 60183: Has open encounters
- Encounter 62020: TEMP/ORDERSONLY status
- Provider 71: Adam Bricker (Department 1)

---

### Why These Are Archived

These documents were created during the API exploration phase and contain valuable reference information, but they are:
- **Not actively maintained** - Current test data should be discovered using utility scripts
- **Historical snapshots** - Data may be outdated as sandbox resets
- **Reference only** - Use for lookups, not as source of truth

**For current test data, use:**
- `find_patients.py` - Discover current patients
- `find_appointment_slots.py` - Find current availability
- `validate_encounter.py` - Verify current encounter states

---

## 🚀 Quick Start

### Setup
```bash
cd /Users/parzival/VSCode/189A
source A2A-Framework/.venv/bin/activate
```

### Find Test Data
```bash
# Find patients without encounters
python3 claude_code/utilities/discovery/find_patients.py \
  --practice-id 195900 --encounter-status no-open

# Find available appointment slots
python3 claude_code/utilities/discovery/find_appointment_slots.py \
  --practice-id 195900 --exhaustive
```

### Validate Encounter
```bash
# Check encounter data
python3 claude_code/utilities/validate_encounter.py \
  --practice-id 195900 --encounter-id 61456

# Test complete pipeline (THE MOST IMPORTANT)
python3 claude_code/utilities/validate_encounter.py \
  --practice-id 195900 --encounter-id 62020 --test-pipeline
```

### Run Behavior Tests
```bash
# Test diagnosis duplicate prevention
python3 claude_code/validation/behavior/identical_diagnosis.py

# Test referral stacking
python3 claude_code/validation/behavior/identical_referrals.py
```

### Test Encounter Creation
```bash
# Order-driven (works)
python3 claude_code/validation/encounter_creation/order_driven_encounter.py

# Visit-driven (blocked in sandbox)
python3 claude_code/validation/encounter_creation/visit_driven_encounter.py
```

---

## 📝 Notes

- All utilities accept command-line arguments (no hardcoded values)
- Validation tests use hardcoded test data for repeatability
- Practice ID 195900 is the primary sandbox practice
- TEMP encounters are fully functional for complete workflows
- Order-driven encounter creation is the recommended approach
- Root directory `.md` files - Complete API workflow documentation