# Catalog follow-up tasks

Requested September 18, 2026. On September 21 the user narrowed the active work to program names and duplicate identities, deferring full factual verification of each opportunity. The name/alias pass screened all 982 identities, consolidated 15 duplicate listings, and cleaned 36 titles. The resulting 967 listings are not a verified count of distinct programs.

The accepted CSV preserves removed rows in `Bundle_Details_JSON` → `catalogIdentityHistory`, including their IDs, names, original fields and cycle snapshots. Original bundle reports and benefit claims remain available; identity consolidation does not upgrade factual review status. Title cleanup preserves original names in `Notes` and existing bundle source records. The database and browser exports have been regenerated.

Consolidated identities include UConn Physiology and Neurobiology, BU Integrated Nanomanufacturing, Greehey/McEwen, Boulder Solar Alliance, Minnesota Lando, Texas A&M Oceanography, Missouri Botanical Garden, Illinois MRSEC, Rutgers Pharmacy SURF, Blandy ecology, SETI/NASA Ames astrobiology, Brandeis MRSEC, South Dakota BACE, Maine sensors, and the duplicated Michigan-specific CELL-MET entry. Existing stable IDs were retained for original-catalog/bundle overlaps. No non-program removal batch was applied in that initial pass.

The subsequent full-catalog overlap screen covered all 967 remaining identities, including 141 shared-host/domain groups (724 records), 240 name/URL candidate pairs, and 1,137 attempted URL checks (969 HTTP 200 responses). Candidate counts are not duplicate counts. Seven additional duplicates were consolidated: Buffalo iSEED/CLIMB UP, Houston engineering REU/BRAIN, Rutgers SROP/RISE, Princeton SURF-C/SURP-DC, Keck Geology, Cincinnati's general biomedical SURF listing, and BU SURF/Gene Expression. The explicit test-name removal excluded `BND-EFE0382FA6FD3579` (`[TEST] SERGUS`). There are now 959 identities and 960 cycle/snapshot records. This is still not a verified distinct-program count.

All-record screening is complete; identity resolution is not exhaustive where evidence is missing. Remaining cases include Cedar Creek umbrella/placement, Wisconsin integrated REU/tracks, ORNL and Harvard directory scope, PARADIM umbrella/campuses, CEMB multi-site representation, Mote's umbrella/two programs, UCSF Amgen/SRTP, Michigan NURO/SIREN, Rutgers Math/DIMACS and UVA Leadership Alliance/SRIP. Wrong-host links and labels also need correction. Preserve possible distinct tracks until evidence resolves them. Rochester MSTP/Graduate Education, Pittsburgh CNUP/SURP, NYU neuroscience/Vilcek and the Louisville REUs were retained as separate named programs.

External audit files are at `/tmp/cortical-full-overlap-audit/`: `REPORT.md`, `all-records.csv`, `host-groups.txt`, `name-pairs.json`, `fetched.json`, `decisions.json`, and `excluded-records.json`. They are temporary and not version-controlled. The accepted CSV retains merged originals; Git history retains the removed test row. The exclusion CLI requires a separate archive before writing the corrected CSV.
For subsequent imports, `scripts/review_catalog_names.py --output /path/outside/repository/candidates.json` screens current and bundle source names and URLs. Candidates are not approved merges. Apply explicit accepted decisions with `--decisions /path/outside/repository/decisions.json --output /path/to/accepted.csv`; this preserves incumbent facts and dated cycles. External review files from this session are at `/tmp/cortical-name-review-2026-09-21/` and are not version-controlled; the accepted CSV contains the reproducible consolidation provenance. Publication remains suspended.

## 1. Resolve remaining identity ambiguities and repeat overlap screening for imports

- Compare every imported bundle candidate with the preexisting catalog and with other bundle candidates. Prior matching consolidated some aliases, but must not be treated as exhaustive.
- Normalize cycle dates in names before comparing identities. Check official names, hosts, redirects, URL variants, network aliases and recurring applications. Different cycles of the same program must not create separate listings.
- Consolidate confirmed duplicates under the existing stable `Program_ID` when available. Preserve all useful field tags, housing, meal and room-and-board details, source references, cycle history and bundle provenance. Keep conflicting claims visible for review rather than silently choosing one.
- Do not merge distinct programs or exclude a whole program merely because several tracks share a URL, host, application portal or funding award. Preserve legitimate campus and collaborative-host distinctions.

## 2. Review the remaining opportunities and imported information (deferred)

- Review all `Catalog_Review_Status=needs_review` records and all `supplement_needs_review` additions, including earlier catalog records that have not completed factual review.
- Confirm undergraduate summer research scope and whether Sacred Heart University students can apply. Remove confirmed host-only or partner/institution restrictions that exclude SHU; retain unknown eligibility with explicit review notes.
- Check official links, participant locations, research fields/tags, eligibility requirements, compensation, housing availability and cost, meals, and room-and-board terms. Distinguish provided housing from free housing, allowances from stipends, and conditional assistance from guaranteed support.
- Keep dates optional. Retain undated or historical programs as potential options without inventing current availability or rolling dates forward.
- Record decisions and evidence outside the repository, then apply accepted corrections to the CSV. Keep unresolved records visibly provisional; source retrieval alone is not verification.

## 3. Keep cycle dates out of program names

- Remove year prefixes/suffixes, date ranges and application-cycle labels from canonical `Program_Name` values and displayed program titles.
- Preserve the original title in import/bundle provenance and preserve supported dates in the appropriate cycle fields or historical metadata.
- Do not strip numbers that belong to a real program name, such as Biosphere 2, or treat a title's year as sufficient evidence for a current application cycle.
- Use the cleaned names for duplicate matching, then review the final catalog for remaining dated titles and duplicate listings. Add regression coverage for recurring-cycle aliases and meaningful numbers in program names.

## Completion checks

Rebuild SQLite and browser JSON from the corrected accepted CSV; run `scripts/validate_catalog.py`, `scripts/test_catalog.py`, `node --check assets/fellowship-questionnaire.js`, and `git diff --check`. Inspect the local preview for one listing per program, clean titles, retained benefit details and accurate review labels. Report confirmed merges, removals and unresolved cases separately. Keep publication suspended and do not push without an explicit request.
