# Accepted catalog data

The CSV in this directory contains accepted catalog records prepared outside this repository. It is the version-controlled source used to reproduce the published SQLite database. Importing a later annual cycle should update the stable opportunity and create or update only that year's cycle.

As explicitly requested on September 18, 2026, accepted records now include provisional bundle candidates. `Catalog_Review_Status=needs_review` identifies an unverified program; `supplement_needs_review` identifies unreviewed additional information attached to an existing program. `Review_Notes` lists pending checks. `Bundle_Details_JSON` retains reported topics, eligibility, location, cycle history, housing provision/cost/amount, meals, room-and-board terms, source references and original evidence classifications. These reports are stored in `opportunity_review` and exported for display, not represented as newly verified facts. Provisional rows have no `Last_Verified`, no fabricated source-verification event, and no inferred hard eligibility exclusions. A missing official program link stays blank.

Known enrollment restrictions that exclude Sacred Heart University students are excluded. A shared URL alone must not exclude or consolidate distinct tracks; ONPRC's general fellowship remains distinct from its Oregon-only Provost track. Unknown external eligibility stays available with review notes. Bundle entries explicitly identified as non-research placements remain outside this summer research catalog.

Boolean fields accept only explicit `1`/`0`, `yes`/`no`, or `true`/`false`; blanks remain `NULL`. Source and verification columns are preserved in SQLite for provenance.

Verified program identities may have a blank `Cycle_Year`. This creates one undated information snapshot per `Program_ID`; it does not invent an application year or claim current availability. Historical, paused and undated programs remain potential options. Keep the same ID when adding a dated cycle: the browser exports one program with its cycles nested underneath it.

Optional `Secondary_Fields` contains semicolon-separated controlled category names. `Field_Tags` retains specific topics, methods and interdisciplinary information. `Bundle_Provenance` records the originating bundle revision and discovery ID in raw import provenance.

Optional `Source_Evidence_JSON` is a JSON list of official-source objects containing `url`, `date_checked` (ISO date), `fields_supported` (populated CSV column names), `checked_by`, and optional `limitations`. When present, these explicit field assignments replace blanket attribution to the program/application pages. Identity verification does not imply complete eligibility verification; incomplete eligibility stays `needs_review`.

Schema 1.3 adds nullable cycle years; schema 1.4 adds explicit provisional review metadata. Use `python3 scripts/rebuild_database.py` to upgrade an existing database from its accepted CSV before importing additional records.

The September 21 name/alias pass consolidated 15 duplicate identities and cleaned 36 titles. Removed rows, including original IDs, names, fields and cycle snapshots, are retained under `catalogIdentityHistory` in the combined `Bundle_Details_JSON`; original bundle reports remain intact apart from this added provenance. Standalone title changes retain their original names in `Notes`. Identity review does not establish factual verification or current availability. Ambiguous pairs remain separate with explicit review notes. Full factual review is deferred at the user's request; follow [the catalog follow-up tasks](../../docs/catalog-follow-up.md).
