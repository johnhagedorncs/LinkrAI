"""Medical audio transcription using Amazon Transcribe Medical.

This package provides a simple interface for transcribing medical audio files
with speaker diarization using AWS Amazon Transcribe Medical.

Example:
    >>> from scribe_agent import MedicalTranscriber
    >>> transcriber = MedicalTranscriber()
    >>> transcript = transcriber.transcribe_file("s3://bucket/audio.mp3")
    >>> print(transcript)
    Speaker 0: Good morning, how are you feeling?
    Speaker 1: I've been having chest pain.
"""

from .transcriber import MedicalTranscriber
from .config import TranscriberConfig
from .exceptions import (
    TranscriptionError,
    TranscriptionJobError,
    TranscriptionTimeoutError,
    AudioFileError,
    ConfigurationError,
)

__version__ = "1.0.0"

__all__ = [
    "MedicalTranscriber",
    "TranscriberConfig",
    "TranscriptionError",
    "TranscriptionJobError",
    "TranscriptionTimeoutError",
    "AudioFileError",
    "ConfigurationError",
]
