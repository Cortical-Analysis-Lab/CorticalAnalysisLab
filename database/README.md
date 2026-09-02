# Canonical database

## Local catalog manager

For ongoing discovery and review, launch the local GUI:

- macOS: double-click `run_catalog_manager.command`
- Windows: double-click `run_catalog_manager.bat`
- Linux or a terminal: `python3 local_catalog_manager.py`

The manager opens at `http://127.0.0.1:8765/`. It can run bounded official-source discovery sessions, retain candidates between sessions, accept opportunity links you find, run automated candidate investigation and approval, rebuild and validate the canonical catalog, and show repository changes. Its working state lives under the git-ignored `database/local/` directory.

Discovery requires outbound HTTPS access to official sources. In Desktop Codex, start or restart the manager with network permission if discovery reports socket permission errors such as `WinError 10013`.

The GUI opens on a workflow dashboard. **Now** shows whether a GUI job is running, queue counts, current proposals, and repository changes. **Next Action** tells you what to do next and whether that step is automated inside the GUI. Ordered workflow stages, live elapsed time, discovered-candidate progress, and source-error counts persist in `database/local/pipeline_state.json` so refreshes and interrupted local sessions can resume context.

Use **Run full automated update** to triage staged candidates locally, reject obvious non-opportunity awards, write structured result files for clean official-source proposals, record strict agent approvals, promote approved records into reviewed imports, rebuild SQLite/JSON, run tests, and write a source audit. The local staging database is not canonical: only reviewed seed changes followed by the deterministic rebuild update `research_opportunities.sqlite` and public exports.

Use **Reinvestigate N/A updates** when existing opportunities may have opened a new cycle or published dates, deadlines, duration, or stipend details after an earlier run. Existing-program matches are not ignored as duplicates: approved official-source proposals may update fields that are currently blank or `N/A`, while populated reviewed fields are left unchanged unless a later explicit review decides otherwise.

For difficult leftovers, **Generate fallback task bundle** can still create a Desktop Codex packet, but it is no longer the primary workflow.

The source audit is written to:

- `database/local/source_audit/retrieved_sources.csv`
- `database/local/source_audit/retrieved_sources.md`

Incomplete optional fields absent from reviewed official sources are recorded as `N/A` in the reviewed import/export files. The automation also writes a follow-up review log to:

- `database/local/review/incomplete_data_review_log.csv`
- `database/local/review/incomplete_data_review_log.md`

The Desktop Codex handoff contract writes:

- `database/local/agent_queue/CODEX_TASK.md`
- `database/local/agent_queue/candidate_investigation_queue.csv`
- `database/local/agent_results/proposed_records.json`
- `database/local/agent_results/source_evidence.json`
- `database/local/agent_results/session_report.json`

Validate and agent-approve results:

```bash
python scripts/validate_agent_results.py
```

Agent decisions are stored in `database/local/review_decisions.json` and are tied to the current proposal/evidence signature. If a proposed record or evidence file changes, the prior approval becomes stale and must be evaluated again. **Validate and agent-approve** approves records without manual review only when structured results validate, evidence is authoritative and official, identity is not ambiguous, and the proposal has no conflicts or validation warnings. Candidates that cannot be validated from official evidence are rejected instead of waiting for human approval.

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
