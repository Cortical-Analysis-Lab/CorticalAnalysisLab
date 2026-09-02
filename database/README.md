# Canonical database

[Run the reviewed database update workflow](https://github.com/Cortical-Analysis-Lab/CorticalAnalysisLab/actions/workflows/update_summer_research_catalog.yml)

The workflow opens in GitHub Actions; choose **Run workflow** on the branch containing reviewed staging changes. It rebuilds SQLite and generated website/review exports, runs validation and regression tests, and commits the regenerated artifacts back to that branch when they changed. GitHub write access is required to run it.

`research_opportunities.sqlite` is the canonical public opportunity catalog. Rebuild it from the committed starter import with:

```bash
python scripts/rebuild_database.py
```

Do not store student profiles, questionnaire answers, saved programs, essays, transcripts, or other personal data here. The database is public-repository content.

`imports/` contains human-reviewable source files. Import provenance and each original row are also retained inside SQLite.

The schema is documented in `schema/data_dictionary.md`. Reviewed update and agent rules are in `docs/database_update_process.md` and `docs/data_sources.md`.

The database stores stable program identities separately from annual cycles, plus institutions, structured eligibility, controlled categories/tags/modes, and field-level source verification.

## Discovery sources

- [NSF Directory of Research Experiences for Undergraduates Sites](https://www.nsf.gov/crssprgm/reu/reu_search.cfm) — use as a broad discovery and NSF-site identity source. Verify cycle dates, benefits, local eligibility rules, and application instructions against each host program's official page before inclusion.
- [NSF REU information for students](https://www.nsf.gov/funding/initiatives/reu/students) — explains directory coverage, baseline NSF participant eligibility, and the separate ETAP opportunity channel.

Discovery must compare directory results against canonical program identities before fetching detailed pages. An NSF listing or award identifier is strong matching evidence, but it does not replace host-level verification and must not cause distinct programs at one institution to be merged.
