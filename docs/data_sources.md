# Summer research data sources

## Source priority

Use sources in this order when practical:

1. Official program or host-institution page
2. Official application portal
3. Official network or federal program directory
4. Reputable discovery aggregator, used to find—not silently verify—a program

The current starter catalog includes official program/application URLs and source verification records. It is seed data, not a claim that every field has received structured review.

## Verification record requirements

Each reviewed record should retain:

- source URL and type
- publisher or host when known
- whether the source is authoritative
- date checked
- verification status
- the fields supported by that source
- conflict notes when sources disagree
- checker identity or agent/run identifier
- retrieved timestamp and evidence hash when snapshot infrastructure is added

Use `last_verified` for the cycle's review date; do not change it merely because an unrelated field was edited.

## Web collection behavior

Collection should follow discovery → extraction → verification → classification → deduplication → reviewed update. Be rate-limited, reuse cached responses, and respect access restrictions and site policies. Do not bypass authentication, CAPTCHAs, paywalls, or anti-bot controls. Do not repeatedly request pages when an adequate recent snapshot already exists.

No national-scale collection should begin until the schema, review workflow, taxonomy, and institution-coordinate process have been approved.
