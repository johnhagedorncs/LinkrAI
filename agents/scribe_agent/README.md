# Medical Transcriber

A production-grade speech-to-text service for medical audio using Amazon Transcribe Medical with speaker diarization.

## Features

- **Medical-optimized transcription** using Amazon Transcribe Medical
- **Speaker diarization** to distinguish between doctor and patient
- **Simple API** - use as Python module or CLI tool
- **Production-ready** with comprehensive error handling and logging
- **Flexible configuration** via environment variables or programmatic overrides
- **HIPAA-eligible** AWS service for healthcare compliance

## Installation

### Prerequisites

- Python 3.8+
- AWS account with Transcribe Medical access
- S3 bucket for storing transcription outputs
- Audio files stored in S3

### Dependencies

```bash
pip install boto3 click python-dotenv
```

Or if using the A2A Framework's pyproject.toml, dependencies are already included.

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
AWS_REGION=us-east-1
TRANSCRIBE_OUTPUT_BUCKET=artera-transcriptions

# AWS Credentials (or use AWS CLI config / IAM roles)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Optional
TRANSCRIBE_SPECIALTY=PRIMARYCARE
TRANSCRIBE_LANGUAGE_CODE=en-US
TRANSCRIBE_MAX_SPEAKERS=2
```

### Supported Medical Specialties

- `PRIMARYCARE` (default)
- `CARDIOLOGY`
- `NEUROLOGY`
- `ONCOLOGY`
- `RADIOLOGY`
- `UROLOGY`
- `OPHTHALMOLOGY`
- `ORTHOPEDICS`

## Usage

### As a Python Module

```python
from scribe_agent import MedicalTranscriber

# Initialize with environment configuration
transcriber = MedicalTranscriber()

# Transcribe an audio file from S3
transcript = transcriber.transcribe_file("s3://my-bucket/recording.mp3")
print(transcript)
```

**Output:**
```
Speaker 0: Good morning Mr Smith. I see you're here for chest pain.
Speaker 1: It started yesterday afternoon.
Speaker 0: I'm referring you to cardiology for evaluation.
```

### With Custom Configuration

```python
from scribe_agent import MedicalTranscriber, TranscriberConfig

# Create custom configuration
config = TranscriberConfig(
    aws_region="us-west-2",
    output_bucket="my-transcription-bucket",
    specialty="CARDIOLOGY",
    max_speakers=3,
    max_wait_seconds=600
)

transcriber = MedicalTranscriber(config)
transcript = transcriber.transcribe_file("s3://bucket/audio.mp3")
```

### As a CLI Tool

```bash
# Basic usage (print to stdout)
python -m scribe_agent s3://my-bucket/recording.mp3

# Save to file
python -m scribe_agent s3://my-bucket/recording.mp3 -o transcript.txt

# Specify options
python -m scribe_agent s3://my-bucket/recording.mp3 \
  --region us-west-2 \
  --bucket my-output-bucket \
  --specialty CARDIOLOGY \
  --max-speakers 3 \
  --verbose
```

**CLI Options:**

- `--output, -o`: Save transcript to file (default: stdout)
- `--region`: AWS region
- `--bucket`: S3 output bucket
- `--specialty`: Medical specialty
- `--max-speakers`: Maximum number of speakers
- `--verbose, -v`: Enable verbose logging

## Audio File Requirements

### Supported Formats

- MP3
- MP4
- WAV
- FLAC
- OGG
- AMR
- WEBM

### Storage

Audio files must be stored in **Amazon S3** and referenced using S3 URIs:
```
s3://bucket-name/path/to/audio.mp3
```

### Best Practices

- **Sample rate**: 16 kHz or higher for medical audio
- **Mono or stereo**: Both supported
- **Duration**: Up to 4 hours per file
- **Quality**: Clear audio with minimal background noise

## Output Format

The transcriber returns plain text with speaker labels:

```
Speaker 0: [Doctor's utterance]
Speaker 1: [Patient's utterance]
Speaker 0: [Next doctor's utterance]
...
```

- **Speaker 0** is typically the first speaker (often the doctor)
- **Speaker 1** is typically the second speaker (often the patient)
- Segments are separated by newlines
- Punctuation is included automatically

## Error Handling

The package includes comprehensive error handling:

```python
from scribe_agent import (
    MedicalTranscriber,
    TranscriptionError,
    TranscriptionJobError,
    TranscriptionTimeoutError,
    AudioFileError,
    ConfigurationError
)

try:
    transcriber = MedicalTranscriber()
    transcript = transcriber.transcribe_file("s3://bucket/audio.mp3")
except ConfigurationError as e:
    print(f"Configuration issue: {e}")
except AudioFileError as e:
    print(f"Audio file problem: {e}")
except TranscriptionTimeoutError as e:
    print(f"Transcription took too long: {e}")
except TranscriptionJobError as e:
    print(f"Transcription job failed: {e}")
except TranscriptionError as e:
    print(f"General transcription error: {e}")
```

## Logging

The package uses Python's standard logging. Enable detailed logs:

```python
import logging

# Set log level
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger('scribe_agent')
logger.setLevel(logging.DEBUG)
```

## Architecture

```
scribe_agent/
├── __init__.py          # Package exports
├── __main__.py          # CLI entry point
├── transcriber.py       # Core transcription logic
├── config.py            # Configuration management
├── exceptions.py        # Custom exceptions
├── .env.example         # Environment template
└── README.md            # Documentation
```

## How It Works

1. **Upload audio** to S3 (prerequisite)
2. **Start transcription job** via Amazon Transcribe Medical API
3. **Poll for completion** (typically 1-3 minutes for short recordings)
4. **Retrieve transcript** from S3 output location
5. **Format with speaker labels** and return plain text

## AWS Permissions

Your AWS credentials need these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartMedicalTranscriptionJob",
        "transcribe:GetMedicalTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-audio-bucket/*",
        "arn:aws:s3:::your-output-bucket/*"
      ]
    }
  ]
}
```

## Cost Considerations

Amazon Transcribe Medical pricing (as of 2025):
- **Pay per second** of audio transcribed
- Medical transcription is more expensive than standard transcription
- Check current AWS pricing: https://aws.amazon.com/transcribe/pricing/

## HIPAA Compliance

- Amazon Transcribe Medical is **HIPAA-eligible**
- Sign a Business Associate Agreement (BAA) with AWS
- Enable encryption at rest for S3 buckets
- Use VPC endpoints for added security
- Enable CloudTrail logging for audit trails

## Troubleshooting

### "Configuration error: AWS region is required"
Set the `AWS_REGION` environment variable or pass `aws_region` in config.

### "Configuration error: Output bucket is required"
Set the `TRANSCRIBE_OUTPUT_BUCKET` environment variable or pass `output_bucket` in config.

### "Audio file problem: Unsupported audio format"
Check that your file has a supported extension (.mp3, .wav, etc.).

### "Transcription job failed"
- Check that the S3 URI is correct and accessible
- Verify your AWS credentials have the required permissions
- Ensure the audio file format is valid

### Job times out
- Increase `max_wait_seconds` in configuration (default: 300 seconds)
- Check AWS Transcribe service status
- For very long audio files, consider splitting them

## Examples

### Example 1: Basic Usage
```python
from scribe_agent import MedicalTranscriber

transcriber = MedicalTranscriber()
transcript = transcriber.transcribe_file("s3://my-bucket/encounter-001.mp3")
print(transcript)
```

### Example 2: Save to File
```python
from scribe_agent import MedicalTranscriber
from pathlib import Path

transcriber = MedicalTranscriber()
transcript = transcriber.transcribe_file("s3://my-bucket/recording.mp3")

Path("output.txt").write_text(transcript)
print("Transcript saved!")
```

### Example 3: Batch Processing
```python
from scribe_agent import MedicalTranscriber

transcriber = MedicalTranscriber()

audio_files = [
    "s3://bucket/recording-001.mp3",
    "s3://bucket/recording-002.mp3",
    "s3://bucket/recording-003.mp3",
]

for audio_uri in audio_files:
    print(f"Processing: {audio_uri}")
    transcript = transcriber.transcribe_file(audio_uri)

    # Save with same name as audio file
    filename = audio_uri.split('/')[-1].replace('.mp3', '.txt')
    Path(filename).write_text(transcript)
```

## Support

For issues or questions:
- Check the AWS Transcribe Medical documentation
- Review CloudWatch logs for job failures
- Verify S3 bucket permissions and accessibility

## License

Part of the A2A Framework - Artera Project
