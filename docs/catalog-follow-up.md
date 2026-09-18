# Catalog follow-up tasks

Requested September 18, 2026. These tasks are pending; the provisional bundle import did not complete a full overlap or factual review. The current 982 listings are not a verified count of distinct programs.

## 1. Complete the overlap audit

- Compare every imported bundle candidate with the preexisting catalog and with other bundle candidates. Prior matching consolidated some aliases, but must not be treated as exhaustive.
- Normalize cycle dates in names before comparing identities. Check official names, hosts, redirects, URL variants, network aliases and recurring applications. Different cycles of the same program must not create separate listings.
- Consolidate confirmed duplicates under the existing stable `Program_ID` when available. Preserve all useful field tags, housing, meal and room-and-board details, source references, cycle history and bundle provenance. Keep conflicting claims visible for review rather than silently choosing one.
- Do not merge distinct programs or exclude a whole program merely because several tracks share a URL, host, application portal or funding award. Preserve legitimate campus and collaborative-host distinctions.

## 2. Review the remaining opportunities and imported information

- Review all `Catalog_Review_Status=needs_review` records and all `supplement_needs_review` additions, including earlier catalog records that have not completed factual review.
- Confirm undergraduate summer research scope and whether Sacred Heart University students can apply. Remove confirmed host-only or partner/institution restrictions that exclude SHU; retain unknown eligibility with explicit review notes.
- Check official links, participant locations, research fields/tags, eligibility requirements, compensation, housing availability and cost, meals, and room-and-board terms. Distinguish provided housing from free housing, allowances from stipends, and conditional assistance from guaranteed support.
- Keep dates optional. Retain undated or historical programs as potential options without inventing current availability or rolling dates forward.
- Record decisions and evidence outside the repository, then apply accepted corrections to the CSV. Keep unresolved records visibly provisional; source retrieval alone is not verification.

## 3. Remove cycle dates from program names during that cleanup

- Remove year prefixes/suffixes, date ranges and application-cycle labels from canonical `Program_Name` values and displayed program titles.
- Preserve the original title in import/bundle provenance and preserve supported dates in the appropriate cycle fields or historical metadata.
- Do not strip numbers that belong to a real program name, such as Biosphere 2, or treat a title's year as sufficient evidence for a current application cycle.
- Use the cleaned names for duplicate matching, then review the final catalog for remaining dated titles and duplicate listings. Add regression coverage for recurring-cycle aliases and meaningful numbers in program names.

## Completion checks

Rebuild SQLite and browser JSON from the corrected accepted CSV; run `scripts/validate_catalog.py`, `scripts/test_catalog.py`, `node --check assets/fellowship-questionnaire.js`, and `git diff --check`. Inspect the local preview for one listing per program, clean titles, retained benefit details and accurate review labels. Report confirmed merges, removals and unresolved cases separately. Keep publication suspended and do not push without an explicit request.
