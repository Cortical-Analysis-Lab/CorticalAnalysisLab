# Accepted catalog data

The accepted CSV is covered by the repository's [all-rights-reserved terms](../../LICENSE).
The October 3, 2026 complete-program package is reconciled with the October 1
integration, retaining historical cycles and source limitations. Screening and
source-recovery reports do not establish full verification. Unaccepted discovery
candidates remain outside the canonical data. See [integration decisions](../../docs/catalog-follow-up.md).

The CSV in this directory contains accepted catalog records prepared outside this repository. It is the version-controlled source used to reproduce the published SQLite database. Importing a later annual cycle should update the stable opportunity and create or update only that year's cycle.

The September 21 user instruction accepts the prior Chat Work bundle review and removes generic provisional warnings. `Catalog_Review_Status=bundle_accepted` represents this acceptance; it is not independent official-source verification. `needs_review` and `supplement_needs_review` now identify specific remaining concerns, described in `Review_Notes`. Accepted entries show a neutral **Program details** section. Entries with no official verification date keep that date blank and gain no verification event merely through acceptance.

`Bundle_Details_JSON` retains reported topics, eligibility, locations, cycles, benefits, references and original evidence classifications. `catalogReviewAcceptance` preserves the previous generic review status/notes; `catalogFactHistory` preserves rows before official-source corrections; `catalogIdentityHistory` preserves merged identities. These reports remain in SQLite and browser JSON. A missing official program link stays blank.

Known enrollment restrictions that exclude Sacred Heart University students are excluded. A shared URL alone must not exclude or consolidate distinct tracks; ONPRC's general fellowship remains distinct from its Oregon-only Provost track. Unknown external eligibility stays available with review notes. Bundle entries explicitly identified as non-research placements remain outside this summer research catalog.

Boolean fields accept only explicit `1`/`0`, `yes`/`no`, or `true`/`false`; blanks remain `NULL`. Source and verification columns are preserved in SQLite for provenance.

Verified program identities may have a blank `Cycle_Year`. This creates one undated information snapshot per `Program_ID`; it does not invent an application year or claim current availability. Historical, paused and undated programs remain potential options. Keep the same ID when adding a dated cycle: the browser exports one program with its cycles nested underneath it.

Optional `Secondary_Fields` contains semicolon-separated controlled category names. `Field_Tags` retains specific topics, methods and interdisciplinary information. `Bundle_Provenance` records the originating bundle revision and discovery ID in raw import provenance.

Optional `Source_Evidence_JSON` is a JSON list of official-source objects containing `url`, `date_checked` (ISO date), `fields_supported` (populated CSV column names), `checked_by`, and optional `limitations`. When present, these explicit field assignments replace blanket attribution to the program/application pages. Identity verification does not imply complete eligibility verification; incomplete eligibility stays `needs_review`.

Schema 1.3 adds nullable cycle years; schema 1.4 adds explicit provisional review metadata; schema 1.5 adds user-accepted bundle status. Use `python3 scripts/rebuild_database.py` to upgrade an existing database from its accepted CSV before importing additional records.

The September 21 name/alias pass consolidated 15 duplicate identities and cleaned 36 titles. Removed rows, including original IDs, names, fields and cycle snapshots, are retained under `catalogIdentityHistory` in the combined `Bundle_Details_JSON`; original bundle reports remain intact apart from this added provenance. Standalone title changes retain their original names in `Notes`. Identity review does not establish factual verification or current availability. Ambiguous pairs remain separate with explicit review notes. Full factual review is deferred at the user's request; follow [the catalog follow-up tasks](../../docs/catalog-follow-up.md).

The subsequent full-catalog overlap screen consolidated seven more identities (22 total across the two September 21 passes) and removed one `[TEST]` listing at the user's request. The catalog now has 959 identities / 960 cycle snapshots. Shared institution names and redirects to broad portals were not automatic merge grounds. Remaining ambiguous umbrella/track cases are tracked in the follow-up document and review notes. All original merged records remain in identity history; the excluded test record remains in Git history and the external audit archive.

The unresolved-record review covered 29 records, merged one further duplicate, removed four umbrella/directory listings, and excluded the locally restricted WashU CEMB placement. The final catalog has 953 identities / 954 snapshots: 923 accepted bundle/supplement identities, five with specific review notes, and 25 without bundle review metadata. Publication remains suspended.
