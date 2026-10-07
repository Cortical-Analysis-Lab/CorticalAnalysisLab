# Cortical Analysis Lab repository guidance

- Non-database lab website changes belong on `main`.
- Database, catalog, and fellowship explorer changes belong on `Summer-REU-Database`; only database-related changes should be pushed to that branch.
- Do not push or modify remote branches without an explicit user request.
- Fellowship publication remains suspended. Preserve the lab-only deployment and do not restore fellowship publication without an explicit request.
- Keep changes narrowly scoped and preserve unrelated pages, content, and styles.
- For previews, run `python3 -m http.server 4174 --bind 0.0.0.0`, outside the sandbox when required to bind the port. Share the forwarded Codespaces HTTPS URL using `CODESPACE_NAME` and `GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN`, rather than localhost links.
- Run `git diff --check` and the relevant checks before committing.
