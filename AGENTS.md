# Cortical Analysis Lab repository handoff

## Current working state

- Fellowship publication is suspended as of September 6, 2026 pending catalog-quality remediation. Production publishes only the lab site from `main`; the fellowship UI and data remain in this development branch.
- Database-branch pushes run validation but do not publish. Do not restore publication without an explicit user request. See `docs/website-deployment.md`.
- Work on `Summer-REU-Database`, not `main`.
- The branch contains the Summer Undergraduate Research Opportunity Explorer database foundation and questionnaire UI.
- Keep unrelated lab website pages and styles intact.
- The repository is a static HTML/CSS/JavaScript GitHub Pages site. There is no frontend framework or application server.
- The accepted CSV under `database/imports/` is the version-controlled source used to reproduce `database/research_opportunities.sqlite`, the canonical published database. Browser code reads generated JSON from `data/summer-research/`; it must never query SQLite directly.
- Do not push, merge, or modify remote branches unless the user explicitly requests it.

## Product and privacy boundaries

- Eligibility questions answer “Can I apply?” Preference filters answer “Which programs do I want?” Keep these concepts separate in code and UI.
- All questionnaire evaluation is client-side. Do not save or transmit GPA, citizenship/residency, enrollment answers, or other student data.
- Never commit profiles, transcripts, essays, CVs, recommendation data, or application answers.
- Preserve missing facts as `NULL`/`unknown` in canonical data. Display them as `N/A` in the UI.
- Never infer a stipend, benefit, deadline, coordinate, or eligibility rule from absent text.
- Prefer official program and institution sources for verification.

## Implemented database foundation

Key files:

- `schema/schema.sql` — normalized SQLite schema
- `schema/data_dictionary.md` — field semantics and unknown-value policy
- `database/research_opportunities.sqlite` — canonical public database
- `database/imports/` — accepted CSV source
- `scripts/import_catalog.py` — deterministic CSV importer
- `scripts/validate_catalog.py` — structural integrity validation
- `scripts/export_catalog.py` — browser JSON exports
- `scripts/rebuild_database.py` — clean seed rebuild
- `scripts/test_catalog.py` — regression and round-trip tests

The schema separates institutions, stable programs (`opportunities`), annual cycles, structured eligibility, categories, tags, research modes, sources, verifications, and import provenance. Stable program identity and annual cycle data must remain separate.

Current catalog scale after the September 21, 2026 name/identity cleanup (remaining entries are not all fact-verified):

- 953 program identities; 954 cycle/snapshot records, including 638 undated snapshots
- 661 reported host/location records; provisional locations still need review
- 13 broad categories
- 1,843 detailed research tags, including provisional bundle topic assignments
- 11 controlled research modes
- 397 source-verification events; provisional imports do not create verification events

Planning scale target:

- 2,300 to 4,200 verified distinct programs as a working discovery estimate
- Schema and workflow capacity for at least 5,000 stable program identities
- 15,000 to 25,000 annual-cycle records over time

A distinct program is a separately named research program or application at a host institution. Do not count student slots, individual faculty projects, annual cycles, funding records, directories, news/support pages, or program-list hubs as separate public opportunity records.

Opportunity discovery, evaluation, verification, and review happen outside this repository. Only accepted records enter the committed CSV. Missing facts remain `NULL`/`unknown`. Funding, grant, and award records are local discovery leads only; do not use them as canonical program records, application URLs, or field-verification evidence.

The user's September 21 instruction accepts the prior Chat Work review of bundle entries and removes the generic provisional-review tag. `Catalog_Review_Status=bundle_accepted` now identifies 923 accepted bundle/supplement identities and renders a neutral **Program details** section. This acceptance does not create official-source verification events, dates, or inferred eligibility. Keep original bundle reports, benefit claims and acceptance history reproducible. Five records retain specific review notes: UCSF SRTP, Penn CEMB, two Wisconsin chemistry REUs, and Western Michigan Environmental Signal Transduction. Do not restore generic provisional warnings on accepted entries.

The unresolved-record review covered 29 records, merged UCSF SRTP/Amgen, removed four directory/umbrella records and excluded the WashU CEMB placement for institution restrictions. Penn CEMB remains separately represented with eligibility unknown. Corrected hosts include Blandy/UVA, Cedar Creek/UMN, CELL-MET/Michigan, and PARADIM/JHU. Keep the distinct Mote URE/NSF REU, Wisconsin, Michigan neuroscience, Rochester, Pittsburgh and UVA programs. See [docs/catalog-follow-up.md](docs/catalog-follow-up.md) for the remaining specific evidence gaps. Publication remains suspended.

A listing count is not an independently verified distinct-program count. Preserve original names and dates in provenance/cycle history, meaningful numbers such as Biosphere 2, and missing facts as unknown. Exclude confirmed host-only, partner-only or institution-type restrictions that rule out SHU students; retain unknown external eligibility. Never exclude a general program because a different track shares its URL.

## Required opportunity verification

Apply these checks to existing records and future additions before accepting corrections or describing opportunities as verified. Structural validation and round-trip tests do not establish factual accuracy.

- **Scope:** Confirm a distinct undergraduate summer research opportunity. Directories, search results, mentor/advice pages, historical recaps, PI conferences, and academic-year-only programs must not become independent summer opportunities.
- **Identity and duplicates:** Check redirects, URL variants, repeated program/host names, and NSF grant renewals. Preserve stable program IDs and provenance when consolidating. Shared names or portals alone do not prove duplication; retain legitimate collaborative hosts and campuses.
- **Annual cycles:** Verify cycle years, application windows, deadlines, and availability from official evidence. Do not use grant funding/end years as application-cycle years or roll historical dates forward. Verified identities may remain included with a blank CSV `Cycle_Year` (NULL in SQLite). Retain historical and paused programs as potential options without claiming current availability. Keep the same `Program_ID` across cycles: one public program listing, with dated cycles and at most one undated snapshot. Never invent a year to satisfy the importer.
- **Eligibility:** Verify external applicants, citizenship/residency, class standing, graduation timing, enrollment, institution type, minimum GPA, and other hard requirements. Separate preferences from exclusions and NSF-funded eligibility from host-wide admission rules. Unsupported booleans remain NULL; incomplete parsing is `needs_review`, not `reviewed`.
- **Duration and format:** Verify full program duration rather than an orientation/training segment, and confirm in-person, virtual, or hybrid delivery. Investigate outliers without automatically changing valid values.
- **Institutions and locations:** Verify institution names and actual participant locations rather than assuming the grant recipient's mailing address is the research site. Preserve supported multi-site/international locations and distinguish real campuses from naming artifacts. Do not infer coordinates or missing locations.
- **Benefits and links:** Verify stipend amounts/units, housing, meals, travel, and credit for the relevant cycle. Program links should lead to student-facing information; application URLs must not be grant records or directories. Keep unsupported benefits unknown.
- **Text and topics:** Check encoding corruption, malformed names, administrative grant codes presented as research topics, and dates trapped in free text. Do not convert historical or approximate wording into unsupported current dates.
- **Evidence and presentation:** Record official source URLs, date checked, supported fields, reviewer, limitations, and the retain/consolidate/exclude/needs-evidence decision outside the repository. Source retrieval alone is not full verification. UI verification wording and eligibility exclusions must match the evidence.

Prioritize confirmed non-program entries and duplicates, then stable identities/cycle years, decision-critical fields, and recurrence checks. Only accepted correction batches enter the CSV; regenerate SQLite/JSON and run the required checks. Do not bulk-delete NSF-derived records or fill gaps by assumption. Review the corrected result locally and keep publication suspended until the user explicitly requests restoration.

## Implemented Fellowship Database UI

Primary files:

- `fellowship-database.html`
- `assets/fellowship-database.css`
- `assets/fellowship-results.css`
- `assets/fellowship-questionnaire.js`

Current behavior:

- The main page title is **Find Your Fellowship**.
- The top hero uses the wide 4173-inspired layout in Sacred Heart red. Only the top hero received that treatment; the rest retains the existing explorer/questionnaire styling.
- Step 1 uses accessible circular radio controls for hard eligibility questions.
- The preliminary form groups academic standing and enrollment, then residency and institution. GPA is not collected or used to filter results; program minimum GPA remains visible on opportunity cards.
- Step 2 is titled **Available Opportunities**.
- A subtle bold sentence reports eligible opportunities out of total catalog opportunities; do not restore prominent eligible/ineligible score cards.
- Catalog summary cards beside the Step 2 title show program, institution, and topic counts. They are enlarged, close to the title, and center-aligned.
- Opportunity cards use the original explorer presentation, not eligibility-result badges or reasons. Cards show status, program, institution, deadline, format, duration, housing, minimum GPA, category/tags, official link, and verification date.
- Unknown card values display as `N/A`.
- The card matrix is compact, full-width, and responsive. Do not reintroduce the global 900px section cap.
- The prominent keyword search sits beside **Matching opportunities**, not in the filter sidebar.
- Current preference filters are research area, state, housing, travel, and open/upcoming. Stipend and eligibility-result filters were intentionally removed.
- Keyword input and every preference filter update displayed cards immediately.
- Research-area matching uses primary categories plus explicit topic-tag terms, so multidisciplinary physics programs remain visible when Physics & Astronomy is selected.
- Known eligibility conflicts are excluded automatically; incomplete official requirements remain available rather than being guessed.
- **Go Back** returns from results to questionnaire answers.
- Every main site page includes a **Fellowship Database** navigation link.

## Visual and interaction preferences

- Reuse the existing site's Inter font, Sacred Heart red, navigation, and deployment conventions.
- Keep the fellowship hero bold and exciting, but keep controls and data displays readable and restrained.
- Prefer compact cards in a responsive matrix that uses wide screens fully.
- Avoid emotionally heavy eligibility scoring. Use neutral availability language.
- Center questionnaire section headings within their containing panel.
- Make controls accessible: real labels, native radio inputs, keyboard focus, responsive stacking, and clear selected states.
- Keep changes narrowly scoped and commit them in logical units on `Summer-REU-Database`.
- Use cache-busting query versions when changing fellowship CSS/JS referenced by the HTML.

## Validation commands

Run after database changes:

```bash
python3 scripts/rebuild_database.py
python3 scripts/validate_catalog.py
python3 scripts/test_catalog.py
```

Run after questionnaire/UI changes:

```bash
node --check assets/fellowship-questionnaire.js
git diff --check
python3 scripts/test_catalog.py
```

For a local static preview:

```bash
python3 -m http.server 4174 --bind 0.0.0.0
```

The prior port 4173 prototype is only a visual reference and may not exist in a new session. The repository implementation on port 4174 is authoritative.

## State opportunity map

The explorer uses an institution-count U.S. state map instead of institution-level location markers. Do not collect coordinates or add a map provider for this feature.

- Show the contiguous lower 48 states plus D.C. in a tightly cropped, self-contained geographic SVG map, not a tile grid. Do not show Alaska, Hawaii, territories, Canada, Mexico, or the rest of the Americas.
- States with matching institutions are white with bold Sacred Heart red institution counts.
- Provide SVG leader-line callouts for geographically small states whose in-map counts are difficult to read; show the state abbreviation and institution count in red when opportunities match and in black when none match. Opportunity callouts must activate the same shared state filter. Do not use separate cards or button blocks for these labels.
- States without matching institutions remain Sacred Heart red.
- Use thick black geographic state/coastline borders; do not place the map in a framed or horizontally scrolling box.
- Selecting a state filters the opportunity cards through the same shared result state as the other preference controls.
- Count each institution once per state, even when it offers multiple matching programs.
- Put non-specific catalog locations such as `Multiple` and `International` in an **Other** list beside the map; selecting one filters the cards to that exact catalog value.
- When a catalog record explicitly identifies multiple city/state pairs, render one card per verified location and count the institution in each applicable state. Keep unspecified `Multiple` records in **Other** until their host sites are verified.
- Keep the state map, Other list, eligibility results, preference filters, keyword search, and opportunity cards synchronized.
- Provide keyboard-accessible buttons and responsive/mobile presentation.
- On screens 720px wide or narrower, hide the map and Other panel and show a location dropdown in the preference filters instead.
- Preserve unknown location values rather than assigning them to a state.

Do not build the future application-profile/template system yet.
