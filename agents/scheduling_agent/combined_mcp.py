"""Combined MCP module that exposes both scheduling and messaging tools.

This module combines tools from:
1. scheduling_mcp - Athena appointment search and booking
2. messaging/messaging_mcp - Twilio SMS communication

The combined tool set allows the scheduling agent to handle the complete
SMS-based appointment scheduling workflow.
"""

import logging
from mcp.types import Tool, TextContent

# Import both MCP modules
from . import scheduling_mcp
from .messaging import messaging_mcp

logger = logging.getLogger(__name__)


async def list_tools() -> list[Tool]:
    """List all available tools from both scheduling and messaging modules.

    Returns:
        Combined list of tools from scheduling_mcp and messaging_mcp
    """
    # Get tools from scheduling module
    scheduling_tools = await scheduling_mcp.list_tools()
    logger.info(f"Loaded {len(scheduling_tools)} tools from scheduling_mcp")

    # Get tools from messaging module
    messaging_tools = await messaging_mcp.list_tools()
    logger.info(f"Loaded {len(messaging_tools)} tools from messaging_mcp")

    # Combine and return
    all_tools = scheduling_tools + messaging_tools
    logger.info(f"Total tools available: {len(all_tools)}")

    # Log all tool names for debugging
    for tool in all_tools:
        logger.debug(f"  - {tool.name}")

    return all_tools


async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to the appropriate MCP module.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent responses
    """
    # Scheduling tools
    scheduling_tool_names = {
        'find_appointment_options_by_specialty',
        'find_athena_appointment_slots',
        'book_athena_appointment',
        'schedule_appointment_from_encounter'
    }

    # Messaging tools
    messaging_tool_names = {
        'send_appointment_sms',
        'check_sms_response',
        'simulate_patient_response',
        'get_conversation_state'
    }

    if name in scheduling_tool_names:
        logger.info(f"Routing tool call to scheduling_mcp: {name}")
        return await scheduling_mcp.call_tool(name, arguments)

    elif name in messaging_tool_names:
        logger.info(f"Routing tool call to messaging_mcp: {name}")
        return await messaging_mcp.call_tool(name, arguments)

    else:
        logger.error(f"Unknown tool: {name}")
        return [TextContent(
            type="text",
            text=f"Error: Unknown tool '{name}'. Available tools: {', '.join(scheduling_tool_names | messaging_tool_names)}"
        )]


# For standalone MCP server usage (if needed)
async def main():
    """Main entry point for standalone MCP server."""
    from mcp.server.stdio import stdio_server

    logger.info("Starting combined MCP server (scheduling + messaging)")

    # Use the app from scheduling_mcp as the base
    # (both modules use the same Server instance pattern)
    app = scheduling_mcp.app

    # Add messaging tools to the app
    # This is handled automatically through the list_tools and call_tool functions above

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
