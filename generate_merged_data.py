#!/usr/bin/env python3
"""
Build merged/joined datasets so findings and obligations are easy to
identify without cross-referencing policy_metadata separately.

Outputs:
  - findings_merged.csv / .json   (80 rows: findings + full metadata for
                                    every referenced policy)
  - obligations_merged.csv / .json (350 rows: obligations + full metadata
                                     for their policy)
"""
import json
import csv
from pathlib import Path

# Path configurations aligned for local workspace prototyping
UPLOADS = Path("sample_data")
OUT_DIR = Path("sample_data/merged")
OUT_DIR.mkdir(exist_ok=True)

metadata = json.load(open(UPLOADS / "policy_metadata.json", encoding="utf-8"))
obligations = json.load(open(UPLOADS / "obligation_extracts_labels.json", encoding="utf-8"))
findings = json.load(open(UPLOADS / "findings_labels.json", encoding="utf-8"))

meta_by_file = {m["file"]: m for m in metadata}


def meta_cols(file_name, prefix):
    """Return metadata fields for a policy file, prefixed (e.g. policy_a_title)."""
    if not file_name:
        return {f"{prefix}_{k}": "" for k in ("title", "department", "author", "version", "last_reviewed", "status")}
    m = meta_by_file.get(file_name, {})
    return {
        f"{prefix}_title": m.get("title", ""),
        f"{prefix}_department": m.get("department", ""),
        f"{prefix}_author": m.get("author", ""),
        f"{prefix}_version": m.get("version", ""),
        f"{prefix}_last_reviewed": m.get("last_reviewed", ""),
        f"{prefix}_status": m.get("status", ""),
    }


# ---------- Findings merged ----------
findings_merged = []
for f in findings:
    row = dict(f)  # finding_type, finding_subtype, severity, policy/policy_a/policy_b, description, explanation
    policy = f.get("policy")
    policy_a = f.get("policy_a")
    policy_b = f.get("policy_b")

    if policy:
        row.update(meta_cols(policy, "policy"))
    else:
        row.update(meta_cols(policy_a, "policy_a"))
        row.update(meta_cols(policy_b, "policy_b"))

    findings_merged.append(row)

# Normalize columns across all rows (single-policy rows won't have policy_a_* etc.)
all_keys = []
for row in findings_merged:
    for k in row:
        if k not in all_keys:
            all_keys.append(k)
for row in findings_merged:
    for k in all_keys:
        row.setdefault(k, "")

with open(OUT_DIR / "findings_merged.json", "w", encoding="utf-8") as fp:
    json.dump(findings_merged, fp, indent=2)

with open(OUT_DIR / "findings_merged.csv", "w", newline="", encoding="utf-8") as fp:
    writer = csv.DictWriter(fp, fieldnames=all_keys)
    writer.writeheader()
    writer.writerows(findings_merged)

# ---------- Obligations merged ----------
obligations_merged = []
for o in obligations:
    row = dict(o)  # policy_file, obligation_text, topic, strength, scope
    row.update(meta_cols(o["policy_file"], "policy"))
    obligations_merged.append(row)

obl_keys = list(obligations_merged[0].keys()) if obligations_merged else []

with open(OUT_DIR / "obligations_merged.json", "w", encoding="utf-8") as fp:
    json.dump(obligations_merged, fp, indent=2)

with open(OUT_DIR / "obligations_merged.csv", "w", newline="", encoding="utf-8") as fp:
    writer = csv.DictWriter(fp, fieldnames=obl_keys)
    writer.writeheader()
    writer.writerows(obligations_merged)

print(f"findings_merged: {len(findings_merged)} rows, {len(all_keys)} columns")
print(f"obligations_merged: {len(obligations_merged)} rows, {len(obl_keys)} columns")
