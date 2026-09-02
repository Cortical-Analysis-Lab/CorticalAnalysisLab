#!/usr/bin/env python3
"""Run the local end-to-end catalog update pipeline."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from automated_investigate_candidates import run as investigate
from catalog_common import ROOT
from catalog_staging import investigation_counts
from validate_agent_results import validate_results


LOCAL_DIR = ROOT / "database" / "local"
PIPELINE_REPORT = LOCAL_DIR / "pipeline_report.json"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def pending_count():
    counts = investigation_counts()["by_review_status"]
    return counts.get("pending", 0) + counts.get("needs_review", 0)


def command_text(args):
    return " ".join(Path(str(arg)).name if str(arg).endswith(".py") else str(arg) for arg in args)


def run_command(args):
    result = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True, capture_output=True, text=True)
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def run_pipeline_command(report, label, args):
    try:
        output = run_command(args)
    except subprocess.CalledProcessError as error:
        output = "\n".join(part for part in (error.stdout, error.stderr) if part)
        report["commands"].append({"command": label, "status": "failed", "output": output[-12000:]})
        report["status"] = "failed"
        report["completed_at"] = now_utc()
        report["updated_at"] = report["completed_at"]
        write_report(report)
        return False
    report["commands"].append({"command": label, "status": "complete", "output": output[-12000:]})
    report["updated_at"] = now_utc()
    write_report(report)
    return True


def write_report(report):
    PIPELINE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run_pipeline(batch_size=100, max_batches=None, delay=0.05, promote=True, rebuild=True):
    started_at = now_utc()
    starting_pending = pending_count()
    if max_batches is None:
        max_batches = max(1, math.ceil(starting_pending / batch_size)) if starting_pending else 0
    report = {
        "started_at": started_at,
        "updated_at": started_at,
        "status": "running",
        "batch_size": batch_size,
        "starting_pending": starting_pending,
        "max_batches": max_batches,
        "batches": [],
        "validation_errors": [],
        "commands": [],
        "source_audit": {
            "csv": str(LOCAL_DIR / "source_audit" / "retrieved_sources.csv"),
            "markdown": str(LOCAL_DIR / "source_audit" / "retrieved_sources.md"),
        },
    }
    write_report(report)
    batch_number = 0
    while pending_count() > 0 and (max_batches is None or batch_number < max_batches):
        batch_number += 1
        result = investigate(batch_size, delay=delay)
        report["batches"].append(result)
        report["updated_at"] = now_utc()
        write_report(report)
        if result["checked"] == 0:
            break

    errors = validate_results()
    report["validation_errors"] = errors
    if errors:
        report["status"] = "failed"
        report["completed_at"] = now_utc()
        write_report(report)
        return report

    if promote:
        args = [ROOT / "scripts" / "promote_catalog_candidates.py", "--approved-only"]
        if not run_pipeline_command(report, "promote_catalog_candidates.py --approved-only", args):
            return report
        args = [ROOT / "scripts" / "reinvestigate_catalog_updates.py", "--no-rebuild"]
        if not run_pipeline_command(report, "reinvestigate_catalog_updates.py --no-rebuild", args):
            return report
    if rebuild:
        for command, args in (
            ("rebuild_database.py", [ROOT / "scripts" / "rebuild_database.py"]),
            ("test_catalog.py", [ROOT / "scripts" / "test_catalog.py"]),
            ("export_review_xlsx.py", [ROOT / "scripts" / "export_review_xlsx.py"]),
            ("log_incomplete_catalog_data.py", [ROOT / "scripts" / "log_incomplete_catalog_data.py"]),
        ):
            if not run_pipeline_command(report, command, args):
                return report
        try:
            diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            output = "\n".join(part for part in (error.stdout, error.stderr) if part)
            report["commands"].append({"command": "git diff --check", "status": "failed", "output": output[-12000:]})
            report["status"] = "failed"
            report["completed_at"] = now_utc()
            report["updated_at"] = report["completed_at"]
            write_report(report)
            return report
        report["commands"].append({"command": "git diff --check", "status": "complete", "output": "\n".join(part for part in (diff.stdout, diff.stderr) if part)})

    report["status"] = "complete"
    report["completed_at"] = now_utc()
    report["final_counts"] = investigation_counts()
    write_report(report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--no-promote", action="store_true")
    parser.add_argument("--no-rebuild", action="store_true")
    args = parser.parse_args()
    report = run_pipeline(args.batch_size, args.max_batches, args.delay, not args.no_promote, not args.no_rebuild)
    print(json.dumps({
        "status": report["status"],
        "batches": len(report["batches"]),
        "checked": sum(batch["checked"] for batch in report["batches"]),
        "approved": sum(batch["approved"] for batch in report["batches"]),
        "rejected": sum(batch["rejected"] for batch in report["batches"]),
        "unresolved": sum(batch["unresolved"] for batch in report["batches"]),
        "report": str(PIPELINE_REPORT),
        "source_audit": report["source_audit"],
    }, indent=2))
    raise SystemExit(0 if report["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
