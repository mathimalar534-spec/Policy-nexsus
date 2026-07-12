#!/usr/bin/env python3
"""
Build policies/*.md from policy_metadata.json + obligation_extracts_labels.json
(+ findings_labels.json, used only to decide which policies get a
'deprecated reference' line for STALE_REFERENCE findings).

The generated documents are deliberately written so that every obligation's
exact `obligation_text` string appears verbatim in the corresponding policy
document, and every STALE_REFERENCE policy contains a clearly deprecated
technology/regulation mention -- so that a downstream extraction pipeline
run against these documents reproduces the supplied label files.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

# Paths adjusted for local workspace prototyping
UPLOADS = Path("sample_data")
OUT_DIR = Path("sample_data/policies")

metadata = json.load(open(UPLOADS / "policy_metadata.json", encoding="utf-8"))
obligations = json.load(open(UPLOADS / "obligation_extracts_labels.json", encoding="utf-8"))
findings = json.load(open(UPLOADS / "findings_labels.json", encoding="utf-8"))

meta_by_file = {m["file"]: m for m in metadata}

obs_by_file = defaultdict(list)
for o in obligations:
    obs_by_file[o["policy_file"]].append(o)

stale_reference_files = {
    f["policy"] for f in findings if f.get("finding_subtype") == "STALE_REFERENCE"
}
stale_policy_files = {
    f["policy"] for f in findings if f.get("finding_subtype") == "STALE_POLICY"
}

# Deprecated tech / regulation call-outs, cycled deterministically per file
DEPRECATED_REFERENCES = [
    "SHA-1 hashing",
    "TLS 1.0",
    "the pre-2018 draft of the EU Data Protection Directive (superseded by GDPR)",
    "SSL 3.0",
    "Windows Server 2008 R2",
    "the 1996 HIPAA Security Rule guidance (pre-Omnibus Rule)",
    "WEP wireless encryption",
    "the Safe Harbor framework (invalidated in 2015)",
]

SECTION_INTROS = {
    "backup": "Backup and recovery obligations ensure business continuity in the event of data loss.",
    "password": "Password obligations govern how credentials are created, stored, and rotated.",
    "access": "Access control obligations define who may reach which systems and data.",
    "asset": "Asset management obligations cover the tracking and disposal of company assets.",
    "mobile": "Mobile device obligations apply to any device used to access company resources.",
    "third-party": "Third-party obligations govern engagements with vendors and external partners.",
    "HR": "HR obligations apply to onboarding, offboarding, and personnel security practices.",
    "data retention": "Data retention obligations set minimum and maximum retention periods for records.",
    "encryption": "Encryption obligations specify how data must be protected at rest and in transit.",
    "endpoint": "Endpoint obligations apply to laptops, workstations, and other managed endpoints.",
    "logging": "Logging obligations define what activity must be recorded and for how long.",
    "network": "Network obligations govern segmentation, firewalling, and perimeter defenses.",
    "cloud": "Cloud obligations apply to infrastructure and services hosted with cloud providers.",
    "change": "Change management obligations govern how modifications to production systems are approved.",
    "monitoring": "Monitoring obligations define what systems must be observed and alerted on.",
    "patch": "Patch management obligations set expectations for applying security updates.",
    "physical": "Physical security obligations cover access to offices, data centers, and equipment.",
    "privacy": "Privacy obligations govern the collection, use, and disclosure of personal data.",
    "provisioning": "Provisioning obligations define how user accounts are created and deprovisioned.",
    "vendor": "Vendor obligations apply to the selection and oversight of external suppliers.",
    "api": "API obligations govern how internal and external interfaces must be secured.",
}

STRENGTH_LABEL = {
    "must": "Mandatory",
    "required": "Mandatory",
    "shall": "Mandatory",
    "should": "Recommended",
    "recommended": "Recommended",
    "prohibited": "Prohibited",
}


def slugify(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")


def build_document(file_name: str) -> str:
    meta = meta_by_file[file_name]
    obs = obs_by_file[file_name]

    lines = []
    # --- Front matter ---
    lines.append("---")
    lines.append(f"title: {meta['title']}")
    lines.append(f"author: {meta['author']}")
    lines.append(f"department: {meta['department']}")
    lines.append(f"version: {meta['version']}")
    lines.append(f"last_reviewed: {meta['last_reviewed']}")
    lines.append(f"status: {meta['status']}")
    lines.append("---")
    lines.append("")

    # --- Title ---
    lines.append(f"# {meta['title']}")
    lines.append("")
    lines.append(f"**Version:** {meta['version']}  ")
    lines.append(f"**Owner:** {meta['author']} ({meta['department']})  ")
    lines.append(f"**Last Reviewed:** {meta['last_reviewed']}  ")
    lines.append(f"**Status:** {meta['status'].capitalize()}")
    lines.append("")

    # --- Purpose ---
    lines.append("## 1. Purpose")
    lines.append("")
    lines.append(
        f"This document establishes the {meta['title'].lower()} for the "
        f"organization. It is maintained by the {meta['department']} "
        f"department and applies to all personnel and systems in scope "
        f"below."
    )
    lines.append("")

    # --- Scope ---
    lines.append("## 2. Scope")
    lines.append("")
    scopes = sorted({o["scope"] for o in obs})
    lines.append(
        "This policy applies to the following groups: "
        + ", ".join(scopes)
        + "."
    )
    lines.append("")

    # --- Obligations, grouped by topic ---
    lines.append("## 3. Obligations")
    lines.append("")
    topics_in_order = []
    for o in obs:
        if o["topic"] not in topics_in_order:
            topics_in_order.append(o["topic"])

    section_num = 1
    for topic in topics_in_order:
        topic_obs = [o for o in obs if o["topic"] == topic]
        heading = topic[0].upper() + topic[1:]
        lines.append(f"### 3.{section_num} {heading}")
        lines.append("")
        intro = SECTION_INTROS.get(topic)
        if intro:
            lines.append(intro)
            lines.append("")
        for o in topic_obs:
            label = STRENGTH_LABEL.get(o["strength"], o["strength"].capitalize())
            lines.append(f"- **[{label}]** {o['obligation_text']}")
        lines.append("")
        section_num += 1

    # --- References (only for STALE_REFERENCE-labeled policies) ---
    if file_name in stale_reference_files:
        idx = int(file_name.split("_")[1].split(".")[0]) % len(DEPRECATED_REFERENCES)
        ref = DEPRECATED_REFERENCES[idx]
        lines.append("## 4. References")
        lines.append("")
        lines.append(
            f"This policy's technical baseline is defined with reference to "
            f"{ref}, as adopted at the time of the last major revision."
        )
        lines.append("")

    # --- Review history ---
    lines.append("## 5. Review History")
    lines.append("")
    lines.append("| Version | Reviewed | Reviewer | Notes |")
    lines.append("|---|---|---|---|")
    note = (
        "Overdue for review; scheduled review cycle exceeded."
        if file_name in stale_policy_files
        else "Reviewed on schedule."
    )
    lines.append(f"| {meta['version']} | {meta['last_reviewed']} | {meta['author']} | {note} |")
    lines.append("")

    return "\n".join(lines)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for meta in metadata:
        file_name = meta["file"]
        content = build_document(file_name)
        (OUT_DIR / file_name).write_text(content, encoding="utf-8")
    print(f"Wrote {len(metadata)} policy documents to {OUT_DIR}")


if __name__ == "__main__":
    main()
