#!/usr/bin/env python3
"""Create the next bounded Desktop Codex investigation batch."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import ROOT
from catalog_staging import claim_investigation_batch, investigation_counts


DEFAULT_BATCH_ROOT = ROOT / "database" / "local" / "agent_batches"
DEFAULT_QUEUE_DIR = ROOT / "database" / "local" / "agent_queue"


def write_csv(path, rows):
    fields = list(rows[0]) if rows else [
        "candidate_id", "observed_name", "observed_institution", "observed_url",
        "match_state", "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_task(path, batch_id, csv_path, limit):
    path.write_text(f"""# Batch catalog investigation task

Work on the `Summer-REU-Database` branch. Read `AGENTS.md`, `database/README.md`, `docs/data_sources.md`, and `docs/database_update_process.md` before changing anything.

Investigate only this bounded batch first:

- Batch ID: `{batch_id}`
- Candidate CSV: `{csv_path.as_posix()}`
- Requested batch size: {limit}

For each candidate, compare against canonical stable program identities before deep retrieval. Search official host/program pages, NSF, ETAP, official university research offices, departments, medical schools, research institutes, government programs, and official program networks.

Use social posts, aggregators, search snippets, forums, and third-party summaries only as discovery leads. Verify canonical fields only with official program, host-institution, government, official network, or explicitly delegated opportunity-specific application sources.

Append or update the global result files:

- `database/local/agent_results/proposed_records.json`
- `database/local/agent_results/source_evidence.json`
- `database/local/agent_results/session_report.json`

Use contract version `1.0`. Preserve unknown and conditional facts. Record field-level source evidence and evidence hashes. Mark unresolved candidates in the session report rather than inventing values.

Validate before finishing:

```bash
python scripts/validate_agent_results.py
```

Never edit canonical SQLite or generated JSON directly. Finish with verified, rejected, ambiguous, unresolved, and included counts for this batch plus the files changed.
""", encoding="utf-8")


def create_batch(limit, batch_root=DEFAULT_BATCH_ROOT, queue_dir=DEFAULT_QUEUE_DIR):
    batch_id = datetime.now(timezone.utc).strftime("batch-%Y%m%dT%H%M%SZ")
    rows = claim_investigation_batch(limit=limit)
    batch_dir = Path(batch_root) / batch_id
    batch_csv = batch_dir / "candidate_batch.csv"
    batch_task = batch_dir / "CODEX_TASK.md"
    write_csv(batch_csv, rows)
    write_task(batch_task, batch_id, batch_csv.relative_to(ROOT), limit)

    queue_dir.mkdir(parents=True, exist_ok=True)
    write_csv(queue_dir / "candidate_investigation_queue.csv", rows)
    write_task(queue_dir / "CODEX_TASK.md", batch_id, (queue_dir / "candidate_investigation_queue.csv").relative_to(ROOT), limit)
    return {
        "batch_id": batch_id,
        "count": len(rows),
        "batch_dir": str(batch_dir),
        "queue_csv": str(queue_dir / "candidate_investigation_queue.csv"),
        "queue_task": str(queue_dir / "CODEX_TASK.md"),
        "staging": investigation_counts(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    batch = create_batch(args.limit)
    print(f"Created {batch['batch_id']} with {batch['count']} candidate(s)")
    print(f"Task: {batch['queue_task']}")
    print(f"Queue: {batch['queue_csv']}")


if __name__ == "__main__":
    main()
