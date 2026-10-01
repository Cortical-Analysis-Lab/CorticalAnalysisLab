# Catalog follow-up tasks

## Information review integration — October 1, 2026

Compared `program-information-review-2026-10-01.zip` with its exact baseline, `2b2866d`. All supplied program IDs match existing identities. Integrated the 225 observations, the overlapping 23-entry targeted batch, and nine additional reconfirmation/gap notes into 250 existing programs. These are newly captured reports, reconfirmations and conflicts; they are not 250 independently verified changes. Original values and source metadata remain reproducible in the accepted CSV's bundle review/fact history.

Existing annual records now include corrected NIH SIP and NASA OSTEM deadlines, BU RISE's application deadline, St. Jude's June 1 start, and high-school application windows at Iowa, Salk, Roswell and Hillman. Hillman's program dates remain tentative, and Roswell's portal availability remains unconfirmed. DAAD and Penn application/reference deadlines remain distinct. Repaired UTMB NSURP and Hillman links; removed the unrelated `reucsu.org` student-facing link without deleting the program. Retained paused/cancelled programs with explicit status wording. Currency, hourly pay, conditional benefits and conflicting eligibility remain narrative where no canonical amount or rule is supported.

The existing Program details dialog exposes program notes and information updates in a collapsed disclosure, including records without bundle reports. No generic provisional warnings were restored. High-school source reports and existing annual rows stay synchronized; paid housing is not converted to free housing.

The user authorized adding supported 2027 annual information under existing programs. Added **206 annual cycles**, including the targeted batch's 17 proposals, for **1,035 identities / 1,245 cycle records**; 231 cycles now have year 2027. Exact dates and explicitly supported benefits are separated from tentative schedules, priority/reference deadlines, hourly pay, foreign-currency allowances, conditional funding and unresolved eligibility. Historical cycles remain intact. New deadline-only cycles do not inherit old benefits or eligibility exclusions. Programs without supported 2027 information remain discoverable with their historical or undated facts, without a claimed 2027 offering.

Machine-generated amount signals and recovered candidate URLs were not promoted to accepted facts. The package reports 255 unresolved stored sources and 25 identities without stored URLs; retrieval screening does not establish full verification. No blanket verification dates were advanced, and the source-verification count remains 397. The existing specific UCSF eligibility conflict remains visible; Amgen funding-track benefits were not applied to all SRTP participants. All 225 observations and overlapping targeted notes remain available in the generated catalog.

The original review package, integration comparison, annual-cycle decisions and baseline CSV are retained under `/tmp/program-information-review-audit/`, `/tmp/program-review-integration-results.json`, `/tmp/program-review-cycle-results.json` and `/tmp/program-review-before.csv`. Structural validation, catalog regression tests, narrative/display tests, all-program JavaScript rendering checks, syntax checks and whitespace checks pass. These checks do not establish full factual verification. Publication remains suspended; no push or remote-branch change is authorized.

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

The September 21 display-consistency correction pass updated 15 accepted records, including stipend amount/unit corrections, housing deductions, and removal of unsupported annual benefit claims. GeoPEERS is now an undated snapshot because the official page does not establish a year (639 undated snapshots total). Prior values are preserved in bundle fact history. Field-specific official evidence remains distinct from full-program verification.

Generated `reported_facts` now connects narrative evidence to the corresponding detail field when structured facts are unknown. Statements retain their source, reported year, wording and qualifications; they are not numeric data or eligibility rules. Older descriptions remain expandable instead of appearing as the main overview. Audit and correction records are local under `database/local/review/display-consistency/` and `database/local/review/display-fixes/`; the latter includes accepted changes and an after-audit. Dates, locations and unresolved source/track differences still require factual review rather than inferred completion.

Additional regression checks: `python3 scripts/test_display_consistency.py` and `node scripts/test_fellowship_display.js`.

Rebuild SQLite/JSON with `python3 scripts/rebuild_database.py`, then run `scripts/validate_catalog.py`, `scripts/test_catalog.py`, `node --check assets/fellowship-questionnaire.js` and `git diff --check`. Schema 1.5 adds accepted bundle status; rebuild older databases before importing. Publication remains suspended; do not push or restore publication without an explicit request.

## High-school integration — September 21, 2026

Accepted 89 supplied high-school reports from `high-school-research-files.zip`: 82 new identities plus seven supplements, for 1,035 total programs. Four unresolved discovery leads remain outside the catalog. The complete imported review and integration decisions are kept locally under `database/local/review/high-school-files/`; accepted records and their full report provenance are reproducible from the CSV.

The questionnaire now routes high-school and college applicants by catalog audience. Institution type determines the current-year choices, including grades 9–12 for high school. Explicit grade restrictions participate in matching; exceptions remain available for review. Age, nomination, local residence and partner-school conditions remain visible requirements to confirm; these answers are not collected. Existing undergraduate facts are preserved. This integration uses the supplied review and is not independent fact verification of all 89 programs. Publication remains suspended.
