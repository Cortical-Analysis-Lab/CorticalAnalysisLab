# Summer Undergraduate Research Opportunity Explorer: data architecture

## Repository placement

This site is a static GitHub Pages repository with existing browser data in `/data`. The catalog therefore uses:

- `/database/research_opportunities.sqlite` — canonical published database
- `/database/imports/` — accepted CSV data used to reproduce SQLite
- `/schema/` — versioned SQL schema and data dictionary
- `/scripts/` — deterministic import, structural validation, rebuild, test, and export commands
- `/data/summer-research/` — generated static JSON for the browser

The current pages and existing `data/people.json` and `data/publications.json` remain unchanged.

## Normalization choices

Institutions and stable opportunities are independent of annual cycles. Dates, deadlines, application URLs, status, compensation, benefits, hard eligibility, and verification are cycle-specific. Broad categories, narrower tags, and controlled research modes use many-to-many links. Sources are deduplicated by URL, while verification events retain check date, supported fields, conflict status, and future evidence hashes.

The starter's original row is retained as JSON with its import-run hash. This makes later corrections auditable and prevents normalization from destroying source wording.

## Scale posture

The schema is intended to support at least 5,000 stable program identities and 15,000 to 25,000 annual-cycle records over time. Program identity is intentionally separate from annual cycle data so refreshes create or update cycle records rather than duplicating the same opportunity each year.

Use one stable opportunity for a separately named research program or application at a host institution. Do not model student slots, individual lab projects, grant records, annual cycles, directories, or news/support pages as separate opportunities.

## Website contract

GitHub Pages reads static JSON only; it does not open SQLite in the browser. `catalog.json` is the convenient denormalized payload. Normalized JSON files are also exported for smaller or specialized loads.

Eligibility fields are nullable. A future evaluator must return three outcomes: `eligible`, `ineligible`, or `unknown/review needed`. Unknown must never be treated as false. Preference filters—including research mode—operate separately from hard eligibility.

## Data build

```bash
python scripts/rebuild_database.py
python scripts/test_catalog.py
```

Opportunity discovery, evaluation, verification, and review happen outside this repository. Only accepted records enter the committed CSV. The repository build checks relational integrity and produces SQLite and browser JSON deterministically.

## Explicitly out of scope

No application templates, student profiles, saved applications, essays, transcripts, recommenders, or questionnaire responses are stored in this public repository.
