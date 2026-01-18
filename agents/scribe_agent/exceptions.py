"""Custom exceptions for the Medical Transcriber."""


class TranscriptionError(Exception):
    """Base exception for all transcription-related errors."""
    pass


class TranscriptionJobError(TranscriptionError):
    """Raised when a transcription job fails to start or complete."""
    pass


class TranscriptionTimeoutError(TranscriptionError):
    """Raised when a transcription job exceeds the maximum wait time."""
    pass


class AudioFileError(TranscriptionError):
    """Raised when there's an issue with the audio file (format, location, etc.)."""
    pass


class ConfigurationError(TranscriptionError):
    """Raised when configuration is invalid or missing."""
    pass
