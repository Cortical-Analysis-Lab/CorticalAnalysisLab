# Import staging

Files here are inputs reviewed by a person before promotion into SQLite. Use `scripts/import_catalog.py --dry-run` first. Importing a later annual cycle should update the stable opportunity and create or update only that year's cycle.

Structured eligibility review is carried in the optional `Eligibility_*` columns of the seed. Boolean fields accept only explicit `1`/`0`, `yes`/`no`, or `true`/`false`; blanks remain `NULL`. Set `Eligibility_Parse_Status` to `reviewed` only when the structured values were checked against the URL in `Eligibility_Source_URL`. Record `Eligibility_Checked_On` and `Eligibility_Checked_By` so the importer can create a reproducible source-verification event.
