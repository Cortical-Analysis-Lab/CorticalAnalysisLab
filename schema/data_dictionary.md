# Summer Research Opportunity data dictionary

The accepted CSV under `database/imports/` is the version-controlled source used to reproduce the canonical published SQLite database. Files under `data/summer-research/` are generated views and must not be edited directly.

## Entity boundaries

- **Institution**: one physical host/location used for map aggregation. A national network or multi-site federal program may use a clearly labeled umbrella institution until site-level placements are modeled.
- **Opportunity**: the stable identity of a named program, independent of year.
- **Program cycle**: annual dates, status, compensation, benefits, and verification metadata.
- **Eligibility rule**: cycle-specific hard eligibility. Nullable Boolean fields mean “not established,” not “no.” The original rule text is always retained.
- **Category**: broad, controlled subject grouping used for filters.
- **Tag**: narrower research topic, method, mode, audience, or program characteristic.
- **Research mode**: controlled, many-to-many methodology values such as wet lab, computational, field, or clinical.
- **Source verification**: which source supported which fields, when it was checked, and whether conflicts existed.

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
| `evidence_hash` | Optional content snapshot hash supplied with accepted source data. |

| `discovery_sources.authority_scope` | Whether the source is discovery-only, can support network rules, can support government records, or is itself an official program source. |
| `opportunity_discovery.discovery_url` | The URL that revealed the candidate; this is preserved even if a later official verification source is different. |
| `crawl_targets.crawl_status` | Coverage state for institutional and organized-source crawling. Counts based on this field support completeness claims. |
