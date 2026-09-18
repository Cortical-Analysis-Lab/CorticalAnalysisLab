# Accepted catalog data

The CSV in this directory contains accepted catalog records prepared outside this repository. It is the version-controlled source used to reproduce the published SQLite database. Importing a later annual cycle should update the stable opportunity and create or update only that year's cycle.

Boolean fields accept only explicit `1`/`0`, `yes`/`no`, or `true`/`false`; blanks remain `NULL`. Source and verification columns are preserved in SQLite for provenance.

Verified program identities may have a blank `Cycle_Year`. This creates one undated information snapshot per `Program_ID`; it does not invent an application year or claim current availability. Historical, paused and undated programs remain potential options. Keep the same ID when adding a dated cycle: the browser exports one program with its cycles nested underneath it.

Optional `Secondary_Fields` contains semicolon-separated controlled category names. `Field_Tags` retains specific topics, methods and interdisciplinary information. `Bundle_Provenance` records the originating bundle revision and discovery ID in raw import provenance.

Optional `Source_Evidence_JSON` is a JSON list of official-source objects containing `url`, `date_checked` (ISO date), `fields_supported` (populated CSV column names), `checked_by`, and optional `limitations`. When present, these explicit field assignments replace blanket attribution to the program/application pages. Identity verification does not imply complete eligibility verification; incomplete eligibility stays `needs_review`.

Schema 1.3 adds nullable cycle years. Use `python3 scripts/rebuild_database.py` to upgrade an existing database from its accepted CSV before importing additional records.
