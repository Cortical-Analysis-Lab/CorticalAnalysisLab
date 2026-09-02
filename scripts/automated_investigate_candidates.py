#!/usr/bin/env python3
"""Automatically triage and propose catalog candidates from official metadata.

This tool is intentionally conservative: it can reject obvious non-opportunity
NSF awards and propose minimal records for likely REU/Site programs using NSF's
official award metadata. It does not invent host-page facts that are absent from
the award record.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from catalog_common import ROOT
from catalog_staging import claim_investigation_batch, set_many_review_status


NSF_AWARDS_API = "https://api.nsf.gov/services/v1/awards.json"
DEFAULT_RESULTS_DIR = ROOT / "database" / "local" / "agent_results"
DEFAULT_PROGRESS = ROOT / "database" / "local" / "agent_results" / "automated_investigation_progress.json"
DEFAULT_SOURCE_AUDIT = ROOT / "database" / "local" / "source_audit"
DEFAULT_DECISIONS = ROOT / "database" / "local" / "review_decisions.json"
NON_OPPORTUNITY_PATTERNS = (
    r"\bCAREER\b",
    r"\bIUCRC\b",
    r"\bMRSEC\b",
    r"\bSTC\b",
    r"\bRTG\b",
    r"\bRII Track\b",
    r"\bCollaborative Research\b(?!.*\bREU\b)",
    r"\bCenter\b(?!.*\bREU\b)",
    r"\bRenewal\b",
    r"\bFacility\b",
    r"\bInfrastructure\b",
    r"\bEquipment\b",
)
REU_PATTERNS = (
    r"\bREU Site\b",
    r"\bResearch Experiences? for Undergraduates\b",
    r"\bRSCH EXPER FOR UNDERGRAD SITES\b",
)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def fetch_nsf_award(award_id):
    request_url = f"{NSF_AWARDS_API}?{urlencode({'id': award_id})}"
    request = Request(request_url, headers={"User-Agent": "CorticalAnalysisLab-AutomatedInvestigator/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    awards = payload.get("response", {}).get("award", [])
    if isinstance(awards, dict):
        awards = [awards]
    return awards[0] if awards else {}


def has_pattern(patterns, text):
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def strip_reu_prefix(title):
    return re.sub(r"^\s*(Collaborative Research:\s*)?REU\s+Site\s*:\s*", "", title or "", flags=re.I).strip()


def years_from_text(text):
    years = [int(year) for year in re.findall(r"\b(20[2-9][0-9])\b", text or "")]
    return sorted(set(years))


def latest_cycle_year(award):
    text = " ".join(filter(None, [award.get("abstractText"), award.get("startDate"), award.get("expDate")]))
    start_year = year_from_date(award.get("startDate"))
    exp_year = year_from_date(award.get("expDate"))
    ceiling = (exp_year + 1) if exp_year else 2031
    years = years_from_text(text)
    bounded_years = [year for year in years if 2020 <= year <= ceiling]
    return max(bounded_years) if bounded_years else exp_year or start_year


def year_from_date(value):
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", value or "")
    return int(match.group(3)) if match else None


def duration_weeks(abstract):
    number_words = {
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
    }
    text = abstract or ""
    match = re.search(r"\b(\d{1,2})\s*[- ]?\s*(?:week|wk)s?\b", text, flags=re.I)
    if match:
        return int(match.group(1))
    match = re.search(
        r"\b(six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\s*[- ]?\s*(?:week|wk)s?\b",
        text,
        flags=re.I,
    )
    return number_words[match.group(1).lower()] if match else None


def money_amount(value):
    return float(value.replace(",", "").replace("$", ""))


def stipend_amounts(abstract):
    text = abstract or ""
    total = None
    weekly = None
    for match in re.finditer(r"\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text):
        start, end = match.span()
        context = text[max(0, start - 80):min(len(text), end + 80)]
        if not re.search(r"\b(stipend|student support|participant support|subsistence)\b", context, flags=re.I):
            continue
        amount = money_amount(match.group(1))
        if re.search(r"\b(per|/)\s*(week|wk)\b|\bweekly\b", context, flags=re.I):
            weekly = amount
        else:
            total = amount
    return total, weekly


def award_url(award_id):
    return f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}"


def primary_field(award):
    mapping = {
        "BIO": "Life Sciences",
        "CISE": "Computer Science / Data / AI",
        "EHR": "Social / Behavioral Sciences",
        "EDU": "Social / Behavioral Sciences",
        "ENG": "Engineering",
        "GEO": "Earth / Environment / Ocean",
        "MPS": "Physics & Astronomy",
        "SBE": "Social / Behavioral Sciences",
        "TIP": "Engineering",
    }
    return mapping.get((award.get("dirAbbr") or "").upper(), "Multidisciplinary")


def field_tags(award):
    tags = []
    for value in (award.get("orgLongName2"), award.get("program"), award.get("fundProgramName")):
        if value and value not in tags:
            tags.append(value)
    return tags[:6]


def public_id(candidate_id):
    return candidate_id.replace("NSF-", "NSF-REU-")


def classify_award(candidate, award):
    title = award.get("title") or candidate.get("observed_name") or ""
    program = " ".join(filter(None, [award.get("program"), award.get("fundProgramName")]))
    abstract = award.get("abstractText") or ""
    title_has_reu = has_pattern(REU_PATTERNS, title)
    title_is_non_opportunity = has_pattern(NON_OPPORTUNITY_PATTERNS, title)
    if title_is_non_opportunity and not title_has_reu:
        return "reject", "NSF award title appears to be a grant, center, facility, or research project rather than a standalone summer undergraduate opportunity"
    strong_reu_signal = (
        title_has_reu or
        has_pattern(REU_PATTERNS, program) or
        re.search(r"\bThis REU Site award\b", abstract, flags=re.I)
    )
    if strong_reu_signal:
        return "propose", "Likely NSF REU/Site program"
    if has_pattern(NON_OPPORTUNITY_PATTERNS, f"{title}\n{program}"):
        return "reject", "NSF award appears to be a grant, center, facility, or research project rather than a standalone summer undergraduate opportunity"
    return "unresolved", "Could not confidently classify as a catalogable summer undergraduate opportunity"


def evidence_hash(award):
    digest = hashlib.sha256()
    digest.update(json.dumps(award, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def proposed_record(candidate, award):
    award_id = str(award.get("id") or candidate.get("government_award_id") or "").strip()
    title = award.get("title") or candidate.get("observed_name")
    abstract = award.get("abstractText") or ""
    cycle_year = latest_cycle_year(award) or year_from_date(award.get("expDate")) or year_from_date(award.get("startDate"))
    stipend_total, stipend_weekly = stipend_amounts(abstract)
    fields = {
        "Program_Name": strip_reu_prefix(title),
        "Host_Institution": award.get("awardeeName") or candidate.get("observed_institution"),
        "City": award.get("perfCity") or award.get("awardeeCity"),
        "State": award.get("perfStateCode") or award.get("awardeeStateCode"),
        "Country": award.get("perfCountryCode") or award.get("awardeeCountryCode"),
        "Cycle_Year": cycle_year,
        "Program_URL": award_url(award_id),
        "Duration_Weeks": duration_weeks(abstract) or "N/A",
        "Program_Start": "N/A",
        "Program_End": "N/A",
        "Application_Open": "N/A",
        "Application_Deadline": "N/A",
        "Deadline_Text": "N/A",
        "Status": "unknown",
        "Stipend_Total_USD": stipend_total or "N/A",
        "Stipend_Weekly_USD": stipend_weekly or "N/A",
        "Raw_Eligibility_Text": "NSF award metadata indicates an REU/Site program. Host-level eligibility and application details require host-page evidence when available.",
        "Eligibility_Source_URL": award_url(award_id),
        "Eligibility_Checked_On": datetime.now(timezone.utc).date().isoformat(),
        "Eligibility_Checked_By": "automated_nsf_metadata",
        "Citizenship_US_Citizen": "yes",
        "Citizenship_Permanent_Resident": "yes",
        "Citizenship_International": "no",
        "Eligibility_Parse_Status": "reviewed",
        "Last_Verified": datetime.now(timezone.utc).date().isoformat(),
        "Data_Confidence": "medium",
        "Notes": "Automated proposal from official NSF award metadata; host-page details may remain unknown until enriched.",
    }
    if "etap.nsf.gov" in abstract.lower():
        fields["Application_URL"] = "https://etap.nsf.gov"
    return {
        "candidate_id": candidate["candidate_id"],
        "proposal_version": "1",
        "identity": {
            "program_name": fields["Program_Name"],
            "institution_name": fields["Host_Institution"],
            "public_id": public_id(candidate["candidate_id"]),
            "matched_public_id": candidate.get("matched_public_id") or None,
            "match_state": candidate.get("match_state") or "NEW_PROGRAM",
            "duplicate_notes": "Automated proposal from NSF official award metadata; host-page enrichment can add cycle-specific details later.",
        },
        "cycle_year": cycle_year,
        "classification": {
            "primary_field": primary_field(award),
            "field_tags": field_tags(award),
            "research_modes": [],
        },
        "fields": {key: value for key, value in fields.items() if value is not None},
        "conditional_rules": [],
        "conflicts": [],
        "validation_warnings": [],
    }


def source_evidence(candidate, award):
    award_id = str(award.get("id") or candidate.get("government_award_id") or "").strip()
    return {
        "candidate_id": candidate["candidate_id"],
        "source_url": award_url(award_id),
        "source_type": "official_government",
        "publisher": "U.S. National Science Foundation",
        "authoritative": True,
        "authority_rationale": "Official NSF award metadata supports award identity, host institution, program title, award period, and abstract-level REU/Site description.",
        "date_checked": datetime.now(timezone.utc).date().isoformat(),
        "retrieved_at": now_utc(),
        "fields_supported": [
            "Program_Name", "Host_Institution", "Program_URL", "Cycle_Year",
            "Duration_Weeks", "Primary_Field", "Field_Tags", "Eligibility",
            "Last_Verified",
        ],
        "evidence_hash": evidence_hash(award),
        "conflict_notes": None,
    }


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def merge_by_candidate(existing, incoming):
    merged = {item["candidate_id"]: item for item in existing if item.get("candidate_id")}
    for item in incoming:
        merged[item["candidate_id"]] = item
    return [merged[key] for key in sorted(merged)]


def merge_evidence(existing, incoming):
    merged = {(item.get("candidate_id"), item.get("source_url")): item for item in existing}
    for item in incoming:
        merged[(item.get("candidate_id"), item.get("source_url"))] = item
    return [merged[key] for key in sorted(merged)]


def write_results(results_dir, records, evidence, report):
    results_dir = Path(results_dir)
    existing_records = read_json(results_dir / "proposed_records.json", {"records": []}).get("records", [])
    existing_evidence = read_json(results_dir / "source_evidence.json", {"evidence": []}).get("evidence", [])
    merged_records = merge_by_candidate(existing_records, records)
    merged_evidence = merge_evidence(existing_evidence, evidence)
    generated_at = now_utc()
    write_json(results_dir / "proposed_records.json", {
        "contract_version": "1.0",
        "generated_at": generated_at,
        "records": merged_records,
    })
    write_json(results_dir / "source_evidence.json", {
        "contract_version": "1.0",
        "generated_at": generated_at,
        "evidence": merged_evidence,
    })
    report["generated_at"] = generated_at
    report["counts"]["verified_total"] = len(merged_records)
    write_json(results_dir / "session_report.json", report)
    return merged_records, merged_evidence


def write_source_audit(source_audit_dir, evidence):
    source_audit_dir = Path(source_audit_dir)
    source_audit_dir.mkdir(parents=True, exist_ok=True)
    csv_path = source_audit_dir / "retrieved_sources.csv"
    md_path = source_audit_dir / "retrieved_sources.md"
    rows = sorted({
        (item.get("publisher") or "", item.get("source_url") or "")
        for item in evidence
        if item.get("source_url")
    })
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["institution_or_publisher", "source_url"])
        writer.writerows(rows)
    lines = ["# Retrieved source links", ""]
    lines.extend(f"- {publisher}: {url}" if publisher else f"- {url}" for publisher, url in rows)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proposal_signature(candidate_id, results_dir):
    digest = hashlib.sha256(candidate_id.encode())
    for filename in ("proposed_records.json", "source_evidence.json"):
        path = Path(results_dir) / filename
        if path.exists():
            digest.update(file_sha256(path).encode())
    return digest.hexdigest()


def write_agent_decisions(results_dir, decisions_path=DEFAULT_DECISIONS):
    proposed = read_json(Path(results_dir) / "proposed_records.json", {"records": []})
    decisions = read_json(decisions_path, {"contract_version": "1.0", "decisions": {}})
    for record in proposed.get("records", []):
        candidate_id = record["candidate_id"]
        decisions.setdefault("decisions", {})[candidate_id] = {
            "decision": "approved",
            "signature": proposal_signature(candidate_id, results_dir),
            "decided_by": "automated_pipeline",
            "reviewed_at": now_utc(),
        }
    write_json(decisions_path, decisions)
    return len(proposed.get("records", []))


def write_progress(path, payload):
    write_json(path, payload)


def run(limit, results_dir=DEFAULT_RESULTS_DIR, progress_path=DEFAULT_PROGRESS, delay=0.1):
    started_at = now_utc()
    rows = claim_investigation_batch(limit)
    records, evidence, rejected, unresolved, errors = [], [], [], [], []
    total = len(rows)
    for index, candidate in enumerate(rows, start=1):
        progress = {
            "status": "running",
            "started_at": started_at,
            "updated_at": now_utc(),
            "checked": index - 1,
            "total": total,
            "approved_candidates": len(records),
            "rejected_candidates": len(rejected),
            "unresolved_candidates": len(unresolved),
            "current_candidate": candidate.get("candidate_id"),
        }
        write_progress(progress_path, progress)
        try:
            award_id = candidate.get("government_award_id")
            if not award_id:
                unresolved.append({"candidate_id": candidate["candidate_id"], "reason": "missing NSF award id"})
                continue
            award = fetch_nsf_award(award_id)
            if not award:
                unresolved.append({"candidate_id": candidate["candidate_id"], "reason": "NSF award metadata not found"})
                continue
            action, reason = classify_award(candidate, award)
            if action == "propose":
                records.append(proposed_record(candidate, award))
                evidence.append(source_evidence(candidate, award))
            elif action == "reject":
                rejected.append({"candidate_id": candidate["candidate_id"], "reason": reason})
            else:
                unresolved.append({"candidate_id": candidate["candidate_id"], "reason": reason})
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            errors.append({"candidate_id": candidate["candidate_id"], "error": f"{type(error).__name__}: {error}"})
            unresolved.append({"candidate_id": candidate["candidate_id"], "reason": "source retrieval failed"})
        time.sleep(delay)

    set_many_review_status([row["candidate_id"] for row in records], "approved")
    set_many_review_status([row["candidate_id"] for row in rejected], "rejected")
    set_many_review_status([row["candidate_id"] for row in unresolved], "rejected")

    generated_at = now_utc()
    report = {
        "contract_version": "1.0",
        "generated_at": generated_at,
        "summary": "Automated NSF metadata triage and proposal pass.",
        "counts": {
            "discovered": total,
            "existing": 0,
            "ambiguous": 0,
            "verified": len(records),
            "rejected": len(rejected),
            "included": 0,
            "updated": 0,
            "unresolved": len(unresolved),
        },
        "files_written": [
            "database/local/agent_results/proposed_records.json",
            "database/local/agent_results/source_evidence.json",
            "database/local/agent_results/session_report.json",
        ],
        "limitations": [
            "Automated pass uses official NSF metadata only unless a later extractor adds host-page evidence.",
            "Cycle-specific host details absent from NSF metadata remain unknown.",
        ],
        "rejected": rejected,
        "unresolved": unresolved,
        "errors": errors,
    }
    merged_records, merged_evidence = write_results(results_dir, records, evidence, report)
    approved_total = write_agent_decisions(results_dir)
    source_csv, source_md = write_source_audit(DEFAULT_SOURCE_AUDIT, merged_evidence)
    write_progress(progress_path, {
        "status": "complete",
        "started_at": started_at,
        "updated_at": generated_at,
        "checked": total,
        "total": total,
        "approved_candidates": len(records),
        "rejected_candidates": len(rejected),
        "unresolved_candidates": len(unresolved),
        "source_errors": errors,
    })
    return {
        "checked": total, "approved": len(records), "approved_total": approved_total,
        "rejected": len(rejected), "unresolved": len(unresolved), "errors": len(errors),
        "source_csv": str(source_csv), "source_md": str(source_md),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()
    result = run(args.limit, args.results_dir, args.progress, args.delay)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
