# Summer research data sources

## Source priority

Use sources in this order when practical:

1. Official program or host-institution page
2. Official application portal
3. Official network or federal program directory
4. Reputable discovery aggregator, used to find—not silently verify—a program

Use the [NSF Directory of REU Sites](https://www.nsf.gov/crssprgm/reu/reu_search.cfm) and [NSF ETAP](https://etap.nsf.gov/) as recurring discovery channels. An NSF directory or ETAP entry can establish discovery provenance and provide identity signals such as an award or site identifier. It does not replace the host program's official page for cycle-specific dates, benefits, local eligibility conditions, or application instructions.

## Verification authority gate

Canonical field verification may use only:

- the official program or host-institution website;
- an official government source for the rule or program it administers;
- an official network source for network-wide requirements only; or
- an opportunity-specific application portal explicitly linked or delegated by an official program source.

Social media posts, search snippets, discussion forums, commercial listings, discovery aggregators, reposted announcements, and third-party summaries are never verification evidence. They may lead discovery to a candidate, but every proposed catalog fact must be confirmed on an allowed primary source. A social post from an official account is still discovery-only because posts can be incomplete, edited, or detached from the maintained program record.

Cross-domain portals and network/government pages require an explicit authority review and narrowly scoped `fields_supported`; they must not inherit authority merely because an importer encountered the URL. An application portal can support application instructions it displays, but cannot automatically verify stipend, benefits, dates, or eligibility copied from elsewhere.

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

At national scale, compare discoveries with the canonical identity index before detailed retrieval. Skip fresh, unchanged known records; route ambiguous identity matches for review; and deeply extract only new programs, explicit new cycles, stale evidence, or changed official pages.
