# Website deployment

The public site combines two branches without merging the database into `main`:

- `main` owns the lab pages, navigation, shared styles/scripts, and deployment workflow.
- `Summer-REU-Database` owns `fellowship-database.html`, the three `assets/fellowship-*` files, `data/summer-research/`, and the published SQLite database.

The permanent database URL is https://corticalanalysis.org/fellowship-database.html.
Browser code reads the generated JSON; SQLite is only a downloadable artifact.

GitHub Pages must use **GitHub Actions** as its publishing source. The
`github-pages` environment continues to allow deployments only from `main`.

A push to the database branch runs **Validate fellowship database**. A successful
run triggers **Deploy website** on `main` through `workflow_run`. Pushes to `main`
and manual runs also deploy. The deployment checks out the latest versions of
both branches, validates the selected database revision, and uses
`scripts/build_pages.py` from `main` to assemble a fresh public artifact. Failed
validation prevents publication. Runs share one deployment concurrency group.

To change the deployment, edit `.github/workflows/deploy-pages.yml` or
`scripts/build_pages.py` on `main`. Keep the validation workflow on the database
branch so database pushes continue to trigger publication. To add a new
fellowship asset outside `data/summer-research/`, update the explicit file list
in the assembly script.

Successful runs of **🧠 Update Publications from ORCID** also trigger deployment
through `workflow_run`, since pushes made with GitHub's automatic token do not
trigger a separate push workflow.
