# Summer Undergraduate Research Opportunity Explorer: data architecture

## Repository placement

This site is a static GitHub Pages repository with existing browser data in `/data`. The catalog therefore uses:

- `/database/research_opportunities.sqlite` — canonical structured source of truth
- `/database/imports/` — reviewed CSV/XLSX import staging
- `/schema/` — versioned SQL schema and data dictionary
- `/scripts/` — deterministic import, validation, rebuild, test, and export commands
- `/data/summer-research/` — generated static JSON for the browser plus review exports

The current pages and existing `data/people.json` and `data/publications.json` remain unchanged.

## Normalization choices

Institutions and stable opportunities are independent of annual cycles. Dates, deadlines, status, compensation, benefits, hard eligibility, and verification are cycle-specific. Broad categories and narrower tags use many-to-many links. Sources are deduplicated by URL, while verification events retain check date, supported fields, conflict status, and future evidence hashes.

The starter's original row is retained as JSON with its import-run hash. This makes later corrections auditable and prevents normalization from destroying source wording.

## Website contract

GitHub Pages reads static JSON only; it does not open SQLite in the browser. `catalog.json` is the convenient denormalized payload. Normalized JSON files are also exported for smaller or specialized loads.

Eligibility fields are nullable. A future evaluator must return three outcomes: `eligible`, `ineligible`, or `unknown/review needed`. Unknown must never be treated as false. Preference filters operate separately from hard eligibility.

## Update workflow

```bash
python scripts/import_catalog.py path/to/reviewed.csv --dry-run
python scripts/import_catalog.py path/to/reviewed.csv
python scripts/validate_catalog.py
python scripts/export_catalog.py
python scripts/export_review_xlsx.py
python scripts/test_catalog.py
```

For a clean deterministic seed rebuild:

```bash
python scripts/rebuild_database.py
```

The validator treats missing deadlines, stipends, durations, and unparsed eligibility as review warnings. Structural corruption, broken foreign keys, invalid URLs, duplicates, and missing required relationships are errors.

## Future discovery and verification agents

Use a staged pipeline: discovery → extraction → verification → classification → deduplication → reviewed update. Agents should emit candidate rows and source evidence into staging. They should not write public JSON or silently overwrite canonical records. Promotion into SQLite remains deterministic, validated, and attributable to an import run.

Potential next schema additions include immutable source snapshots, proposed-change tables, reviewer decisions, and job/run metadata. The current source hashes, raw imports, verification events, and stable public IDs provide the attachment points for those additions.

## Explicitly out of scope

No application templates, student profiles, saved applications, essays, transcripts, recommenders, or questionnaire responses are stored in this public repository.
