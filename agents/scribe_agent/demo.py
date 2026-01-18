#!/usr/bin/env python3
"""
Interactive demo for Medical Transcriber.
Records audio, uploads to S3, and transcribes in real-time.
"""

import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime

import boto3
import sounddevice as sd
import soundfile as sf
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load .env file from scribe_agent directory
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from scribe_agent import MedicalTranscriber, TranscriberConfig
from scribe_agent.exceptions import TranscriptionError, ConfigurationError


class RecordingDemo:
    """Interactive recording and transcription demo."""

    def __init__(self):
        """Initialize demo with transcriber and S3 client."""
        try:
            self.config = TranscriberConfig.from_env()
            self.transcriber = MedicalTranscriber(self.config)
            self.s3_client = boto3.client('s3', region_name=self.config.aws_region)
        except ConfigurationError as e:
            print(f"❌ Configuration error: {e}")
            print("\nMake sure your .env file is set up with:")
            print("  - AWS_REGION")
            print("  - TRANSCRIBE_OUTPUT_BUCKET")
            print("  - AWS credentials")
            sys.exit(1)

        # Recording settings
        self.sample_rate = 16000  # 16kHz - optimal for medical transcription
        self.channels = 1  # Mono
        self.recording = []

    def print_header(self):
        """Print demo header."""
        print("\n" + "=" * 70)
        print("🎙️  MEDICAL TRANSCRIBER - INTERACTIVE DEMO")
        print("=" * 70)
        print(f"\nRegion: {self.config.aws_region}")
        print(f"Output Bucket: {self.config.output_bucket}")
        print(f"Sample Rate: {self.sample_rate} Hz")
        print(f"Specialty: {self.config.specialty}")
        print("\n" + "=" * 70)

    def record_audio(self) -> Path:
        """Record audio interactively.

        Returns:
            Path to the recorded audio file
        """
        print("\n🎙️  Press ENTER to START recording...")
        input()

        print("🔴 RECORDING... (Press ENTER to STOP)")
        print("   Speak clearly into your microphone")

        # Start recording in callback mode
        self.recording = []

        def callback(indata, frames, time, status):
            if status:
                print(f"⚠️  {status}", file=sys.stderr)
            self.recording.append(indata.copy())

        # Record until Enter is pressed
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback
        ):
            input()  # Wait for Enter key

        print("⏹️  Recording stopped")

        # Combine all recorded chunks
        import numpy as np
        if not self.recording:
            raise ValueError("No audio was recorded")

        audio_data = np.concatenate(self.recording, axis=0)

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.wav',
            prefix='recording_'
        )
        temp_path = Path(temp_file.name)

        sf.write(temp_path, audio_data, self.sample_rate)

        duration = len(audio_data) / self.sample_rate
        print(f"✅ Saved recording: {temp_path} ({duration:.1f} seconds)")

        return temp_path

    def upload_to_s3(self, audio_path: Path) -> str:
        """Upload audio file to S3.

        Args:
            audio_path: Local path to audio file

        Returns:
            S3 URI of uploaded file
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"recordings/{timestamp}.wav"

        print(f"\n📤 Uploading to S3...")

        try:
            self.s3_client.upload_file(
                str(audio_path),
                self.config.output_bucket,
                s3_key
            )

            s3_uri = f"s3://{self.config.output_bucket}/{s3_key}"
            print(f"✅ Uploaded: {s3_uri}")
            return s3_uri

        except ClientError as e:
            print(f"❌ Upload failed: {e}")
            raise

    def transcribe_and_display(self, s3_uri: str):
        """Transcribe audio and display results.

        Args:
            s3_uri: S3 URI of audio file
        """
        print(f"\n🔄 Starting transcription...")
        print("   This may take 1-3 minutes depending on audio length...")

        try:
            transcript = self.transcriber.transcribe_file(s3_uri)

            print("\n" + "=" * 70)
            print("📝 TRANSCRIPTION RESULT")
            print("=" * 70 + "\n")
            print(transcript)
            print("\n" + "=" * 70)

        except TranscriptionError as e:
            print(f"\n❌ Transcription failed: {e}")
            raise

    def cleanup(self, audio_path: Path):
        """Clean up temporary files.

        Args:
            audio_path: Path to temporary audio file
        """
        try:
            audio_path.unlink()
            print(f"\n🗑️  Cleaned up temporary file")
        except Exception as e:
            print(f"⚠️  Could not delete temp file: {e}")

    def run(self):
        """Run the interactive demo."""
        self.print_header()

        try:
            while True:
                # Record audio
                audio_path = self.record_audio()

                # Upload to S3
                s3_uri = self.upload_to_s3(audio_path)

                # Transcribe
                self.transcribe_and_display(s3_uri)

                # Cleanup
                self.cleanup(audio_path)

                # Ask if user wants to continue
                print("\n" + "=" * 70)
                response = input("Record another? (y/n): ").strip().lower()
                if response != 'y':
                    break

            print("\n👋 Thanks for using Medical Transcriber!")

        except KeyboardInterrupt:
            print("\n\n⏹️  Demo stopped by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []

    try:
        import sounddevice
    except ImportError:
        missing.append("sounddevice")

    try:
        import soundfile
    except ImportError:
        missing.append("soundfile")

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    if missing:
        print("❌ Missing required dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\nInstall with:")
        print(f"   pip install {' '.join(missing)}")
        sys.exit(1)


def main():
    """Main entry point."""
    check_dependencies()

    demo = RecordingDemo()
    demo.run()


if __name__ == "__main__":
    main()
