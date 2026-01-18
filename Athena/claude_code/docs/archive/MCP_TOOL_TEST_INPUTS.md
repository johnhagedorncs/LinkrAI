# MCP Tool Test Inputs

## Test Case: Chest Pain → Cardiology Referral

### Complete Input Data
```json
{
  "practice_id": "195900",
  "patientid": "60183",
  "diagnosis_snomed_code": "29857009",
  "diagnosis_icd10_code": "R07.9",
  "diagnosis_note": "Patient experiencing intermittent chest pain",
  "referral_ordertypeid": "257362",
  "provider_note": "Patient needs cardiology evaluation for chest pain",
  "reason_for_referral": "Chest pain evaluation"
}
```

### MCP Tool Calls

**Tool 1: add_diagnosis**
```json
{
  "tool": "add_diagnosis",
  "parameters": {
    "patientid": "60183",
    "snomed_code": "29857009",
    "icd10_code": "R07.9",
    "note": "Patient experiencing intermittent chest pain"
  }
}
```
*Auto-fetches active encounter for patient, then adds diagnosis to that encounter*

**Tool 2: create_referral_order**
```json
{
  "tool": "create_referral_order",
  "parameters": {
    "patientid": "60183",
    "ordertypeid": "257362",
    "diagnosis_snomed_code": "29857009",
    "provider_note": "Patient needs cardiology evaluation for chest pain",
    "reason_for_referral": "Chest pain evaluation"
  }
}
```
*Auto-fetches active encounter for patient, then creates referral order*

---

## How It Works

Both tools automatically fetch the patient's active encounter using `get_active_encounter(patientid)`, so the agent only needs to provide the patient ID. The tools handle the encounter lookup internally.

**Data Sources:**
- Patient 60183 (Gary Sandboxtest) - has open encounter 61456
- SNOMED 29857009 / ICD-10 R07.9 = "Chest pain, unspecified"
- Order Type 257362 = "cardiologist referral"

---

## Alternative Test Case: Angina → Cardiology Referral

**Use this if chest pain diagnosis already exists on encounter 61456**

The Athena API rejects duplicate diagnoses with the same SNOMED code. If "chest pain" (29857009) already exists on the encounter, use "angina" instead:

### Complete Input Data
```json
{
  "practice_id": "195900",
  "patientid": "60183",
  "diagnosis_snomed_code": "194828000",
  "diagnosis_icd10_code": "I20.9",
  "diagnosis_note": "Suspected stable angina",
  "referral_ordertypeid": "257362",
  "provider_note": "Patient needs cardiology evaluation for angina",
  "reason_for_referral": "Angina pectoris evaluation"
}
```

### MCP Tool Calls

**Tool 1: add_diagnosis**
```json
{
  "tool": "add_diagnosis",
  "parameters": {
    "patientid": "60183",
    "snomed_code": "194828000",
    "icd10_code": "I20.9",
    "note": "Suspected stable angina"
  }
}
```

**Tool 2: create_referral_order**
```json
{
  "tool": "create_referral_order",
  "parameters": {
    "patientid": "60183",
    "ordertypeid": "257362",
    "diagnosis_snomed_code": "194828000",
    "provider_note": "Patient needs cardiology evaluation for angina",
    "reason_for_referral": "Angina pectoris evaluation"
  }
}
```

**Why This Alternative Exists:**
- Encounter 61456 currently has chest pain diagnosis (SNOMED: 29857009)
- Athena API returns error: "Diagnosis with same snomed code already present in encounter"
- Angina (SNOMED: 194828000) is NOT on the encounter and can be added
- Both are cardiology-related, so same referral type (257362) works

**Other Fresh Diagnosis Options:**
- Shortness of breath: SNOMED 267036007 / ICD-10 R06.02
- Palpitations: SNOMED 80313002 / ICD-10 R00.2