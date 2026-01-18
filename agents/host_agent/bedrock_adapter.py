"""
Bedrock LLM Adapter for Google ADK
Allows Google ADK Agent to use AWS Bedrock models (Claude) instead of Gemini
"""
import os
import json
from typing import AsyncGenerator, Any, Dict, List, Optional
import boto3
from google.genai import types as genai_types
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


class BedrockLlm(BaseLlm):
    """AWS Bedrock LLM that implements Google ADK's BaseLlm interface"""

    def __init__(self, model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0", **data):
        # Call parent constructor with model name
        super().__init__(model=model_id, **data)
        # Initialize bedrock client after pydantic validation
        self._bedrock_client = None

    @property
    def bedrock(self):
        """Lazy initialization of Bedrock client"""
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
        return self._bedrock_client

    def _convert_adk_to_bedrock_messages(self, adk_content: List[genai_types.Content]) -> List[Dict]:
        """Convert Google ADK message format to Bedrock format"""
        bedrock_messages = []

        for content in adk_content:
            role = "user" if content.role == "user" else "assistant"

            # Handle parts
            message_parts = []
            for part in content.parts:
                if hasattr(part, 'text') and part.text:
                    message_parts.append({"text": part.text})
                elif hasattr(part, 'function_call') and part.function_call:
                    # Tool use in Bedrock format
                    message_parts.append({
                        "toolUse": {
                            "toolUseId": part.function_call.id or "tool_" + str(hash(part.function_call.name)),
                            "name": part.function_call.name,
                            "input": part.function_call.args or {}
                        }
                    })
                elif hasattr(part, 'function_response') and part.function_response:
                    # Tool result in Bedrock format
                    message_parts.append({
                        "toolResult": {
                            "toolUseId": part.function_response.id,
                            "content": [{"text": str(part.function_response.response)}]
                        }
                    })

            if message_parts:
                bedrock_messages.append({
                    "role": role,
                    "content": message_parts
                })

        return bedrock_messages

    def _convert_adk_tools_to_bedrock(self, adk_tools: List[genai_types.Tool]) -> List[Dict]:
        """Convert Google ADK tool definitions to Bedrock format"""
        bedrock_tools = []

        for tool in adk_tools:
            if hasattr(tool, 'function_declarations') and tool.function_declarations:
                for func_decl in tool.function_declarations:
                    # Convert Google ADK Schema to JSON schema dict
                    input_schema = self._schema_to_json(func_decl.parameters) if func_decl.parameters else {}

                    # Convert function declaration to Bedrock tool spec
                    tool_def = {
                        "toolSpec": {
                            "name": func_decl.name,
                            "description": func_decl.description or "",
                            "inputSchema": {
                                "json": input_schema
                            }
                        }
                    }
                    bedrock_tools.append(tool_def)

        return bedrock_tools

    def _schema_to_json(self, schema: Any) -> Dict:
        """Convert Google ADK Schema object to JSON schema dict"""
        if isinstance(schema, dict):
            return schema

        # If it's a Schema object, extract its properties
        if hasattr(schema, 'type'):
            result = {}

            # Map the type
            if schema.type:
                type_mapping = {
                    'OBJECT': 'object',
                    'STRING': 'string',
                    'INTEGER': 'integer',
                    'NUMBER': 'number',
                    'BOOLEAN': 'boolean',
                    'ARRAY': 'array'
                }
                result['type'] = type_mapping.get(str(schema.type).split('.')[-1], 'object')

            # Add properties if present
            if hasattr(schema, 'properties') and schema.properties:
                result['properties'] = {}
                for prop_name, prop_schema in schema.properties.items():
                    result['properties'][prop_name] = self._schema_to_json(prop_schema)

            # Add required fields
            if hasattr(schema, 'required') and schema.required:
                result['required'] = schema.required

            # Add description
            if hasattr(schema, 'description') and schema.description:
                result['description'] = schema.description

            return result

        return {}

    def _convert_bedrock_to_adk_response(self, bedrock_response: Dict) -> genai_types.Content:
        """Convert Bedrock response to Google ADK format"""
        parts = []

        # Handle content blocks from Bedrock
        for block in bedrock_response.get('content', []):
            if 'text' in block:
                parts.append(genai_types.Part(text=block['text']))
            elif 'toolUse' in block:
                # Convert to ADK function call format
                tool_use = block['toolUse']
                parts.append(genai_types.Part(
                    function_call=genai_types.FunctionCall(
                        id=tool_use['toolUseId'],
                        name=tool_use['name'],
                        args=tool_use.get('input', {})
                    )
                ))

        return genai_types.Content(
            role='model',
            parts=parts
        )

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        """
        Main method that ADK calls - translates ADK request to Bedrock

        Args:
            llm_request: The LlmRequest object from ADK
            stream: Whether to stream the response (not yet supported)

        Yields:
            LlmResponse objects containing the model's response
        """
        # Convert messages
        bedrock_messages = self._convert_adk_to_bedrock_messages(llm_request.contents)

        # Build request
        request = {
            "modelId": self.model,
            "messages": bedrock_messages,
        }

        # Add system instruction if provided
        if llm_request.config and llm_request.config.system_instruction:
            system_text = llm_request.config.system_instruction
            if isinstance(system_text, str):
                request["system"] = [{"text": system_text}]

        # Add tools if provided
        if llm_request.config and llm_request.config.tools:
            bedrock_tools = self._convert_adk_tools_to_bedrock(llm_request.config.tools)
            if bedrock_tools:
                request["toolConfig"] = {"tools": bedrock_tools}

        # Call Bedrock (synchronous call, but we're in async context)
        try:
            response = self.bedrock.converse(**request)

            # Convert response to ADK format
            adk_content = self._convert_bedrock_to_adk_response(response['output']['message'])

            # Create LlmResponse
            llm_response = LlmResponse(
                content=adk_content,
                finish_reason=response.get('stopReason'),
                usage_metadata=genai_types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=response.get('usage', {}).get('inputTokens', 0),
                    candidates_token_count=response.get('usage', {}).get('outputTokens', 0),
                    total_token_count=(
                        response.get('usage', {}).get('inputTokens', 0) +
                        response.get('usage', {}).get('outputTokens', 0)
                    )
                )
            )

            yield llm_response

        except Exception as e:
            # Return error response
            error_response = LlmResponse(
                error_code="BEDROCK_ERROR",
                error_message=str(e)
            )
            yield error_response


def create_bedrock_model(model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0") -> BedrockLlm:
    """
    Factory function to create a Bedrock LLM that works with Google ADK

    Usage in routing_agent.py:
        from bedrock_adapter import create_bedrock_model

        return Agent(
            model=create_bedrock_model('us.anthropic.claude-haiku-4-5-20251001-v1:0'),
            name='Routing_agent',
            ...
        )
    """
    return BedrockLlm(model_id=model_id)