#!/usr/bin/env python3
"""
Medical Scribe Agent - Extracts referral information from medical conversations.
Uses AWS Bedrock with Claude to process transcripts.
"""

import boto3
import json
from pathlib import Path
from typing import Dict, Any


class ScribeAgent:
    def __init__(self, region: str = None):
        """
        Initialize Medical Scribe Agent.

        Args:
            region: AWS region for Bedrock (defaults to region in config.json)
        """
        # Load configuration first
        config_path = Path(__file__).parent / "config.json"
        with open(config_path) as f:
            self.config = json.load(f)

        # Use provided region or fall back to config
        if region is None:
            region = self.config.get('region', 'us-west-2')

        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region
        )

        # Load system prompt
        system_prompt_path = Path(__file__).parent / "prompts" / "system-instruction.txt"
        with open(system_prompt_path) as f:
            self.system_prompt = f.read()

        self.model_id = self.config['model_id']
        self.temperature = self.config.get('temperature', 0.0)
        self.max_tokens = self.config.get('max_tokens', 1000)

    def extract_referrals(self, conversation_text: str) -> Dict[str, Any]:
        """
        Extract referral information from conversation transcript.

        Args:
            conversation_text: Medical conversation transcript

        Returns:
            Structured referral data with diagnoses and medical codes
        """
        try:
            # Prepare the request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": self.system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": conversation_text
                    }
                ]
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract the text content
            content = response_body['content'][0]['text']

            # Parse JSON from response
            result = json.loads(content)

            return result

        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON response: {e}")
            print(f"Raw response: {content}")
            return {
                "referral_detected": False,
                "referrals": [],
                "error": "JSON parsing error"
            }
        except Exception as e:
            print(f"❌ Error invoking Bedrock: {e}")
            return {
                "referral_detected": False,
                "referrals": [],
                "error": str(e)
            }


class ScribeAgentTester:
    """Wrapper for testing the Scribe Agent."""

    def __init__(self):
        self.agent = ScribeAgent()

    def invoke_scribe_agent(self, conversation_text: str) -> Dict[str, Any]:
        """
        Invoke the scribe agent with a conversation transcript.

        Args:
            conversation_text: Medical conversation transcript

        Returns:
            Structured referral data
        """
        return self.agent.extract_referrals(conversation_text)


def main():
    """Test the Scribe Agent with a sample conversation."""
    agent = ScribeAgent()

    # Sample conversation
    conversation = """
    Doctor: Good morning Mr. Smith. I see you're here for chest pain.
    Can you tell me when this started?

    Patient: It started yesterday afternoon. It feels like pressure in the
    center of my chest.

    Doctor: Does the pain radiate anywhere? To your arm, jaw, or back?

    Patient: Yes, sometimes it goes down my left arm.

    Doctor: Okay, that's concerning. Your EKG shows some abnormalities.
    I'm referring you to cardiology for evaluation of your chest pain.
    You need to see them as soon as possible, ideally within 24 hours.

    Patient: Is it serious?

    Doctor: We need to rule out any cardiac issues. I'll have my office
    call them right now to get you an urgent appointment.
    """

    print("Testing Medical Scribe Agent")
    print("=" * 80)
    print(f"\nInput Conversation:\n{conversation}\n")

    result = agent.extract_referrals(conversation)

    print("=" * 80)
    print("Extracted Referral Information:")
    print("=" * 80)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
