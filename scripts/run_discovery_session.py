#!/usr/bin/env python3
"""Run a bounded, catalog-aware discovery session against approved public sources.

Discovery output is staging evidence. This script never changes canonical SQLite.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from catalog_common import DEFAULT_DB


NSF_AWARDS_API = "https://api.nsf.gov/services/v1/awards.json"
APPROVED_DISCOVERY_SOURCES = (
    {
        "source_code": "nsf_awards_reu_site",
        "publisher": "U.S. National Science Foundation",
        "source_url": "https://www.nsf.gov/funding/initiatives/reu/search",
        "api_url": NSF_AWARDS_API,
        "query": '"REU Site"',
    },
    {
        "source_code": "nsf_awards_research_experiences_undergraduates",
        "publisher": "U.S. National Science Foundation",
        "source_url": "https://www.nsf.gov/funding/initiatives/reu/search",
        "api_url": NSF_AWARDS_API,
        "query": '"Research Experiences for Undergraduates"',
    },
)


def normalized(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = re.sub(r"\breu\s+site\s*:\s*", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def candidate_identity(title, institution, award_id):
    return f"NSF-{award_id}" if award_id else f"NSF-{normalized(institution)}-{normalized(title)}"


def load_catalog(database):
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute("""
        SELECT o.public_id, o.program_name, o.program_url, i.institution_name
        FROM opportunities o
        JOIN institutions i USING(institution_id)
        ORDER BY o.public_id
    """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def classify_candidate(title, institution, catalog):
    title_key, institution_key = normalized(title), normalized(institution)
    exact, possible = [], []
    title_tokens = set(title_key.split())
    for row in catalog:
        program_key = normalized(row["program_name"])
        host_key = normalized(row["institution_name"])
        same_host = institution_key and (institution_key == host_key or institution_key in host_key or host_key in institution_key)
        if same_host and title_key == program_key:
            exact.append(row["public_id"])
            continue
        overlap = len(title_tokens & set(program_key.split())) / max(1, len(title_tokens | set(program_key.split())))
        if same_host and overlap >= 0.55:
            possible.append(row["public_id"])
    if len(exact) == 1:
        return "EXISTING_PROGRAM", exact[0], "Exact normalized title and host match"
    if exact or possible:
        matches = sorted(set(exact + possible))
        return "POSSIBLE_DUPLICATE", ";".join(matches), "Similar title at matching host requires review"
    return "NEW_PROGRAM", "", "No canonical title/host match"


def fetch_json(url, params, attempts=3):
    request_url = f"{url}?{urlencode(params)}"
    request = Request(request_url, headers={"User-Agent": "CorticalAnalysisLab-CatalogDiscovery/1.0"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)


def nsf_awards(payload):
    response = payload.get("response", {})
    awards = response.get("award", [])
    metadata = response.get("metadata", {})
    if isinstance(awards, dict):
        awards = [awards]
    if isinstance(metadata, list):
        metadata = metadata[0] if metadata else {}
    return awards, int(metadata.get("totalCount") or len(awards))


def discover_nsf(source, catalog, deadline, max_results):
    results, offset, page_size = [], 0, 25
    while time.monotonic() < deadline and len(results) < max_results:
        payload = fetch_json(source["api_url"], {
            "keyword": source["query"], "ActiveAwards": "True",
            "rpp": page_size, "offset": offset,
        })
        awards, total = nsf_awards(payload)
        if not awards:
            break
        for award in awards:
            title = (award.get("title") or "").strip()
            institution = (award.get("awardeeName") or award.get("awardee") or "").strip()
            award_id = str(award.get("id") or "").strip()
            if not title or not institution:
                continue
            match_state, matched_public_id, rationale = classify_candidate(title, institution, catalog)
            results.append({
                "candidate_id": candidate_identity(title, institution, award_id),
                "match_state": match_state,
                "matched_public_id": matched_public_id,
                "match_rationale": rationale,
                "program_name_observed": re.sub(r"^REU\s+Site\s*:\s*", "", title, flags=re.I),
                "institution_observed": institution,
                "cycle_year_observed": "",
                "official_program_url": "",
                "discovery_source": source["source_code"],
                "discovery_source_url": source["source_url"],
                "government_award_id": award_id,
                "government_award_url": f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}" if award_id else "",
                "verification_status": "discovery_only",
                "inclusion_status": "not_included_requires_official_host_verification",
            })
            if len(results) >= max_results:
                break
        offset += len(awards)
        if offset >= total:
            break
    return results


def discovery_counts(candidates):
    return {state: sum(row["match_state"] == state for row in candidates) for state in (
        "NEW_PROGRAM", "EXISTING_PROGRAM", "POSSIBLE_DUPLICATE", "NEW_CYCLE_FOR_EXISTING_PROGRAM"
    )}


def write_candidate_csv(path, candidates):
    fields = list(candidates[0]) if candidates else [
        "candidate_id", "match_state", "matched_public_id", "match_rationale",
        "program_name_observed", "institution_observed", "cycle_year_observed",
        "official_program_url", "discovery_source", "discovery_source_url",
        "government_award_id", "government_award_url", "verification_status", "inclusion_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)


def write_progress(output, session_id, started_at, candidates, source_errors, canonical_count, current_source=None):
    output.mkdir(parents=True, exist_ok=True)
    candidates = deduplicate(candidates)
    write_candidate_csv(output / "candidates.csv", candidates)
    progress = {
        "session_id": session_id,
        "started_at": started_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "canonical_programs_before": canonical_count,
        "discovered_unique": len(candidates),
        "counts": discovery_counts(candidates),
        "source_errors": source_errors,
        "current_source": current_source,
    }
    (output / "progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")


def deduplicate(candidates):
    deduplicated = {}
    for candidate in candidates:
        key = candidate["candidate_id"]
        if key not in deduplicated:
            deduplicated[key] = candidate
            continue
        sources = set(deduplicated[key]["discovery_source"].split(";"))
        sources.add(candidate["discovery_source"])
        deduplicated[key]["discovery_source"] = ";".join(sorted(sources))
    return sorted(deduplicated.values(), key=lambda item: (item["match_state"], item["institution_observed"], item["program_name_observed"]))


def write_outputs(output, session_id, started_at, candidates, source_errors, canonical_count):
    output.mkdir(parents=True, exist_ok=True)
    write_candidate_csv(output / "candidates.csv", candidates)
    counts = discovery_counts(candidates)
    report = {
        "session_id": session_id,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "canonical_programs_before": canonical_count,
        "discovered_unique": len(candidates),
        "counts": counts,
        "official_host_verified": 0,
        "included_in_canonical_database": 0,
        "source_errors": source_errors,
        "note": "Discovery candidates require official host-page verification and reviewed promotion before canonical inclusion.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    progress = dict(report)
    progress["status"] = "complete"
    progress["updated_at"] = report["completed_at"]
    (output / "progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Summer research discovery session {session_id}", "",
        f"- Completed: {report['completed_at']}",
        f"- Canonical programs at session start: {canonical_count}",
        f"- Unique candidates discovered: {len(candidates)}",
        f"- New program candidates: {counts['NEW_PROGRAM']}",
        f"- Existing program matches: {counts['EXISTING_PROGRAM']}",
        f"- Possible duplicates requiring review: {counts['POSSIBLE_DUPLICATE']}",
        f"- New cycles identified: {counts['NEW_CYCLE_FOR_EXISTING_PROGRAM']}",
        "- Official host pages verified this session: 0",
        "- Included in canonical database this session: 0",
        "",
        "Candidates from the NSF awards API are discovery evidence only. They remain staged until an official host page is verified and a reviewed promotion is committed.",
    ]
    if source_errors:
        lines.extend(["", "## Source errors", ""] + [f"- {error}" for error in source_errors])
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--time-budget-minutes", type=int, default=30)
    parser.add_argument("--max-results-per-source", type=int, default=3000)
    args = parser.parse_args()
    if not 1 <= args.time_budget_minutes <= 300:
        raise SystemExit("--time-budget-minutes must be between 1 and 300")
    session_id = args.session_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    started_at = datetime.now(timezone.utc).isoformat()
    catalog = load_catalog(args.database)
    deadline = time.monotonic() + args.time_budget_minutes * 60
    candidates, errors = [], []
    write_progress(args.output, session_id, started_at, candidates, errors, len(catalog))
    for source in APPROVED_DISCOVERY_SOURCES:
        if time.monotonic() >= deadline:
            break
        try:
            source_candidates = discover_nsf(source, catalog, deadline, args.max_results_per_source)
            candidates.extend(source_candidates)
            write_progress(args.output, session_id, started_at, candidates, errors, len(catalog), source["source_code"])
        except Exception as error:  # Preserve a partial session report when one source is unavailable.
            errors.append(f"{source['source_code']}: {type(error).__name__}: {error}")
            write_progress(args.output, session_id, started_at, candidates, errors, len(catalog), source["source_code"])
    candidates = deduplicate(candidates)
    write_outputs(args.output, session_id, started_at, candidates, errors, len(catalog))
    print(f"Discovery session {session_id}: {len(candidates)} unique candidates; {len(errors)} source errors")


if __name__ == "__main__":
    main()
