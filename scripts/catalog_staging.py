#!/usr/bin/env python3
"""Persistent local staging store for catalog discovery and agent handoffs."""

from __future__ import annotations

import csv
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from catalog_common import ROOT


DEFAULT_STAGING_DB = ROOT / "database" / "local" / "catalog_candidates.sqlite"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS discovery_sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    source_set TEXT NOT NULL,
    discovered_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    report_path TEXT
);
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    observed_name TEXT,
    observed_institution TEXT,
    observed_url TEXT,
    normalized_url TEXT,
    discovery_source TEXT NOT NULL,
    government_award_id TEXT,
    matched_public_id TEXT,
    match_state TEXT NOT NULL DEFAULT 'UNREVIEWED',
    verification_status TEXT NOT NULL DEFAULT 'discovery_only',
    review_status TEXT NOT NULL DEFAULT 'pending',
    inclusion_status TEXT NOT NULL DEFAULT 'not_included',
    notes TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_session_id TEXT,
    FOREIGN KEY(last_session_id) REFERENCES discovery_sessions(session_id)
);
CREATE TABLE IF NOT EXISTS candidate_sources (
    candidate_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_role TEXT NOT NULL DEFAULT 'discovery',
    authority_status TEXT NOT NULL DEFAULT 'unreviewed',
    added_at TEXT NOT NULL,
    PRIMARY KEY(candidate_id, source_url),
    FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_candidates_review ON candidates(review_status, match_state);
CREATE INDEX IF NOT EXISTS idx_candidates_url ON candidates(normalized_url);
"""


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def normalize_url(value):
    parsed = urlparse((value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Expected an HTTP(S) URL: {value}")
    host = parsed.hostname.lower().rstrip(".")
    port = parsed.port
    netloc = host if not port or (parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80) else f"{host}:{port}"
    return urlunparse((parsed.scheme.lower(), netloc, parsed.path or "/", "", parsed.query, ""))


def connect(path=DEFAULT_STAGING_DB):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def manual_candidate_id(url):
    return "MANUAL-" + hashlib.sha256(normalize_url(url).encode()).hexdigest()[:16].upper()


def add_manual_links(urls, notes=None, database=DEFAULT_STAGING_DB):
    timestamp, added = now_utc(), []
    connection = connect(database)
    with connection:
        for raw_url in urls:
            normalized_url = normalize_url(raw_url)
            candidate_id = manual_candidate_id(normalized_url)
            connection.execute("""
                INSERT INTO candidates(
                    candidate_id, observed_url, normalized_url, discovery_source, notes,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, 'manual_link', ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    observed_url=excluded.observed_url,
                    last_seen_at=excluded.last_seen_at,
                    notes=COALESCE(excluded.notes, candidates.notes)
            """, (candidate_id, raw_url.strip(), normalized_url, notes, timestamp, timestamp))
            connection.execute("""
                INSERT OR IGNORE INTO candidate_sources(candidate_id, source_url, source_role, authority_status, added_at)
                VALUES (?, ?, 'discovery', 'unreviewed', ?)
            """, (candidate_id, normalized_url, timestamp))
            added.append(candidate_id)
    connection.close()
    return added


def import_discovery_csv(csv_path, session_id, report_path=None, database=DEFAULT_STAGING_DB):
    timestamp = now_utc()
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    connection = connect(database)
    with connection:
        connection.execute("""
            INSERT INTO discovery_sessions(session_id, started_at, completed_at, source_set, discovered_count, report_path)
            VALUES (?, ?, ?, 'approved_official_directories', ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET completed_at=excluded.completed_at,
                discovered_count=excluded.discovered_count, report_path=excluded.report_path
        """, (session_id, timestamp, timestamp, len(rows), str(report_path) if report_path else None))
        for row in rows:
            candidate_id = row["candidate_id"]
            observed_url = row.get("official_program_url") or row.get("government_award_url") or ""
            normalized_url = normalize_url(observed_url) if observed_url else None
            connection.execute("""
                INSERT INTO candidates(
                    candidate_id, observed_name, observed_institution, observed_url, normalized_url,
                    discovery_source, government_award_id, matched_public_id, match_state,
                    verification_status, inclusion_status, first_seen_at, last_seen_at, last_session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    observed_name=excluded.observed_name,
                    observed_institution=excluded.observed_institution,
                    observed_url=COALESCE(NULLIF(excluded.observed_url, ''), candidates.observed_url),
                    normalized_url=COALESCE(excluded.normalized_url, candidates.normalized_url),
                    discovery_source=excluded.discovery_source,
                    matched_public_id=excluded.matched_public_id,
                    match_state=excluded.match_state,
                    verification_status=excluded.verification_status,
                    last_seen_at=excluded.last_seen_at,
                    last_session_id=excluded.last_session_id
            """, (
                candidate_id, row.get("program_name_observed"), row.get("institution_observed"),
                observed_url, normalized_url, row.get("discovery_source") or "unknown",
                row.get("government_award_id"), row.get("matched_public_id"),
                row.get("match_state") or "UNREVIEWED", row.get("verification_status") or "discovery_only",
                row.get("inclusion_status") or "not_included", timestamp, timestamp, session_id,
            ))
            for source_url in filter(None, [row.get("discovery_source_url"), row.get("government_award_url")]):
                connection.execute("""
                    INSERT OR IGNORE INTO candidate_sources(candidate_id, source_url, source_role, authority_status, added_at)
                    VALUES (?, ?, 'discovery', 'validated_government_discovery', ?)
                """, (candidate_id, source_url, timestamp))
    connection.close()
    return len(rows)


def list_candidates(database=DEFAULT_STAGING_DB, limit=500):
    connection = connect(database)
    rows = [dict(row) for row in connection.execute("""
        SELECT * FROM candidates
        ORDER BY CASE review_status WHEN 'pending' THEN 0 WHEN 'investigating' THEN 1 ELSE 2 END,
                 last_seen_at DESC
        LIMIT ?
    """, (limit,))]
    connection.close()
    return rows


def claim_investigation_batch(limit=25, database=DEFAULT_STAGING_DB):
    if not 1 <= int(limit) <= 100:
        raise ValueError("Batch limit must be between 1 and 100")
    connection = connect(database)
    with connection:
        rows = [dict(row) for row in connection.execute("""
            SELECT * FROM candidates
            WHERE review_status IN ('pending', 'needs_review')
            ORDER BY
                CASE match_state
                    WHEN 'POSSIBLE_DUPLICATE' THEN 0
                    WHEN 'NEW_CYCLE_FOR_EXISTING_PROGRAM' THEN 1
                    WHEN 'NEW_PROGRAM' THEN 2
                    ELSE 3
                END,
                last_seen_at DESC,
                candidate_id
            LIMIT ?
        """, (int(limit),))]
        for row in rows:
            connection.execute(
                "UPDATE candidates SET review_status='investigating' WHERE candidate_id=?",
                (row["candidate_id"],),
            )
    connection.close()
    return rows


def investigation_counts(database=DEFAULT_STAGING_DB):
    connection = connect(database)
    counts = {row["review_status"]: row["count"] for row in connection.execute(
        "SELECT review_status, COUNT(*) AS count FROM candidates GROUP BY review_status"
    )}
    match_counts = {row["match_state"]: row["count"] for row in connection.execute(
        "SELECT match_state, COUNT(*) AS count FROM candidates GROUP BY match_state"
    )}
    connection.close()
    return {"by_review_status": counts, "by_match_state": match_counts}


def candidate_counts(database=DEFAULT_STAGING_DB):
    connection = connect(database)
    counts = {row["review_status"]: row["count"] for row in connection.execute(
        "SELECT review_status, COUNT(*) AS count FROM candidates GROUP BY review_status"
    )}
    total = connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    sessions = connection.execute("SELECT COUNT(*) FROM discovery_sessions").fetchone()[0]
    connection.close()
    return {"total": total, "sessions": sessions, "by_review_status": counts}


def set_review_status(candidate_id, status, database=DEFAULT_STAGING_DB):
    allowed = {"pending", "investigating", "needs_review", "approved", "rejected", "included"}
    if status not in allowed:
        raise ValueError(f"Unsupported review status: {status}")
    connection = connect(database)
    with connection:
        cursor = connection.execute("UPDATE candidates SET review_status=? WHERE candidate_id=?", (status, candidate_id))
        if cursor.rowcount != 1:
            raise KeyError(candidate_id)
    connection.close()


def set_many_review_status(candidate_ids, status, database=DEFAULT_STAGING_DB):
    allowed = {"pending", "investigating", "needs_review", "approved", "rejected", "included"}
    if status not in allowed:
        raise ValueError(f"Unsupported review status: {status}")
    ids = list(candidate_ids)
    if not ids:
        return 0
    connection = connect(database)
    with connection:
        connection.executemany(
            "UPDATE candidates SET review_status=? WHERE candidate_id=?",
            [(status, candidate_id) for candidate_id in ids],
        )
    connection.close()
    return len(ids)
