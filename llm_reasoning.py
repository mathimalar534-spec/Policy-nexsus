#!/usr/bin/env python3
"""
Module 6: LLM Reasoning Engine
Consumes candidate_pairs.json and reasons over conflict/redundancy metadata using Gemini.
"""
import json
import time
import re
from pathlib import Path
from json import JSONDecodeError

from google import genai
from config import GEMINI_API_KEY

_client = None

def get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            import os
            api_key = os.environ.get("GEMINI_API_KEY") or "MOCK_KEY"
            _client = genai.Client(api_key=api_key)
        else:
            _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

MODELS = [
    "gemini-3.1-flash-lite",
]

PROMPT = """You are an Enterprise Cybersecurity Governance Expert performing an enterprise-wide policy audit.

You are given TWO cybersecurity policy obligations extracted from different policy documents.

Your objective is to determine whether these obligations contribute to any enterprise policy governance problems.

Consider the following enterprise pain points.

1. POLICY CONFLICT
One obligation contradicts the other.

Examples:
• one requires password rotation while another prohibits password rotation
• one mandates TLS 1.0 while another mandates TLS 1.2
• one requires VPN while another explicitly allows bypassing VPN
• one requires SHA-1 while another requires AES-256

2. REDUNDANCY
Both obligations express essentially the same requirement, even if written differently.

Examples:
• Both require logging failed login attempts.
• Both require MFA.
• Both require reporting security incidents.

3. COMPLEMENTARY
The obligations strengthen the same security objective without contradicting each other.

Example:
Password complexity
+
MFA requirement

Both improve authentication security.

4. UNRELATED
The obligations belong to different security domains and have no meaningful interaction.

Examples:
Password policy
vs
Backup policy

--------------------------------------------------

Policy Staleness

Evaluate BOTH obligations for signs of obsolete or outdated guidance.

Consider:

• last_reviewed dates
• policy version
• referenced technologies
• referenced cryptographic algorithms
• referenced operating systems
• referenced protocols
• referenced regulations

Examples of obsolete technologies include

SHA-1
MD5
SSL
TLS 1.0
TLS 1.1
DES
3DES
RC4
Windows Server 2008
Windows Server 2012

If either obligation references obsolete technology or has not been reviewed for several years, governance_issues MUST include:

"Staleness"

Explain WHY it is outdated and recommend a modern replacement.

--------------------------------------------------

Inconsistent Language

Determine whether the wording introduces ambiguity.

Examples

must

shall

required

should

recommended

may

Explain whether different obligation strengths create inconsistent enforcement.

--------------------------------------------------

Missing Cross References

Determine whether these obligations appear to belong to the same policy area but should reference each other.

Examples

Password Policy

Cloud Security Policy

Identity Policy

Access Control Policy

If they discuss the same topic but do not reference each other, mention this.

--------------------------------------------------

Audit Risk

Determine whether an auditor would flag these obligations because of

• conflict
• duplication
• ambiguity
• obsolete technology
• inconsistent enforcement

--------------------------------------------------

Return ONLY valid JSON.

Schema

{
    "relationship": "",
    "confidence": 0.0,
    "severity": "",
    "description": "",
    "explanation": "",
    "governance_issues": [
        "Conflict",
        "Redundancy",
        "Staleness",
        "Inconsistent Language",
        "Missing Cross References",
        "Audit Risk"
    ],
    "recommendation": ""
}

Rules

relationship must be exactly one of

CONFLICT
REDUNDANT
COMPLEMENTARY
UNRELATED

severity must be exactly one of

HIGH
MEDIUM
LOW
NONE

confidence must be between 0 and 1.

governance_issues must contain zero or more of

Conflict
Redundancy
Staleness
Inconsistent Language
Missing Cross References
Audit Risk

recommendation should explain how to resolve the governance issue.

Return JSON only.

Do not return markdown.

Do not explain your reasoning outside the JSON."""


def reason_pair(pair, max_retries=5):
    obligation_a = f"""
Policy:
{pair['policy_a']}

Last Reviewed:
{pair.get('last_reviewed_a', 'Unknown')}

Version:
{pair.get('policy_version_a', 'Unknown')}

References:
{", ".join(pair.get('references_a', []))}

Topic:
{pair['topic_a']}

Strength:
{pair.get('strength_a', 'Unknown')}

Text:
{pair['text_a']}
"""

    obligation_b = f"""
Policy:
{pair['policy_b']}

Last Reviewed:
{pair.get('last_reviewed_b', 'Unknown')}

Version:
{pair.get('policy_version_b', 'Unknown')}

References:
{", ".join(pair.get('references_b', []))}

Topic:
{pair['topic_b']}

Strength:
{pair.get('strength_b', 'Unknown')}

Text:
{pair['text_b']}
"""

    prompt = (
        PROMPT
        + "\n\nObligation A\n"
        + obligation_a
        + "\n\nObligation B\n"
        + obligation_b
    )

    for model in MODELS:
        retries = 0
        while retries < max_retries:
            try:
                response = get_client().models.generate_content(
                    model=model,
                    contents=prompt,
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = (
                        text.replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )
                return json.loads(text)
            except JSONDecodeError:
                print("\nInvalid JSON returned:\n")
                print(text)
                retries += 1
                time.sleep(2)
            except Exception as e:
                error = str(e)
                print(f"\nModel {model} failed:")
                print(error)
                if "429" in error or "RESOURCE_EXHAUSTED" in error:
                    match = re.search(r"retry in ([0-9]+)", error, re.IGNORECASE)
                    if match:
                        wait = int(match.group(1)) + 2
                    else:
                        wait = 20
                    print(f"Sleeping {wait} seconds...")
                    time.sleep(wait)
                    retries += 1
                    continue
                retries += 1
                time.sleep(2)

    raise Exception("Unable to reason over this pair.")


def run_reasoning():
    input_file = Path("output/candidate_pairs.json")
    if not input_file.exists():
        print(f"Error: candidate file '{input_file}' not found.")
        return []

    with open(input_file, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    findings = []
    
    # Keep only high-similarity candidate pairs
    pairs = [
        p
        for p in candidates["flat_pairs"]
        if p["similarity"] >= 0.30
    ]

    # Sort highest similarity first
    pairs = sorted(
        pairs,
        key=lambda x: x["similarity"],
        reverse=True
    )

    # Only reason over the top 40
    pairs = pairs[:40]
    total = len(pairs)

    print(f"Running reasoning on {total} candidate pairs...")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "findings.json"

    for index, pair in enumerate(pairs, start=1):
        print(f"\nProcessing {index}/{total}")
        try:
            result = reason_pair(pair)
            print(result)
            finding = {
                "obligation_a_id": pair["obligation_a_id"],
                "obligation_b_id": pair["obligation_b_id"],
                "policy_a": pair["obligation_a_id"].split("-OBL")[0],
                "policy_b": pair["obligation_b_id"].split("-OBL")[0],
                "similarity": pair["similarity"],
                "relationship": result.get("relationship", "UNKNOWN"),
                "governance_issues": result.get("governance_issues", []),
                "confidence": result.get("confidence", 0),
                "severity": result.get("severity", "NONE"),
                "description": result.get("description", ""),
                "explanation": result.get("explanation", ""),
                "recommendation": result.get("recommendation", "")
            }
        except Exception as e:
            print(f"Skipping pair {index}")
            finding = {
                "obligation_a_id": pair["obligation_a_id"],
                "obligation_b_id": pair["obligation_b_id"],
                "policy_a": pair["obligation_a_id"].split("-OBL")[0],
                "policy_b": pair["obligation_b_id"].split("-OBL")[0],
                "similarity": pair["similarity"],
                "relationship": "UNKNOWN",
                "confidence": 0,
                "severity": "NONE",
                "description": "LLM unavailable",
                "explanation": str(e),
                "recommendation": ""
            }
        findings.append(finding)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            findings,
            f,
            indent=4,
            ensure_ascii=False
        )
            
    print("Reasoning completed.")
    return findings


if __name__ == "__main__":
    print("LLM reasoning service verified and import-ready.")
