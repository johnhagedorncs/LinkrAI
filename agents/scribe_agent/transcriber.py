"""Medical audio transcription using Amazon Transcribe Medical."""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from .config import TranscriberConfig
from .exceptions import (
    TranscriptionJobError,
    TranscriptionTimeoutError,
    AudioFileError,
)


logger = logging.getLogger(__name__)


class MedicalTranscriber:
    """Amazon Transcribe Medical client for converting medical audio to text.

    This class handles the complete workflow of medical audio transcription:
    1. Starting transcription jobs with speaker diarization
    2. Polling for job completion
    3. Retrieving and formatting transcripts with speaker labels

    Attributes:
        config: TranscriberConfig instance with AWS settings
        transcribe_client: boto3 Transcribe client
        s3_client: boto3 S3 client
    """

    def __init__(self, config: Optional[TranscriberConfig] = None):
        """Initialize the Medical Transcriber.

        Args:
            config: TranscriberConfig instance. If None, loads from environment.

        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        self.config = config or TranscriberConfig.from_env()
        self.config.validate()

        self.transcribe_client = boto3.client(
            'transcribe',
            region_name=self.config.aws_region
        )
        self.s3_client = boto3.client(
            's3',
            region_name=self.config.aws_region
        )

        logger.info(
            f"Initialized MedicalTranscriber (region={self.config.aws_region}, "
            f"bucket={self.config.output_bucket})"
        )

    def transcribe_file(
        self,
        audio_s3_uri: str,
        job_name_prefix: str = "medical-transcribe"
    ) -> str:
        """Transcribe an audio file from S3 to plain text with speaker labels.

        This is the main public method that orchestrates the complete transcription
        workflow: start job → wait for completion → retrieve → format output.

        Args:
            audio_s3_uri: S3 URI of audio file (e.g., s3://bucket/audio.mp3)
            job_name_prefix: Prefix for the transcription job name

        Returns:
            Plain text transcript with speaker labels, formatted as:
            "Speaker 0: Hello doctor.\\nSpeaker 1: Good morning..."

        Raises:
            AudioFileError: If audio file format is invalid or inaccessible
            TranscriptionJobError: If transcription job fails
            TranscriptionTimeoutError: If job exceeds maximum wait time
        """
        logger.info(f"Starting transcription for: {audio_s3_uri}")

        # Generate unique job name
        timestamp = int(time.time())
        job_name = f"{job_name_prefix}-{timestamp}"

        try:
            # Step 1: Start transcription job
            self._start_job(audio_s3_uri, job_name)

            # Step 2: Wait for completion
            job_response = self._wait_for_completion(job_name)

            # Step 3: Retrieve transcript data
            transcript_data = self._get_transcript(job_response)

            # Step 4: Format with speaker labels
            formatted_text = self._format_output(transcript_data)

            logger.info(f"Transcription completed successfully: {job_name}")
            return formatted_text

        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS error during transcription: {e}")
            raise TranscriptionJobError(f"AWS error: {str(e)}") from e

    def _start_job(self, audio_s3_uri: str, job_name: str) -> None:
        """Start a medical transcription job.

        Args:
            audio_s3_uri: S3 URI of audio file
            job_name: Unique name for this transcription job

        Raises:
            AudioFileError: If media format is invalid
            TranscriptionJobError: If job fails to start
        """
        try:
            media_format = self._get_media_format(audio_s3_uri)

            self.transcribe_client.start_medical_transcription_job(
                MedicalTranscriptionJobName=job_name,
                LanguageCode=self.config.language_code,
                MediaFormat=media_format,
                Media={'MediaFileUri': audio_s3_uri},
                OutputBucketName=self.config.output_bucket,
                Specialty=self.config.specialty,
                Type='CONVERSATION',
                Settings={
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': self.config.max_speakers
                }
            )

            logger.info(f"Started transcription job: {job_name}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'BadRequestException':
                raise AudioFileError(f"Invalid audio file or format: {str(e)}") from e
            raise TranscriptionJobError(f"Failed to start job: {str(e)}") from e

    def _get_media_format(self, s3_uri: str) -> str:
        """Extract media format from S3 URI file extension.

        Args:
            s3_uri: S3 URI of audio file

        Returns:
            Media format string for Transcribe API

        Raises:
            AudioFileError: If file extension is not supported
        """
        extension = s3_uri.split('.')[-1].lower()
        format_map = {
            'mp3': 'mp3',
            'mp4': 'mp4',
            'wav': 'wav',
            'flac': 'flac',
            'ogg': 'ogg',
            'amr': 'amr',
            'webm': 'webm'
        }

        if extension not in format_map:
            raise AudioFileError(
                f"Unsupported audio format: {extension}. "
                f"Supported formats: {', '.join(format_map.keys())}"
            )

        return format_map[extension]

    def _wait_for_completion(self, job_name: str) -> Dict[str, Any]:
        """Wait for transcription job to complete.

        Polls the job status at regular intervals until completion or timeout.

        Args:
            job_name: Name of the transcription job

        Returns:
            Final job response with status COMPLETED

        Raises:
            TranscriptionJobError: If job fails
            TranscriptionTimeoutError: If job exceeds max_wait_seconds
        """
        start_time = time.time()
        max_wait = self.config.max_wait_seconds
        poll_interval = self.config.poll_interval

        logger.info(f"Waiting for job completion (max {max_wait}s)...")

        while (time.time() - start_time) < max_wait:
            response = self.transcribe_client.get_medical_transcription_job(
                MedicalTranscriptionJobName=job_name
            )

            job_status = response['MedicalTranscriptionJob']['TranscriptionJobStatus']

            if job_status == 'COMPLETED':
                elapsed = int(time.time() - start_time)
                logger.info(f"Job completed in {elapsed}s")
                return response

            elif job_status == 'FAILED':
                failure_reason = response['MedicalTranscriptionJob'].get(
                    'FailureReason', 'Unknown error'
                )
                raise TranscriptionJobError(f"Job failed: {failure_reason}")

            elif job_status in ['IN_PROGRESS', 'QUEUED']:
                logger.debug(f"Job status: {job_status}, waiting...")
                time.sleep(poll_interval)

            else:
                logger.warning(f"Unexpected job status: {job_status}")
                time.sleep(poll_interval)

        raise TranscriptionTimeoutError(
            f"Job did not complete within {max_wait} seconds"
        )

    def _get_transcript(self, job_response: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the transcript JSON from a completed job.

        Args:
            job_response: Response from get_medical_transcription_job

        Returns:
            Transcript data including results, speaker labels, etc.

        Raises:
            TranscriptionJobError: If transcript cannot be retrieved
        """
        try:
            # Get the TranscriptFileUri from the job response
            transcript_uri = job_response['MedicalTranscriptionJob']['Transcript']['TranscriptFileUri']

            print(f"DEBUG: Transcript URI: {transcript_uri}")

            # Parse bucket and key from the URI
            # URI formats:
            # - https://s3.region.amazonaws.com/bucket/key
            # - https://s3.amazonaws.com/bucket/key
            # - https://bucket.s3.region.amazonaws.com/key
            # - s3://bucket/key

            if transcript_uri.startswith('https://'):
                # HTTPS URL format
                parts = transcript_uri.split('/')

                # Check if it's s3.*.amazonaws.com/bucket/key format
                domain = parts[2]  # e.g., s3.us-east-2.amazonaws.com

                if domain.startswith('s3.') and 'amazonaws.com' in domain:
                    # Format: https://s3.region.amazonaws.com/bucket/key
                    bucket = parts[3]
                    s3_key = '/'.join(parts[4:])
                elif 's3.' in domain and 'amazonaws.com' in domain:
                    # Format: https://bucket.s3.region.amazonaws.com/key
                    bucket = domain.split('.')[0]
                    s3_key = '/'.join(parts[3:])
                else:
                    raise ValueError(f"Unrecognized S3 domain format: {domain}")

            elif transcript_uri.startswith('s3://'):
                # S3 URI format: s3://bucket/key
                parts = transcript_uri[5:].split('/', 1)
                bucket = parts[0]
                s3_key = parts[1] if len(parts) > 1 else None
            else:
                raise ValueError(f"Unrecognized URI format: {transcript_uri}")

            if not s3_key:
                raise ValueError(f"Could not parse S3 key from URI: {transcript_uri}")

            print(f"DEBUG: Parsed bucket: {bucket}, key: {s3_key}")

            # Download directly from S3 using boto3
            response = self.s3_client.get_object(
                Bucket=bucket,
                Key=s3_key
            )

            transcript_data = json.loads(response['Body'].read())

            return transcript_data

        except Exception as e:
            raise TranscriptionJobError(f"Failed to retrieve transcript: {str(e)}") from e

    def _format_output(self, transcript_data: Dict[str, Any]) -> str:
        """Format transcript with speaker labels as plain text.

        Extracts speaker segments and formats them as:
        "Speaker 0: text\\nSpeaker 1: text\\n..."

        Args:
            transcript_data: Raw transcript JSON from Transcribe

        Returns:
            Formatted plain text with speaker labels

        Raises:
            TranscriptionJobError: If transcript format is unexpected
        """
        try:
            results = transcript_data.get('results', {})

            # Get speaker segments if available
            speaker_labels = results.get('speaker_labels')
            if speaker_labels and 'segments' in speaker_labels:
                return self._format_with_speakers(transcript_data)

            # Fallback: just return the full transcript without speaker labels
            transcripts = results.get('transcripts', [])
            if transcripts:
                return transcripts[0].get('transcript', '')

            return ""

        except Exception as e:
            raise TranscriptionJobError(f"Failed to format transcript: {str(e)}") from e

    def _format_with_speakers(self, transcript_data: Dict[str, Any]) -> str:
        """Format transcript with speaker diarization.

        Args:
            transcript_data: Raw transcript JSON with speaker labels

        Returns:
            Plain text formatted with speaker labels
        """
        results = transcript_data['results']
        items = results.get('items', [])
        segments = results.get('speaker_labels', {}).get('segments', [])

        # Build a mapping of time ranges to speakers
        speaker_map = {}
        for segment in segments:
            speaker_label = segment.get('speaker_label', 'unknown')
            for item in segment.get('items', []):
                start_time = float(item.get('start_time', 0))
                speaker_map[start_time] = speaker_label

        # Group words by speaker
        current_speaker = None
        current_text = []
        output_lines = []

        for item in items:
            if item.get('type') == 'pronunciation':
                start_time = float(item.get('start_time', 0))
                speaker = speaker_map.get(start_time, 'unknown')
                content = item.get('alternatives', [{}])[0].get('content', '')

                # Convert speaker label to number (spk_0 -> Speaker 0)
                speaker_num = speaker.replace('spk_', '').upper() if 'spk_' in speaker else speaker

                if speaker != current_speaker:
                    # New speaker, save previous segment
                    if current_text:
                        text = ' '.join(current_text)
                        output_lines.append(f"Speaker {speaker_num}: {text}")
                        current_text = []
                    current_speaker = speaker

                current_text.append(content)

            elif item.get('type') == 'punctuation':
                # Add punctuation to current text
                content = item.get('alternatives', [{}])[0].get('content', '')
                if current_text:
                    current_text[-1] += content

        # Add final segment
        if current_text and current_speaker:
            speaker_num = current_speaker.replace('spk_', '').upper() if 'spk_' in current_speaker else current_speaker
            text = ' '.join(current_text)
            output_lines.append(f"Speaker {speaker_num}: {text}")

        return '\n'.join(output_lines)
