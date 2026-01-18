"""Configuration management for Medical Transcriber."""

import os
from dataclasses import dataclass
from typing import Optional

from .exceptions import ConfigurationError


@dataclass
class TranscriberConfig:
    """Configuration for the Medical Transcriber.

    Attributes:
        aws_region: AWS region for Transcribe service
        output_bucket: S3 bucket for transcription outputs
        specialty: Medical specialty for context (PRIMARYCARE, CARDIOLOGY, etc.)
        language_code: Language of the audio (default: en-US)
        max_speakers: Maximum number of speakers for diarization
        max_wait_seconds: Maximum time to wait for job completion
        poll_interval: How often to check job status (seconds)
    """
    aws_region: str
    output_bucket: str
    specialty: str = "PRIMARYCARE"
    language_code: str = "en-US"
    max_speakers: int = 2
    max_wait_seconds: int = 300
    poll_interval: int = 10

    @classmethod
    def from_env(cls, **overrides) -> "TranscriberConfig":
        """Create configuration from environment variables.

        Environment variables:
            AWS_REGION or TRANSCRIBE_AWS_REGION
            TRANSCRIBE_OUTPUT_BUCKET
            TRANSCRIBE_SPECIALTY (optional)
            TRANSCRIBE_LANGUAGE_CODE (optional)
            TRANSCRIBE_MAX_SPEAKERS (optional)

        Args:
            **overrides: Override specific config values

        Returns:
            TranscriberConfig instance

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        aws_region = overrides.get("aws_region") or \
                     os.getenv("TRANSCRIBE_AWS_REGION") or \
                     os.getenv("AWS_REGION")

        output_bucket = overrides.get("output_bucket") or \
                       os.getenv("TRANSCRIBE_OUTPUT_BUCKET")

        if not aws_region:
            raise ConfigurationError(
                "AWS region is required. Set AWS_REGION or TRANSCRIBE_AWS_REGION environment variable."
            )

        if not output_bucket:
            raise ConfigurationError(
                "Output bucket is required. Set TRANSCRIBE_OUTPUT_BUCKET environment variable."
            )

        return cls(
            aws_region=aws_region,
            output_bucket=output_bucket,
            specialty=overrides.get("specialty") or os.getenv("TRANSCRIBE_SPECIALTY", "PRIMARYCARE"),
            language_code=overrides.get("language_code") or os.getenv("TRANSCRIBE_LANGUAGE_CODE", "en-US"),
            max_speakers=int(overrides.get("max_speakers") or os.getenv("TRANSCRIBE_MAX_SPEAKERS", "2")),
            max_wait_seconds=int(overrides.get("max_wait_seconds", 300)),
            poll_interval=int(overrides.get("poll_interval", 10)),
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If any configuration value is invalid
        """
        if self.max_speakers < 1:
            raise ConfigurationError("max_speakers must be at least 1")

        if self.max_wait_seconds < 1:
            raise ConfigurationError("max_wait_seconds must be at least 1")

        if self.poll_interval < 1:
            raise ConfigurationError("poll_interval must be at least 1")

        valid_specialties = [
            "PRIMARYCARE", "CARDIOLOGY", "NEUROLOGY", "ONCOLOGY",
            "RADIOLOGY", "UROLOGY", "OPHTHALMOLOGY", "ORTHOPEDICS"
        ]
        if self.specialty.upper() not in valid_specialties:
            raise ConfigurationError(
                f"Invalid specialty: {self.specialty}. Must be one of: {', '.join(valid_specialties)}"
            )
