"""Shared Bedrock executor and utilities for A2A agents.

This module provides reusable components for building A2A agents that use
AWS Bedrock's Claude models instead of Google ADK.
"""

from .bedrock_executor import BedrockExecutor
from .bedrock_conversions import (
    convert_a2a_part_to_bedrock,
    convert_bedrock_content_to_a2a,
    create_bedrock_message,
    extract_text_from_bedrock_response,
)
from .mcp_to_bedrock import (
    create_bedrock_tools_from_mcp,
    mcp_tool_to_bedrock_tool,
)

__all__ = [
    'BedrockExecutor',
    'convert_a2a_part_to_bedrock',
    'convert_bedrock_content_to_a2a',
    'create_bedrock_message',
    'extract_text_from_bedrock_response',
    'create_bedrock_tools_from_mcp',
    'mcp_tool_to_bedrock_tool',
]
