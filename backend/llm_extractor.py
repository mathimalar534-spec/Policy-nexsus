#!/usr/bin/env python3
"""
Policy-Conflict-Staleness-Detector/backend/llm_extractor.py
"""
import json
from json import JSONDecodeError

from google import genai

from config import GEMINI_API_KEY


_client = None

def get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            # Fallback to check environment directly or raise clean message
            import os
            api_key = os.environ.get("GEMINI_API_KEY") or "MOCK_KEY"
            _client = genai.Client(api_key=api_key)
        else:
            _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

PROMPT = """
You are an expert Enterprise Cybersecurity Governance Analyst.

You are given an ENTIRE cybersecurity policy document.

Your task is to extract ONLY enforceable policy obligations.

Ignore these as obligations, but extract them as metadata if present.

Metadata to extract once for every obligation:

- Policy Title
- References (standards, regulations, technologies)

Do NOT treat metadata as obligations.

Extract ONLY statements that impose requirements, permissions, recommendations or prohibitions.

Examples

Mandatory
- must
- shall
- required

Recommended
- should
- recommended

Prohibited
- must not
- shall not
- prohibited

Optional
- may

Return ONLY JSON.

Schema

[
{
"id":"",
"policy_name":"",
"policy_version":"",
"last_reviewed":"",
"references":[],
"topic":"",
"actor":"",
"action":"",
"object":"",
"strength":"",
"scope":"",
"reference":"",
"original_text":""
}
]

The fields policy_name, policy_version and last_reviewed are document-level metadata.

Extract them from the policy header and copy them into EVERY obligation.

references must contain every technology, framework, standard, regulation or platform explicitly mentioned in the obligation or elsewhere in the policy that applies to it.

Examples:

SHA-1
MD5
TLS 1.0
TLS 1.1
TLS 1.2
SSL
Windows Server 2012
Windows Server 2008
PCI DSS
ISO 27001
NIST SP 800-63B
GDPR
HIPAA
SOX

Rules

• One JSON object per obligation.

• Preserve the original wording.

• Copy the following metadata into EVERY obligation:

  - policy_name
  - policy_version
  - last_reviewed
  - references

• references must be a JSON array.

Example

"references":[
"NIST SP 800-63B",
"SHA-1",
"Windows Server 2012"
]

If a value is not available, use an empty string or empty list.

Do not invent metadata.

Return ONLY JSON."""

# Ordered by preference
MODELS = [
     "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
]


class LLMUnavailableError(Exception):
    """Raised when all Gemini models are unavailable."""
    pass


class LLMOutputError(Exception):
    """Raised when the model returns invalid output."""
    pass


def extract_obligations(policy_text: str, policy_name: str):
    """
    Extract obligations from a policy document using Gemini.
    Automatically falls back to other Gemini models if one is unavailable.
    """

    last_error = None

    for model in MODELS:

        try:
            print(f"\nTrying model: {model}")

            response = get_client().models.generate_content(
                model=model,
                contents=(
                PROMPT
                + f"\n\nPolicy Name: {policy_name}"
                + "\n\nPolicy Document:\n"
                + policy_text
            ),
        
        )

            text = response.text.strip()

            # Remove Markdown code fences if present
            if text.startswith("```"):
                text = (
                    text.replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            try:
                obligations = json.loads(text)

            except JSONDecodeError as e:
                raise LLMOutputError(
                    f"{model} returned invalid JSON.\n\nResponse:\n{text}"
                ) from e

            if not isinstance(obligations, list):
                raise LLMOutputError(
                    f"{model} returned an unexpected response format."
                )

            # Auto-generate IDs
            for i, obj in enumerate(obligations, start=1):
                obj["id"] = f"{policy_name}-OBL-{i:03d}"

            print(f"✓ Successfully extracted obligations using {model}")

            return obligations

        except LLMOutputError:
            # Prompt/model output problem.
            # Don't try another model because it usually won't help.
            raise

        except Exception as e:

            error = str(e)

            # Retry only for temporary service issues
            if any(
                keyword.lower() in error.lower()
                for keyword in [
                    "503",
                    "429",
                    "UNAVAILABLE",
                    "RESOURCE_EXHAUSTED",
                    "DEADLINE_EXCEEDED",
                    "INTERNAL",
                    "not found",
                    "404",
                ]
            ):

                print(f"⚠ {model} unavailable.")
                print(error)
                print("Trying next model...\n")

                last_error = e
                continue

            # Unknown error - surface immediately
            raise

    raise LLMUnavailableError(
        "All configured Gemini models are currently unavailable. "
        "Please try again in a few minutes."
    ) from last_error

if __name__ == "__main__":
    print("LLM extractor module initialized.")
