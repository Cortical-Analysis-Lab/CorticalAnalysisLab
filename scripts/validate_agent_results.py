#!/usr/bin/env python3
"""Validate Desktop Codex catalog-investigation result files.

The validator intentionally covers the repository's local handoff contract without
adding a runtime dependency on a full JSON Schema implementation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog_common import ROOT, disallowed_verification_source, valid_url


CONTRACT_VERSION = "1.0"
DEFAULT_RESULTS_DIR = ROOT / "database" / "local" / "agent_results"
REQUIRED_FILES = {
    "proposed_records.json": ("records",),
    "source_evidence.json": ("evidence",),
    "session_report.json": ("summary", "counts"),
}
APPROVED_SOURCE_TYPES = {
    "official_program",
    "official_institution",
    "official_government",
    "official_network",
    "official_application",
}
MATCH_STATES = {
    "NEW_PROGRAM",
    "EXISTING_PROGRAM",
    "POSSIBLE_DUPLICATE",
    "NEW_CYCLE_FOR_EXISTING_PROGRAM",
    "AMBIGUOUS",
}


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Missing required result file: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"{path.name}: invalid JSON: {error}") from None


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def validate_top_level(name, payload, required, errors):
    require(isinstance(payload, dict), f"{name}: expected an object", errors)
    if not isinstance(payload, dict):
        return
    require(payload.get("contract_version") == CONTRACT_VERSION, f"{name}: contract_version must be {CONTRACT_VERSION}", errors)
    require(isinstance(payload.get("generated_at"), str) and payload.get("generated_at"), f"{name}: generated_at is required", errors)
    for key in required:
        require(key in payload, f"{name}: missing {key}", errors)


def validate_proposed_records(payload, errors):
    records = payload.get("records")
    require(isinstance(records, list), "proposed_records.json: records must be an array", errors)
    if not isinstance(records, list):
        return
    seen = set()
    for index, record in enumerate(records):
        label = f"proposed_records.json records[{index}]"
        require(isinstance(record, dict), f"{label}: expected object", errors)
        if not isinstance(record, dict):
            continue
        candidate_id = record.get("candidate_id")
        require(isinstance(candidate_id, str) and candidate_id, f"{label}: candidate_id is required", errors)
        require(isinstance(record.get("proposal_version"), str) and record.get("proposal_version"), f"{label}: proposal_version is required", errors)
        if candidate_id:
            require(candidate_id not in seen, f"{label}: duplicate candidate_id {candidate_id}", errors)
            seen.add(candidate_id)
        identity = record.get("identity")
        require(isinstance(identity, dict), f"{label}: identity is required", errors)
        if isinstance(identity, dict):
            require(identity.get("match_state") in MATCH_STATES, f"{label}: unsupported match_state", errors)
            require(identity.get("program_name") is None or isinstance(identity.get("program_name"), str), f"{label}: program_name must be string/null", errors)
            require(identity.get("institution_name") is None or isinstance(identity.get("institution_name"), str), f"{label}: institution_name must be string/null", errors)
        cycle_year = record.get("cycle_year")
        require(cycle_year is None or (isinstance(cycle_year, int) and 2000 <= cycle_year <= 2200), f"{label}: invalid cycle_year", errors)
        require(isinstance(record.get("classification"), dict), f"{label}: classification is required", errors)
        require(isinstance(record.get("fields"), dict), f"{label}: fields must be an object", errors)
        for key in ("conditional_rules", "conflicts", "validation_warnings"):
            value = record.get(key, [])
            require(isinstance(value, list), f"{label}: {key} must be an array when present", errors)


def validate_source_evidence(payload, proposed_ids, errors):
    evidence = payload.get("evidence")
    require(isinstance(evidence, list), "source_evidence.json: evidence must be an array", errors)
    if not isinstance(evidence, list):
        return
    official_by_candidate = set()
    for index, item in enumerate(evidence):
        label = f"source_evidence.json evidence[{index}]"
        require(isinstance(item, dict), f"{label}: expected object", errors)
        if not isinstance(item, dict):
            continue
        candidate_id = item.get("candidate_id")
        source_url = item.get("source_url")
        source_type = item.get("source_type")
        authoritative = item.get("authoritative")
        fields_supported = item.get("fields_supported")
        require(candidate_id in proposed_ids, f"{label}: candidate_id does not match a proposed record", errors)
        require(isinstance(source_url, str) and valid_url(source_url), f"{label}: source_url must be an HTTP(S) URL", errors)
        require(source_type in APPROVED_SOURCE_TYPES | {"discovery_only"}, f"{label}: unsupported source_type", errors)
        require(isinstance(authoritative, bool), f"{label}: authoritative must be boolean", errors)
        require(isinstance(fields_supported, list), f"{label}: fields_supported must be an array", errors)
        require(isinstance(item.get("evidence_hash"), str) and len(item.get("evidence_hash", "")) >= 12, f"{label}: evidence_hash is required", errors)
        if source_url and disallowed_verification_source(source_url):
            require(source_type == "discovery_only" and authoritative is False, f"{label}: social/aggregator URLs are discovery-only", errors)
        if authoritative and source_type in APPROVED_SOURCE_TYPES and fields_supported:
            official_by_candidate.add(candidate_id)
    for candidate_id in proposed_ids:
        require(candidate_id in official_by_candidate, f"{candidate_id}: at least one authoritative official evidence item is required", errors)


def validate_session_report(payload, errors):
    counts = payload.get("counts")
    require(isinstance(payload.get("summary"), str), "session_report.json: summary is required", errors)
    require(isinstance(counts, dict), "session_report.json: counts must be an object", errors)
    if isinstance(counts, dict):
        for key in ("discovered", "existing", "ambiguous", "verified", "rejected", "included"):
            require(isinstance(counts.get(key), int) and counts.get(key) >= 0, f"session_report.json: counts.{key} must be a non-negative integer", errors)


def validate_results(results_dir=DEFAULT_RESULTS_DIR):
    errors = []
    payloads = {}
    for filename, required in REQUIRED_FILES.items():
        path = Path(results_dir) / filename
        try:
            payload = load_json(path)
            payloads[filename] = payload
            validate_top_level(filename, payload, required, errors)
        except ValueError as error:
            errors.append(str(error))
    if "proposed_records.json" in payloads:
        validate_proposed_records(payloads["proposed_records.json"], errors)
    proposed_ids = {
        record.get("candidate_id")
        for record in payloads.get("proposed_records.json", {}).get("records", [])
        if isinstance(record, dict) and record.get("candidate_id")
    }
    if "source_evidence.json" in payloads:
        validate_source_evidence(payloads["source_evidence.json"], proposed_ids, errors)
    if "session_report.json" in payloads:
        validate_session_report(payloads["session_report.json"], errors)
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    args = parser.parse_args()
    errors = validate_results(args.results_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Agent result validation passed: {args.results_dir}")


if __name__ == "__main__":
    main()
