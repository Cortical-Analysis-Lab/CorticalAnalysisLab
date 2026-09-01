# Canonical database

`research_opportunities.sqlite` is the canonical public opportunity catalog. Rebuild it from the committed starter import with:

```bash
python scripts/rebuild_database.py
```

Do not store student profiles, questionnaire answers, saved programs, essays, transcripts, or other personal data here. The database is public-repository content.

`imports/` contains human-reviewable source files. Import provenance and each original row are also retained inside SQLite.

The schema is documented in `schema/data_dictionary.md`. Reviewed update and agent rules are in `docs/database_update_process.md` and `docs/data_sources.md`.

The database stores stable program identities separately from annual cycles, plus institutions, structured eligibility, controlled categories/tags/modes, and field-level source verification. Institution latitude and longitude are nullable until verified; all seed institutions currently need coordinates before the map can launch.
