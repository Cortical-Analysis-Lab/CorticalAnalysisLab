#!/usr/bin/env python3
"""Revisit existing catalog rows that still have optional N/A values.

This agent is for reruns after cycles open. It does not create new opportunities;
it refreshes existing records from official-source enrichment passes and keeps an
audit trail of fields that remain unavailable.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import ROOT
from enrich_nsf_optional_fields import audit_and_update


LOCAL_DIR = ROOT / "database" / "local"
DEFAULT_REPORT = LOCAL_DIR / "review" / "catalog_update_reinvestigation_report.json"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def run_command(label, args):
    try:
        result = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        output = "\n".join(part for part in (error.stdout, error.stderr) if part)
        return {"command": label, "status": "failed", "output": output[-12000:]}
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return {"command": label, "status": "complete", "output": output[-12000:]}


def reinvestigate(seed, output_dir, report_path, delay=0.02, rebuild=True):
    started_at = now_utc()
    report = {
        "started_at": started_at,
        "updated_at": started_at,
        "status": "running",
        "scope": "existing catalog rows with optional N/A values",
        "commands": [],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    nsf = audit_and_update(seed, output_dir, delay)
    report["nsf_optional_field_audit"] = {
        "reviewed": nsf["reviewed"],
        "updated": nsf["updated"],
        "confirmed": nsf["confirmed"],
        "audit_csv": str(nsf["audit_csv"]),
        "audit_md": str(nsf["audit_md"]),
    }
    report["updated_at"] = now_utc()
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if rebuild:
        for label, args in (
            ("rebuild_database.py", [ROOT / "scripts" / "rebuild_database.py"]),
            ("test_catalog.py", [ROOT / "scripts" / "test_catalog.py"]),
            ("export_review_xlsx.py", [ROOT / "scripts" / "export_review_xlsx.py"]),
            ("log_incomplete_catalog_data.py", [ROOT / "scripts" / "log_incomplete_catalog_data.py"]),
        ):
            command = run_command(label, args)
            report["commands"].append(command)
            report["updated_at"] = now_utc()
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            if command["status"] != "complete":
                report["status"] = "failed"
                report["completed_at"] = now_utc()
                report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                return report

    report["status"] = "complete"
    report["completed_at"] = now_utc()
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv")
    parser.add_argument("--output-dir", type=Path, default=LOCAL_DIR / "review")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--delay", type=float, default=0.02)
    parser.add_argument("--no-rebuild", action="store_true")
    args = parser.parse_args()
    report = reinvestigate(args.seed, args.output_dir, args.report, args.delay, not args.no_rebuild)
    print(json.dumps({
        "status": report["status"],
        "updated": report["nsf_optional_field_audit"]["updated"],
        "confirmed": report["nsf_optional_field_audit"]["confirmed"],
        "audit_csv": report["nsf_optional_field_audit"]["audit_csv"],
        "report": str(args.report),
    }, indent=2))
    raise SystemExit(0 if report["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
