#!/usr/bin/env python3
"""Flag catalog records that need factual review beyond structural validation."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from catalog_common import ROOT, disallowed_verification_source, is_funding_identity_url, load_rows, text_or_none


DEFAULT_IMPORT = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"
DEFAULT_OUTPUT = ROOT / "database" / "local" / "review" / "catalog_accuracy_audit.csv"
DEFAULT_SUMMARY = ROOT / "database" / "local" / "review" / "catalog_accuracy_audit.md"

REQUIRED_FACT_FIELDS = (
    "Duration_Weeks",
    "Program_Start",
    "Program_End",
    "Application_Open",
    "Application_Deadline",
    "Stipend_Total_USD",
    "Stipend_Weekly_USD",
)

NON_PROGRAM_TITLE_TERMS = (
    "conference:",
    "workshop",
    "abstract book",
    "where are they now",
    "history of",
    "alumni",
)

HUB_TITLE_TERMS = (
    "summer research programs",
    "summer research opportunities",
    "summer research & medical fellowships",
    "student research opportunities",
)

HUB_PATH_TERMS = (
    "/opportunities",
    "/resources",
    "/programs",
    "/pre-health-resources/",
)


def normalized(value):
    return (text_or_none(value) or "").strip()


def is_blank(value):
    value = normalized(value)
    return not value or value.upper() == "N/A"


def is_funding_url(value):
    return is_funding_identity_url(value)


def is_award_only(row):
    checked_by = normalized(row.get("Eligibility_Checked_By")).lower()
    network_source = normalized(row.get("Network_Source")).lower()
    return (
        is_funding_url(row.get("Program_URL"))
        and (
            checked_by in {"", "automated_nsf_metadata", "local automated pipeline; official program source"}
            or network_source == "nsf_awards_reu_site"
            or normalized(row.get("Program_ID")).startswith("NSF-REU-")
        )
    )


def path_text(url):
    parsed = urlparse(normalized(url))
    return parsed.path.replace("-", " ").replace("_", " ").lower()


def issue(row, severity, code, reason, field="record"):
    return {
        "Severity": severity,
        "Issue_Code": code,
        "Program_ID": normalized(row.get("Program_ID")),
        "Program_Name": normalized(row.get("Program_Name")),
        "Host_Institution": normalized(row.get("Host_Institution")),
        "Field": field,
        "Program_URL": normalized(row.get("Program_URL")),
        "Reason": reason,
    }


def audit_rows(rows):
    findings = []
    by_url = defaultdict(list)
    by_identity = defaultdict(list)

    for row in rows:
        program_url = normalized(row.get("Program_URL"))
        title = normalized(row.get("Program_Name")).lower()
        path = path_text(program_url)
        identity = (
            normalized(row.get("Host_Institution")).lower(),
            normalized(row.get("Program_Name")).lower(),
        )
        if program_url:
            by_url[program_url.lower()].append(row)
        by_identity[identity].append(row)

        if disallowed_verification_source(program_url):
            findings.append(issue(
                row,
                "error",
                "discovery_only_program_url",
                "Program URL is a discovery-only, social, article, outcome, listing, or funding identity page and cannot verify a canonical record.",
                "Program_URL",
            ))
        if is_funding_identity_url(program_url):
            findings.append(issue(
                row,
                "error",
                "funding_identity_record",
                "Funding/award/grant records are discovery leads only and must not be canonical opportunity records.",
                "Program_URL",
            ))
        if is_award_only(row):
            findings.append(issue(
                row,
                "review",
                "award_metadata_only",
                "Funding or award metadata is a discovery lead only; host-page review is required for current cycle dates, benefits, application URL, location, and host-specific eligibility.",
                "Program_URL",
            ))
        if any(term in title for term in NON_PROGRAM_TITLE_TERMS):
            findings.append(issue(
                row,
                "error",
                "non_program_title",
                "Title looks like a conference, workshop, archive, historical recap, or other non-program page.",
                "Program_Name",
            ))
        if any(term in title for term in HUB_TITLE_TERMS) or any(term in path for term in HUB_PATH_TERMS):
            findings.append(issue(
                row,
                "review",
                "possible_hub_or_listing",
                "Record may be a hub/listing page. Use it for discovery unless the page is the maintained canonical program page.",
                "Program_URL",
            ))
        if normalized(row.get("Eligibility_Parse_Status")) == "reviewed" and is_award_only(row):
            findings.append(issue(
                row,
                "error",
                "award_only_eligibility_marked_reviewed",
                "Award-only records must not mark host-specific eligibility as reviewed.",
                "Eligibility_Parse_Status",
            ))
        if is_funding_url(row.get("Application_URL")):
            findings.append(issue(
                row,
                "error",
                "award_url_used_as_application",
                "Funding or award pages are not application pages.",
                "Application_URL",
            ))
        missing = [field for field in REQUIRED_FACT_FIELDS if is_blank(row.get(field))]
        if missing:
            findings.append(issue(
                row,
                "info",
                "incomplete_cycle_facts",
                f"Missing or N/A cycle/detail fields: {', '.join(missing)}.",
                "cycle_fields",
            ))

    for url, matches in by_url.items():
        ids = sorted(normalized(row.get("Program_ID")) for row in matches)
        if len(matches) > 1 and "btaa.org/resources-for/students/srop/campus-profiles" not in url:
            for row in matches:
                findings.append(issue(
                    row,
                    "review",
                    "duplicate_program_url",
                    f"Program URL is shared by multiple records: {', '.join(ids)}.",
                    "Program_URL",
                ))

    for (_institution, _name), matches in by_identity.items():
        ids = sorted(normalized(row.get("Program_ID")) for row in matches)
        if len(matches) > 1:
            for row in matches:
                findings.append(issue(
                    row,
                    "review",
                    "duplicate_identity",
                    f"Same institution/program-name identity appears multiple times: {', '.join(ids)}.",
                    "Program_Name",
                ))

    return findings


def write_outputs(findings, output, summary):
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Severity", "Issue_Code", "Program_ID", "Program_Name", "Host_Institution", "Field", "Program_URL", "Reason"]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(findings)

    counts = Counter((row["Severity"], row["Issue_Code"]) for row in findings)
    lines = ["# Catalog Accuracy Audit", ""]
    lines.append(f"Findings: {len(findings)}")
    lines.append("")
    for (severity, code), count in counts.most_common():
        lines.append(f"- {count} {severity} {code}")
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_IMPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    findings = audit_rows(load_rows(args.input))
    write_outputs(findings, args.output, args.summary)
    counts = Counter(row["Severity"] for row in findings)
    report = {
        "findings": len(findings),
        "by_severity": dict(sorted(counts.items())),
        "output": str(args.output),
        "summary": str(args.summary),
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Catalog accuracy audit wrote {len(findings)} findings to {args.output}")
        print(", ".join(f"{key}={value}" for key, value in sorted(counts.items())))


if __name__ == "__main__":
    main()
