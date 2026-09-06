# Website deployment

Fellowship publication is suspended as of September 6, 2026 pending catalog
quality remediation. Production publishes only the lab pages from `main`.
The fellowship navigation, page, assets, catalog JSON, and SQLite download
are excluded from the current deployment.

`Summer-REU-Database` retains the accepted CSV, SQLite, browser exports, and
questionnaire for local development. Its validation workflow still checks
pushes, but no longer triggers production deployment. Repository visibility
has not changed.

The **Deploy website** workflow and `scripts/build_pages.py` live on `main`.
They assemble a fresh artifact on pushes to `main`, manual requests, and
successful **🧠 Update Publications from ORCID** runs.

GitHub Pages was still configured to **Deploy from a branch**, `main` at `/`,
when publication was suspended. Both that legacy publisher and the custom
workflow now publish only the lab site. If Pages is switched to GitHub Actions,
the custom workflow continues to publish the same lab-only artifact.

Restoring fellowship publication requires an explicit user request after
accepted-data remediation and validation. Structural tests alone are not a
republication gate. The former combined workflow is in main commit `7d0a7bb`;
withdrawal is commit `71c4567`.
