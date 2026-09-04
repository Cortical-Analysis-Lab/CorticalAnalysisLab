# National discovery protocol

This is the baseline crawling and discovery protocol for the Summer Undergraduate Research Opportunity Explorer. The objective is a traceable, refreshable, coverage-measurable national database of legitimate summer undergraduate research opportunities, not a narrow NSF REU list.

Do not begin a full national crawl unless the staging database, provenance tables, coverage tracking, deduplication checks, and rebuild/test path are working.

## Core principle

Use layered discovery:

1. Structured directories
2. Federal and organized network sources
3. Institutional host universe
4. Grant database backfill
5. Broad web gap search

Every candidate should ultimately be verified against the official host/program source wherever practical. A discovery source and a verification source are different relationships. For example, AAMC may discover a biomedical summer program, a university page may verify deadline and eligibility, and NIH RePORTER may document R25 funding.

## Pass 1: Structured Directories

High-priority discovery sources:

- NSF REU Site Directory, NSF ETAP, NSF undergraduate pages, NSF IRES where undergraduate summer research is relevant, and NSF Award Search for REU Sites or undergraduate research awards.
- PathwaysToScience summer research database.
- Council on Undergraduate Research student and discipline resources.
- AAMC Summer Undergraduate Research Programs and AAMC MD-PhD Summer Undergraduate Research Programs.
- ORISE and Zintellect undergraduate opportunities.
- USAJOBS student opportunities only when the position has meaningful research, scientific analysis, engineering R&D, laboratory, data-analysis, or research-training content.
- Discipline-specific professional society directories.

Deduplicate candidates before continuing to later passes.

## Pass 2: Federal And Organized Networks

Search dedicated sources and host pages for NIH, NCI cancer centers, DOE national laboratories, NASA centers, NIST, NOAA, Sea Grant, USDA/NIFA REEU, EPA, FDA, CDC, USGS, DoD, DHS, Smithsonian, Library of Congress, Federal Reserve, federal statistical or research agencies, Big Ten Academic Alliance SROP, Leadership Alliance, Amgen Scholars, HHMI, LSAMP, McNair/TRIO, UC-HBCU, EPSCoR, and similar networks.

When a program has a service commitment, flag that condition clearly.

## Pass 3: Institutional Host Universe

Do not search only R1 universities. Build target lists from authoritative host universes and track coverage for each target:

- Carnegie 2025 R1, R2, and Research Colleges and Universities.
- IPEDS, used as a completeness and backfill universe.
- LCME and AACOM medical schools.
- NCI-designated cancer centers.
- NCATS CTSA hubs.
- Independent research institutes, including AIRI members and other nonprofit research organizations.
- Federally Funded Research and Development Centers.
- Academic medical centers, research hospitals, and children's hospitals.
- Biological field stations, marine laboratories, museums, observatories, botanical gardens, zoos with research divisions, and conservation institutes.

Each target should carry status fields such as `not_started`, `queued`, `searched`, `candidates_found`, `no_opportunity_found`, `inaccessible`, or `error`.

## Pass 4: Grant Database Backfill

Use funding databases to discover hosts and program leads, then locate student-facing official pages before canonical inclusion.

Search NIH RePORTER for terms such as `summer undergraduate`, `summer research`, `undergraduate research program`, `R25`, `ENDURE`, `CURE`, `SURP`, `SURF`, `research education`, `pipeline`, and `undergraduate training`.

Search NSF Award Search for REU Sites, REU supplements, IRES, LSAMP, EPSCoR, Engineering Research Centers, Science and Technology Centers, MRSECs, AI Institutes, undergraduate research, and summer research.

Search USDA NIFA awards and USAspending carefully for undergraduate research and summer research phrases. Award records are discovery/funding evidence, not a replacement for host verification.

## Pass 5: Broad Web Gap Search

Use search engines and site search as discovery-only backfill across remaining official domains and likely research hosts. Standard vocabulary lives in `database/discovery/host_universe_protocol.json`.

Secondary lead sources, including Google/Bing results, institutional newsletters, PDFs, faculty pages, LinkedIn, Indeed, Handshake, Workday, Reddit, professional mailing lists, and student resource pages may reveal candidates. They must not verify stipend, eligibility, dates, housing, meals, travel, or deadlines unless the linked official source supports those facts.

## Inclusion Rules

Include legitimate summer undergraduate research experiences even when they are not NSF-funded, internally funded, federally funded, medical-school based, hospital based, institute based, field based, humanities/social-science focused, computational, engineering, community-college focused, restricted to certain groups, or home-institution-only.

Do not discard home-institution-only programs. Encode restricted reach with `external_applicants_status = 'no'` or `limited`.

Exclude generic summer jobs, administrative internships, clinical shadowing-only activities, and volunteer-only activities unless they satisfy the research-opportunity definition.

## Extraction Priorities

For every verified annual cycle, attempt to capture identity, geography, research field/tags/modes, eligibility, dates, financial support, application requirements, program URL, application URL when available, source URL, check date, confidence, conflicts, and notes.

Unknown values must remain unknown. Do not infer or invent missing values from context.

## Crawling Rules

- Prefer official pages.
- Be rate-limited and polite.
- Respect robots.txt and site policies where applicable.
- Do not bypass authentication, CAPTCHAs, paywalls, private systems, or anti-bot controls.
- Cache fetched content when practical.
- Track `last_checked` and avoid rechecking unchanged resources unnecessarily.
- Use structured feeds and APIs when legitimately available.
- Preserve page/source URL and retrieval date.
- Flag inaccessible pages for review instead of trying to defeat access restrictions.

## Completeness Metrics

Pipeline reports should include coverage metrics, not only record counts:

- NSF records discovered and verified.
- Carnegie R1/R2/RCU institutions searched.
- Medical schools, NCI centers, CTSA hubs, AIRI institutes, FFRDCs, field stations, marine labs, federal agencies, and professional-society directories searched.
- Candidates awaiting verification.
- Duplicates and rejected non-research opportunities.
- Sites inaccessible to automation.
- Institutions searched with no opportunity found.

Coverage statements must be grounded in target counts, such as `318 of 326 R1/R2 institutions searched`.
