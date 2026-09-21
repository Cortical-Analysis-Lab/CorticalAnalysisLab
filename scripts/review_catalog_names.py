#!/usr/bin/env python3
"""Screen names/aliases and apply explicit identity decisions without verifying facts.

Review files belong outside the repository. Screening never authorizes a merge.
The accepted CSV retains original titles, removed rows, and bundle reports.
"""

from __future__ import annotations

import argparse
import copy
import csv
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

from catalog_common import load_rows
from review_duplicate_identities import DEFAULT_IMPORT


def clean_name(name):
    """Remove explicit cycle labels, preserving meaningful program-name numbers."""
    had_year = bool(re.search(r"\b(?:19|20)\d{2}\b", name))
    name = re.sub(r"\b(?:19|20)\d{2}(?:\s*[-–/]\s*(?:(?:19|20)?\d{2}))?\b", "", name)
    name = re.sub(r"\b(?:Summer|Fall|Spring|Winter)\s*['’]?\d{2}\b\s*:?", "", name, flags=re.I)
    name = re.sub(r"\bREU['’]?(?:2[0-9])\b", "REU", name)
    name = re.sub(r"\(\s*(?:(?:Summer|Fall|Spring|Winter)\s*)?\)", "", name, flags=re.I)
    name = re.sub(r"\bApplications?\s+for\s+Summer\s*$", "", name, flags=re.I)
    if had_year:
        name = re.sub(r"\s*(?:[-–—,:]\s*)?\bSummer\s*$", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).strip(" ,:;–—-")


def canonical_url(value):
    url = urlsplit(value or "")
    if not url.netloc:
        return ""
    query = [(k, v) for k, v in parse_qsl(url.query) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    # Keep meaningful query parameters and anchors: a portal can contain distinct tracks.
    return url.netloc.lower().removeprefix("www.") + url.path.rstrip("/") + ("?" + urlencode(sorted(query)) if query else "") + ("#" + url.fragment if url.fragment else "")


def identity_terms(name):
    generic = set("research experience experiences undergraduate undergraduates summer program programs university site nsf reu for the and with applications application opportunities opportunity internship internships students student college science sciences institute institution".split())
    return set(re.findall(r"[a-z0-9]+", clean_name(name).lower())) - generic


def identity_signals(rows):
    names, urls = set(), set()
    for row in rows:
        names.add(row["Program_Name"])
        urls.add(canonical_url(row.get("Program_URL")))
        for report in json.loads(row.get("Bundle_Details_JSON") or "[]"):
            names.add(report.get("title", ""))
            urls.add(canonical_url(report.get("programUrl")))
            for source in report.get("sourceRecords", []):
                names.add(source.get("title", ""))
                urls.update(canonical_url(source.get(key)) for key in ("programUrl", "resolvedProgramUrl"))
    return [identity_terms(n) for n in names if n], urls - {""}


def screen(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["Program_ID"]].append(row)
    signals = {key: identity_signals(group) for key, group in groups.items()}
    candidates = []
    for left, right in itertools.combinations(groups, 2):
        a, b = groups[left][0], groups[right][0]
        an, au = signals[left]
        bn, bu = signals[right]
        shared_urls = au & bu
        same_host = re.sub(r"\W", "", a["Host_Institution"].lower()) == re.sub(r"\W", "", b["Host_Institution"].lower())
        domains_a = {u.split("/")[0] for u in au}
        domains_b = {u.split("/")[0] for u in bu}
        same_domain = bool(domains_a & domains_b)
        similarity = max((len(x & y) / len(x | y) for x in an for y in bn if x | y), default=0)
        if shared_urls or ((same_host or same_domain) and similarity >= .4) or similarity == 1:
            candidates.append({"left": left, "right": right, "left_name": a["Program_Name"], "right_name": b["Program_Name"], "shared_urls": sorted(shared_urls), "name_similarity": round(similarity, 3), "decision": "needs_identity_review"})
    return candidates


def combine(*values):
    return "; ".join(dict.fromkeys(part.strip() for value in values for part in (value or "").split(";") if part.strip()))


def apply_decisions(rows, decisions):
    """Preserve incumbent facts; store conflicting/undated duplicate data as provenance."""
    rows = copy.deepcopy(rows)
    exclusions = decisions.get("exclusions", {})
    if any(not reason for reason in exclusions.values()):
        raise ValueError("Every exclusion requires a reason")
    by_id = defaultdict(list)
    for row in rows:
        by_id[row["Program_ID"]].append(row)
    removed = set()
    merges = decisions.get("merges", [])
    keep_ids = {m["keep"] for m in merges}
    remove_ids = [rid for m in merges for rid in m["remove"]]
    if set(exclusions) & (keep_ids | set(remove_ids)):
        raise ValueError("Excluded identities cannot participate in merges")
    if keep_ids & set(remove_ids) or len(remove_ids) != len(set(remove_ids)) or len(keep_ids) != len(merges):
        raise ValueError("Decisions must contain disjoint merge groups without chains")
    for merge in merges:
        keep_id = merge["keep"]
        if keep_id not in by_id or not merge.get("reason"):
            raise ValueError(f"Missing retained identity or decision reason: {keep_id}")
        incumbents = by_id[keep_id]
        incoming = [r for rid in merge["remove"] for r in by_id.get(rid, [])]
        if not incoming:  # Reapplying the same accepted batch is harmless.
            continue
        all_rows = incumbents + incoming
        reports = []
        for row in all_rows:
            for report in json.loads(row.get("Bundle_Details_JSON") or "[]"):
                if report not in reports:
                    reports.append(report)
        if not reports:
            reports.append({"id": f"catalog-identity:{keep_id}", "title": incumbents[0]["Program_Name"]})
        history = reports[0].setdefault("catalogIdentityHistory", [])
        history.append({"retainedProgramId": keep_id, "removedProgramIds": merge["remove"], "reason": merge["reason"], "scope": "Identity only; no factual re-verification", "originalRows": [{k: v for k, v in r.items() if k != "Bundle_Details_JSON"} for r in all_rows]})
        # Preserve dated cycles under the stable ID. Undated imports become supplements
        # when the incumbent already has cycle data; their full snapshots survive above.
        years = {r.get("Cycle_Year", "") for r in incumbents}
        for row in incoming:
            year = row.get("Cycle_Year", "")
            if year and year not in years:
                cycle = copy.deepcopy(row)
                cycle["Program_ID"] = keep_id
                for key in ("Program_Name", "Host_Institution", "City", "State", "Country", "Program_URL", "Format", "Location_Scope", "Program_Type", "Primary_Field"):
                    cycle[key] = incumbents[0].get(key, "")
                rows.append(cycle)
                incumbents.append(cycle)
                years.add(year)
        status = "needs_review" if all(r.get("Catalog_Review_Status") == "needs_review" for r in all_rows) else "supplement_needs_review"
        if any(r.get("Catalog_Review_Status") == "bundle_accepted" for r in all_rows) and all(r.get("Catalog_Review_Status", "") in {"", "bundle_accepted"} for r in all_rows):
            status = "bundle_accepted"
        metadata = {
            "Bundle_Details_JSON": json.dumps(reports, ensure_ascii=False, separators=(",", ":")),
            "Bundle_Provenance": combine(*(r.get("Bundle_Provenance") for r in all_rows)),
            "Field_Tags": combine(*(r.get("Field_Tags") for r in all_rows)),
            "Secondary_Fields": combine(*(r.get("Secondary_Fields") for r in all_rows), *(r.get("Primary_Field") for r in incoming if r.get("Primary_Field") != incumbents[0].get("Primary_Field"))),
            "Catalog_Review_Status": status,
            "Review_Notes": combine(*(r.get("Review_Notes") for r in all_rows), "Name/identity overlap reviewed; imported facts and conflicting claims remain subject to review. Original rows retained in catalogIdentityHistory."),
            "Notes": combine(*(r.get("Notes") for r in incumbents), f"Identity consolidation: retained {keep_id}; merged {', '.join(merge['remove'])}. {merge['reason']} Original rows and bundle reports retained in Bundle_Details_JSON; no factual re-verification."),
        }
        if status == "bundle_accepted":
            metadata["Review_Notes"] = combine(*(r.get("Review_Notes") for r in all_rows))
        for row in incumbents:
            row.update(metadata)
        removed.update(merge["remove"])
    rows = [r for r in rows if r["Program_ID"] not in removed and r["Program_ID"] not in exclusions]
    for row in rows:
        for obsolete in decisions.get("resolved_review_notes", {}).get(row["Program_ID"], []):
            row["Review_Notes"] = row.get("Review_Notes", "").replace(obsolete, "").strip("; ")
        old = row["Program_Name"]
        new = decisions.get("renames", {}).get(row["Program_ID"], clean_name(old))
        if not new:
            raise ValueError(f"Cleanup would erase title: {old}")
        if new != old:
            row["Program_Name"] = new
            row["Notes"] = (row.get("Notes", "") + " Original Program_Name before identity cleanup: " + json.dumps(old, ensure_ascii=False) + ".").strip()
        flag = decisions.get("flags", {}).get(row["Program_ID"])
        if flag and flag not in row.get("Review_Notes", ""):
            row["Catalog_Review_Status"] = row.get("Catalog_Review_Status") or "supplement_needs_review"
            row["Review_Notes"] = combine(row.get("Review_Notes"), flag)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_IMPORT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, help="Explicit accepted JSON merge/rename decisions; otherwise screen only")
    parser.add_argument("--excluded-output", type=Path, help="External archive required when applying exclusions")
    args = parser.parse_args()
    rows = load_rows(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.decisions:
        decisions = json.loads(args.decisions.read_text())
        exclusions = decisions.get("exclusions", {})
        if exclusions:
            if not args.excluded_output or args.excluded_output.resolve() in {args.input.resolve(), args.output.resolve()}:
                parser.error("Exclusions require a separate --excluded-output archive")
            args.excluded_output.parent.mkdir(parents=True, exist_ok=True)
            archived = json.loads(args.excluded_output.read_text()) if args.excluded_output.exists() else []
            additions = [
                {"reason": exclusions[r["Program_ID"]], "originalRow": r}
                for r in rows if r["Program_ID"] in exclusions
            ]
            archived.extend(item for item in additions if item not in archived)
            args.excluded_output.write_text(json.dumps(archived, ensure_ascii=False, indent=2) + "\n")
        updated = apply_decisions(rows, decisions)
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(updated)
        print(f"Wrote {len(updated)} rows / {len({r['Program_ID'] for r in updated})} identities")
    else:
        candidates = screen(rows)
        args.output.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n")
        print(f"Screened {len({r['Program_ID'] for r in rows})} identities: {len(candidates)} candidate pairs (not merge decisions)")


if __name__ == "__main__":
    main()
