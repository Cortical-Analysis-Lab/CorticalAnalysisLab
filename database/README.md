# Canonical database

`research_opportunities.sqlite` is the canonical published opportunity catalog. The accepted CSV under `imports/` is its version-controlled source. Rebuild SQLite and the browser JSON from that CSV with:

```bash
python scripts/rebuild_database.py
```

Run factual guardrails after changing the accepted CSV:

```bash
python scripts/remove_funding_identity_records.py --dry-run --fail-if-found
python scripts/review_duplicate_identities.py
python scripts/audit_catalog_accuracy.py
python scripts/test_catalog.py
```

Do not store student profiles, questionnaire answers, saved programs, essays, transcripts, or other personal data here. The database is public-repository content.

`imports/` contains accepted database records produced by the external evaluation process. Import provenance and each original row are retained inside SQLite.

The schema is documented in `schema/data_dictionary.md`.

The database stores stable program identities separately from annual cycles, plus institutions, structured eligibility, controlled categories/tags/modes, and field-level source verification.

Discovery-source metadata is seeded from `database/discovery/source_catalog_seed.json`. Discovery provenance remains separate from official-source verification evidence. Funding, grant, and award records are discovery-only leads; do not commit them as public program records, application URLs, or field-verification evidence.

Current accepted scale after rebuild: 86 program identities and 86 annual cycles.

Planning target: design the discovery/review workflow for at least 5,000 stable program identities and 15,000 to 25,000 annual-cycle records over time. A program identity is a separately named research program or application at a host institution. Student slots, individual faculty projects, annual cycles, funding records, directories, and news/support pages are not program identities.
