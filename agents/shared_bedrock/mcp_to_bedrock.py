"""Utility to convert MCP tool definitions to Bedrock tool format.

This allows defining tools once in the MCP server and automatically
generating the Bedrock toolSpec format.
"""

import asyncio
import logging
from typing import Any

from mcp.types import Tool

logger = logging.getLogger(__name__)


def mcp_tool_to_bedrock_tool(mcp_tool: Tool) -> dict[str, Any]:
    return {
        'toolSpec': {
            'name': mcp_tool.name,
            'description': mcp_tool.description,
            'inputSchema': {
                'json': mcp_tool.inputSchema
            }
        }
    }


async def extract_tools_from_mcp(mcp_module) -> list[dict[str, Any]]:
    try:
        # Get the MCP server's list_tools function
        if hasattr(mcp_module, 'list_tools'):
            list_tools_func = mcp_module.list_tools
        elif hasattr(mcp_module, 'app') and hasattr(mcp_module.app, '_tool_handlers'):
            # For MCP servers using decorators, need to call the decorated function
            # The decorator stores the actual function, we need to call it
            mcp_tools = await mcp_module.list_tools()
        else:
            raise AttributeError(f"Module {mcp_module.__name__} has no list_tools function")

        # Get MCP tools
        mcp_tools = await list_tools_func()

        # Convert each MCP tool to Bedrock format
        bedrock_tools = [mcp_tool_to_bedrock_tool(tool) for tool in mcp_tools]

        logger.info(f"Extracted {len(bedrock_tools)} tools from MCP module")
        for tool in bedrock_tools:
            logger.debug(f"  - {tool['toolSpec']['name']}: {tool['toolSpec']['description']}")

        return bedrock_tools

    except Exception as e:
        logger.error(f"Error extracting tools from MCP module: {e}", exc_info=True)
        return []


def create_bedrock_tools_from_mcp(mcp_module) -> list[dict[str, Any]]:
    try:
        # Create event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Extract tools
        tools = loop.run_until_complete(extract_tools_from_mcp(mcp_module))
        return tools

    except Exception as e:
        logger.error(f"Error in synchronous tool extraction: {e}", exc_info=True)
        return []
