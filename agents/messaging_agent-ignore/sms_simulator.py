#!/usr/bin/env python3
"""CLI tool to simulate user SMS responses for testing.

This tool allows you to view pending SMS messages and simulate user responses
without needing a real SMS gateway.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import click


# Path to SMS storage
SMS_STORAGE_FILE = Path(__file__).parent / "message_state" / "sms_messages.json"


def load_messages():
    """Load SMS messages from storage."""
    if not SMS_STORAGE_FILE.exists():
        return []
    with open(SMS_STORAGE_FILE, 'r') as f:
        return json.load(f)


def save_messages(messages):
    """Save SMS messages to storage."""
    SMS_STORAGE_FILE.parent.mkdir(exist_ok=True)
    with open(SMS_STORAGE_FILE, 'w') as f:
        json.dump(messages, f, indent=2)


@click.group()
def cli():
    """SMS Simulator - View and respond to simulated SMS messages."""
    pass


@cli.command()
def list():
    """List all SMS messages (sent and responses)."""
    messages = load_messages()

    if not messages:
        click.echo("📭 No SMS messages found.")
        return

    click.echo(f"\n📱 SMS Messages ({len(messages)} total)\n")

    for msg in messages:
        status_icon = "✅" if msg.get("response") else "⏳"
        direction_icon = "📤" if msg["direction"] == "outbound" else "📥"

        click.echo(f"{status_icon} {direction_icon} {msg['message_id']}")
        click.echo(f"   Conversation: {msg['conversation_id']}")
        click.echo(f"   To: {msg['phone_number']}")
        click.echo(f"   Time: {msg['timestamp']}")
        click.echo(f"   Status: {msg['status']}")

        if msg.get("response"):
            click.echo(f"   ✉️  Response: {msg['response']} (at {msg['response_timestamp']})")
        else:
            click.echo(f"   ⏳ Awaiting response...")

        click.echo()


@cli.command()
@click.argument('conversation_id')
def view(conversation_id):
    """View SMS message for a specific conversation."""
    messages = load_messages()

    conversation_msgs = [
        msg for msg in messages
        if msg['conversation_id'] == conversation_id and msg['direction'] == 'outbound'
    ]

    if not conversation_msgs:
        click.echo(f"❌ No messages found for conversation: {conversation_id}")
        return

    msg = conversation_msgs[-1]  # Get most recent

    click.echo(f"\n📱 SMS Message\n")
    click.echo(f"Message ID: {msg['message_id']}")
    click.echo(f"Conversation ID: {msg['conversation_id']}")
    click.echo(f"To: {msg['phone_number']}")
    click.echo(f"Sent: {msg['timestamp']}")
    click.echo(f"Status: {msg['status']}")
    click.echo()
    click.echo("=" * 60)
    click.echo(msg['message'])
    click.echo("=" * 60)
    click.echo()

    if msg.get("response"):
        click.echo(f"✅ User responded: {msg['response']}")
        click.echo(f"   Time: {msg['response_timestamp']}")
    else:
        click.echo("⏳ No response yet")
    click.echo()


@cli.command()
@click.argument('conversation_id')
@click.argument('response')
def respond(conversation_id, response):
    """Simulate a user SMS response.

    CONVERSATION_ID: The conversation to respond to
    RESPONSE: User's response (e.g., '1' for slot 1, 'NONE' for no slots)
    """
    messages = load_messages()

    # Find the most recent outbound message for this conversation
    found = False
    for msg in reversed(messages):
        if (msg['conversation_id'] == conversation_id and
            msg['direction'] == 'outbound' and
            msg.get('response') is None):

            msg['response'] = response
            msg['response_timestamp'] = datetime.now().isoformat()
            found = True

            save_messages(messages)

            click.echo(f"\n✅ Simulated user response!")
            click.echo(f"   Conversation: {conversation_id}")
            click.echo(f"   Response: {response}")
            click.echo(f"\n💡 The messaging agent can now process this response using 'check_sms_response'")
            break

    if not found:
        click.echo(f"❌ No pending outbound message found for conversation: {conversation_id}")
        click.echo(f"\nEither:")
        click.echo(f"  - The conversation doesn't exist")
        click.echo(f"  - No SMS was sent yet")
        click.echo(f"  - User already responded")


@cli.command()
def pending():
    """List all messages awaiting user response."""
    messages = load_messages()

    pending_msgs = [
        msg for msg in messages
        if msg['direction'] == 'outbound' and msg.get('response') is None
    ]

    if not pending_msgs:
        click.echo("✅ No pending messages - all have been responded to!")
        return

    click.echo(f"\n⏳ Pending SMS Messages ({len(pending_msgs)})\n")

    for msg in pending_msgs:
        click.echo(f"📤 Conversation: {msg['conversation_id']}")
        click.echo(f"   To: {msg['phone_number']}")
        click.echo(f"   Sent: {msg['timestamp']}")
        click.echo(f"   Message ID: {msg['message_id']}")
        click.echo()
        click.echo(f"   To respond: python sms_simulator.py respond {msg['conversation_id']} <response>")
        click.echo()


@cli.command()
def clear():
    """Clear all SMS messages (for testing)."""
    if click.confirm("⚠️  This will delete all SMS messages. Continue?"):
        save_messages([])
        click.echo("✅ All SMS messages cleared!")


if __name__ == '__main__':
    cli()