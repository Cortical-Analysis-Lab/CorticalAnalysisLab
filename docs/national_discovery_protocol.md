# National discovery protocol

This is the baseline crawling and discovery protocol for the Summer Undergraduate Research Opportunity Explorer. The objective is a traceable, refreshable, coverage-measurable national database of legitimate summer undergraduate research opportunities, not a narrow NSF REU list.

Do not begin a full national crawl unless the staging database, provenance tables, coverage tracking, deduplication checks, and rebuild/test path are working.

## Scale Target

Design the discovery and review system for at least 5,000 stable program identities and 15,000 to 25,000 annual-cycle records over time. The working planning estimate is roughly 2,300 to 4,200 distinct programs across U.S. and international coverage after the full search plan is executed.

This target is a capacity and coverage goal, not a permission to relax verification. The public catalog should grow only through accepted records with official-source evidence, stable identity handling, and unknown facts preserved as unknown.

Expected coverage bands:

- U.S. NSF REUs and related NSF undergraduate research programs: roughly 400 to 600 distinct programs.
- Other U.S. university SURP, SURF, SURE, SROP, and similar named programs: roughly 900 to 1,500.
- Medical schools, hospitals, cancer centers, and research institutes: roughly 250 to 450.
- Federal labs, agencies, and national programs: roughly 100 to 200.
- Social science, humanities, field stations, museums, observatories, and specialized programs: roughly 200 to 400.
- International programs genuinely open to U.S. students: roughly 300 to 700.

## Core principle

Use layered discovery:

1. Structured directories
2. Federal and organized network sources
3. Institutional host universe
4. Official host/domain gap crawl
5. Broad web gap search

Every candidate should ultimately be verified against the official host/program source wherever practical. A discovery source and a verification source are different relationships. For example, AAMC may discover a biomedical summer program, while the university program page verifies deadline, eligibility, and benefits.

Funding, grant, and award records are not opportunity records. They may be retained locally as discovery hints only when needed, but they must not be promoted into the public catalog, used as canonical program/application URLs, or used as field verification evidence.

## Program Identity Rule

Count one program as one separately named research program or application at a host institution. A university-wide SURP with many participating labs is one program, not one record per lab or faculty project. A university with separate named neuroscience, chemistry, physics, and cancer summer research programs has separate program identities. Summer 2026 and Summer 2027 are annual cycles of the same stable program, not separate programs.

Network programs require special handling. A network-level page such as Amgen Scholars, Big Ten SROP, Mitacs Globalink, or DAAD RISE may be a discovery source or may verify network-wide rules, but host-specific applications should become separate records only when the host page or application process identifies a distinct student-facing program. Do not count directories, partner lists, or host networks as public opportunities unless the network itself is the application students apply to.

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

PathwaysToScience may be parsed automatically as a discovery-only aggregator. Use its Summer Research / Undergraduate result pages and `programhub.aspx` detail pages to find official outbound program URLs, then verify identity, eligibility, dates, benefits, and application facts on the official host page. Do not use Pathways pages themselves as canonical program URLs or field-verification evidence.

## Pass 2: Federal And Organized Networks

Search dedicated sources and host pages for NIH, NCI cancer centers, DOE national laboratories, NASA centers, NIST, NOAA, Sea Grant, USDA/NIFA REEU, EPA, FDA, CDC, USGS, DoD, DHS, Smithsonian, Library of Congress, Federal Reserve, federal statistical or research agencies, Big Ten Academic Alliance SROP, Leadership Alliance, Amgen Scholars, HHMI, LSAMP, McNair/TRIO, UC-HBCU, EPSCoR, and similar networks.

When a program has a service commitment, flag that condition clearly.

## Pass 2B: International Programs Open To U.S. Students

Search international programs only when they are genuinely open to U.S. undergraduates or broadly international undergraduates. Examples include Mitacs Globalink, DAAD RISE Germany, ETH Student Summer Research Fellowship, EPFL summer research programs, OIST research internships, Max Planck institute summer programs, EMBL and similar institute programs, and host-specific university summer research programs.

International projects or lab placements should not be over-counted as separate programs when students apply through one common program. Count the umbrella program once unless the host offers a separately named application.

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

## Pass 4: Official Host/Domain Gap Crawl

Use each target host's official domain, sitemap, undergraduate research office,
training office, department pages, and program-directory pages to find
student-facing summer undergraduate research programs that did not appear in
structured directories or network sources.

Funding databases such as NSF Award Search, NIH RePORTER, USDA award systems,
TAGGS, and USAspending are excluded from the default acquisition loop. If they
are used manually as a last-resort lead source, the discovered funding identity
must be resolved to an official student-facing program page before the candidate
can be promoted.

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
