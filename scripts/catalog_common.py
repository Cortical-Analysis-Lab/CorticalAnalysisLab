"""Shared helpers for the summer-research catalog tooling."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "database" / "research_opportunities.sqlite"
SCHEMA = ROOT / "schema" / "schema.sql"
IMPORTER_VERSION = "1.0.0"

CATEGORIES = [
    ("biomedical-health", "Biomedical & Health", "Human health, medicine, public health, and biomedical research"),
    ("life-sciences", "Life Sciences", "Biology, molecular and cellular sciences, ecology, and related life sciences"),
    ("neuroscience-cognitive", "Neuroscience & Cognitive Science", "Neural systems, behavior, cognition, and brain health"),
    ("computer-data-ai", "Computer Science / Data / AI", "Computing, data science, machine learning, and artificial intelligence"),
    ("mathematics-statistics", "Mathematics & Statistics", "Pure and applied mathematics, statistics, and quantitative modeling"),
    ("physics-astronomy", "Physics & Astronomy", "Physics, astronomy, and space sciences"),
    ("chemistry-materials", "Chemistry & Materials", "Chemistry, chemical science, and materials research"),
    ("engineering", "Engineering", "Engineering research and design across disciplines"),
    ("earth-environment-ocean", "Earth / Environment / Ocean", "Earth systems, environmental science, climate, and ocean research"),
    ("social-behavioral", "Social / Behavioral Sciences", "Psychology, sociology, education, economics, and related social sciences"),
    ("humanities-arts", "Humanities & Arts", "Humanities, arts, languages, and humanistic scholarship"),
    ("interdisciplinary-stem", "Interdisciplinary STEM", "Programs intentionally spanning multiple STEM disciplines"),
    ("multidisciplinary", "Multidisciplinary", "Programs spanning STEM, social sciences, humanities, or other broad areas"),
]

TAG_ALIASES = {
    "stem": ("discipline", "STEM"),
    "social sciences": ("discipline", "Social sciences"),
    "humanities": ("discipline", "Humanities"),
    "biomedical": ("discipline", "Biomedical research"),
    "neuroscience": ("discipline", "Neuroscience"),
    "computational": ("research_mode", "Computational research"),
    "data science": ("discipline", "Data science"),
    "machine learning": ("discipline", "Machine learning"),
    "field research": ("research_mode", "Field research"),
    "clinical": ("research_mode", "Clinical research"),
    "engineering": ("discipline", "Engineering"),
    "phd-oriented research": ("program_characteristic", "PhD-oriented research"),
    "international": ("program_characteristic", "International"),
    "varies by host": ("scope", "Varies by host"),
    "varies by project": ("scope", "Varies by project"),
}


def text_or_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def number_or_none(value):
    value = text_or_none(value)
    if value is None:
        return None
    return float(value.replace(",", "").replace("$", ""))


def int_or_none(value):
    number = number_or_none(value)
    return int(number) if number is not None else None


def iso_date(value):
    value = text_or_none(value)
    if value is None:
        return None
    return value[:10]


def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "unknown"


def normalize_country(value):
    value = text_or_none(value)
    return {"USA": "US", "United States": "US", "Germany": "DE"}.get(value, value)


def normalize_status(value):
    value = (text_or_none(value) or "").lower()
    if "closed" in value or "filled" in value:
        return "closed"
    if "upcoming" in value or "expected" in value or "monitor" in value:
        return "upcoming"
    if "open" in value:
        return "open"
    if "active" in value:
        return "active"
    return "unknown"


def normalize_choice(value):
    value = (text_or_none(value) or "unknown").lower().replace("not specified", "unknown")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_") or "unknown"


def normalize_external(value):
    value = normalize_choice(value)
    if value in {"yes", "no", "limited"}:
        return value
    return "unknown"


def safe_bool_from_explicit(text, positive_patterns, negative_patterns=()):
    """Return only explicit True/False; ambiguity remains None."""
    lower = (text_or_none(text) or "").lower()
    if any(pattern in lower for pattern in negative_patterns):
        return 0
    if any(pattern in lower for pattern in positive_patterns):
        return 1
    return None


def load_rows(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if path.suffix.lower() == ".xlsx":
        try:
            import openpyxl
        except ImportError as exc:
            raise SystemExit("XLSX import requires: pip install -r scripts/requirements.txt") from exc
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = workbook["Programs"] if "Programs" in workbook.sheetnames else workbook.active
        values = sheet.iter_rows(values_only=True)
        headers = [str(value) if value is not None else "" for value in next(values)]
        return [dict(zip(headers, row)) for row in values if any(value is not None for value in row)]
    raise ValueError(f"Unsupported import format: {path.suffix}")


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_url(value):
    if value is None:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def connect(db_path=DEFAULT_DB):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def dump_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
