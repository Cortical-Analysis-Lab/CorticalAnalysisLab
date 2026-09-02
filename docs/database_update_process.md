# Summer research database update process

SQLite is canonical. Files in `data/summer-research/` are generated and must not be edited directly.

## Local GUI workflow

`local_catalog_manager.py` is the recommended workstation entry point. It binds only to `127.0.0.1`, uses a per-launch request token, and keeps resumable operational state in the git-ignored `database/local/catalog_candidates.sqlite`.

1. Add official or potential opportunity links through **Add opportunity links**.
2. Run an approved-source discovery session. The GUI displays live elapsed time, discovered-candidate progress, and source-error counts from the active session's `progress.json`.
3. Run **Run full automated update**. The local automation claims pending/retry candidates, fetches official NSF metadata, rejects obvious non-opportunity awards, writes structured result files for likely REU/Site programs, records strict agent approvals for clean proposals, promotes approved rows into reviewed imports, rebuilds SQLite/JSON, runs tests, and writes source audits.
4. Run **Reinvestigate N/A updates** on later dates when cycles may have opened or official pages may have published dates, deadlines, duration, stipend, or application links. Existing-program matches are eligible for missing-field enrichment and are not discarded solely because the program identity already exists.
5. Review `database/local/source_audit/` for the compact list of retrieved publishers/links.
6. Review `database/local/review/incomplete_data_review_log.csv` for opportunities where optional fields were recorded as `N/A` because official reviewed sources did not provide them.
7. Repeat only if new discovery adds candidates or a future extractor resolves previously unresolved records.
8. Use **Validate and agent-approve** when you need to re-check current result files. Validation automatically approves clean records when the result contract passes, evidence is authoritative and official, identity is not ambiguous, and there are no conflicts or validation warnings.
9. Manual inspection and Desktop Codex fallback bundles are optional debugging/escalation paths, not required approval gates.
10. Run `python scripts/promote_catalog_candidates.py --approved-only` to produce an approval audit report before any reviewed import update.
11. Use **Rebuild and validate** to regenerate canonical SQLite, browser JSON, and review exports and to run validation/regression checks.
12. Review and commit the repository diff. Local staging and agent work queues remain uncommitted.

The guided GUI stages are:

1. Discovery
2. Identity matching/deduplication
3. Codex investigation bundle generation
4. Waiting for agent results
5. Agent validation/approval
6. Approved-only promotion
7. SQLite/JSON rebuild
8. Validation/testing
9. Git diff review
10. Optional branch/commit/push/PR submission

The GUI deliberately does not embed an API key, invoke an undocumented Desktop Codex interface, or promote discovery-only candidates. Local automation performs the normal investigation and promotion path while repository updates remain deterministic and reviewable.

If local discovery immediately reports socket permission errors, restart the manager from Desktop Codex with network permission. Closing the browser tab does not stop a running job, but stopping the Python manager process, sleeping the computer, or losing network access can interrupt it.

## Agent result contract

Desktop Codex must write structured results under the git-ignored `database/local/agent_results/` directory:

- `proposed_records.json`
- `source_evidence.json`
- `session_report.json`

The tracked schemas live in `schema/agent_results/`. Results must use contract version `1.0`, include field-level official-source evidence, preserve unknown and conditional facts, and treat social posts, aggregators, search snippets, forums, and third-party summaries as discovery-only.

Strict agent approval eliminates mandatory human review for clean records. Any ambiguous duplicate, conflict, stale approval signature, validation warning, or missing official evidence is not promoted; candidates without enough official evidence are rejected by the automated pass.

## Reviewed update sequence

1. **Discover** a candidate from a public directory or institutional search.
2. **Extract** candidate values and exact source URLs into a staging CSV/XLSX. Leave absent facts blank.
3. **Verify** against a validated official program, host-institution, government, network, or explicitly delegated opportunity-specific application page. Social posts, aggregators, search snippets, forums, and third-party summaries are discovery-only and cannot support canonical fields. Record the check date, narrowly supported fields, conflicts, authority rationale, and whether the source is authoritative.
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
- Duplicate identity detection must not suppress updates for missing cycle fields. When an approved official-source proposal maps to an existing `(Program_ID, Cycle_Year)`, the updater may fill fields that are currently blank or `N/A` with non-`N/A` values from the official source. It must not silently overwrite existing reviewed non-empty values.
- Never overwrite a historical cycle with a newer year's dates, funding, eligibility, or application URL.

Potential fuzzy matches should be blocked from promotion or rejected unless a later automated pass obtains enough official evidence to resolve the identity. An automated updater must not decide ambiguous identity matches silently.

## Unknown and conflict handling

- Blank or ambiguous typed fields remain `NULL` in SQLite/JSON; reviewed CSV/XLSX files use `N/A` for absent optional dates, deadlines, durations, and stipend amounts so missing data is visible during review. Controlled status fields use `unknown` where non-null values are required.
- Missing text never implies `no`, unpaid, ineligible, or unsupported.
- Preserve the source wording in raw import records and matching text/details fields.
- If official sources disagree, retain the best-supported current value only after review and add a `conflict` source verification with `conflict_notes`.
- Research modes are assigned only when an imported or reviewed source explicitly supports them.

## Commands

Run a bounded discovery session locally (this writes staging reports only):

```bash
python scripts/run_discovery_session.py --time-budget-minutes 30 --output /tmp/summer-research-discovery
```

Run a local automated investigation batch:

```bash
python scripts/automated_investigate_candidates.py --limit 100
```

Run the full local automated pipeline:

```bash
python scripts/run_catalog_update_pipeline.py --batch-size 100
```

Source links retrieved by automation are written to:

```text
database/local/source_audit/retrieved_sources.csv
database/local/source_audit/retrieved_sources.md
```

Create an optional Desktop Codex fallback batch:

```bash
python scripts/create_agent_batch.py --limit 25
```

The GitHub **Update summer research catalog** workflow runs the same catalog-aware session, uploads `candidates.csv`, `report.json`, and `summary.md`, then rebuilds and validates reviewed inclusions. When requested, it opens a GitHub issue containing the completion summary.

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
