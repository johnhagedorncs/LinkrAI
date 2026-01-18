"""Command-line interface for Medical Transcriber."""

import logging
import sys
from pathlib import Path

import click

from .transcriber import MedicalTranscriber
from .config import TranscriberConfig
from .exceptions import TranscriptionError, ConfigurationError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@click.command()
@click.argument('audio_uri')
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file path for transcript (default: stdout)'
)
@click.option(
    '--region',
    envvar='AWS_REGION',
    help='AWS region (default: from AWS_REGION env var)'
)
@click.option(
    '--bucket',
    envvar='TRANSCRIBE_OUTPUT_BUCKET',
    help='S3 bucket for transcription output'
)
@click.option(
    '--specialty',
    default='PRIMARYCARE',
    type=click.Choice([
        'PRIMARYCARE', 'CARDIOLOGY', 'NEUROLOGY', 'ONCOLOGY',
        'RADIOLOGY', 'UROLOGY', 'OPHTHALMOLOGY', 'ORTHOPEDICS'
    ], case_sensitive=False),
    help='Medical specialty for transcription context'
)
@click.option(
    '--max-speakers',
    default=2,
    type=int,
    help='Maximum number of speakers (default: 2)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def main(
    audio_uri: str,
    output: str,
    region: str,
    bucket: str,
    specialty: str,
    max_speakers: int,
    verbose: bool
):
    """Transcribe medical audio files using Amazon Transcribe Medical.

    AUDIO_URI: S3 URI of the audio file (e.g., s3://bucket/audio.mp3)

    Examples:

        # Transcribe and print to stdout
        python -m scribe_agent s3://my-bucket/recording.mp3

        # Save to file
        python -m scribe_agent s3://my-bucket/recording.mp3 -o transcript.txt

        # Specify region and bucket
        python -m scribe_agent s3://my-bucket/recording.mp3 --region us-west-2 --bucket my-output-bucket

        # Enable verbose logging
        python -m scribe_agent s3://my-bucket/recording.mp3 -v
    """
    # Configure logging level
    if verbose:
        logging.getLogger('scribe_agent').setLevel(logging.DEBUG)

    try:
        # Build configuration
        config_overrides = {}
        if region:
            config_overrides['aws_region'] = region
        if bucket:
            config_overrides['output_bucket'] = bucket
        if specialty:
            config_overrides['specialty'] = specialty.upper()
        if max_speakers:
            config_overrides['max_speakers'] = max_speakers

        # Initialize transcriber
        config = TranscriberConfig.from_env(**config_overrides)
        transcriber = MedicalTranscriber(config)

        # Transcribe
        click.echo(f"Transcribing: {audio_uri}", err=True)
        transcript = transcriber.transcribe_file(audio_uri)

        # Output
        if output:
            output_path = Path(output)
            output_path.write_text(transcript)
            click.echo(f"Transcript saved to: {output}", err=True)
        else:
            click.echo("\n--- TRANSCRIPT ---")
            click.echo(transcript)

        click.echo("\nTranscription completed successfully!", err=True)

    except ConfigurationError as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo("\nMake sure to set required environment variables:", err=True)
        click.echo("  - AWS_REGION or TRANSCRIBE_AWS_REGION", err=True)
        click.echo("  - TRANSCRIBE_OUTPUT_BUCKET", err=True)
        sys.exit(1)

    except TranscriptionError as e:
        click.echo(f"Transcription error: {e}", err=True)
        sys.exit(1)

    except Exception as e:
        logger.exception("Unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
