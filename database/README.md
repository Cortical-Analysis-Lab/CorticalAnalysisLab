# Canonical database

## Local catalog manager

For ongoing discovery and review, launch the local GUI:

- macOS: double-click `run_catalog_manager.command`
- Windows: double-click `run_catalog_manager.bat`
- Linux or a terminal: `python3 local_catalog_manager.py`

The manager opens at `http://127.0.0.1:8765/`. It can run bounded official-source discovery sessions, retain candidates between sessions, accept opportunity links you find, export a Desktop Codex investigation bundle, rebuild and validate the canonical catalog, and show repository changes. Its working state lives under the git-ignored `database/local/` directory.

Use **Generate agent investigation bundle**, then open this repository in Desktop Codex and direct it to `database/local/agent_queue/CODEX_TASK.md`. The local staging database is not canonical: only reviewed seed changes followed by the deterministic rebuild update `research_opportunities.sqlite` and public exports.

[Run the reviewed database update workflow](https://github.com/Cortical-Analysis-Lab/CorticalAnalysisLab/actions/workflows/update_summer_research_catalog.yml)

The workflow opens in GitHub Actions; choose **Run workflow** on the branch containing reviewed staging changes, select a discovery time budget, and choose whether to receive a completion issue. During the bounded session it repeatedly queries approved official discovery channels until the sources are exhausted or the time budget is reached, compares findings with canonical identities, uploads a candidate inventory/report, rebuilds reviewed database changes, runs validation and regression tests, and commits changed generated artifacts back to that branch. GitHub write access is required to run it.

The completion report distinguishes discoveries, existing matches, possible duplicates, new cycles, official-host verifications, and canonical inclusions. Discovery alone never inserts a program: candidates must pass official host-source verification and reviewed promotion first.

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
