# Accepted catalog data

The CSV in this directory contains accepted catalog records prepared outside this repository. It is the version-controlled source used to reproduce the published SQLite database. Importing a later annual cycle should update the stable opportunity and create or update only that year's cycle.

Boolean fields accept only explicit `1`/`0`, `yes`/`no`, or `true`/`false`; blanks remain `NULL`. Source and verification columns are preserved in SQLite for provenance.
