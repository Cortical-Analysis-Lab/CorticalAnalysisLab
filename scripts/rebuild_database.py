#!/usr/bin/env python3
"""Rebuild canonical SQLite and generated web/review outputs from the committed seed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from catalog_common import DEFAULT_DB, ROOT

SEED = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def main():
    if DEFAULT_DB.exists():
        DEFAULT_DB.unlink()
    run(ROOT / "scripts" / "import_catalog.py", SEED)
    run(ROOT / "scripts" / "validate_catalog.py")
    run(ROOT / "scripts" / "export_catalog.py")


if __name__ == "__main__":
    main()
