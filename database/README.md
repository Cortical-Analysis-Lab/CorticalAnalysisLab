# Canonical database

`research_opportunities.sqlite` is the canonical published opportunity catalog. The accepted CSV under `imports/` is its version-controlled source. Rebuild SQLite and the browser JSON from that CSV with:

```bash
python scripts/rebuild_database.py
```

Do not store student profiles, questionnaire answers, saved programs, essays, transcripts, or other personal data here. The database is public-repository content.

`imports/` contains accepted database records produced by the external evaluation process. Import provenance and each original row are retained inside SQLite.

The schema is documented in `schema/data_dictionary.md`.

The database stores stable program identities separately from annual cycles, plus institutions, structured eligibility, controlled categories/tags/modes, and field-level source verification.

Discovery-source metadata is seeded from `database/discovery/source_catalog_seed.json`. Discovery provenance remains separate from official-source verification evidence.
