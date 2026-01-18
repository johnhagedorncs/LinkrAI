"""
Athena Health API Wrapper
Provides functions to interact with the Athena Health Legacy REST API (v1)
For workflow orchestration, see scheduling_workflow.py and referral_workflow.py
"""

import os
import json
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import requests

# Get the directory where this file is located (Athena directory)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load shared .env from A2A-Framework root
load_dotenv(dotenv_path=os.path.join(_SCRIPT_DIR, '../.env'))

# Auth utils


CLIENT_ID = os.getenv("ATHENA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ATHENA_CLIENT_SECRET")
BASE_URL = os.getenv("ATHENA_BASE_URL", "https://api.preview.platform.athenahealth.com")
PRACTICE_ID = os.getenv("ATHENA_PRACTICE_ID")  # Must be set in .env file
TOKEN_CACHE_FILE = os.path.join(_SCRIPT_DIR, ".athena_token.json")

def _load_cached_token():
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    with open(TOKEN_CACHE_FILE, "r") as f:
        data = json.load(f)
    if data.get("expires_at", 0) > time.time() + 60:
        return data["access_token"]
    return None


def _save_cached_token(token, expires_in):
    expires_at = time.time() + expires_in
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump({"access_token": token, "expires_at": expires_at}, f)


def _fetch_token(scope: str):
    token_url = f"{BASE_URL}/oauth2/v1/token"
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials", "scope": scope}

    r = requests.post(token_url, headers=headers, data=data)
    if r.status_code == 401 and os.path.exists(TOKEN_CACHE_FILE):
        os.remove(TOKEN_CACHE_FILE)
    r.raise_for_status()

    body = r.json()
    print("DEBUG TOKEN:", json.dumps(body, indent=2))
    token = body["access_token"]
    _save_cached_token(token, body.get("expires_in", 3600))
    return token


def get_token():
    cached = _load_cached_token()
    if cached:
        return cached
    try:
        return _fetch_token("system/Patient.read system/Organization.read")
    except Exception:
        print("⚠️  FHIR scope failed; using legacy Preview scope instead")
        return _fetch_token("athena/service/Athenanet.MDP.*")


def legacy_get(path, params=None, practice_id=None):
    """Execute GET request to Athena legacy API"""
    if practice_id is None:
        practice_id = PRACTICE_ID
    token = get_token()
    url = f"{BASE_URL}{path.format(practiceid=practice_id)}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(url, headers=headers, params=params)
    try:
        r.raise_for_status()
        print(f"✅ Legacy API GET success: {path}")
        return r.json()
    except requests.HTTPError:
        print(f"❌ Legacy API GET failed ({r.status_code}): {r.text}")
        raise


def legacy_post(path, data=None, params=None, practice_id=None):
    """Execute POST request to Athena legacy API"""
    if practice_id is None:
        practice_id = PRACTICE_ID
    token = get_token()
    url = f"{BASE_URL}{path.format(practiceid=practice_id)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.post(url, headers=headers, data=data, params=params)
    try:
        r.raise_for_status()
        print(f"✅ Legacy API POST success: {path}")
        return r.json()
    except requests.HTTPError:
        print(f"❌ Legacy API POST failed ({r.status_code}): {r.text}")
        raise


def legacy_put(path, data=None, params=None, practice_id=None):
    """Execute PUT request to Athena legacy API"""
    if practice_id is None:
        practice_id = PRACTICE_ID
    token = get_token()
    url = f"{BASE_URL}{path.format(practiceid=practice_id)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.put(url, headers=headers, data=data, params=params)
    try:
        r.raise_for_status()
        print(f"✅ Legacy API PUT success: {path}")
        return r.json()
    except requests.HTTPError:
        print(f"❌ Legacy API PUT failed ({r.status_code}): {r.text}")
        raise

# Diagnosis mappings (in real agent, LLM would determine these)
DIAGNOSIS_MAPPINGS = {
    "chest pain": {"snomed": "29857009", "icd10": "R07.9", "description": "Chest pain, unspecified"},
    "angina": {"snomed": "194828000", "icd10": "I20.9", "description": "Angina pectoris, unspecified"},
    "shortness of breath": {"snomed": "267036007", "icd10": "R06.02", "description": "Shortness of breath"},
    "palpitations": {"snomed": "80313002", "icd10": "R00.2", "description": "Palpitations"},
}

# Specialty to order type mappings
SPECIALTY_MAPPINGS = {
    "cardiology": {"searchterm": "cardiology", "specialty": "Cardiology"},
    "orthopedics": {"searchterm": "orthopedic", "specialty": "Orthopedics"},
    "neurology": {"searchterm": "neurologist", "specialty": "Neurology"},
    "dermatology": {"searchterm": "dermatologist", "specialty": "Dermatology"},
}


class WorkflowResult:
    """Container for workflow execution results"""
    def __init__(self):
        self.patient_id: Optional[str] = None
        self.encounter_id: Optional[str] = None
        self.diagnosis_id: Optional[str] = None
        self.diagnosis_snomed: Optional[str] = None
        self.referral_id: Optional[str] = None
        self.insurance_status: Optional[Dict] = None
        self.appointment_id: Optional[str] = None
        self.errors: List[str] = []
        self.steps_completed: List[str] = []

    def add_step(self, step: str):
        self.steps_completed.append(step)
        print(f"✅ {step}")

    def add_error(self, error: str):
        self.errors.append(error)
        print(f"❌ {error}")

    def to_dict(self) -> Dict:
        return {
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "diagnosis_id": self.diagnosis_id,
            "referral_id": self.referral_id,
            "insurance_status": self.insurance_status,
            "appointment_id": self.appointment_id,
            "steps_completed": self.steps_completed,
            "errors": self.errors,
            "success": len(self.errors) == 0
        }


class AthenaWorkflow:
    """Complete referral workflow orchestrator"""

    def __init__(self, practice_id: Optional[str] = None):
        # Use provided practice_id, or fall back to environment variable
        self.practice_id = practice_id or PRACTICE_ID
        if not self.practice_id:
            raise ValueError("Practice ID must be provided or set in ATHENA_PRACTICE_ID environment variable")
        self.use_mocks = True  # Set to False when in production

    # ============================================================================
    # STEP 1: PATIENT IDENTIFICATION
    # ============================================================================

    def find_patient(self, lastname: str, firstname: Optional[str] = None) -> Dict[str, Any]:
        """Search for patient by name"""
        params = {"lastname": lastname}
        if firstname:
            params["firstname"] = firstname

        result = legacy_get("/v1/{practiceid}/patients", params=params, practice_id=self.practice_id)

        if not result.get("patients"):
            raise ValueError(f"No patients found with lastname={lastname}")

        patients = result["patients"]

        # Try to find a patient with an encounter (preferably with firstappointment)
        for patient in patients:
            if patient.get("firstappointment"):
                return patient

        # Otherwise return first patient
        return patients[0]

    def get_patient_details(self, patient_id: str) -> Dict[str, Any]:
        """Get full patient demographics"""
        result = legacy_get(f"/v1/{{practiceid}}/patients/{patient_id}", practice_id=self.practice_id)
        # API returns a list with one patient object
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result

    def get_patient_insurance(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient insurance information"""
        result = legacy_get(f"/v1/{{practiceid}}/patients/{patient_id}/insurances", practice_id=self.practice_id)
        return result.get("insurances", [])

    def create_patient(
        self,
        firstname: str,
        lastname: str,
        dob: str,
        sex: str,
        department_id: str,
        address1: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip: Optional[str] = None,
        email: Optional[str] = None,
        homephone: Optional[str] = None,
        mobilephone: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new patient record in the system.

        Args:
            firstname: Patient's first name (required, max 20 chars)
            lastname: Patient's last name (required, max 20 chars)
            dob: Patient's date of birth in mm/dd/yyyy format (required)
            sex: Patient's sex - M or F (required)
            department_id: Primary registration department ID (required)
            address1: Patient's address line 1 (optional, max 100 chars)
            city: Patient's city (optional, max 30 chars)
            state: Patient's state 2-letter code (optional)
            zip: Patient's zip code (optional)
            email: Patient's email address (optional)
            homephone: Patient's home phone (optional, NANP format)
            mobilephone: Patient's mobile phone (optional, NANP format)
            **kwargs: Additional optional fields (see API docs)

        Returns:
            Dict with 'patientid' of newly created patient

        Raises:
            HTTPError: If patient creation fails or duplicate found
        """
        data = {
            "firstname": firstname,
            "lastname": lastname,
            "dob": dob,
            "sex": sex,
            "departmentid": department_id
        }

        # Add optional fields if provided
        if address1:
            data["address1"] = address1
        if city:
            data["city"] = city
        if state:
            data["state"] = state
        if zip:
            data["zip"] = zip
        if email:
            data["email"] = email
        if homephone:
            data["homephone"] = homephone
        if mobilephone:
            data["mobilephone"] = mobilephone

        # Add any additional kwargs
        data.update(kwargs)

        result = legacy_post(
            "/v1/{practiceid}/patients",
            data=data,
            practice_id=self.practice_id
        )

        # API returns a list with one patient object
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result

    # ============================================================================
    # STEP 2: ENCOUNTER MANAGEMENT
    # ============================================================================

    def get_encounter(self, patient_id: str, department_id: str = "1") -> Dict[str, Any]:
        """
        Get active encounter for patient. Raises error if none exists.
        Note: Encounters are created naturally (not exactly sure on logistics), so we must use existing ones for now.

        Args:
            patient_id: Patient ID
            department_id: Department ID (default: 1)

        Returns:
            Encounter dict with encounterid

        Raises:
            ValueError: If no active encounter exists for patient
        """
        # Try to get existing open encounter
        result = legacy_get(
            f"/v1/{{practiceid}}/chart/{patient_id}/encounters",
            params={"departmentid": department_id, "status": "OPEN"},
            practice_id=self.practice_id
        )

        encounters = result.get("encounters", [])
        if encounters:
            # Return most recent encounter
            return encounters[0]

        # No active encounter found - cannot create via API
        raise ValueError(
            f"No active encounter found for patient {patient_id} in department {department_id}. "
            f"Please create an encounter via athenaNet UI first. "
            f"Note: Encounter creation API is not available in sandbox environment."
        )

    def get_active_encounter(self, patient_id: str, department_id: str = "1") -> Dict[str, Any]:
        """
        Alias for get_encounter() - maintained for compatibility with referral_mcp.py
        """
        return self.get_encounter(patient_id, department_id)

    # ============================================================================
    # STEP 3: DIAGNOSIS MANAGEMENT
    # ============================================================================

    def get_encounter_diagnoses(self, encounter_id: str) -> List[Dict[str, Any]]:
        """Get all existing diagnoses for an encounter"""
        return legacy_get(
            f"/v1/{{practiceid}}/chart/encounter/{encounter_id}/diagnoses",
            practice_id=self.practice_id
        )

    def add_diagnosis(
        self,
        encounter_id: str,
        snomed_code: str,
        icd10_code: str,
        note: str = ""
    ) -> Dict[str, Any]:
        """Add diagnosis to encounter"""
        data = {
            "snomedcode": snomed_code,
            "icd10codes": icd10_code,
            "note": note
        }

        return legacy_post(
            f"/v1/{{practiceid}}/chart/encounter/{encounter_id}/diagnoses",
            data=data,
            practice_id=self.practice_id
        )

    # ============================================================================
    # STEP 4: PROVIDER & DEPARTMENT LOOKUP
    # ============================================================================

    def get_departments(self) -> List[Dict[str, Any]]:
        """Get all practice departments"""
        result = legacy_get("/v1/{practiceid}/departments", practice_id=self.practice_id)
        return result.get("departments", [])

    def get_providers(self, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get providers, optionally filtered by name"""
        params = {}
        if name_filter:
            params["name"] = name_filter

        result = legacy_get("/v1/{practiceid}/providers", params=params, practice_id=self.practice_id)
        return result.get("providers", [])

    def get_all_specialties(self) -> List[Dict[str, Any]]:
        """
        Get all unique provider specialties in the practice.
        Useful for LLM to map user requests like "cardiologist" to specialty ID.

        Returns list of unique specialties with:
        - specialty: Name (e.g., "Cardiology")
        - specialtyid: ID to use for filtering (e.g., "006")
        - provider_count: How many providers have this specialty

        Example usage in MCP tool:
            specialties = workflow.get_all_specialties()
            # LLM can see: "Cardiology (ID: 006, 3 providers)"
            # Then use specialty_id "006" with get_providers_by_specialty()
        """
        providers = self.get_providers()

        # Group by specialty
        specialty_map = {}
        for provider in providers:
            specialty = provider.get("specialty")
            specialty_id = provider.get("specialtyid")

            if specialty and specialty_id:
                key = (specialty, specialty_id)
                if key not in specialty_map:
                    specialty_map[key] = {
                        "specialty": specialty,
                        "specialtyid": specialty_id,
                        "provider_count": 0
                    }
                specialty_map[key]["provider_count"] += 1

        # Return as sorted list
        specialties = list(specialty_map.values())
        specialties.sort(key=lambda x: x["specialty"])
        return specialties

    # ============================================================================
    # STEP 5: REFERRAL ORDER CREATION
    # ============================================================================

    def get_referral_order_types(self, search_term: str) -> List[Dict[str, Any]]:
        """Get referral order types by search term"""
        result = legacy_get(
            "/v1/{practiceid}/reference/order/referral",
            params={"searchvalue": search_term},
            practice_id=self.practice_id
        )
        return result if isinstance(result, list) else []

    def create_referral_order(
        self,
        encounter_id: str,
        order_type_id: str,
        diagnosis_snomed_code: str,
        provider_note: str = "",
        reason_for_referral: str = ""
    ) -> Dict[str, Any]:
        """Create referral order"""
        data = {
            "ordertypeid": order_type_id,
            "diagnosissnomedcode": diagnosis_snomed_code,
        }

        if provider_note:
            data["providernote"] = provider_note
        if reason_for_referral:
            data["reasonforreferral"] = reason_for_referral

        return legacy_post(
            f"/v1/{{practiceid}}/chart/encounter/{encounter_id}/orders/referral",
            data=data,
            practice_id=self.practice_id
        )

    def get_referral_details(self, encounter_id: str, order_id: str) -> Dict[str, Any]:
        """Get details of created referral order"""
        return legacy_get(
            f"/v1/{{practiceid}}/chart/encounter/{encounter_id}/orders/{order_id}",
            practice_id=self.practice_id
        )

    def get_encounter_orders(self, encounter_id: str) -> List[Dict[str, Any]]:
        """Get all orders for an encounter"""
        result = legacy_get(
            f"/v1/{{practiceid}}/chart/encounter/{encounter_id}/orders",
            practice_id=self.practice_id
        )
        # API may return list directly or dict with "orders" key
        if isinstance(result, list):
            return result
        return result.get("orders", [])

    # ============================================================================
    # STEP 6: APPOINTMENT SCHEDULING
    # ============================================================================

    def get_providers_by_specialty(
        self,
        specialty_id: str,
        department_id: str = "162"
    ) -> List[Dict[str, Any]]:
        """
        Get providers filtered by specialty ID and optionally department.

        Args:
            specialty_id: Specialty ID (e.g., "006" for Cardiology)
            department_id: Department to filter by (default: 162)

        Returns:
            List of providers with matching specialty
        """
        providers = self.get_providers()

        # Filter by specialty
        specialist_providers = [
            p for p in providers
            if p.get('specialtyid') == specialty_id
        ]

        # Optionally filter by department (using usualdepartmentid)
        if department_id:
            specialist_providers = [
                p for p in specialist_providers
                if str(p.get('usualdepartmentid')) == str(department_id)
            ]

        return specialist_providers

    def get_appointment_reasons(
        self,
        department_id: str,
        provider_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get appointment reasons for specific provider+department combination.
        Appointment reasons are configured per provider+department.

        Returns list of reasons with:
        - reasonid: ID to use when booking/slot search
        - reason: Patient-friendly name (e.g., "Specialist Consultation")
        - description: Detailed description
        - reasontype: "new", "existing", or "all"
        - schedulingminhours: Min hours before appointment can be booked
        - schedulingmaxdays: Max days in advance appointment can be booked
        """
        params = {
            "departmentid": department_id,
            "providerid": provider_id
        }
        result = legacy_get(
            "/v1/{practiceid}/patientappointmentreasons",
            params=params,
            practice_id=self.practice_id
        )
        return result.get("patientappointmentreasons", result) if isinstance(result, dict) else result

    def find_appointment_slots(
        self,
        department_id: str,
        provider_id: str,
        reason_id: str,
        start_date: str,
        end_date: str,
        bypass_checks: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find open appointment slots for specific provider+department+reason.

        Args:
            department_id: Department ID (e.g., "162")
            provider_id: Provider ID (e.g., "121")
            reason_id: Appointment reason ID from get_appointment_reasons()
                       Use "-1" to get all slots regardless of reason
            start_date: Start date (MM/DD/YYYY format)
            end_date: End date (MM/DD/YYYY format)
            bypass_checks: If True, ignores scheduling time restrictions

        Returns:
            List of available appointment slots
        """
        params = {
            "departmentid": department_id,
            "providerid": provider_id,
            "reasonid": reason_id,
            "startdate": start_date,
            "enddate": end_date
        }

        if bypass_checks:
            params["ignoreschedulablepermission"] = "true"
            params["bypassscheduletimechecks"] = "true"

        result = legacy_get(
            "/v1/{practiceid}/appointments/open",
            params=params,
            practice_id=self.practice_id
        )
        return result.get("appointments", [])

    def book_appointment(
        self,
        appointment_id: str,
        patient_id: str,
        appointment_type_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Book appointment with appointment type ID.

        Args:
            appointment_id: Appointment slot ID from find_appointment_slots()
            patient_id: Patient ID
            appointment_type_id: Appointment type ID from the slot (required for proper booking)
        """
        data = {
            "patientid": patient_id,
            "ignoreschedulablepermission": "true"
        }

        # Add appointment type ID if provided (required for proper booking)
        if appointment_type_id:
            data["appointmenttypeid"] = appointment_type_id

        result = legacy_put(
            f"/v1/{{practiceid}}/appointments/{appointment_id}",
            data=data,
            practice_id=self.practice_id
        )

        # API returns a list with one appointment object
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result
        
    # ============================================================================
    # END OF API FUNCTIONS
    # For workflow orchestration, see:
    # - scheduling_workflow.py for appointment booking
    # - referral_workflow.py for referral creation
    # ============================================================================