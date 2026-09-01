# Canonical database

`research_opportunities.sqlite` is the canonical public opportunity catalog. Rebuild it from the committed starter import with:

```bash
python scripts/rebuild_database.py
```

Do not store student profiles, questionnaire answers, saved programs, essays, transcripts, or other personal data here. The database is public-repository content.

`imports/` contains human-reviewable source files. Import provenance and each original row are also retained inside SQLite.
