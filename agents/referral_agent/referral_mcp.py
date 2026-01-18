"""MCP server for referral operations with Athena Health API integration."""
import asyncio
import logging
import os
import sys

# Add parent directory to path to import athena modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import Athena API helper
try:
    # Import from Athena directory (two levels up from A2A-Framework/referral_agent)
    from Athena.athena_api import AthenaWorkflow
    ATHENA_AVAILABLE = True
except ImportError:
    ATHENA_AVAILABLE = False
    print("⚠️ Athena API modules not available, using mock responses only")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("referral-mcp-server")

# Create an MCP server
app = Server("referral-server")

# Cached diagnosis mappings (from athena_workflow.py)
DIAGNOSIS_MAPPINGS = {
    # Cardiology
    "chest pain": {"snomed": "29857009", "icd10": "R07.9", "description": "Chest pain, unspecified"},
    "hypertension": {"snomed": "38341003", "icd10": "I10", "description": "Essential (primary) hypertension"},
    "arrhythmia": {"snomed": "698247007", "icd10": "I49.9", "description": "Cardiac arrhythmia, unspecified"},
    "heart murmur": {"snomed": "88610006", "icd10": "R01.1", "description": "Cardiac murmur, unspecified"},
    "shortness of breath": {"snomed": "267036007", "icd10": "R06.02", "description": "Shortness of breath"},

    # Dermatology
    "suspicious mole": {"snomed": "400210000", "icd10": "D22.9", "description": "Melanocytic nevi, unspecified"},
    "severe acne": {"snomed": "278009009", "icd10": "L70.0", "description": "Acne vulgaris"},
    "psoriasis": {"snomed": "9014002", "icd10": "L40.9", "description": "Psoriasis, unspecified"},
    "chronic rash": {"snomed": "271807003", "icd10": "R21", "description": "Rash and other nonspecific skin eruption"},
    "skin lesion": {"snomed": "95324001", "icd10": "L98.9", "description": "Disorder of the skin and subcutaneous tissue, unspecified"},

    # Primary Care
    "annual physical": {"snomed": "185349003", "icd10": "Z00.00", "description": "Encounter for general adult medical examination without abnormal findings"},
    "diabetes management": {"snomed": "44054006", "icd10": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
    "fatigue": {"snomed": "84229001", "icd10": "R53.83", "description": "Other fatigue"},
    "weight management": {"snomed": "238131007", "icd10": "E66.9", "description": "Obesity, unspecified"},
    "medication refill": {"snomed": "182838006", "icd10": "Z76.0", "description": "Encounter for issue of repeat prescription"},

    # Internal Medicine
    "abdominal pain": {"snomed": "21522001", "icd10": "R10.9", "description": "Unspecified abdominal pain"},
    "anemia": {"snomed": "271737000", "icd10": "D64.9", "description": "Anemia, unspecified"},
    "thyroid disorder": {"snomed": "40930008", "icd10": "E07.9", "description": "Disorder of thyroid, unspecified"},
    "joint pain": {"snomed": "57676002", "icd10": "M25.50", "description": "Pain in unspecified joint"},
    "chronic cough": {"snomed": "68154008", "icd10": "R05", "description": "Cough"},

    # Oncology
    "abnormal mammogram": {"snomed": "116223007", "icd10": "R92.8", "description": "Other abnormal and inconclusive findings on diagnostic imaging of breast"},
    "lymphadenopathy": {"snomed": "111590001", "icd10": "R59.9", "description": "Enlarged lymph nodes, unspecified"},
    "abnormal blood counts": {"snomed": "165517008", "icd10": "R72", "description": "Abnormality of white blood cells, not elsewhere classified"},
    "weight loss": {"snomed": "89362005", "icd10": "R63.4", "description": "Abnormal weight loss"},
    "prostate cancer": {"snomed": "399068003", "icd10": "C61", "description": "Malignant neoplasm of prostate"},

    # Pediatrics
    "developmental delay": {"snomed": "248290002", "icd10": "F88", "description": "Other disorders of psychological development"},
    "asthma": {"snomed": "195967001", "icd10": "J45.909", "description": "Unspecified asthma, uncomplicated"},
    "failure to thrive": {"snomed": "309257005", "icd10": "R62.51", "description": "Failure to thrive (child)"},
    "ear infection": {"snomed": "128139000", "icd10": "H66.90", "description": "Otitis media, unspecified, unspecified ear"},
    "adhd evaluation": {"snomed": "406506008", "icd10": "F90.9", "description": "Attention-deficit hyperactivity disorder, unspecified type"},
}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available referral tools."""
    return [
        Tool(
            name="list_diagnoses",
            description="Lists available diagnoses with SNOMED codes from cached list",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="list_referral_types",
            description="Gets available referral order types from Athena Health API by searching for a specialty",
            inputSchema={
                "type": "object",
                "properties": {
                    "specialty": {
                        "type": "string",
                        "description": "Specialty to search for (e.g., cardiology, orthopedics, neurology)",
                    }
                },
                "required": ["specialty"],
            },
        ),
        Tool(
            name="add_diagnosis",
            description="Adds a diagnosis to the patient's active encounter using Athena Health API",
            inputSchema={
                "type": "object",
                "properties": {
                    "patientid": {
                        "type": "string",
                        "description": "Patient ID (if known directly)",
                    },
                    "encounter_id": {
                        "type": "string",
                        "description": "Encounter ID (if known directly - takes priority over patient lookup)",
                    },
                    "patient_lastname": {
                        "type": "string",
                        "description": "Patient's last name to search and find their active encounter",
                    },
                    "diagnosis_key": {
                        "type": "string",
                        "description": "Key from diagnosis list (e.g., 'chest pain', 'angina', 'hypertension')",
                    },
                    "snomed_code": {
                        "type": "string",
                        "description": "Optional: Direct SNOMED code (if not using diagnosis_key)",
                    },
                    "icd10_code": {
                        "type": "string",
                        "description": "Optional: Direct ICD-10 code (if not using diagnosis_key)",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional clinical notes about the diagnosis",
                    }
                },
                "required": ["diagnosis_key"],
            },
        ),
        Tool(
            name="create_referral",
            description="Creates a referral order for the patient using Athena Health API",
            inputSchema={
                "type": "object",
                "properties": {
                    "patientid": {
                        "type": "string",
                        "description": "Patient ID (if known directly)",
                    },
                    "encounter_id": {
                        "type": "string",
                        "description": "Encounter ID (if known directly - takes priority over patient lookup)",
                    },
                    "patient_lastname": {
                        "type": "string",
                        "description": "Patient's last name to search for patient",
                    },
                    "ordertypeid": {
                        "type": "string",
                        "description": "Order type ID from list_referral_types (alternative to referral_type_id)",
                    },
                    "referral_type_id": {
                        "type": "string",
                        "description": "Order type ID from list_referral_types",
                    },
                    "diagnosis_key": {
                        "type": "string",
                        "description": "Diagnosis key that was added to encounter (e.g., 'chest pain', 'angina')",
                    },
                    "diagnosis_snomed_code": {
                        "type": "string",
                        "description": "Direct SNOMED code (alternative to diagnosis_key)",
                    },
                    "provider_note": {
                        "type": "string",
                        "description": "Optional provider notes for the referral",
                    },
                    "reason_for_referral": {
                        "type": "string",
                        "description": "Optional reason for the referral",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_patient_diagnoses",
            description="Lists all diagnoses for a patient's active encounter from Athena Health API",
            inputSchema={
                "type": "object",
                "properties": {
                    "patientid": {
                        "type": "string",
                        "description": "Patient ID (if known directly)",
                    },
                    "encounterid": {
                        "type": "string",
                        "description": "Optional: Encounter ID. If not provided, will automatically find the patient's active encounter.",
                    },
                    "patient_lastname": {
                        "type": "string",
                        "description": "Patient's last name to search for patient",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_patient_referrals",
            description="Lists all referral orders for a patient's active encounter from Athena Health API",
            inputSchema={
                "type": "object",
                "properties": {
                    "patientid": {
                        "type": "string",
                        "description": "Patient ID (if known directly)",
                    },
                    "encounterid": {
                        "type": "string",
                        "description": "Optional: Encounter ID. If not provided, will automatically find the patient's active encounter.",
                    },
                    "patient_lastname": {
                        "type": "string",
                        "description": "Patient's last name to search for patient",
                    }
                },
                "required": [],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for referral operations."""

    if name == "list_diagnoses":
        logger.info("Listing available diagnoses")

        # Format diagnosis list
        diagnosis_list = []
        diagnosis_list.append("📋 **Available Diagnoses:**\n")

        for key, diagnosis in DIAGNOSIS_MAPPINGS.items():
            diagnosis_list.append(f"**{key.title()}**")
            diagnosis_list.append(f"  • SNOMED Code: {diagnosis['snomed']}")
            diagnosis_list.append(f"  • ICD-10 Code: {diagnosis['icd10']}")
            diagnosis_list.append(f"  • Description: {diagnosis['description']}")
            diagnosis_list.append("")

        return [
            TextContent(
                type="text",
                text="\n".join(diagnosis_list),
            )
        ]

    elif name == "list_referral_types":
        specialty = arguments.get("specialty")
        logger.info(f"Listing referral types for specialty: {specialty}")

        if not ATHENA_AVAILABLE:
            return [
                TextContent(
                    type="text",
                    text="⚠️ Athena API not available. Unable to fetch referral types.",
                )
            ]

        try:
            workflow = AthenaWorkflow()
            referral_types = workflow.get_referral_order_types(specialty)

            if not referral_types:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ No referral types found for specialty: {specialty}",
                    )
                ]

            # Format referral types
            referral_list = []
            referral_list.append(f"🏥 **Referral Types for {specialty.title()}:**\n")

            for order_type in referral_types[:10]:  # Limit to first 10
                referral_list.append(f"**ID: {order_type.get('ordertypeid')}**")
                referral_list.append(f"  • Name: {order_type.get('name', 'N/A')}")
                referral_list.append(f"  • Description: {order_type.get('description', 'N/A')}")
                referral_list.append("")

            if len(referral_types) > 10:
                referral_list.append(f"_Showing 10 of {len(referral_types)} results_")

            return [
                TextContent(
                    type="text",
                    text="\n".join(referral_list),
                )
            ]

        except Exception as e:
            logger.error(f"Error fetching referral types: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: Unable to fetch referral types. {str(e)}",
                )
            ]

    elif name == "add_diagnosis":
        # Support encounter_id, patientid, or patient_lastname
        encounter_id = arguments.get("encounter_id")
        patient_id = arguments.get("patientid")
        encounter_id = arguments.get("encounterid")  # Optional
        patient_lastname = arguments.get("patient_lastname")
        diagnosis_key = arguments.get("diagnosis_key")
        snomed_code = arguments.get("snomed_code")
        icd10_code = arguments.get("icd10_code")
        note = arguments.get("note", "")

        logger.info(f"Adding diagnosis - encounter_id: {encounter_id}, patient_id: {patient_id}, patient_lastname: {patient_lastname}")

        if not ATHENA_AVAILABLE:
            return [
                TextContent(
                    type="text",
                    text="⚠️ Athena API not available. Unable to add diagnosis.",
                )
            ]

        try:
            workflow = AthenaWorkflow()

            # If encounter_id is provided, use it directly (priority)
            if encounter_id:
                logger.info(f"Using provided encounter_id: {encounter_id}")
                # Get patient info if we have patient_id
                if patient_id:
                    patient_name = f"Patient {patient_id}"
                else:
                    patient_name = "Patient (ID from encounter)"
            else:
                # Find patient if not provided directly
                if not patient_id and patient_lastname:
                    patient = workflow.find_patient(patient_lastname)
                    patient_id = patient["patientid"]
                    patient_name = f"{patient.get('firstname', '')} {patient.get('lastname', '')}"
                elif patient_id:
                    patient_name = f"Patient {patient_id}"
                else:
                    return [
                        TextContent(
                            type="text",
                            text="❌ Error: Must provide either encounter_id, patientid, or patient_lastname",
                        )
                    ]

                # Get active encounter
                encounter = workflow.get_active_encounter(patient_id)
                encounter_id = encounter["encounterid"]

            # Get diagnosis details - either from key or direct codes
            if diagnosis_key and diagnosis_key in DIAGNOSIS_MAPPINGS:
                diagnosis = DIAGNOSIS_MAPPINGS[diagnosis_key]
                snomed_code = diagnosis["snomed"]
                icd10_code = diagnosis["icd10"]
                description = diagnosis["description"]
            elif snomed_code and icd10_code:
                description = f"SNOMED: {snomed_code}, ICD-10: {icd10_code}"
            else:
                available = ", ".join(DIAGNOSIS_MAPPINGS.keys())
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Must provide either diagnosis_key or both snomed_code and icd10_code. Available keys: {available}",
                    )
                ]

            # Add diagnosis to encounter
            workflow.add_diagnosis(
                encounter_id,
                snomed_code,
                icd10_code,
                note=""
            )
            return [
                TextContent(
                    type="text",
                    text=f"✅ **Diagnosis Added Successfully**\n\nPatient: {patient_name} (ID: {patient_id})\nEncounter ID: {encounter_id}\nDiagnosis: {description}\nSNOMED Code: {snomed_code}\nICD-10 Code: {icd10_code}\n{f'Notes: {note}' if note else ''}",
                )
            ]

        except ValueError as e:
            logger.error(f"Patient or encounter not found: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}",
                )
            ]
        except Exception as e:
            logger.error(f"Error adding diagnosis: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: Unable to add diagnosis. {str(e)}",
                )
            ]

    elif name == "create_referral":
        # Support encounter_id, patientid, or patient_lastname
        encounter_id = arguments.get("encounter_id")
        patient_id = arguments.get("patientid")
        encounter_id = arguments.get("encounterid")  # Optional
        patient_lastname = arguments.get("patient_lastname")
        # Support both ordertypeid and referral_type_id
        order_type_id = arguments.get("ordertypeid") or arguments.get("referral_type_id")
        # Support both diagnosis_key and diagnosis_snomed_code
        diagnosis_key = arguments.get("diagnosis_key")
        diagnosis_snomed_code = arguments.get("diagnosis_snomed_code")
        provider_note = arguments.get("provider_note", "")
        reason_for_referral = arguments.get("reason_for_referral", "")

        logger.info(f"Creating referral - encounter_id: {encounter_id}, patient_id: {patient_id}, patient_lastname: {patient_lastname}")

        if not ATHENA_AVAILABLE:
            return [
                TextContent(
                    type="text",
                    text="⚠️ Athena API not available. Unable to create referral.",
                )
            ]

        try:
            workflow = AthenaWorkflow()

            # If encounter_id is provided, use it directly (priority)
            if encounter_id:
                logger.info(f"Using provided encounter_id: {encounter_id}")
                # Get patient info if we have patient_id
                if patient_id:
                    patient_name = f"Patient {patient_id}"
                else:
                    patient_name = "Patient (ID from encounter)"
            else:
                # Find patient if not provided directly
                if not patient_id and patient_lastname:
                    patient = workflow.find_patient(patient_lastname)
                    patient_id = patient["patientid"]
                    patient_name = f"{patient.get('firstname', '')} {patient.get('lastname', '')}"
                elif patient_id:
                    patient_name = f"Patient {patient_id}"
                else:
                    return [
                        TextContent(
                            type="text",
                            text="❌ Error: Must provide either encounter_id, patientid, or patient_lastname",
                        )
                    ]

                # Get active encounter
                encounter = workflow.get_active_encounter(patient_id)
                encounter_id = encounter["encounterid"]

            # Get diagnosis SNOMED code - either from key or direct
            if diagnosis_key and diagnosis_key in DIAGNOSIS_MAPPINGS:
                diagnosis = DIAGNOSIS_MAPPINGS[diagnosis_key]
                snomed_code = diagnosis["snomed"]
                description = diagnosis["description"]
            elif diagnosis_snomed_code:
                snomed_code = diagnosis_snomed_code
                description = f"SNOMED: {snomed_code}"
            else:
                available = ", ".join(DIAGNOSIS_MAPPINGS.keys())
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Must provide either diagnosis_key or diagnosis_snomed_code. Available keys: {available}",
                    )
                ]

            if not order_type_id:
                return [
                    TextContent(
                        type="text",
                        text="❌ Error: Must provide ordertypeid or referral_type_id",
                    )
                ]

            # Create referral order
            referral_result = workflow.create_referral_order(
                encounter_id,
                order_type_id,
                snomed_code,
                provider_note=provider_note or f"Referral for {diagnosis_key if diagnosis_key else 'specialist consultation'}",
                reason_for_referral=reason_for_referral or description
            )

            # Extract order ID from result - handle different response formats
            referral_id = "N/A"
            if isinstance(referral_result, list) and len(referral_result) > 0:
                referral_id = referral_result[0].get("orderid", "N/A")
            elif isinstance(referral_result, dict):
                referral_id = referral_result.get("orderid", referral_result.get("id", "N/A"))

            return [
                TextContent(
                    type="text",
                    text=f"✅ **Referral Created Successfully**\n\nPatient: {patient_name} (ID: {patient_id})\nEncounter ID: {encounter_id}\nReferral Order ID: {referral_id}\nDiagnosis: {description}\nOrder Type ID: {order_type_id}\n{f'Provider Note: {provider_note}' if provider_note else ''}\n{f'Reason: {reason_for_referral}' if reason_for_referral else ''}",
                )
            ]

        except ValueError as e:
            logger.error(f"Patient or encounter not found: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}",
                )
            ]
        except Exception as e:
            logger.error(f"Error creating referral: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: Unable to create referral. {str(e)}",
                )
            ]

    elif name == "list_patient_diagnoses":
        # Support both patientid (direct) and patient_lastname (search)
        patient_id = arguments.get("patientid")
        encounter_id = arguments.get("encounterid")  # Optional
        patient_lastname = arguments.get("patient_lastname")

        logger.info(f"Listing diagnoses for patient: {patient_id or patient_lastname}")

        if not ATHENA_AVAILABLE:
            return [
                TextContent(
                    type="text",
                    text="⚠️ Athena API not available. Unable to list diagnoses.",
                )
            ]

        try:
            workflow = AthenaWorkflow()

            # Find patient if not provided directly
            if not patient_id and patient_lastname:
                patient = workflow.find_patient(patient_lastname)
                patient_id = patient["patientid"]
                patient_name = f"{patient.get('firstname', '')} {patient.get('lastname', '')}"
            elif patient_id:
                patient_name = f"Patient {patient_id}"
            else:
                return [
                    TextContent(
                        type="text",
                        text="❌ Error: Must provide either patientid or patient_lastname",
                    )
                ]

            # Get encounter ID - either from parameter or find active encounter
            if not encounter_id:
                encounter = workflow.get_active_encounter(patient_id)
                encounter_id = encounter["encounterid"]
                logger.info(f"Found active encounter: {encounter_id}")

            # Get diagnoses for the encounter
            diagnoses = workflow.get_encounter_diagnoses(encounter_id)

            if not diagnoses:
                return [
                    TextContent(
                        type="text",
                        text=f"📋 **No diagnoses found**\n\nPatient: {patient_name} (ID: {patient_id})\nEncounter ID: {encounter_id}\n\nNo diagnoses have been added to this encounter yet.",
                    )
                ]

            # Format diagnosis list - simple format with just SNOMED and name
            diagnosis_list = []
            diagnosis_list.append(f"📋 **Diagnoses for {patient_name} (ID: {patient_id})**\n")

            for idx, diagnosis in enumerate(diagnoses, 1):
                snomed = diagnosis.get('snomedcode', 'N/A')

                # Try to find name from our DIAGNOSIS_MAPPINGS
                # Convert snomed to string for comparison since API returns it as int
                name = None
                snomed_str = str(snomed)
                for key, mapping in DIAGNOSIS_MAPPINGS.items():
                    if mapping['snomed'] == snomed_str:
                        name = mapping['description']
                        break

                # Fallback to API response description field
                if not name:
                    name = diagnosis.get('description', 'Unknown diagnosis')

                diagnosis_list.append(f"{idx}. SNOMED {snomed} - {name}")

            return [
                TextContent(
                    type="text",
                    text="\n".join(diagnosis_list),
                )
            ]

        except ValueError as e:
            logger.error(f"Patient or encounter not found: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}",
                )
            ]
        except Exception as e:
            logger.error(f"Error listing diagnoses: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: Unable to list diagnoses. {str(e)}",
                )
            ]

    elif name == "list_patient_referrals":
        # Support both patientid (direct) and patient_lastname (search)
        patient_id = arguments.get("patientid")
        encounter_id = arguments.get("encounterid")  # Optional
        patient_lastname = arguments.get("patient_lastname")

        logger.info(f"Listing referrals for patient: {patient_id or patient_lastname}")

        if not ATHENA_AVAILABLE:
            return [
                TextContent(
                    type="text",
                    text="⚠️ Athena API not available. Unable to list referrals.",
                )
            ]

        try:
            workflow = AthenaWorkflow()

            # Find patient if not provided directly
            if not patient_id and patient_lastname:
                patient = workflow.find_patient(patient_lastname)
                patient_id = patient["patientid"]
                patient_name = f"{patient.get('firstname', '')} {patient.get('lastname', '')}"
            elif patient_id:
                patient_name = f"Patient {patient_id}"
            else:
                return [
                    TextContent(
                        type="text",
                        text="❌ Error: Must provide either patientid or patient_lastname",
                    )
                ]

            # Get encounter ID - either from parameter or find active encounter
            if not encounter_id:
                encounter = workflow.get_active_encounter(patient_id)
                encounter_id = encounter["encounterid"]
                logger.info(f"Found active encounter: {encounter_id}")

            # Get all orders for the encounter
            orders_response = workflow.get_encounter_orders(encounter_id)

            # Flatten nested orders structure - API returns list of diagnosis groups, each with "orders" array
            all_orders = []
            for group in orders_response:
                if isinstance(group, dict) and 'orders' in group:
                    all_orders.extend(group['orders'])
                elif isinstance(group, dict):
                    # Single order without nesting
                    all_orders.append(group)

            # Filter for referral/consult orders only
            referrals = [order for order in all_orders if order.get('ordertype') == 'Consult']

            if not referrals:
                return [
                    TextContent(
                        type="text",
                        text=f"📋 **No referrals found**\n\nPatient: {patient_name} (ID: {patient_id})\nEncounter ID: {encounter_id}\n\nNo referral orders have been created for this encounter yet.",
                    )
                ]

            # Format referral list - simple format
            referral_list = []
            referral_list.append(f"📋 **Referrals for {patient_name} (ID: {patient_id})**\n")

            for idx, referral in enumerate(referrals, 1):
                order_id = referral.get('orderid', 'N/A')
                order_type = referral.get('ordertypename', 'Unknown')
                status = referral.get('status', 'N/A')

                # Get diagnosis info
                diagnosis_list = referral.get('diagnosislist', [])
                if diagnosis_list and len(diagnosis_list) > 0:
                    diag_info = diagnosis_list[0].get('diagnosiscode', {})
                    snomed = diag_info.get('code', 'N/A')
                    diag_desc = diag_info.get('description', 'Unknown')
                else:
                    snomed = 'N/A'
                    diag_desc = 'Unknown'

                referral_list.append(f"{idx}. Order ID {order_id} - {order_type}")
                referral_list.append(f"   Status: {status}")
                referral_list.append(f"   Diagnosis: SNOMED {snomed} - {diag_desc}")

            return [
                TextContent(
                    type="text",
                    text="\n".join(referral_list),
                )
            ]

        except ValueError as e:
            logger.error(f"Patient or encounter not found: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}",
                )
            ]
        except Exception as e:
            logger.error(f"Error listing referrals: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error: Unable to list referrals. {str(e)}",
                )
            ]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    logger.info("Starting Referral MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
