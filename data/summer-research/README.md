# Generated website data

These JSON and CSV files are generated from `database/research_opportunities.sqlite` by `scripts/export_catalog.py`. They are static assets suitable for GitHub Pages.

- `catalog.json`: denormalized payload for opportunity cards, filters, comparison, and eligibility evaluation.
- `institutions.json`: map markers and institution-level aggregation inputs.
- `opportunities.json`: stable program records.
- `program_cycles.json`: annual dates, benefits, and status.
- `eligibility_rules.json`: hard-eligibility fields with nullable unknowns.
- `research_categories.json` and `research_tags.json`: controlled filter vocabularies.
- `sources.json`: source and verification metadata.
- `review/*.csv` and `review/*.xlsx`: human review/import/export artifacts.

Do not hand-edit generated files.
