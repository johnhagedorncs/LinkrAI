"""Messaging MCP server for SMS communication with appointment scheduling.

This MCP server provides tools for sending SMS messages to users and receiving
their responses, with persistent state management for long-running conversations.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("messaging-mcp-server")

# Create an MCP server
app = Server("messaging-server")

# State directory for persistent conversation storage
STATE_DIR = Path(__file__).parent / "message_state"
STATE_DIR.mkdir(exist_ok=True)

# Mock SMS storage (simulates SMS gateway)
SMS_STORAGE_FILE = STATE_DIR / "sms_messages.json"


class MessageState:
    """Manages persistent state for SMS conversations."""

    def __init__(self, state_dir: Path = STATE_DIR):
        self.state_dir = state_dir
        self.state_dir.mkdir(exist_ok=True)
        self.phone_index_file = self.state_dir / "phone_index.json"

    def save_conversation(self, conversation_id: str, data: dict):
        """Save conversation state to disk and update phone number index."""
        file_path = self.state_dir / f"{conversation_id}.json"
        data["last_updated"] = datetime.now().isoformat()
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved conversation state: {conversation_id}")

        # Update phone number index for incoming message lookup
        if "phone_number" in data:
            self._update_phone_index(data["phone_number"], conversation_id)

    def _update_phone_index(self, phone_number: str, conversation_id: str):
        """Update phone number to conversation ID mapping."""
        index = {}
        if self.phone_index_file.exists():
            with open(self.phone_index_file, 'r') as f:
                index = json.load(f)

        index[phone_number] = conversation_id

        with open(self.phone_index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def find_conversation_by_phone(self, phone_number: str) -> Optional[dict]:
        """Find active conversation for a phone number."""
        if not self.phone_index_file.exists():
            return None

        with open(self.phone_index_file, 'r') as f:
            index = json.load(f)

        conversation_id = index.get(phone_number)
        if conversation_id:
            return self.load_conversation(conversation_id)

        return None

    def load_conversation(self, conversation_id: str) -> Optional[dict]:
        """Load conversation state from disk."""
        file_path = self.state_dir / f"{conversation_id}.json"
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return None

    def delete_conversation(self, conversation_id: str):
        """Delete conversation state and remove from phone index."""
        file_path = self.state_dir / f"{conversation_id}.json"
        if file_path.exists():
            # Load conversation to get phone number
            conv_data = self.load_conversation(conversation_id)

            # Delete conversation file
            file_path.unlink()
            logger.info(f"Deleted conversation state: {conversation_id}")

            # Remove from phone index
            if conv_data and "phone_number" in conv_data:
                self._remove_from_phone_index(conv_data["phone_number"])

    def _remove_from_phone_index(self, phone_number: str):
        """Remove phone number from index."""
        if not self.phone_index_file.exists():
            return

        with open(self.phone_index_file, 'r') as f:
            index = json.load(f)

        if phone_number in index:
            del index[phone_number]

            with open(self.phone_index_file, 'w') as f:
                json.dump(index, f, indent=2)


class MockSMSGateway:
    """Mock SMS gateway for testing and demonstration."""

    def __init__(self, storage_file: Path = SMS_STORAGE_FILE):
        self.storage_file = storage_file
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure SMS storage file exists."""
        if not self.storage_file.exists():
            self._save_messages([])

    def _load_messages(self) -> list[dict]:
        """Load all SMS messages from storage."""
        with open(self.storage_file, "r") as f:
            return json.load(f)

    def _save_messages(self, messages: list[dict]):
        """Save all SMS messages to storage."""
        with open(self.storage_file, "w") as f:
            json.dump(messages, f, indent=2)

    def send_sms(self, phone_number: str, message: str, conversation_id: str) -> dict:
        """Send an SMS message (mock)."""
        messages = self._load_messages()

        message_id = f"msg_{len(messages) + 1}_{conversation_id}"
        sms_record = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "phone_number": phone_number,
            "message": message,
            "direction": "outbound",
            "timestamp": datetime.now().isoformat(),
            "status": "sent",
            "response": None,
            "response_timestamp": None
        }

        messages.append(sms_record)
        self._save_messages(messages)

        logger.info(f"Sent SMS to {phone_number}: {message_id}")
        return sms_record

    def check_response(self, conversation_id: str) -> Optional[dict]:
        """Check if there's a response for a conversation."""
        messages = self._load_messages()

        for msg in reversed(messages):
            if msg["conversation_id"] == conversation_id and msg["direction"] == "outbound":
                if msg["response"] is not None:
                    return {
                        "message_id": msg["message_id"],
                        "response": msg["response"],
                        "timestamp": msg["response_timestamp"]
                    }
                else:
                    return None

        return None

    def simulate_user_response(self, conversation_id: str, response: str) -> bool:
        """Simulate a user response (for testing)."""
        messages = self._load_messages()

        for msg in reversed(messages):
            if msg["conversation_id"] == conversation_id and msg["direction"] == "outbound":
                if msg["response"] is None:
                    msg["response"] = response
                    msg["response_timestamp"] = datetime.now().isoformat()
                    self._save_messages(messages)
                    logger.info(f"User responded to {conversation_id}: {response}")
                    return True

        logger.warning(f"No pending message found for conversation: {conversation_id}")
        return False


# Initialize global instances
message_state = MessageState()

# Initialize SMS gateway with multi-provider support
# Priority: Twilio > AWS > Mock (based on environment variables)
try:
    from aws_sms_gateway import create_unified_gateway
    sms_gateway = create_unified_gateway()
    logger.info(f"Initialized unified SMS gateway (provider: {sms_gateway.provider_name})")
except Exception as e:
    logger.warning(f"Failed to initialize unified gateway: {e}, falling back to Mock")
    sms_gateway = MockSMSGateway()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available messaging tools."""
    return [
        Tool(
            name="send_appointment_sms",
            description="Send SMS to user with available appointment slots and wait for their response",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "User's phone number (e.g., '+1234567890')",
                    },
                    "appointment_slots": {
                        "type": "array",
                        "description": "List of available appointment slots",
                        "items": {
                            "type": "object",
                            "properties": {
                                "slot_number": {"type": "integer"},
                                "date": {"type": "string"},
                                "time": {"type": "string"},
                                "provider": {"type": "string"},
                                "cost_estimate": {"type": "string"}
                            }
                        }
                    },
                    "cost_estimate": {
                        "type": "string",
                        "description": "Overall cost estimate for the procedure",
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Unique conversation identifier for tracking",
                    }
                },
                "required": ["phone_number", "appointment_slots", "conversation_id"],
            },
        ),
        Tool(
            name="check_sms_response",
            description="Check if user has responded to the appointment SMS",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID to check for response",
                    }
                },
                "required": ["conversation_id"],
            },
        ),
        Tool(
            name="simulate_user_sms_response",
            description="Simulate a user SMS response for testing purposes (reply with slot number or 'NONE')",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID to respond to",
                    },
                    "response": {
                        "type": "string",
                        "description": "User's response (e.g., '1' for slot 1, 'NONE' for no slots work)",
                    }
                },
                "required": ["conversation_id", "response"],
            },
        ),
        Tool(
            name="get_conversation_state",
            description="Get the current state of a conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID to retrieve",
                    }
                },
                "required": ["conversation_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for messaging operations."""

    if name == "send_appointment_sms":
        phone_number = arguments["phone_number"]
        appointment_slots = arguments["appointment_slots"]
        conversation_id = arguments["conversation_id"]
        cost_estimate = arguments.get("cost_estimate", "TBD")

        # Format SMS message
        message_lines = [
            "🏥 Appointment Slots Available",
            "",
            f"Estimated Cost: {cost_estimate}",
            "",
            "Available Times:"
        ]

        for slot in appointment_slots:
            slot_num = slot.get("slot_number", 0)
            date = slot.get("date", "TBD")
            time = slot.get("time", "TBD")
            provider = slot.get("provider", "TBD")
            message_lines.append(f"{slot_num}. {date} at {time} - Dr. {provider}")

        message_lines.extend([
            "",
            "Reply with:",
            "- Slot number (1, 2, 3) to confirm",
            "- NONE if no slots work"
        ])

        sms_message = "\n".join(message_lines)

        # Send SMS via mock gateway
        sms_record = sms_gateway.send_sms(phone_number, sms_message, conversation_id)

        # Save conversation state
        conversation_state = {
            "conversation_id": conversation_id,
            "phone_number": phone_number,
            "appointment_slots": appointment_slots,
            "cost_estimate": cost_estimate,
            "message_id": sms_record["message_id"],
            "status": "awaiting_response",
            "created_at": datetime.now().isoformat()
        }
        message_state.save_conversation(conversation_id, conversation_state)

        result_text = (
            f"✅ SMS sent successfully!\n\n"
            f"To: {phone_number}\n"
            f"Message ID: {sms_record['message_id']}\n"
            f"Conversation ID: {conversation_id}\n\n"
            f"Message:\n{sms_message}\n\n"
            f"⏳ Use 'check_sms_response' to check for user's reply.\n"
            f"💡 For testing, use 'simulate_user_sms_response' to send a mock reply."
        )

        return [TextContent(type="text", text=result_text)]

    elif name == "check_sms_response":
        conversation_id = arguments["conversation_id"]

        # Check for response
        response = sms_gateway.check_response(conversation_id)

        if response is None:
            return [TextContent(
                type="text",
                text=f"⏳ No response yet for conversation: {conversation_id}\n\n"
                     f"The user has not replied to the SMS. Check again later or use "
                     f"'simulate_user_sms_response' to test with a mock reply."
            )]

        # Load conversation state
        conv_state = message_state.load_conversation(conversation_id)
        if not conv_state:
            return [TextContent(
                type="text",
                text=f"❌ Conversation state not found: {conversation_id}"
            )]

        user_response = response["response"].strip().upper()

        # Parse user response
        result_text = (
            f"✅ User responded!\n\n"
            f"Conversation ID: {conversation_id}\n"
            f"Response: {response['response']}\n"
            f"Timestamp: {response['timestamp']}\n\n"
        )

        # Check if user selected a slot
        try:
            slot_number = int(user_response)
            # Find the selected slot
            selected_slot = None
            for slot in conv_state["appointment_slots"]:
                if slot.get("slot_number") == slot_number:
                    selected_slot = slot
                    break

            if selected_slot:
                result_text += (
                    f"📅 User confirmed slot #{slot_number}:\n"
                    f"  Date: {selected_slot.get('date')}\n"
                    f"  Time: {selected_slot.get('time')}\n"
                    f"  Provider: {selected_slot.get('provider')}\n\n"
                    f"➡️ Next: Book this appointment with the scheduling agent"
                )

                # Update conversation state
                conv_state["status"] = "slot_confirmed"
                conv_state["selected_slot"] = selected_slot
                message_state.save_conversation(conversation_id, conv_state)
            else:
                result_text += f"⚠️ Invalid slot number: {slot_number}"

        except ValueError:
            # User responded with text (likely "NONE")
            if user_response == "NONE":
                result_text += (
                    f"❌ User declined all slots\n\n"
                    f"➡️ Next: Request more appointment slots from scheduling agent"
                )

                # Update conversation state
                conv_state["status"] = "slots_declined"
                message_state.save_conversation(conversation_id, conv_state)
            else:
                result_text += f"⚠️ Unrecognized response: {user_response}"

        return [TextContent(type="text", text=result_text)]

    elif name == "simulate_user_sms_response":
        conversation_id = arguments["conversation_id"]
        response = arguments["response"]

        success = sms_gateway.simulate_user_response(conversation_id, response)

        if success:
            result_text = (
                f"✅ Simulated user response\n\n"
                f"Conversation ID: {conversation_id}\n"
                f"Response: {response}\n\n"
                f"Use 'check_sms_response' to process this response."
            )
        else:
            result_text = (
                f"❌ Failed to simulate response\n\n"
                f"No pending outbound message found for conversation: {conversation_id}"
            )

        return [TextContent(type="text", text=result_text)]

    elif name == "get_conversation_state":
        conversation_id = arguments["conversation_id"]

        conv_state = message_state.load_conversation(conversation_id)

        if not conv_state:
            return [TextContent(
                type="text",
                text=f"❌ No conversation found with ID: {conversation_id}"
            )]

        result_text = (
            f"📋 Conversation State\n\n"
            f"ID: {conv_state['conversation_id']}\n"
            f"Phone: {conv_state['phone_number']}\n"
            f"Status: {conv_state['status']}\n"
            f"Created: {conv_state['created_at']}\n"
            f"Last Updated: {conv_state.get('last_updated', 'N/A')}\n\n"
            f"Appointment Slots: {len(conv_state['appointment_slots'])}\n"
        )

        if conv_state.get("selected_slot"):
            slot = conv_state["selected_slot"]
            result_text += (
                f"\nSelected Slot:\n"
                f"  Date: {slot.get('date')}\n"
                f"  Time: {slot.get('time')}\n"
                f"  Provider: {slot.get('provider')}\n"
            )

        return [TextContent(type="text", text=result_text)]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    logger.info("Starting Messaging MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())