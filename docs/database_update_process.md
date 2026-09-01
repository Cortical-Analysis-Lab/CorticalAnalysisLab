# Summer research database update process

SQLite is canonical. Files in `data/summer-research/` are generated and must not be edited directly.

## Reviewed update sequence

1. **Discover** a candidate from a public directory or institutional search.
2. **Extract** candidate values and exact source URLs into a staging CSV/XLSX. Leave absent facts blank.
3. **Verify** against an official program, institution, or application page. Record the check date, supported fields, conflicts, and whether the source is authoritative.
4. **Classify** reviewed broad categories, detailed tags, and only explicitly supported research modes.
5. **Deduplicate** before import using the rules below.
6. **Import** into a temporary database first, validate it, review warnings, and then update canonical SQLite.
7. **Export** browser JSON and human-review artifacts from SQLite.
8. **Review the diff** for unexpected deletions, invented values, changed stable IDs, or overwritten historical cycles.

Automated discovery or extraction agents may create candidate staging rows. They must not modify canonical SQLite or public JSON without the deterministic reviewed import step.

## Deduplication and identity rules

- Match institutions by reviewed name, city, state, and country. Name aliases should resolve to the same institution; do not create a second marker for spelling or abbreviation differences.
- Match a stable program by `public_id` and official identity, not by cycle year. A returning program gets a new `program_cycles` row.
- Treat renamed programs as the existing stable program when official evidence establishes continuity. Preserve the old name in source/raw-import history.
- Treat programs at the same institution as distinct when they have different official identities, eligibility, applications, or program pages.
- Deduplicate sources by normalized exact URL. A new verification event should reference the existing source.
- Never overwrite a historical cycle with a newer year's dates, funding, eligibility, or application URL.

Potential fuzzy matches should be emitted for human review. An automated updater must not decide ambiguous identity matches silently.

## Unknown and conflict handling

- Blank or ambiguous typed fields remain `NULL`; controlled status fields use `unknown` where non-null values are required.
- Missing text never implies `no`, unpaid, ineligible, or unsupported.
- Preserve the source wording in raw import records and matching text/details fields.
- If official sources disagree, retain the best-supported current value only after review and add a `conflict` source verification with `conflict_notes`.
- Research modes are assigned only when an imported or reviewed source explicitly supports them.

## Commands

Dry-run a reviewed import:

```bash
python scripts/import_catalog.py path/to/reviewed.csv --dry-run
```

Test an import without touching the canonical database:

```bash
python scripts/import_catalog.py path/to/reviewed.csv --database /tmp/summer-research-review.sqlite
python scripts/validate_catalog.py --database /tmp/summer-research-review.sqlite
python scripts/export_catalog.py --database /tmp/summer-research-review.sqlite --output /tmp/summer-research-export
```

After review, update, validate, and export:

```bash
python scripts/import_catalog.py path/to/reviewed.csv
python scripts/validate_catalog.py
python scripts/export_catalog.py
python scripts/export_review_xlsx.py
python scripts/test_catalog.py
```

For a deterministic rebuild from the committed starter seed:

```bash
python scripts/rebuild_database.py
```

## Future updater contract

A future updater should operate in a transaction and emit an audit summary containing the import run, inserted and updated institution/program/cycle IDs, warnings, conflicts, and sources checked. Candidate updates should eventually use proposed-change and reviewer-decision tables rather than writing canonical rows directly. Student eligibility answers and application materials are out of scope and must never enter this public database.
