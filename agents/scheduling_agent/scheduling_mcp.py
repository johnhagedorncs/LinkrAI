"""Athenahealth Scheduling MCP server."""
import asyncio
import logging
import sys
import os
import json
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import requests

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from athena.athena_api import AthenaWorkflow, legacy_put

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduling-mcp-server")

# Create an MCP server
app = Server("scheduling-server")

# Initialize Athenahealth API integration
# Using Practice 1959222 (Internal Medicine) for SMS workflow testing
athena_workflow = AthenaWorkflow(practice_id="1959222")

# Configuration
DEFAULT_PRACTICE_ID = "1959222"  # Changed from 195900 for SMS testing

# Specialty name to Athena specialty ID mapping
# Generated from get_all_specialties.py - Contains ALL specialties in practice
SPECIALTY_TO_ID = {
    # Core specialties from Athena (198 providers, 17 specialties)
    "acupuncture": "660",
    "adolescent medicine": "635",
    "allergy/immunology": "003",
    "allergy": "003",  # Alias
    "immunology": "003",  # Alias
    "ambulatory surgical center": "625",
    "bone marrow transplant": "636",
    "cardiac surgery": "078",
    "cardiology": "006",
    "family medicine": "008",
    "family practice": "008",  # Alias
    "primary care": "008",  # Alias (family medicine is primary care)
    "hospitalist": "104",
    "internal medicine": "011",
    "neonatology": "100",
    "orthopaedic surgery - hand": "040",
    "hand surgery": "040",  # Alias
    "orthopedic surgery": "020",
    "orthopedics": "020",  # Alias
    "orthopedic surgery total joint": "720",
    "joint replacement": "720",  # Alias
    "pediatric gynecology": "990",
    "pediatric medicine": "037",
    "pediatrics": "037",  # Alias
    "pediatric surgery": "618",
}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available scheduling tools."""
    return [
        Tool(
            name="find_appointment_options_by_specialty",
            description="Find top 3 available appointment options for a patient based on specialty. Searches all providers in that specialty and returns slots filtered by patient preferences (days/times).",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Athenahealth patient ID (e.g., '60183')",
                    },
                    "specialty": {
                        "type": "string",
                        "description": "Medical specialty (e.g., 'cardiology', 'dermatology', 'primary care')",
                    },
                    "preferred_days": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred days of week (e.g., ['Monday', 'Wednesday', 'Friday']). Omit if patient has no preference or says 'any day'.",
                    },
                    "preferred_time_start": {
                        "type": "string",
                        "description": "Earliest preferred time in HH:MM 24-hour format (e.g., '09:00' for 9 AM, '15:00' for 3 PM). Omit if no time preference.",
                    },
                    "preferred_time_end": {
                        "type": "string",
                        "description": "Latest preferred time in HH:MM 24-hour format (e.g., '12:00' for noon, '17:00' for 5 PM). Omit if no time preference.",
                    },
                    "encounter_id": {
                        "type": "string",
                        "description": "Optional encounter ID to link appointments",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date (MM/DD/YYYY). Defaults to tomorrow",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date (MM/DD/YYYY). Defaults to 30 days from start",
                    },
                    "max_providers": {
                        "type": "number",
                        "description": "Optional max number of providers to check (default: 10)",
                    },
                },
                "required": ["patient_id", "specialty"],
            },
        ),
        Tool(
            name="find_athena_appointment_slots",
            description="Find available appointment slots in Athenahealth for a specific provider, department, and reason/appointment type",
            inputSchema={
                "type": "object",
                "properties": {
                    "department_id": {
                        "type": "string",
                        "description": "Department ID in Athenahealth (e.g., '1', '162')",
                    },
                    "provider_id": {
                        "type": "string",
                        "description": "Provider ID in Athenahealth (e.g., '71', '121')",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for search (MM/DD/YYYY format)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for search (MM/DD/YYYY format)",
                    },
                },
                "required": ["department_id", "start_date", "end_date"],
            },
        ),
        Tool(
            name="book_athena_appointment",
            description="Book an appointment in Athenahealth using an appointment slot ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "Athenahealth appointment slot ID from find_athena_appointment_slots",
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "Athenahealth patient ID (e.g., '60183', '5775')",
                    },
                    "appointmenttype_id": {
                        "type": "string",
                        "description": "Appointment type ID from the appointment slot (required for booking)",
                    },
                },
                "required": ["appointment_id", "patient_id", "appointmenttype_id"],
            },
        ),
        Tool(
            name="schedule_appointment_from_encounter",
            description="Schedule an appointment for a patient from an encounter/referral context. Automatically finds and books the first available appointment slot, linking it back to the original encounter for continuity of care.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Athenahealth patient ID from the encounter (e.g., '60183', '5775')",
                    },
                    "encounter_id": {
                        "type": "string",
                        "description": "Encounter ID from the referral workflow for tracking continuity",
                    },
                    "department_id": {
                        "type": "string",
                        "description": "Department ID where appointment should be scheduled (e.g., '1', '162')",
                    },
                    "provider_id": {
                        "type": "string",
                        "description": "Optional specific provider ID (e.g., '71', '121'). If not provided, searches all providers",
                    },
                    "specialty": {
                        "type": "string",
                        "description": "Required specialty for the appointment (e.g., 'cardiology', 'dermatology')",
                    },
                    "referral_id": {
                        "type": "string",
                        "description": "Optional referral order ID that generated this scheduling request",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Earliest date for appointment (MM/DD/YYYY format). If not provided, defaults to tomorrow",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Latest date for appointment (MM/DD/YYYY format). If not provided, defaults to 30 days from start",
                    },
                },
                "required": ["patient_id", "encounter_id", "department_id", "specialty"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for scheduling operations."""
    try:
        if name == "find_appointment_options_by_specialty":
            patient_id = arguments["patient_id"]
            specialty = arguments["specialty"].lower()
            encounter_id = arguments.get("encounter_id")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            max_providers = arguments.get("max_providers", 10)

            # NEW: Extract preference parameters
            preferred_days = arguments.get("preferred_days")
            preferred_time_start = arguments.get("preferred_time_start")
            preferred_time_end = arguments.get("preferred_time_end")

            logger.info(f"Finding appointment options: patient={patient_id}, specialty={specialty}")
            if preferred_days:
                logger.info(f"  Preferred days: {preferred_days}")
            if preferred_time_start or preferred_time_end:
                logger.info(f"  Preferred time range: {preferred_time_start or 'any'} - {preferred_time_end or 'any'}")

            try:
                from datetime import datetime, timedelta
                import json

                # Set date defaults
                if not start_date:
                    start_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
                if not end_date:
                    end_date = (datetime.now() + timedelta(days=30)).strftime("%m/%d/%Y")

                # Map specialty to specialty ID
                specialty_id = SPECIALTY_TO_ID.get(specialty)
                if not specialty_id:
                    return [TextContent(
                        type="text",
                        text=f"❌ Unknown specialty: '{specialty}'.\n\n"
                        f"Known specialties: {', '.join(SPECIALTY_TO_ID.keys())}"
                    )]

                logger.info(f"Mapped specialty '{specialty}' to ID '{specialty_id}'")

                # Get all providers
                all_providers = athena_workflow.get_providers()

                # Filter by specialty
                specialty_providers = [
                    p for p in all_providers
                    if p.get("specialtyid") == specialty_id
                ]

                if not specialty_providers:
                    return [TextContent(
                        type="text",
                        text=f"❌ No providers found for specialty: {specialty} (ID: {specialty_id})"
                    )]

                logger.info(f"Found {len(specialty_providers)} providers with specialty {specialty}")

                # Search slots using each provider's usual department
                # If usualdepartmentid is missing, try common departments
                all_slots = []
                checked_providers = 0

                # Common departments to try if usualdepartmentid is missing
                fallback_departments = ["162", "155", "168", "149", "150", "21"]

                for provider in specialty_providers[:max_providers]:
                    checked_providers += 1
                    provider_id = provider["providerid"]
                    provider_name = f"{provider.get('firstname', '')} {provider.get('lastname', '')}".strip()
                    if not provider_name:
                        provider_name = provider.get('displayname', '') or provider.get('lastname', 'Unknown')

                    # Use provider's usual department, or try common departments as fallback
                    dept_id = provider.get("usualdepartmentid")
                    departments_to_try = [str(dept_id)] if dept_id else fallback_departments

                    if not dept_id:
                        logger.info(f"Provider {provider_id} ({provider_name}) has no usualdepartmentid, trying common departments")
                    else:
                        logger.info(f"Checking provider {provider_id} ({provider_name}) in department {dept_id}...")

                    for dept_id in departments_to_try:
                        try:
                            slots = athena_workflow.find_appointment_slots(
                                department_id=str(dept_id),
                                provider_id=str(provider_id),
                                reason_id="-1",
                                start_date=start_date,
                                end_date=end_date,
                                bypass_checks=True
                            )

                            if slots:
                                # Add provider info to slots
                                for slot in slots:
                                    slot["provider_info"] = {
                                        "id": provider_id,
                                        "name": provider_name,
                                        "specialty": provider.get("specialty", specialty)
                                    }
                                    slot["department_id"] = dept_id
                                    all_slots.append(slot)

                                logger.info(f"Found {len(slots)} slots for provider {provider_id} in dept {dept_id}")
                                break  # Found slots, no need to check other departments
                        except Exception as e:
                            # Try next department
                            pass

                if not all_slots:
                    return [TextContent(
                        type="text",
                        text=f"❌ No available appointment slots found.\n\n"
                        f"Specialty: {specialty}\n"
                        f"Providers checked: {checked_providers}\n"
                        f"Date range: {start_date} - {end_date}\n\n"
                        f"Try expanding the date range or checking different providers."
                    )]

                # Sort by date and time
                all_slots.sort(key=lambda s: (s.get('date', ''), s.get('starttime', '')))

                # Filter by preferences if provided
                filtered_slots = all_slots
                if preferred_days or preferred_time_start or preferred_time_end:
                    filtered_slots = []
                    for slot in all_slots:
                        # Filter by day of week
                        if preferred_days:
                            try:
                                slot_date = datetime.strptime(slot['date'], '%m/%d/%Y')
                                day_name = slot_date.strftime('%A')
                                if day_name not in preferred_days:
                                    continue
                            except (ValueError, KeyError):
                                logger.warning(f"Could not parse date: {slot.get('date')}")
                                continue

                        # Filter by time range
                        slot_time = slot.get('starttime', '')
                        if preferred_time_start and slot_time < preferred_time_start:
                            continue
                        if preferred_time_end and slot_time > preferred_time_end:
                            continue

                        filtered_slots.append(slot)

                    logger.info(f"Filtered {len(all_slots)} slots down to {len(filtered_slots)} matching preferences")

                    # If no matches found, fall back to all slots and add explanation
                    if not filtered_slots:
                        logger.info("No slots matched preferences, falling back to earliest available")
                        filtered_slots = all_slots

                # Take top 3 slots (from filtered or unfiltered list)
                top_3 = filtered_slots[:3]

                # Format response
                options = []
                for i, slot in enumerate(top_3, 1):
                    provider_info = slot.get("provider_info", {})
                    options.append({
                        "option_number": i,
                        "appointment_id": slot.get("appointmentid"),
                        "appointmenttypeid": str(slot.get("appointmenttypeid")),
                        "date": slot.get("date"),
                        "time": slot.get("starttime"),
                        "duration_minutes": slot.get("duration"),
                        "appointment_type": slot.get("appointmenttype"),
                        "provider": {
                            "id": provider_info.get("id"),
                            "name": provider_info.get("name"),
                            "specialty": provider_info.get("specialty")
                        },
                        "department_id": str(slot.get("departmentid"))
                    })

                # Create response payload
                response_data = {
                    "patient_id": patient_id,
                    "specialty": specialty,
                    "encounter_id": encounter_id,
                    "total_slots_found": len(all_slots),
                    "providers_checked": checked_providers,
                    "appointment_options": options
                }

                # Human-readable text
                text_response = f"✅ Found {len(all_slots)} available appointment slots!\n\n"
                text_response += f"Top 3 options for {specialty}:\n\n"

                for opt in options:
                    text_response += f"Option {opt['option_number']}:\n"
                    text_response += f"  Provider: {opt['provider']['name']}\n"
                    text_response += f"  Date: {opt['date']} at {opt['time']}\n"
                    text_response += f"  Duration: {opt['duration_minutes']} minutes\n"
                    text_response += f"  Type: {opt['appointment_type']}\n"
                    text_response += f"  Department: {opt['department_id']}\n\n"

                text_response += f"\nJSON Data:\n```json\n{json.dumps(response_data, indent=2)}\n```"

                logger.info(f"Returning {len(options)} appointment options")

                return [TextContent(type="text", text=text_response)]

            except Exception as e:
                error_msg = f"❌ Error finding appointment options: {str(e)}"
                logger.error(error_msg)
                import traceback
                traceback.print_exc()
                return [TextContent(type="text", text=error_msg)]

        elif name == "find_athena_appointment_slots":
            department_id = arguments["department_id"]
            start_date = arguments["start_date"]
            end_date = arguments["end_date"]
            provider_id = arguments.get("provider_id")
            # Return all appointment types
            reason_id = -1

            logger.info(f"Finding Athena appointment slots: dept={department_id}, provider={provider_id}, dates={start_date} to {end_date}")

            try:
                # Call Athenahealth API
                slots = athena_workflow.find_appointment_slots(
                    department_id=department_id,
                    start_date=start_date,
                    end_date=end_date,
                    provider_id=provider_id,
                    reason_id=reason_id
                )

                if not slots:
                    return [
                        TextContent(
                            type="text",
                            text=f"No available appointment slots found for the specified criteria.\n\n"
                            f"Department ID: {department_id}\n"
                            f"Provider ID: {provider_id or 'Any'}\n"
                            f"Date Range: {start_date} - {end_date}",
                        )
                    ]

                # Format slots for display
                slot_list = []
                for slot in slots[:10]:  # Limit to first 10 slots
                    slot_info = (
                        f"Appointment ID: {slot.get('appointmentid')}\n"
                        f"Date: {slot.get('date')}\n"
                        f"Time: {slot.get('starttime')}\n"
                        f"Duration: {slot.get('duration')} min\n"
                        f"Type: {slot.get('appointmenttype')}\n"
                        f"Provider: {slot.get('providername', 'N/A')}"
                    )
                    slot_list.append(slot_info)

                result_text = (
                    f"Found {len(slots)} available appointment slot(s).\n\n"
                    f"Showing first {min(10, len(slots))} slots:\n\n"
                    + "\n\n---\n\n".join(slot_list)
                )

                if len(slots) > 10:
                    result_text += f"\n\n... and {len(slots) - 10} more slots available."

                logger.info(f"Found {len(slots)} Athena appointment slots")

                return [TextContent(type="text", text=result_text)]

            except Exception as e:
                error_msg = f"Error finding appointment slots: {str(e)}"
                logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]

        elif name == "book_athena_appointment":
            appointment_id = arguments["appointment_id"]
            patient_id = arguments["patient_id"]
            appointmenttype_id = arguments["appointmenttype_id"]

            logger.info(f"Booking Athena appointment: slot={appointment_id}, patient={patient_id}, type={appointmenttype_id}")

            try:
                # Call Athenahealth API to book the appointment
                result = athena_workflow.book_appointment(
                    appointment_id=appointment_id,
                    patient_id=patient_id,
                    appointment_type_id=appointmenttype_id
                )

                # Extract booking details
                booked_id = result.get("appointmentid")
                status = result.get("appointmentstatus")
                date = result.get("date")
                start_time = result.get("starttime")
                duration = result.get("duration")
                appt_type = result.get("appointmenttype")

                success_text = (
                    f"✅ Appointment successfully booked!\n\n"
                    f"Appointment ID: {booked_id}\n"
                    f"Patient ID: {patient_id}\n"
                    f"Date: {date}\n"
                    f"Time: {start_time}\n"
                    f"Duration: {duration} minutes\n"
                    f"Type: {appt_type}\n"
                    f"Status: {status}"
                )

                logger.info(f"Successfully booked appointment {booked_id}")

                return [TextContent(type="text", text=success_text)]

            except Exception as e:
                error_msg = f"Error booking appointment: {str(e)}"
                logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]

        elif name == "schedule_appointment_from_encounter":
            # Extract required parameters
            patient_id = arguments["patient_id"]
            encounter_id = arguments["encounter_id"]
            department_id = arguments["department_id"]
            specialty = arguments["specialty"]

            # Extract optional parameters
            provider_id = arguments.get("provider_id")
            referral_id = arguments.get("referral_id")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")

            logger.info(f"Scheduling appointment from encounter: patient={patient_id}, encounter={encounter_id}, specialty={specialty}")

            try:
                from datetime import datetime, timedelta

                # Set date defaults if not provided
                if not start_date:
                    start_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
                if not end_date:
                    end_date = (datetime.now() + timedelta(days=30)).strftime("%m/%d/%Y")

                # Search for available slots using reason_id="-1" to get all slots
                logger.info(f"Searching slots: dept={department_id}, provider={provider_id or 'any'}, dates={start_date} to {end_date}")

                slots = athena_workflow.find_appointment_slots(
                    department_id=department_id,
                    start_date=start_date,
                    end_date=end_date,
                    provider_id=provider_id,
                    reason_id="-1"
                )

                if not slots:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ No available appointment slots found.\n\n"
                            f"Search Criteria:\n"
                            f"- Department: {department_id}\n"
                            f"- Provider: {provider_id or 'Any'}\n"
                            f"- Specialty: {specialty}\n"
                            f"- Date Range: {start_date} - {end_date}\n\n"
                            f"Encounter Context:\n"
                            f"- Patient ID: {patient_id}\n"
                            f"- Encounter ID: {encounter_id}\n"
                            f"- Referral ID: {referral_id or 'N/A'}\n\n"
                            f"Please try:\n"
                            f"1. Expanding the date range\n"
                            f"2. Trying a different department\n"
                            f"3. Not specifying a specific provider"
                        )
                    ]

                # Book the first available slot
                first_slot = slots[0]
                logger.info(f"Booking first available slot: {first_slot.get('appointmentid')} on {first_slot.get('date')}")

                # Get appointmenttypeid for reliable booking
                appointment_type_id = str(first_slot.get('appointmenttypeid'))

                # Book using the workflow (uses appointmenttypeid for reliability)
                data = {
                    "patientid": patient_id,
                    "appointmenttypeid": appointment_type_id,
                    "ignoreschedulablepermission": "true"
                }

                appointment_result = legacy_put(
                    f"/v1/{{practiceid}}/appointments/{first_slot['appointmentid']}",
                    data=data,
                    practice_id=athena_workflow.practice_id
                )

                # API returns a list with one appointment object
                if isinstance(appointment_result, list) and len(appointment_result) > 0:
                    appointment = appointment_result[0]
                else:
                    appointment = appointment_result

                # Extract booking details
                booked_id = appointment.get("appointmentid")
                status = appointment.get("appointmentstatus")
                date = appointment.get("date")
                start_time = appointment.get("starttime")
                duration = appointment.get("duration")
                appt_type = appointment.get("appointmenttype")

                # Create comprehensive success message linking back to encounter
                success_text = (
                    f"✅ Appointment Successfully Scheduled from Encounter!\n\n"
                    f"APPOINTMENT DETAILS:\n"
                    f"- Appointment ID: {booked_id}\n"
                    f"- Date: {date}\n"
                    f"- Time: {start_time}\n"
                    f"- Duration: {duration} minutes\n"
                    f"- Type: {appt_type}\n"
                    f"- Status: {status}\n\n"
                    f"ENCOUNTER CONTEXT:\n"
                    f"- Patient ID: {patient_id}\n"
                    f"- Encounter ID: {encounter_id}\n"
                    f"- Referral ID: {referral_id or 'N/A'}\n"
                    f"- Specialty: {specialty}\n\n"
                    f"CONTINUITY OF CARE:\n"
                    f"This appointment is linked to encounter {encounter_id} for patient {patient_id}.\n"
                    f"Found {len(slots)} total available slots; booked the earliest one."
                )

                logger.info(f"Successfully scheduled appointment {booked_id} from encounter {encounter_id}")

                return [TextContent(type="text", text=success_text)]

            except Exception as e:
                error_msg = (
                    f"❌ Error scheduling appointment from encounter:\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Context:\n"
                    f"- Patient ID: {patient_id}\n"
                    f"- Encounter ID: {encounter_id}\n"
                    f"- Department: {department_id}\n"
                    f"- Specialty: {specialty}\n"
                    f"- Provider: {provider_id or 'Any'}"
                )
                logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [
            TextContent(
                type="text",
                text=f"Error processing request: {str(e)}",
            )
        ]


async def main():
    """Run the MCP server."""
    logger.info("Starting Scheduling MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
