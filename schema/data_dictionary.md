# Summer Research Opportunity data dictionary

The accepted CSV under `database/imports/` is the version-controlled source used to reproduce the canonical published SQLite database. Files under `data/summer-research/` are generated views and must not be edited directly.

The catalog JSON also exposes derived `reported_facts`: field-indexed excerpts of accepted bundle descriptions with the original reported cycle, source URL, text-year mentions and report index. These are presentation evidence, not parsed canonical facts. Do not use them for numeric sorting or eligibility exclusions. Text-year mentions do not establish a program cycle. Missing canonical values remain NULL even when a reported statement is displayed.

Within `Bundle_Details_JSON`, accepted `catalogDisplayNotes` can supply cycle-specific display wording and source context for reviewed qualifications (for example, minimum support before housing deductions). They must match the displayed cycle and must not overwrite preserved source reports. Prior values remain in `catalogFactHistory`.

## Entity boundaries

- **Institution**: one physical host/location used for map aggregation. A national network or multi-site federal program may use a clearly labeled umbrella institution until site-level placements are modeled.
- **Opportunity**: the stable identity of a named program, independent of year.
- **Program cycle**: annual dates, status, compensation, benefits, and verification metadata.
- **Undated snapshot**: one `program_cycles` row with a NULL `cycle_year` per stable program when its identity is verified but a cycle year is not established. Exact annual dates and claims of current application availability require a known year. An undated snapshot can coexist with dated cycles without creating another public program listing.
- **Eligibility rule**: cycle-specific hard eligibility. Nullable Boolean fields mean “not established,” not “no.” The original rule text is always retained.
- **Category**: broad, controlled subject grouping used for filters.
- **Tag**: narrower research topic, method, mode, audience, or program characteristic.
- **Research mode**: controlled, many-to-many methodology values such as wet lab, computational, field, or clinical.
- **Source verification**: which source supported which fields, when it was checked, and whether conflicts existed.
- **Opportunity review**: catalog acceptance status, specific pending checks and original bundle reports. `bundle_accepted` records the user’s acceptance of prior Chat Work review; it renders neutral program details rather than a provisional warning. It does not create a verification date or independently establish eligibility. `needs_review` and `supplement_needs_review` remain available for specific evidence gaps. Reported housing availability is distinct from who pays for it; room and board may be covered, paid through a fee, conditional, or unknown. Bundle extraction/review labels do not imply independent verification. These records add no source-verification event.

- **Discovery source**: a directory, database, network, search engine, professional society, host universe, or secondary lead source that produced a candidate. It may or may not be authoritative for any program fact.
- **Opportunity discovery**: many-to-many provenance linking a candidate or canonical opportunity to the source and URL where it was discovered.
- **Crawl target**: a coverage-tracked institution, agency, research center, society, lab, field station, or host domain searched by the national discovery protocol.

## Unknown-value policy

Missing or ambiguous information is stored as `NULL` in typed fields and preserved verbatim in the matching `*_text`, `*_details`, notes, or raw-import record. Status fields use `unknown` only when a non-null categorical value is operationally necessary. Importers never convert an unknown value to `no` or infer a benefit.

## Stable identifiers

`opportunities.public_id` preserves the starter `Program_ID`. Database integer IDs are internal foreign keys. Future importers should retain a public ID across annual cycles; a new year creates a `program_cycles` row, not a duplicate opportunity.

## Important field semantics

| Field | Meaning |
|---|---|
| `status_code` | Small website-facing status vocabulary derived only from explicit status text. |
| `status_text` | Full official/imported wording; authoritative when the code is insufficient. |
| `*_status` benefit fields | Controlled value such as `yes`, `no`, `partial`, `allowance`, `assistance`, `local`, `varies`, or `unknown`. |
| `parse_status` | Review status supplied with the accepted eligibility data. |
| `raw_eligibility_text` | Lossless combined seed wording used while structured eligibility fields await review. |
| `prior_research_status` | Controlled hard-rule state: `required`, `preferred`, `not_required`, or `unknown`. |
| `program_cycles.application_url` | Cycle-specific application destination; historical cycles retain their own URL. |
| `research_modes.mode_code` | Controlled preference/filter vocabulary; absent assignments mean unknown, not “no.” |
| `fields_supported` | JSON array of field names supported by that source. |
| `Source_Evidence_JSON` (CSV) | Explicit per-source field assignments, reviewer, check date and limitations; imported as partial source verifications rather than a claim that all eligibility is reviewed. |
| `Secondary_Fields` (CSV) | Additional controlled research categories, separated by semicolons; complements specific topic tags. |
| `Bundle_Provenance` (CSV) | Bundle revision and originating discovery ID retained in raw import records; not factual source evidence. |
| `evidence_hash` | Optional content snapshot hash supplied with accepted source data. |

| `discovery_sources.authority_scope` | Whether the source is discovery-only, can support network rules, can support government records, or is itself an official program source. |
| `opportunity_discovery.discovery_url` | The URL that revealed the candidate; this is preserved even if a later official verification source is different. |
| `crawl_targets.crawl_status` | Coverage state for institutional and organized-source crawling. Counts based on this field support completeness claims. |

## High-school audiences (schema 1.6.0)

`Catalog_Audience` in the accepted CSV maps to `opportunities.catalog_audience`: `undergraduate`, `high_school`, or `both`. It routes listings to the appropriate academic-level collection. The default preserves the legacy undergraduate collection; it does not establish a verified high-school exclusion. Rebuild the database to upgrade older schemas.

Accepted high-school reports are stored in `Bundle_Details_JSON[].highSchoolRecord` and exported as `high_school_details`. Preserve the original ID, descriptions, evidence labels, sources, checked date, eligibility text, age/grades, housing/cost distinctions, financial aid and all reported annual cycles. `catalogCitizenship` contains nullable, explicitly reviewed admission mappings; employment authorization and NSF funding rules alone do not establish exclusion. `catalogCycleStatus` records explicitly reported annual availability, never an inferred opening from a future deadline. `catalogTravelStatus` retains conditional allowances with their full text.

New identities have canonical annual cycles for supplied dated facts, or one undated snapshot. Shared identities keep existing cycles intact; their high-school reports provide cohort-specific presentation. The browser projects high-school facts into the selected view without changing the canonical undergraduate facts or transferring benefits between cohorts. Historical prices remain year-labelled in the detail panel. Paid housing is not included housing. Unknown city, stipend and eligibility fields remain unknown. Imported review dates do not create independent verification events.
