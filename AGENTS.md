# Cortical Analysis Lab repository handoff

## Current working state

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
- `database/imports/` — accepted 706-row CSV source
- `scripts/import_catalog.py` — deterministic CSV importer
- `scripts/validate_catalog.py` — structural integrity validation
- `scripts/export_catalog.py` — browser JSON exports
- `scripts/rebuild_database.py` — clean seed rebuild
- `scripts/test_catalog.py` — regression and round-trip tests

The schema separates institutions, stable programs (`opportunities`), annual cycles, structured eligibility, categories, tags, research modes, sources, verifications, and import provenance. Stable program identity and annual cycle data must remain separate.

Current seed scale:

- 706 programs and annual cycles
- 337 normalized institutions
- 13 broad categories
- 352 detailed research tags
- 11 controlled research modes
- 842 source-verification events

Opportunity discovery, evaluation, verification, and review happen outside this repository. Only accepted records enter the committed CSV. Missing facts remain `NULL`/`unknown`.

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
- GPA is an optional text field. Blank or invalid GPA does not filter results. A valid GPA excludes only programs with a verified higher minimum. Programs with unknown minimum GPA remain available.
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
