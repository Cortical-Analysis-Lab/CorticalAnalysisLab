#!/usr/bin/env python3
"""Local browser GUI for discovery, staging, agent handoff, and catalog rebuilds."""

from __future__ import annotations

import argparse
import csv
import json
import secrets
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from catalog_staging import (  # noqa: E402
    DEFAULT_STAGING_DB, add_manual_links, candidate_counts, import_discovery_csv,
    list_candidates, set_review_status,
)


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fellowship Catalog Manager</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#171717;background:#f5f4f2;--red:#c8102e;--line:#d8d3ce}
*{box-sizing:border-box}body{margin:0}header{background:var(--red);color:white;padding:24px clamp(20px,5vw,64px)}h1{margin:0;font-size:clamp(25px,4vw,42px)}header p{margin:8px 0 0;max-width:850px}
main{max-width:1500px;margin:auto;padding:24px;display:grid;gap:20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}.panel{background:white;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 2px 10px #0000000a}
h2{margin:0 0 12px;font-size:19px}label{display:block;font-weight:650;margin:12px 0 6px}textarea,input,select{width:100%;padding:10px;border:1px solid #aaa;border-radius:7px;font:inherit}textarea{min-height:110px}button{background:var(--red);color:white;border:0;border-radius:7px;padding:10px 14px;font-weight:700;cursor:pointer;margin-top:12px}button.secondary{background:#222}button:disabled{opacity:.5;cursor:wait}.stats{display:flex;flex-wrap:wrap;gap:10px}.stat{border:1px solid var(--line);border-radius:9px;padding:10px 14px;min-width:110px}.stat strong{display:block;font-size:22px;color:var(--red)}
#message{display:none;padding:12px;border-radius:8px;background:#fff4d7;border:1px solid #d7ad45}.table-wrap{overflow:auto;max-height:560px;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:9px;border-bottom:1px solid #eee;vertical-align:top}th{position:sticky;top:0;background:#f8f7f5;z-index:1}.url{max-width:320px;word-break:break-all}.tag{display:inline-block;padding:3px 7px;border-radius:999px;background:#eee;font-size:11px}.NEW_PROGRAM{background:#ffe2e7;color:#8b0018}.EXISTING_PROGRAM{background:#dff3e4;color:#145d29}.POSSIBLE_DUPLICATE{background:#fff0c7;color:#754e00}pre{white-space:pre-wrap;background:#171717;color:#eee;padding:12px;border-radius:8px;max-height:300px;overflow:auto}
@media(max-width:650px){main{padding:12px}.panel{padding:15px}header{padding:20px}}
</style></head><body><header><h1>Fellowship Catalog Manager</h1><p>Discover broadly, stage safely, investigate with Codex, and promote only reviewed official-source records.</p></header><main>
<div id="message"></div><section class="grid">
<div class="panel"><h2>Catalog status</h2><div id="stats" class="stats"></div><button class="secondary" onclick="refresh()">Refresh</button></div>
<div class="panel"><h2>Add opportunity links</h2><label for="links">One URL per line</label><textarea id="links" placeholder="https://university.edu/research/summer-program"></textarea><label for="notes">Notes</label><input id="notes" placeholder="Why this may be relevant"><button onclick="addLinks()">Add to investigation queue</button></div>
<div class="panel"><h2>Run official-source discovery</h2><label for="minutes">Time budget</label><select id="minutes"><option>15</option><option selected>30</option><option>60</option><option>120</option><option>240</option></select><button onclick="runJob('discover',{minutes:+document.querySelector('#minutes').value})">Start discovery session</button><p>Uses approved official directories and persistent identity matching. New findings enter staging only.</p></div>
<div class="panel"><h2>Desktop Codex handoff</h2><p>Export a durable queue and task brief, then open this repository in Desktop Codex and ask it to execute the generated brief.</p><button onclick="runJob('export_queue',{})">Generate agent investigation bundle</button></div>
<div class="panel"><h2>Rebuild repository catalog</h2><p>Rebuilds canonical SQLite from reviewed repository inputs, exports browser/review data, and runs validation and tests.</p><button onclick="runJob('rebuild',{})">Rebuild and validate</button></div>
<div class="panel"><h2>Current job</h2><pre id="job">No job running.</pre></div>
</section>
<section class="panel"><h2>Candidate investigation queue</h2><div class="table-wrap"><table><thead><tr><th>Status</th><th>Match</th><th>Program / link</th><th>Institution</th><th>Source</th><th>Action</th></tr></thead><tbody id="candidates"></tbody></table></div></section>
</main><script>
const token='__TOKEN__';
async function api(path,options={}){options.headers={...(options.headers||{}),'Content-Type':'application/json','X-Local-Token':token};const r=await fetch(path,options);const data=await r.json();if(!r.ok)throw new Error(data.error||r.statusText);return data}
function msg(text){const el=document.querySelector('#message');el.textContent=text;el.style.display='block';setTimeout(()=>el.style.display='none',6000)}
async function refresh(){try{const data=await api('/api/status');document.querySelector('#stats').innerHTML=`<div class=stat><strong>${data.canonical_programs}</strong>canonical</div><div class=stat><strong>${data.staging.total}</strong>candidates</div><div class=stat><strong>${data.staging.sessions}</strong>sessions</div><div class=stat><strong>${data.git_changes}</strong>repo changes</div>`;document.querySelector('#candidates').innerHTML=data.candidates.map(c=>`<tr><td>${esc(c.review_status)}</td><td><span class="tag ${esc(c.match_state)}">${esc(c.match_state)}</span>${c.matched_public_id?'<br>'+esc(c.matched_public_id):''}</td><td>${esc(c.observed_name||'Manual link')}<br><span class=url>${link(c.observed_url)}</span></td><td>${esc(c.observed_institution||'')}</td><td>${esc(c.discovery_source)}</td><td><select onchange="setStatus('${esc(c.candidate_id)}',this.value)">${['pending','investigating','needs_review','approved','rejected','included'].map(s=>`<option ${s===c.review_status?'selected':''}>${s}</option>`).join('')}</select></td></tr>`).join('');if(data.job)document.querySelector('#job').textContent=JSON.stringify(data.job,null,2)}catch(e){msg(e.message)}}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function link(v){return v?`<a href="${esc(v)}" target=_blank rel=noopener>${esc(v)}</a>`:''}
async function addLinks(){const urls=document.querySelector('#links').value.split(/\n/).map(x=>x.trim()).filter(Boolean);try{const d=await api('/api/links',{method:'POST',body:JSON.stringify({urls,notes:document.querySelector('#notes').value})});document.querySelector('#links').value='';msg(`Added ${d.added.length} link(s)`);refresh()}catch(e){msg(e.message)}}
async function setStatus(id,status){try{await api('/api/candidate/status',{method:'POST',body:JSON.stringify({candidate_id:id,status})});refresh()}catch(e){msg(e.message)}}
async function runJob(kind,args){try{await api('/api/jobs',{method:'POST',body:JSON.stringify({kind,args})});msg(`${kind} started`);poll()}catch(e){msg(e.message)}}
async function poll(){await refresh();const d=await api('/api/status');if(d.job&&d.job.status==='running')setTimeout(poll,1500)}refresh();
</script></body></html>"""


class JobState:
    def __init__(self):
        self.lock = threading.Lock()
        self.current = None

    def snapshot(self):
        with self.lock:
            return dict(self.current) if self.current else None

    def start(self, kind, target):
        with self.lock:
            if self.current and self.current["status"] == "running":
                raise RuntimeError("Another job is already running")
            self.current = {"kind": kind, "status": "running", "started_at": datetime.now(timezone.utc).isoformat(), "output": ""}
        threading.Thread(target=self._run, args=(target,), daemon=True).start()

    def _run(self, target):
        try:
            output = target()
            with self.lock:
                self.current.update(status="complete", completed_at=datetime.now(timezone.utc).isoformat(), output=output[-12000:])
        except Exception as error:
            with self.lock:
                self.current.update(status="failed", completed_at=datetime.now(timezone.utc).isoformat(), output=f"{type(error).__name__}: {error}")


JOBS = JobState()


def run_commands(commands):
    outputs = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)
        outputs.extend(filter(None, [result.stdout, result.stderr]))
    return "\n".join(outputs)


def discovery_job(minutes):
    session_id = datetime.now(timezone.utc).strftime("local-%Y%m%dT%H%M%SZ")
    output = ROOT / "database" / "local" / "sessions" / session_id
    result = run_commands([[sys.executable, "scripts/run_discovery_session.py", "--session-id", session_id,
                            "--time-budget-minutes", str(minutes), "--output", str(output)]])
    count = import_discovery_csv(output / "candidates.csv", session_id, output / "report.json")
    return f"{result}\nImported {count} candidates into local staging.\nReport: {output / 'summary.md'}"


def export_queue_job():
    queue_dir = ROOT / "database" / "local" / "agent_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    rows = [row for row in list_candidates(limit=10000) if row["review_status"] in {"pending", "investigating", "needs_review"}]
    csv_path = queue_dir / "candidate_investigation_queue.csv"
    fields = list(rows[0]) if rows else ["candidate_id", "observed_name", "observed_institution", "observed_url", "match_state", "notes"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    brief = queue_dir / "CODEX_TASK.md"
    brief.write_text("""# Catalog discovery and investigation task

Investigate the candidates in `candidate_investigation_queue.csv` and continue broad opportunity discovery using the repository rules in `AGENTS.md`, `docs/data_sources.md`, and `docs/database_update_process.md`.

Search approved directories and official university, department, medical-school, research-institute, government, and network websites for as many relevant summer undergraduate research opportunities as practical. Follow university hub pages to distinct program pages, but compare every discovery against canonical stable identities before deep retrieval. Reuse fresh existing evidence rather than repeatedly scraping unchanged records.

Use official program, host-institution, government, official network, or explicitly delegated opportunity-specific application sources only. Social posts, aggregators, and third-party summaries are discovery-only. Preserve absent or conditional facts as unknown. Record new leads in the local staging database and regenerate this queue when useful. Produce reviewed proposed records and field-level source evidence; do not write canonical SQLite or generated JSON directly. After reviewed import changes, run `python3 scripts/rebuild_database.py`, `python3 scripts/test_catalog.py`, `python3 scripts/export_review_xlsx.py`, and `git diff --check`. Finish with discovered, existing, ambiguous, verified, rejected, and included counts plus the files changed.
""", encoding="utf-8")
    return f"Exported {len(rows)} candidates.\nQueue: {csv_path}\nCodex brief: {brief}"


def rebuild_job():
    return run_commands([
        [sys.executable, "scripts/rebuild_database.py"],
        [sys.executable, "scripts/test_catalog.py"],
        [sys.executable, "scripts/export_review_xlsx.py"],
        ["git", "diff", "--check"],
    ])


def canonical_count():
    import sqlite3
    connection = sqlite3.connect(ROOT / "database" / "research_opportunities.sqlite")
    count = connection.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    connection.close()
    return count


class Handler(BaseHTTPRequestHandler):
    token = None

    def log_message(self, format, *args):
        return

    def send_json(self, payload, status=HTTPStatus.OK):
        encoded = json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(encoded)

    def body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def authorized(self):
        return secrets.compare_digest(self.headers.get("X-Local-Token", ""), self.token)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            page = HTML.replace("__TOKEN__", self.token).encode()
            self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(page); return
        if path == "/api/status":
            if not self.authorized(): return self.send_json({"error": "Unauthorized"}, HTTPStatus.FORBIDDEN)
            git = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True)
            return self.send_json({"canonical_programs": canonical_count(), "staging": candidate_counts(),
                                   "candidates": list_candidates(), "git_changes": len(git.stdout.splitlines()), "job": JOBS.snapshot()})
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if not self.authorized(): return self.send_json({"error": "Unauthorized"}, HTTPStatus.FORBIDDEN)
        try:
            data, path = self.body(), urlparse(self.path).path
            if path == "/api/links":
                urls = data.get("urls") or []
                if not urls: raise ValueError("Add at least one URL")
                return self.send_json({"added": add_manual_links(urls, data.get("notes") or None)})
            if path == "/api/candidate/status":
                set_review_status(data["candidate_id"], data["status"]); return self.send_json({"ok": True})
            if path == "/api/jobs":
                kind, args = data.get("kind"), data.get("args") or {}
                if kind == "discover":
                    minutes = int(args.get("minutes", 30))
                    if minutes not in {15, 30, 60, 120, 240}: raise ValueError("Unsupported time budget")
                    JOBS.start(kind, lambda: discovery_job(minutes))
                elif kind == "export_queue": JOBS.start(kind, export_queue_job)
                elif kind == "rebuild": JOBS.start(kind, rebuild_job)
                else: raise ValueError("Unknown job kind")
                return self.send_json({"started": kind}, HTTPStatus.ACCEPTED)
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except RuntimeError as error:
            self.send_json({"error": str(error)}, HTTPStatus.CONFLICT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    Handler.token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Fellowship Catalog Manager: {url}")
    print("Press Ctrl+C to stop. Local staging:", DEFAULT_STAGING_DB)
    if not args.no_browser: threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__":
    main()
