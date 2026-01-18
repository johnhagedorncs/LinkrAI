"""Conversion functions between A2A protocol types and AWS Bedrock types.

This module provides utilities to convert between the A2A agent communication
protocol and AWS Bedrock's Converse API message formats for Claude Haiku 4.5.
"""

import base64
import logging
from typing import Any

from a2a.types import (
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TextPart,
)


logger = logging.getLogger(__name__)


def convert_a2a_part_to_bedrock(part: Part) -> dict[str, Any]:
    part = part.root

    if isinstance(part, TextPart):
        return {'text': part.text}

    if isinstance(part, FilePart):
        if isinstance(part.file, FileWithUri):
            # Bedrock doesn't support direct URI references
            # You'll need to fetch the file and convert to bytes
            raise NotImplementedError(
                'FileWithUri not yet supported for Bedrock. '
                'Please fetch the file and use FileWithBytes instead.'
            )

        if isinstance(part.file, FileWithBytes):
            # Bedrock uses base64-encoded images in content blocks
            # Determine the format from mime_type
            mime_type = part.file.mime_type

            # Bedrock supports specific image formats
            supported_formats = {
                'image/jpeg': 'jpeg',
                'image/jpg': 'jpeg',
                'image/png': 'png',
                'image/gif': 'gif',
                'image/webp': 'webp',
            }

            if mime_type in supported_formats:
                return {
                    'image': {
                        'format': supported_formats[mime_type],
                        'source': {
                            'bytes': part.file.bytes
                        }
                    }
                }

            # For documents (PDF, etc.), Bedrock has a document block
            elif mime_type == 'application/pdf':
                return {
                    'document': {
                        'format': 'pdf',
                        'name': 'document.pdf',
                        'source': {
                            'bytes': part.file.bytes
                        }
                    }
                }

            else:
                raise ValueError(
                    f'Unsupported mime type for Bedrock: {mime_type}. '
                    f'Supported: {list(supported_formats.keys())} and application/pdf'
                )

        raise ValueError(f'Unsupported file type: {type(part.file)}')

    raise ValueError(f'Unsupported part type: {type(part)}')


def convert_bedrock_content_to_a2a(content_block: dict[str, Any]) -> Part:
    # Text content
    if 'text' in content_block:
        return Part(root=TextPart(text=content_block['text']))

    # Image content
    if 'image' in content_block:
        image_data = content_block['image']
        format_to_mime = {
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
        }

        mime_type = format_to_mime.get(
            image_data.get('format', 'jpeg'),
            'image/jpeg'
        )

        # Extract bytes from source
        image_bytes = image_data['source'].get('bytes')
        if not image_bytes:
            raise ValueError('Image content block missing bytes in source')

        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=image_bytes,
                    mime_type=mime_type,
                )
            )
        )

    # Document content (PDF, etc.)
    if 'document' in content_block:
        doc_data = content_block['document']
        format_to_mime = {
            'pdf': 'application/pdf',
            'csv': 'text/csv',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'html': 'text/html',
            'txt': 'text/plain',
            'md': 'text/markdown',
        }

        doc_format = doc_data.get('format', 'pdf')
        mime_type = format_to_mime.get(doc_format, 'application/octet-stream')

        doc_bytes = doc_data['source'].get('bytes')
        if not doc_bytes:
            raise ValueError('Document content block missing bytes in source')

        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=doc_bytes,
                    mime_type=mime_type,
                )
            )
        )

    # Tool use (function calling) - not converted to Part, handled separately
    if 'toolUse' in content_block:
        logger.warning('Tool use content blocks should be handled separately')
        raise ValueError('toolUse content blocks are not converted to A2A Parts')

    raise ValueError(f'Unsupported Bedrock content block: {content_block.keys()}')


def create_bedrock_message(parts: list[Part], role: str = 'user') -> dict[str, Any]:
    return {
        'role': role,
        'content': [convert_a2a_part_to_bedrock(part) for part in parts]
    }


def extract_text_from_bedrock_response(response: dict[str, Any]) -> str:
    content_blocks = response.get('output', {}).get('message', {}).get('content', [])
    text_parts = [block.get('text', '') for block in content_blocks if 'text' in block]
    return ''.join(text_parts)
