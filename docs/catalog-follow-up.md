# Catalog follow-up tasks

## Current result — September 21, 2026

The user requested full review of the remaining unresolved cases and accepted prior Chat Work review of the bundle entries. The review covered all 29 records in the unresolved set, including the additional Rutgers Math/DIMACS and UVA pairs tracked in the external audit.

- Consolidated UCSF SRTP/Amgen into the stable `AMGEN-UCSF` identity. Amgen-only requirements no longer restrict the broader SRTP listing.
- Removed four independent listings that were directories or umbrellas: Harvard research opportunities, ORNL undergraduate opportunities, Wisconsin integrated REU, and PARADIM's network umbrella. Individual programs and PARADIM campus listings remain.
- Excluded the WashU CEMB placement because its current institution restrictions exclude SHU. Penn CEMB is separately represented, with unknown eligibility retained.
- Corrected host labels for Blandy/UVA, Cedar Creek/UMN, CELL-MET/Michigan and PARADIM/JHU. Corrected program links and retained historical snapshots.
- Preserved separate Mote URE/NSF REU tracks, Wisconsin chemistry programs, Cedar Creek LTER/Isbell placements, Michigan NURO/SIREN, Rochester Graduate Education/MSTP, Pittsburgh School of Medicine/CNUP, Rutgers Math/DIMACS and UVA SR-EIP/SRIP.
- Recorded PARADIM's cancelled 2026 cycle. Conditional or future-cycle information was not copied into historical cycles.

The catalog now has **953 identities / 954 snapshots**. Across the three September 21 passes, 23 duplicates were consolidated, one test listing removed, four umbrella/directory listings removed and one restricted placement excluded. This remains a catalog listing count, not a guarantee that every field is independently verified.

## Remaining specific evidence gaps

1. **UCSF SRTP (`AMGEN-UCSF`)**: official main page and FAQ differ on DACA/AB540 eligibility; an application section contains an outdated deadline year. Use the explicitly labeled 2026 deadline and retain the eligibility concern.
2. **Penn CEMB (`BND-21B2481861C524C2`)**: current Penn external-applicant eligibility and housing terms are not stated. Do not transfer WashU restrictions or benefits to Penn.
3. **Wisconsin Future Manufacturing (`BND-642A3AFAFA140976`)**: distinct identity confirmed by UW's graduate-school list; department page was unavailable for detailed eligibility/benefits checks.
4. **Wisconsin Chemistry/CBE (`BND-D833CF56CA9DD95D`)**: same evidence-access limitation; retained as a separately named program.
5. **Western Michigan Environmental Signal Transduction (`BND-4334627EF951B1D4`)**: removed the unrelated BU link. The only official historical match located was a grant mention, which remains discovery-only. Current student-facing program evidence, eligibility, dates and benefits are unavailable; no verification event was created.

These five have specific `Review_Notes`. Review attempts do not justify filling missing facts or treating partial eligibility parsing as complete.

## Bundle acceptance and presentation

The user's acceptance of prior Chat Work review supersedes the earlier blanket provisional-review workflow. **923 identities** now use `Catalog_Review_Status=bundle_accepted` and show **Program details**, without a generic provisional warning. Five retain specific notes and 25 have no bundle review metadata. Keep acceptance separate from official field evidence: do not fabricate verification dates, promote unknown eligibility, or add verification events solely because a bundle is accepted.

Original source reports and benefit claims remain in `Bundle_Details_JSON`. Acceptance history preserves former generic notes. Fact corrections preserve original rows in `catalogFactHistory`; merges preserve originals in `catalogIdentityHistory`. Excluded rows remain in Git history and the external exclusion archive.

## Audit artifacts and future imports

The latest external report and evidence are at `/tmp/cortical-unresolved-review/REPORT.md`, with `review-results.json`, `before.csv`, `excluded-records.json`, `fetched.json`, `pages/` and `apply.py`. These temporary review files are not version-controlled. Earlier audit artifacts remain at `/tmp/cortical-full-overlap-audit/` and `/tmp/cortical-name-review-2026-09-21/`.

For new imports, repeat name, host, link and redirect screening; never automatically merge on a shared portal or institution. Use `scripts/review_catalog_names.py` for explicit accepted decisions and a separate exclusion archive. Preserve stable IDs and dated cycles, clean cycle labels from titles, retain meaningful numbers such as Biosphere 2, and record only supported corrections.

## Validation and publication

Rebuild SQLite/JSON with `python3 scripts/rebuild_database.py`, then run `scripts/validate_catalog.py`, `scripts/test_catalog.py`, `node --check assets/fellowship-questionnaire.js` and `git diff --check`. Schema 1.5 adds accepted bundle status; rebuild older databases before importing. Publication remains suspended; do not push or restore publication without an explicit request.
