# Summer Research Opportunity data dictionary

SQLite is the canonical store. Files under `data/summer-research/` are generated views and must not be edited as the source of truth.

## Entity boundaries

- **Institution**: one physical host/location used for map aggregation. A national network or multi-site federal program may use a clearly labeled umbrella institution until site-level placements are modeled.
- **Opportunity**: the stable identity of a named program, independent of year.
- **Program cycle**: annual dates, status, compensation, benefits, and verification metadata.
- **Eligibility rule**: cycle-specific hard eligibility. Nullable Boolean fields mean “not established,” not “no.” The original rule text is always retained.
- **Category**: broad, controlled subject grouping used for filters.
- **Tag**: narrower research topic, method, mode, audience, or program characteristic.
- **Research mode**: controlled, many-to-many methodology values such as wet lab, computational, field, or clinical. Modes are assigned only when the seed or a reviewed source states them explicitly.
- **Source verification**: which source supported which fields, when it was checked, and whether conflicts existed.

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
| `parse_status` | Whether eligibility text has received explicit structured review. Seed rows remain `needs_review` unless a rule can be copied without interpretation. |
| `raw_eligibility_text` | Lossless combined seed wording used while structured eligibility fields await review. |
| `prior_research_status` | Controlled hard-rule state: `required`, `preferred`, `not_required`, or `unknown`. |
| `program_cycles.application_url` | Cycle-specific application destination; historical cycles retain their own URL. |
| `research_modes.mode_code` | Controlled preference/filter vocabulary; absent assignments mean unknown, not “no.” |
| `fields_supported` | JSON array of field names supported by that source. |
| `evidence_hash` | Reserved for a future content snapshot hash from the verification pipeline. |

## Reviewed eligibility staging

The reviewed import seed may include explicit `Eligibility_*` columns corresponding to structured `eligibility_rules` fields. Blank staging booleans remain `NULL`; the importer never derives them from missing text. `Eligibility_Source_URL`, `Eligibility_Checked_On`, and `Eligibility_Checked_By` create the verification audit record that supports a `reviewed` parse status.

## Future agent pipeline compatibility

Discovery agents should write candidate imports or staging files, not modify public JSON directly. Verification agents can add source records, hashes, supported-field lists, and conflict notes. A deterministic import/update step should promote reviewed changes into SQLite, followed by validation and export.
