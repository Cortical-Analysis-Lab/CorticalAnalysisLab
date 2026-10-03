# Catalog follow-up tasks

## Complete-program update integration — October 3, 2026

Integrated `Opp_Updates/complete-program-updates-2027-2026-10-03.zip` from the remote `Summer-REU-Database` file listing into the local development branch. Package SHA-256: `23330b3a37d841db51d98b81f2bb36a8ce96bbb6da7dd6a2d8b542bece757668`. Compared the exact CSV at package baseline `e444c5f482724418d6df4836dd3e38c1584f17b1` with local integration baseline `611d8a3`: the package baseline contains 1,039 cycles, while local HEAD already contains the October 1 additions, totaling 1,245. All 206 previously added annual cycles are retained. No wholesale baseline replacement was performed.

The package accounts for all 1,035 prior identities, supplies 68 findings, and provides 157 source-recovery reports. The accepted CSV retains attributed screening ledgers for the 1,031 remaining identities, 65 findings applicable to retained programs, and 156 source-recovery reports. The original package and all 68 integration decisions are retained locally. Unaccepted search-result candidate lists remain outside the canonical CSV and exports. Recovered, blocked, historical, related-host and provenance-only sources retain their distinct classifications; retrieval alone creates no verification event or eligibility exclusion.

Accepted narrow official-source fields for 22 identities and added **21 2027 cycles** under existing identities. New annual information covers ECU C2C, RIKEN's internship course, Purdue PURE Tox, Minneapolis Heart Institute, Sanford SPUR, Coral Restoration, Wisconsin SSEC, Broad BSRP, EPFL Life Sciences, Utah ECE, UCSB RMP/SRA, Miami Miller SURF, MSU Plant Genomics, Columbia IICD, JHU NanoBio, Princeton PNI, Denver power/energy REU, REU-EXTEND, Pfizer R&D, and Columbia SR-EIP. NIH SIP's existing January 26 deadline is reconfirmed with separate reference-letter wording. Minneapolis's $680 is weekly, not a guaranteed total. Other reported benefits, hourly pay, caps and eligibility conditions remain attributed reports rather than inferred numeric amounts or exclusions. Pfizer's cohort-wide application window includes R&D; it does not guarantee a specific placement.

Important acceptance boundaries:

- Denver's March 3 date is a **priority** deadline and is stored only in `Deadline_Text`; the final application deadline stays unknown.
- Princeton PNI's February 1 closing remains tentative. Exact program dates and opening are accepted, while the package's funding-contingency report is retained and availability remains unknown. The currently retrieved application page supports dates but does not independently establish that contingency.
- JHU NanoBio explicitly does not accept summer 2027 applications while funding/approval is pending. Its new annual status is closed; historical identity and information remain. A 2028 restart is not guaranteed. [Official program source](https://inbt.jhu.edu/nanobio-reu/).
- UCSB high-school reports now contain the correct 2027 windows and full program dates, including RMP's required virtual phase. The 2027 cycle does not inherit 2026 fees, housing/meal terms or financial aid. Historical reports remain expandable. The audience view respects the explicitly recorded hybrid format.
- Tentative SIMR/Pitt/Penn calendars, CaRSIP's conflicting opening year and graduation wording, OIST's placement window, Van Andel/ITEP track information, Buck's postbaccalaureate identity conflict, and AGA funding/academic-year scope questions remain reports requiring specific follow-up. No unsupported dates or scope consolidations were applied.

Four records were withdrawn from the active accepted CSV, with their full original rows preserved in Git history and the local quarantine/exclusion archive:

| Program ID | Decision | Evidence and limitation |
| --- | --- | --- |
| `BND-730E888D56D253BE` | Quarantine Central Washington “REU Molecular Gen” | Stored bundle summary begins with Lorem ipsum placeholder text. No distinct real summer program is established; retain for external scope review rather than treating it as a confirmed opportunity. |
| `BND-AEC80FD7C401F158` | Exclude Bowie ExLent | [Official eligibility](https://www.bowiestate.edu/academics/colleges/college-of-arts-and-sciences/departments/computer-science/resources-for-students/scholarships/exlent-ai-internship-program/) explicitly requires Bowie State enrollment; this excludes SHU applicants. The October 31 preparatory start is not a summer internship start. |
| `AUTO-97DF9D9FCB` | Exclude ETH Zürich Amgen | [Europe Amgen eligibility](https://amgenscholars.com/europe-programme/) requires a degree at an eligible European institution, excluding SHU enrollment. This is an enrollment restriction, not citizenship. |
| `AUTO-F44FD4F2FE` | Exclude Institut Pasteur Amgen | Same Europe Amgen enrollment requirement; do not attach the February deadline while implying SHU eligibility. |

The integration reviewer is Codex, checked October 3, 2026. These are narrow identity/scope/field decisions, not blanket verification of all facts in the affected programs.

The ACCESS correction takes precedence: the General Internal Medicine internship is a different program. Attached the [ACCESS-specific source](https://gradschool.weill.cornell.edu/access-and-belonging/capacity-building-programs/access), retained the retraction in provenance, and did not create an ACCESS 2027 cycle. NYU chemistry/biology information at `nyureu.org` does not establish Center for Neural Science suspension or 2027 status. The unrelated `reucsu.org` link remains disabled.

Fresh source checks did not confirm the package's proposed 2027 dates for UCLA BRI-SURE, NYU Vilcek SURP, or MBARI: currently retrieved pages still show historical information or lack those dates. NHERI retrieval failed. These proposals remain explicitly unaccepted reports; successful checks elsewhere do not resolve them.

Current result: **1,031 identities / 1,262 cycle records**, including **696 undated snapshots** and **252 records for 2027**, across **730 host/location records**, **13 broad categories**, **1,858 detailed tags**, and **11 research modes**. There are **416 field-source verification events**: narrow accepted fields add 21 events, while the two excluded European records remove their old events. No blanket `Last_Verified` dates or completed eligibility reviews were invented. Listing counts remain distinct from independently verified counts.

The source ZIP, pre-integration CSV, complete integration decisions and withdrawn rows are under `database/local/review/complete-program-updates-2026-10-03/` (ignored local review artifacts). Accepted records, attributed reports, package identity, limitations and prior fact values reproduce from the committed CSV. SQLite/JSON rebuild, structural validation, 35 catalog tests including round-trip reproduction, 10 narrative/display tests, all-program JavaScript rendering/audience checks, syntax and whitespace checks pass. Publication remains suspended; no push, merge, or remote modification was performed.

## Repository reuse terms — October 3, 2026

There was no repository license file. Added a proprietary [all-rights-reserved notice](../LICENSE), with limited permission for individual educational/application browsing and prior written permission required for reuse of protected catalog materials. It covers the accepted CSV, SQLite, JSON, editorial annotations and protected compilation work, as well as original repository code/content. Third-party rights, public facts, statutory exceptions, previously valid permissions and platform rights are preserved.

These terms cannot make public facts exclusively owned or technically prevent copying a public repository. [U.S. Copyright Office database guidance](https://www.copyright.gov/register/tx-databases.html) distinguishes protected compilation authorship from underlying facts; [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains public viewing/forking rights. Actual access controls require a separately authorized hosting/access change. This update changes repository terms only.

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
