# Athena Health API - Method Documentation

**File:** `athena_api.py`
**Purpose:** Python wrapper for Athena Health Legacy REST API (v1)
**Last Updated:** November 7, 2025

---

## Table of Contents

1. [Authentication Methods](#authentication-methods)
2. [Low-Level HTTP Methods](#low-level-http-methods)
3. [Patient Management](#patient-management)
4. [Encounter Management](#encounter-management)
5. [Diagnosis Management](#diagnosis-management)
6. [Provider & Department Lookup](#provider--department-lookup)
7. [Referral Order Management](#referral-order-management)
8. [Appointment Scheduling](#appointment-scheduling)
9. [Data Structures](#data-structures)

---

## Authentication Methods

### `get_token()`

**Purpose:** Get OAuth2 access token for API requests (with automatic caching)

**Inputs:** None

**Outputs:**
- **Type:** `str`
- **Value:** Bearer token for Authorization header

**Behavior:**
- Checks cache file (`.athena_token.json`) for valid token
- If cache expired or missing, fetches new token
- Tries FHIR scope first: `system/Patient.read system/Organization.read`
- Falls back to legacy scope: `athena/service/Athenanet.MDP.*`
- Automatically caches token with expiration time

**Example:**
```python
token = get_token()
# Returns: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Notes:**
- Token cached for performance
- Auto-refreshes when expired
- No manual token management needed

---

## Low-Level HTTP Methods

### `legacy_get(path, params=None, practice_id=None)`

**Purpose:** Execute GET request to Athena Legacy API

**Inputs:**
- `path` (str, required): API endpoint path with `{practiceid}` placeholder
- `params` (dict, optional): Query parameters
- `practice_id` (str, optional): Override default practice ID

**Outputs:**
- **Type:** `dict` or `list`
- **Value:** JSON response from API

**Example:**
```python
result = legacy_get(
    "/v1/{practiceid}/patients",
    params={"lastname": "Smith"}
)
# Returns: {"patients": [...]}
```

**Error Handling:**
- Raises `requests.HTTPError` on failure
- Prints success/failure messages with status code

---

### `legacy_post(path, data=None, params=None, practice_id=None)`

**Purpose:** Execute POST request to Athena Legacy API

**Inputs:**
- `path` (str, required): API endpoint path with `{practiceid}` placeholder
- `data` (dict, optional): Form data (application/x-www-form-urlencoded)
- `params` (dict, optional): Query parameters
- `practice_id` (str, optional): Override default practice ID

**Outputs:**
- **Type:** `dict` or `list`
- **Value:** JSON response from API

**Example:**
```python
result = legacy_post(
    "/v1/{practiceid}/chart/encounter/62020/diagnoses",
    data={"snomedcode": "29857009", "icd10codes": "R07.9"}
)
# Returns: {"diagnosisid": "23167", ...}
```

---

### `legacy_put(path, data=None, params=None, practice_id=None)`

**Purpose:** Execute PUT request to Athena Legacy API

**Inputs:**
- `path` (str, required): API endpoint path
- `data` (dict, optional): Form data
- `params` (dict, optional): Query parameters
- `practice_id` (str, optional): Override default practice ID

**Outputs:**
- **Type:** `dict` or `list`
- **Value:** JSON response from API

**Example:**
```python
result = legacy_put(
    "/v1/{practiceid}/appointments/1234567",
    data={"patientid": "7681"}
)
# Returns: [{"appointmentid": "1234567", ...}]
```

---

## Patient Management

### `find_patient(lastname, firstname=None)`

**Purpose:** Search for patient by name

**Inputs:**
- `lastname` (str, required): Patient's last name
- `firstname` (str, optional): Patient's first name for more specific search

**Outputs:**
- **Type:** `dict`
- **Value:** Patient object with fields:
  - `patientid` (str): Patient ID
  - `firstname` (str): First name
  - `lastname` (str): Last name
  - `dob` (str): Date of birth (MM/DD/YYYY)
  - `sex` (str): Sex (M/F)
  - `firstappointment` (str, optional): Date of first appointment

**Example:**
```python
patient = workflow.find_patient("Smith", "John")
# Returns: {
#   "patientid": "7681",
#   "firstname": "John",
#   "lastname": "Smith",
#   "dob": "01/15/1980",
#   "sex": "M"
# }
```

**Behavior:**
- Prefers patients with `firstappointment` (indicates active patient)
- Falls back to first result if none have appointments
- Raises `ValueError` if no patients found

**API Endpoint:** `GET /v1/{practiceid}/patients`

---

### `get_patient_details(patient_id)`

**Purpose:** Get complete patient demographics

**Inputs:**
- `patient_id` (str, required): Patient ID

**Outputs:**
- **Type:** `dict`
- **Value:** Complete patient object with all demographic fields

**Example:**
```python
details = workflow.get_patient_details("7681")
# Returns: {
#   "patientid": "7681",
#   "firstname": "Test",
#   "lastname": "Test",
#   "dob": "01/01/1990",
#   "sex": "M",
#   "address1": "123 Main St",
#   "city": "Boston",
#   "state": "MA",
#   "zip": "02101",
#   "homephone": "555-1234",
#   ...
# }
```

**API Endpoint:** `GET /v1/{practiceid}/patients/{patientid}`

---

### `get_patient_insurance(patient_id)`

**Purpose:** Get patient's insurance information

**Inputs:**
- `patient_id` (str, required): Patient ID

**Outputs:**
- **Type:** `list`
- **Value:** List of insurance objects with fields:
  - `insuranceid` (str): Insurance ID
  - `insurancetype` (str): Insurance type
  - `insuranceplanname` (str): Plan name
  - `membernumber` (str): Member ID
  - `active` (bool): Whether insurance is active

**Example:**
```python
insurances = workflow.get_patient_insurance("7681")
# Returns: [
#   {
#     "insuranceid": "123",
#     "insurancetype": "Commercial",
#     "insuranceplanname": "Blue Cross",
#     "membernumber": "ABC123456",
#     "active": true
#   }
# ]
```

**API Endpoint:** `GET /v1/{practiceid}/patients/{patientid}/insurances`

---

## Encounter Management

### `get_encounter(patient_id, department_id="1")`

**Purpose:** Get active encounter for patient

**Inputs:**
- `patient_id` (str, required): Patient ID
- `department_id` (str, optional): Department ID (default: "1")

**Outputs:**
- **Type:** `dict`
- **Value:** Encounter object with fields:
  - `encounterid` (str): Encounter ID
  - `encounterdate` (str): Date (MM/DD/YYYY)
  - `status` (str): OPEN/TEMP/CLOSED
  - `encountertype` (str): Type (e.g., ORDERSONLY, OFFICE VISIT)
  - `departmentid` (str): Department ID
  - `providerid` (str): Provider ID

**Example:**
```python
encounter = workflow.get_encounter("7681", department_id="1")
# Returns: {
#   "encounterid": "62020",
#   "encounterdate": "11/06/2025",
#   "status": "TEMP",
#   "encountertype": "ORDERSONLY",
#   "departmentid": "1",
#   "providerid": "71"
# }
```

**Behavior:**
- Returns most recent OPEN encounter if multiple exist
- Raises `ValueError` if no active encounter found
- **Important:** Cannot create encounters via API in sandbox

**Error Message:**
```
ValueError: No active encounter found for patient {patient_id}.
Please create an encounter via athenaNet UI first.
```

**API Endpoint:** `GET /v1/{practiceid}/chart/{patientid}/encounters?status=OPEN`

**Note:** Encounters are created automatically via:
1. **Order-driven:** `POST /ordergroups` creates TEMP encounter
2. **Visit-driven:** Appointment check-in creates OPEN encounter

---

## Diagnosis Management

### `get_encounter_diagnoses(encounter_id)`

**Purpose:** Get all diagnoses on an encounter

**Inputs:**
- `encounter_id` (str, required): Encounter ID

**Outputs:**
- **Type:** `list`
- **Value:** List of diagnosis objects with fields:
  - `diagnosisid` (str): Diagnosis ID
  - `snomedcode` (str): SNOMED CT code
  - `icd10code` (str): ICD-10 code
  - `description` (str): Diagnosis description
  - `note` (str, optional): Provider note

**Example:**
```python
diagnoses = workflow.get_encounter_diagnoses("62020")
# Returns: [
#   {
#     "diagnosisid": "23167",
#     "snomedcode": "29857009",
#     "icd10code": "R07.9",
#     "description": "Chest pain, unspecified",
#     "note": "Patient reports chest pain"
#   }
# ]
```

**API Endpoint:** `GET /v1/{practiceid}/chart/encounter/{encounterid}/diagnoses`

---

### `add_diagnosis(encounter_id, snomed_code, icd10_code, note="")`

**Purpose:** Add diagnosis to encounter

**Inputs:**
- `encounter_id` (str, required): Encounter ID
- `snomed_code` (str, required): SNOMED CT code
- `icd10_code` (str, required): ICD-10 code
- `note` (str, optional): Provider note

**Outputs:**
- **Type:** `dict`
- **Value:** Created diagnosis object with fields:
  - `diagnosisid` (str): New diagnosis ID
  - `snomedcode` (str): SNOMED code
  - `description` (str): Diagnosis description

**Example:**
```python
diagnosis = workflow.add_diagnosis(
    encounter_id="62020",
    snomed_code="29857009",
    icd10_code="R07.9",
    note="Testing diagnosis addition"
)
# Returns: {
#   "diagnosisid": "23167",
#   "snomedcode": "29857009",
#   "description": "Chest pain, unspecified"
# }
```

**Behavior:**
- **Duplicate Prevention:** API rejects duplicate SNOMED codes on same encounter
- Works on TEMP encounters (proved in validation tests)
- Note is optional but recommended for clinical context

**Error Cases:**
- Duplicate SNOMED: Returns error "Diagnosis already present"
- Invalid codes: Returns validation error

**API Endpoint:** `POST /v1/{practiceid}/chart/encounter/{encounterid}/diagnoses`

---

## Provider & Department Lookup

### `get_departments()`

**Purpose:** Get all departments in practice

**Inputs:** None

**Outputs:**
- **Type:** `list`
- **Value:** List of department objects with fields:
  - `departmentid` (str): Department ID
  - `name` (str): Department name
  - `address` (str): Address
  - `city` (str): City
  - `state` (str): State
  - `zip` (str): ZIP code

**Example:**
```python
departments = workflow.get_departments()
# Returns: [
#   {
#     "departmentid": "1",
#     "name": "Main Office",
#     "address": "1234 Medical Dr",
#     "city": "Boston",
#     "state": "MA"
#   }
# ]
```

**API Endpoint:** `GET /v1/{practiceid}/departments`

---

### `get_providers(name_filter=None)`

**Purpose:** Get all providers, optionally filtered by name

**Inputs:**
- `name_filter` (str, optional): Filter by provider name

**Outputs:**
- **Type:** `list`
- **Value:** List of provider objects with fields:
  - `providerid` (str): Provider ID
  - `firstname` (str): First name
  - `lastname` (str): Last name
  - `specialty` (str): Specialty name
  - `specialtyid` (str): Specialty ID
  - `usualdepartmentid` (str): Primary department

**Example:**
```python
providers = workflow.get_providers(name_filter="Bricker")
# Returns: [
#   {
#     "providerid": "71",
#     "firstname": "Adam",
#     "lastname": "Bricker",
#     "specialty": "Internal Medicine",
#     "specialtyid": "008",
#     "usualdepartmentid": "1"
#   }
# ]
```

**API Endpoint:** `GET /v1/{practiceid}/providers`

---

### `get_all_specialties()`

**Purpose:** Get unique specialties with provider counts (useful for LLM mapping)

**Inputs:** None

**Outputs:**
- **Type:** `list`
- **Value:** List of specialty objects with fields:
  - `specialty` (str): Specialty name
  - `specialtyid` (str): Specialty ID
  - `provider_count` (int): Number of providers with this specialty

**Example:**
```python
specialties = workflow.get_all_specialties()
# Returns: [
#   {
#     "specialty": "Cardiology",
#     "specialtyid": "006",
#     "provider_count": 3
#   },
#   {
#     "specialty": "Internal Medicine",
#     "specialtyid": "008",
#     "provider_count": 5
#   }
# ]
```

**Use Case:** LLM can map "I need a cardiologist" → specialty ID "006"

**Behavior:**
- Aggregates all providers by specialty
- Removes duplicates
- Sorted alphabetically by specialty name

---

### `get_providers_by_specialty(specialty_id, department_id="162")`

**Purpose:** Get providers filtered by specialty and department

**Inputs:**
- `specialty_id` (str, required): Specialty ID (e.g., "006" for Cardiology)
- `department_id` (str, optional): Filter by department (default: "162")

**Outputs:**
- **Type:** `list`
- **Value:** List of provider objects matching criteria

**Example:**
```python
cardiologists = workflow.get_providers_by_specialty(
    specialty_id="006",
    department_id="162"
)
# Returns: [
#   {
#     "providerid": "121",
#     "firstname": "Jane",
#     "lastname": "Smith",
#     "specialty": "Cardiology",
#     "specialtyid": "006"
#   }
# ]
```

**Behavior:**
- Filters providers by `specialtyid`
- Optionally filters by `usualdepartmentid`
- Returns empty list if no matches

---

## Referral Order Management

### `get_referral_order_types(search_term)`

**Purpose:** Search for referral order types (e.g., "cardiology", "orthopedic")

**Inputs:**
- `search_term` (str, required): Search keyword (specialty name or description)

**Outputs:**
- **Type:** `list`
- **Value:** List of order type objects with fields:
  - `ordertypeid` (str): Order type ID
  - `ordertype` (str): Order type name
  - `orderclass` (str): Class (e.g., "REFERRAL")
  - `description` (str): Detailed description

**Example:**
```python
order_types = workflow.get_referral_order_types("cardiology")
# Returns: [
#   {
#     "ordertypeid": "257362",
#     "ordertype": "Cardiology Referral",
#     "orderclass": "REFERRAL",
#     "description": "Referral to cardiologist"
#   }
# ]
```

**Common Order Types:**
- `257362` - Cardiology
- `257363` - Orthopedics
- `257364` - Dermatology
- `257365` - Neurology

**API Endpoint:** `GET /v1/{practiceid}/reference/order/referral?searchvalue={term}`

---

### `create_referral_order(encounter_id, order_type_id, diagnosis_snomed_code, provider_note="", reason_for_referral="")`

**Purpose:** Create referral order on encounter

**Inputs:**
- `encounter_id` (str, required): Encounter ID
- `order_type_id` (str, required): Order type ID from `get_referral_order_types()`
- `diagnosis_snomed_code` (str, required): SNOMED code for referral diagnosis
- `provider_note` (str, optional): Provider note
- `reason_for_referral` (str, optional): Clinical reason for referral

**Outputs:**
- **Type:** `dict`
- **Value:** Created referral object with fields:
  - `documentid` (str): Referral ID (use for `get_referral_details`)
  - `success` (bool): Whether creation succeeded

**Example:**
```python
referral = workflow.create_referral_order(
    encounter_id="62020",
    order_type_id="257362",
    diagnosis_snomed_code="29857009",
    provider_note="Chest pain evaluation",
    reason_for_referral="Patient reports persistent chest pain"
)
# Returns: {
#   "documentid": "203763",
#   "success": true
# }
```

**Behavior:**
- Creates referral on encounter
- **Duplicate Allowed:** API allows multiple identical referrals (stacking)
- Works on TEMP encounters
- Diagnosis must exist on encounter (or gets added automatically)

**API Endpoint:** `POST /v1/{practiceid}/chart/encounter/{encounterid}/orders/referral`

**Important Notes:**
- Unlike diagnoses, referrals can be duplicated
- Provider note and reason are optional but recommended
- Referral ID is in `documentid` field

---

### `get_referral_details(encounter_id, order_id)`

**Purpose:** Get details of created referral order

**Inputs:**
- `encounter_id` (str, required): Encounter ID
- `order_id` (str, required): Referral ID (from `create_referral_order`)

**Outputs:**
- **Type:** `dict`
- **Value:** Referral details with fields:
  - `orderid` (str): Order ID
  - `ordertypeid` (str): Order type ID
  - `ordertype` (str): Order type name
  - `status` (str): Referral status
  - `createddate` (str): Creation date
  - `description` (str): Description

**Example:**
```python
details = workflow.get_referral_details(
    encounter_id="62020",
    order_id="203763"
)
# Returns: {
#   "orderid": "203763",
#   "ordertypeid": "257362",
#   "ordertype": "Cardiology Referral",
#   "status": "Created",
#   "createddate": "11/06/2025"
# }
```

**API Endpoint:** `GET /v1/{practiceid}/chart/encounter/{encounterid}/orders/{orderid}`

---

## Appointment Scheduling

### `get_appointment_reasons(department_id, provider_id)`

**Purpose:** Get appointment reasons for specific provider+department

**Inputs:**
- `department_id` (str, required): Department ID
- `provider_id` (str, required): Provider ID

**Outputs:**
- **Type:** `list`
- **Value:** List of appointment reason objects with fields:
  - `reasonid` (str): Reason ID
  - `reason` (str): Patient-friendly name
  - `description` (str): Detailed description
  - `reasontype` (str): "new", "existing", or "all"
  - `schedulingminhours` (int): Min hours before booking
  - `schedulingmaxdays` (int): Max days in advance

**Example:**
```python
reasons = workflow.get_appointment_reasons(
    department_id="162",
    provider_id="121"
)
# Returns: [
#   {
#     "reasonid": "1234",
#     "reason": "Specialist Consultation",
#     "description": "New patient consultation",
#     "reasontype": "new",
#     "schedulingminhours": 24,
#     "schedulingmaxdays": 90
#   }
# ]
```

**API Endpoint:** `GET /v1/{practiceid}/patientappointmentreasons`

**Important:** Appointment reasons are configured per provider+department combination

---

### `find_appointment_slots(department_id, provider_id, reason_id, start_date, end_date, bypass_checks=False)`

**Purpose:** Find open appointment slots

**Inputs:**
- `department_id` (str, required): Department ID
- `provider_id` (str, required): Provider ID
- `reason_id` (str, required): Appointment reason ID (use "-1" for all)
- `start_date` (str, required): Start date (MM/DD/YYYY)
- `end_date` (str, required): End date (MM/DD/YYYY)
- `bypass_checks` (bool, optional): Ignore scheduling restrictions (default: False)

**Outputs:**
- **Type:** `list`
- **Value:** List of slot objects with fields:
  - `appointmentid` (str): Slot ID (use for booking)
  - `appointmenttypeid` (str): Appointment type ID
  - `date` (str): Date (MM/DD/YYYY)
  - `starttime` (str): Time (HH:MM)
  - `duration` (int): Duration in minutes
  - `providerid` (str): Provider ID
  - `departmentid` (str): Department ID

**Example:**
```python
slots = workflow.find_appointment_slots(
    department_id="162",
    provider_id="121",
    reason_id="-1",
    start_date="11/07/2025",
    end_date="11/14/2025",
    bypass_checks=True
)
# Returns: [
#   {
#     "appointmentid": "1421693",
#     "appointmenttypeid": "2",
#     "date": "11/08/2025",
#     "starttime": "09:00",
#     "duration": 30,
#     "providerid": "121",
#     "departmentid": "162"
#   }
# ]
```

**API Endpoint:** `GET /v1/{practiceid}/appointments/open`

**Tips:**
- Use `reason_id="-1"` to see all slots regardless of reason
- Set `bypass_checks=True` for testing (ignores time restrictions)
- Empty list = no slots available

---

### `book_appointment(appointment_id, patient_id, reason_id=None)`

**Purpose:** Book appointment for patient

**Inputs:**
- `appointment_id` (str, required): Appointment slot ID from `find_appointment_slots()`
- `patient_id` (str, required): Patient ID
- `reason_id` (str, optional): Appointment reason ID (recommended)

**Outputs:**
- **Type:** `dict`
- **Value:** Booked appointment object with fields:
  - `appointmentid` (str): Appointment ID
  - `patientid` (str): Patient ID
  - `date` (str): Date
  - `starttime` (str): Time
  - `appointmenttypeid` (str): Appointment type

**Example:**
```python
appointment = workflow.book_appointment(
    appointment_id="1421693",
    patient_id="7681",
    reason_id="1234"
)
# Returns: {
#   "appointmentid": "1421693",
#   "patientid": "7681",
#   "date": "11/08/2025",
#   "starttime": "09:00",
#   "appointmenttypeid": "2"
# }
```

**API Endpoint:** `PUT /v1/{practiceid}/appointments/{appointmentid}`

**Behavior:**
- Books open slot for patient
- `ignoreschedulablepermission` automatically set to true
- Reason ID recommended but optional

---

## Data Structures

### `DIAGNOSIS_MAPPINGS`

**Purpose:** Pre-mapped diagnosis codes for common conditions

**Structure:**
```python
{
    "condition_name": {
        "snomed": "SNOMED_CODE",
        "icd10": "ICD10_CODE",
        "description": "DESCRIPTION"
    }
}
```

**Example:**
```python
DIAGNOSIS_MAPPINGS = {
    "chest pain": {
        "snomed": "29857009",
        "icd10": "R07.9",
        "description": "Chest pain, unspecified"
    },
    "angina": {
        "snomed": "194828000",
        "icd10": "I20.9",
        "description": "Angina pectoris, unspecified"
    }
}
```

---

### `WorkflowResult`

**Purpose:** Container for workflow execution results

**Fields:**
- `patient_id` (str): Patient ID
- `encounter_id` (str): Encounter ID
- `diagnosis_id` (str): Diagnosis ID
- `diagnosis_snomed` (str): SNOMED code used
- `referral_id` (str): Referral/order ID
- `insurance_status` (dict): Insurance information
- `appointment_id` (str): Appointment ID
- `errors` (list): Error messages
- `steps_completed` (list): Successfully completed steps

**Methods:**
- `add_step(step)`: Add completed step
- `add_error(error)`: Add error message
- `to_dict()`: Convert to dictionary

**Example:**
```python
result = WorkflowResult()
result.patient_id = "7681"
result.encounter_id = "62020"
result.add_step("Patient identified")
result.add_step("Encounter retrieved")

output = result.to_dict()
# Returns: {
#   "patient_id": "7681",
#   "encounter_id": "62020",
#   "steps_completed": ["Patient identified", "Encounter retrieved"],
#   "errors": [],
#   "success": true
# }
```

---

## Common Workflows

### Complete Referral Workflow

```python
workflow = AthenaWorkflow(practice_id="195900")

# 1. Find patient
patient = workflow.find_patient("Test", "Test")

# 2. Get encounter
encounter = workflow.get_encounter(patient["patientid"])

# 3. Add diagnosis
diagnosis = workflow.add_diagnosis(
    encounter["encounterid"],
    snomed_code="29857009",
    icd10_code="R07.9",
    note="Chest pain evaluation"
)

# 4. Get referral order type
order_types = workflow.get_referral_order_types("cardiology")
order_type_id = order_types[0]["ordertypeid"]

# 5. Create referral
referral = workflow.create_referral_order(
    encounter["encounterid"],
    order_type_id,
    diagnosis_snomed_code="29857009",
    reason_for_referral="Cardiac evaluation needed"
)

print(f"Referral created: {referral['documentid']}")
```

### Appointment Booking Workflow

```python
workflow = AthenaWorkflow(practice_id="195900")

# 1. Find specialists
specialties = workflow.get_all_specialties()
cardiology_id = "006"  # From specialties list

providers = workflow.get_providers_by_specialty(cardiology_id)
provider_id = providers[0]["providerid"]
department_id = providers[0]["usualdepartmentid"]

# 2. Get appointment reasons
reasons = workflow.get_appointment_reasons(department_id, provider_id)
reason_id = reasons[0]["reasonid"]

# 3. Find slots
from datetime import datetime, timedelta
today = datetime.now().strftime("%m/%d/%Y")
next_week = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")

slots = workflow.find_appointment_slots(
    department_id,
    provider_id,
    reason_id,
    today,
    next_week
)

# 4. Book appointment
appointment = workflow.book_appointment(
    appointment_id=slots[0]["appointmentid"],
    patient_id="7681",
    reason_id=reason_id
)

print(f"Appointment booked: {appointment['appointmentid']}")
```

---

## Error Handling

### Common Errors

**No active encounter:**
```python
ValueError: No active encounter found for patient {patient_id}.
Please create an encounter via athenaNet UI first.
```
**Solution:** Use order-driven encounter creation (POST /ordergroups)

**Duplicate diagnosis:**
```python
HTTPError: 400 - Diagnosis already present on encounter
```
**Solution:** Check existing diagnoses first with `get_encounter_diagnoses()`

**Invalid credentials:**
```python
HTTPError: 401 - Unauthorized
```
**Solution:** Check ATHENA_CLIENT_ID and ATHENA_CLIENT_SECRET in .env

**Practice ID not set:**
```python
ValueError: Practice ID must be provided or set in ATHENA_PRACTICE_ID
```
**Solution:** Set ATHENA_PRACTICE_ID in .env or pass to AthenaWorkflow()

---

## Environment Variables

Required in `.env` file:

```bash
ATHENA_CLIENT_ID=your_client_id
ATHENA_CLIENT_SECRET=your_client_secret
ATHENA_BASE_URL=https://api.preview.platform.athenahealth.com
ATHENA_PRACTICE_ID=195900
```

---

## Notes

- All date inputs use MM/DD/YYYY format
- Practice ID 195900 is the sandbox practice
- TEMP encounters are fully functional for orders/referrals
- Referrals allow duplicates, diagnoses do not
- Token caching improves performance significantly
- Use `bypass_checks=True` for testing appointment booking

---

**For complete workflow examples, see:**
- `referral_workflow.py` - Complete referral creation
- `scheduling_workflow.py` - Appointment booking flow
- `claude_code/utilities/validate_encounter.py` - Testing all operations