# University web team handoff

Status: planning only. The lab's fellowship page and catalog are currently excluded from production deployment. This document is not a request to launch them.

## Link or redirect to the lab website

The proposed integration gives students a university entry point to the lab-maintained database.

1. Obtain the approved public destination URL from the lab contact after publication is authorized.
2. Create a university resource page using the accompanying draft copy, or configure a university address to redirect to that destination using the university's normal hosting tools.
3. Confirm that the link or redirect reaches the approved page on desktop and mobile, including from outside the university network if the university entry point is intended to be public.
4. Assign a university contact to maintain the entry point and a lab contact to notify them of URL changes or interruptions.

The university needs no database installation, JavaScript bundle, repository access, API key, or student-account integration for this arrangement. The university address provides an entry point; students leave the university domain to use the lab page.

The lab owns catalog updates and the hosted interface. The university owns its resource-page wording and link or redirect. Updating catalog records does not require the university to copy a new dataset.

Do not append questionnaire answers, student identifiers, or other student data to destination URLs. The existing lab questionnaire evaluates answers in the browser; it does not save or transmit those answers.

## If the university needs students to stay on its domain

That requires a separate university-hosted presentation of the data. The university would build and maintain its own interface, and the lab would supply an agreed data release. This is an optional future integration, not configured by this folder.

Available development artifacts in the lab repository are:

| Artifact | Repository path | Intended use |
| --- | --- | --- |
| Browser catalog JSON | `data/summer-research/catalog.json` | Input to a university-built interface |
| Canonical SQLite database | `database/research_opportunities.sqlite` | Institutional import or analysis |
| Accepted CSV source | `database/imports/summer_undergraduate_research_opportunities_starter.csv` | Reproducing the catalog or reviewing imported records |
| Data dictionary | `schema/data_dictionary.md` | Field meanings and unknown-value policy |
| Database schema | `schema/schema.sql` | Relational structure |

These are repository paths, not public download URLs. No data files are duplicated in this handoff folder, so it cannot become a stale second catalog.

Before implementing this option, agree on the release location, update frequency, attribution and reuse terms, contacts, and schema-change handling. A university-managed download of approved releases can supply its local data copy. Direct browser requests to a lab-hosted JSON URL would require checking the eventual host's cross-origin access configuration. No live API or automatic synchronization is promised.

University browser code should read JSON, not query SQLite. Preserve stable program identifiers, distinguish programs from annual cycles, retain missing values as unknown and display them as N/A. Preserve source limitations and cycle context; do not treat historical deadlines or reported benefits as current facts. High-school information for shared programs must remain distinct from undergraduate eligibility and funding.

Any questionnaire built by the university must keep eligibility evaluation client-side and must not save or transmit student answers. The data release contains program information, not student profiles or application materials.
