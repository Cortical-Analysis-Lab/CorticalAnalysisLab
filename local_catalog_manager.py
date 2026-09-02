#!/usr/bin/env python3
"""Local browser GUI for discovery, staging, agent handoff, and catalog rebuilds."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
    investigation_counts, list_candidates, set_review_status,
)
from automated_investigate_candidates import DEFAULT_PROGRESS as AUTO_PROGRESS, run as run_automated_investigation  # noqa: E402
from create_agent_batch import create_batch  # noqa: E402
from run_catalog_update_pipeline import PIPELINE_REPORT, run_pipeline  # noqa: E402
from validate_agent_results import validate_results  # noqa: E402


LOCAL_DIR = ROOT / "database" / "local"
PIPELINE_STATE_PATH = LOCAL_DIR / "pipeline_state.json"
REVIEW_DECISIONS_PATH = LOCAL_DIR / "review_decisions.json"
AGENT_RESULTS_DIR = LOCAL_DIR / "agent_results"
PIPELINE_STAGES = [
    "Discovery",
    "Identity matching/deduplication",
    "Codex investigation bundle generation",
    "Waiting for agent results",
    "Agent validation/approval",
    "Approved-only promotion",
    "SQLite/JSON rebuild",
    "Validation/testing",
    "Git diff review",
    "Optional branch/commit/push/PR submission",
]


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json_file(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json_file(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_pipeline_state():
    return {
        "contract_version": "1.0",
        "updated_at": now_utc(),
        "stages": [{"name": name, "status": "pending", "updated_at": None, "details": None} for name in PIPELINE_STAGES],
    }


def load_pipeline_state():
    state = load_json_file(PIPELINE_STATE_PATH, default_pipeline_state())
    known = {stage.get("name"): stage for stage in state.get("stages", [])}
    state["stages"] = [
        known.get(name, {"name": name, "status": "pending", "updated_at": None, "details": None})
        for name in PIPELINE_STAGES
    ]
    report = load_json_file(PIPELINE_REPORT, {})
    if report.get("status") == "complete":
        changed = False
        completed_at = report.get("completed_at") or now_utc()
        completed = {
            "Waiting for agent results": "Agent results validated",
            "Agent validation/approval": f"Processed {sum(batch.get('checked', 0) for batch in report.get('batches', []))} candidate(s)",
            "Approved-only promotion": "Approved records promoted",
            "SQLite/JSON rebuild": "Database and JSON exports rebuilt",
            "Validation/testing": "Validation, tests, and review workbook export passed",
            "Git diff review": "Diff whitespace check passed; review changed files before committing",
        }
        for stage in state["stages"]:
            if stage["name"] in completed and stage.get("status") != "complete":
                stage.update(status="complete", updated_at=completed_at, details=completed[stage["name"]])
                changed = True
        if changed:
            state["updated_at"] = now_utc()
            write_json_file(PIPELINE_STATE_PATH, state)
    return state


def update_pipeline_stage(name, status, details=None):
    state = load_pipeline_state()
    for stage in state["stages"]:
        if stage["name"] == name:
            stage.update(status=status, updated_at=now_utc(), details=details)
            break
    state["updated_at"] = now_utc()
    write_json_file(PIPELINE_STATE_PATH, state)
    return state


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proposal_signature(candidate_id):
    paths = [AGENT_RESULTS_DIR / "proposed_records.json", AGENT_RESULTS_DIR / "source_evidence.json"]
    digest = hashlib.sha256(candidate_id.encode())
    for path in paths:
        if path.exists():
            digest.update(file_sha256(path).encode())
    return digest.hexdigest()


def load_review_decisions():
    return load_json_file(REVIEW_DECISIONS_PATH, {"contract_version": "1.0", "decisions": {}})


def save_review_decision(candidate_id, decision, signature):
    allowed = {"approved", "rejected", "needs_more_investigation"}
    if decision not in allowed:
        raise ValueError(f"Unsupported review decision: {decision}")
    expected = proposal_signature(candidate_id)
    if signature != expected:
        raise ValueError("Proposal or evidence changed; refresh before recording a decision")
    payload = load_review_decisions()
    payload["decisions"][candidate_id] = {
        "decision": decision,
        "signature": signature,
        "decided_by": "local_reviewer",
        "reviewed_at": now_utc(),
    }
    write_json_file(REVIEW_DECISIONS_PATH, payload)
    update_pipeline_stage("Agent validation/approval", "running" if decision != "approved" else "complete", f"{candidate_id}: {decision}")
    return payload["decisions"][candidate_id]


def auto_approve_agent_results():
    errors = validate_results(AGENT_RESULTS_DIR)
    if errors:
        raise ValueError("\n".join(errors))
    proposed = load_json_file(AGENT_RESULTS_DIR / "proposed_records.json", {"records": []})
    decisions = load_review_decisions()
    approved, blocked = [], []
    for record in proposed.get("records", []):
        candidate_id = record.get("candidate_id")
        identity = record.get("identity", {})
        reasons = []
        if identity.get("match_state") in {"POSSIBLE_DUPLICATE", "AMBIGUOUS"}:
            reasons.append("ambiguous identity")
        if record.get("conflicts"):
            reasons.append("conflicts present")
        if record.get("validation_warnings"):
            reasons.append("validation warnings present")
        if reasons:
            decisions["decisions"][candidate_id] = {
                "decision": "needs_more_investigation",
                "signature": proposal_signature(candidate_id),
                "decided_by": "agent_strict_validation",
                "reviewed_at": now_utc(),
                "reasons": reasons,
            }
            blocked.append({"candidate_id": candidate_id, "reasons": reasons})
            continue
        decisions["decisions"][candidate_id] = {
            "decision": "approved",
            "signature": proposal_signature(candidate_id),
            "decided_by": "agent_strict_validation",
            "reviewed_at": now_utc(),
        }
        approved.append(candidate_id)
    write_json_file(REVIEW_DECISIONS_PATH, decisions)
    update_pipeline_stage(
        "Agent validation/approval",
        "complete" if approved and not blocked else "running",
        f"Agent-approved {len(approved)}; blocked {len(blocked)}",
    )
    return {"approved": approved, "blocked": blocked}


def agent_review_payload():
    errors = validate_results(AGENT_RESULTS_DIR)
    proposed = load_json_file(AGENT_RESULTS_DIR / "proposed_records.json", {"records": [], "generated_at": None})
    session_report = load_json_file(AGENT_RESULTS_DIR / "session_report.json", {"counts": {}, "generated_at": None})
    decisions = load_review_decisions()["decisions"]
    if errors:
        return {
            "validation_errors": errors,
            "records": [],
            "decisions": decisions,
            "summary": {
                "generated_at": proposed.get("generated_at") or session_report.get("generated_at"),
                "proposal_count": len(proposed.get("records", [])),
                "approved_count": sum(1 for item in decisions.values() if item.get("decision") == "approved"),
                "blocked_count": sum(1 for item in decisions.values() if item.get("decision") == "needs_more_investigation"),
                "session_counts": session_report.get("counts", {}),
            },
        }
    evidence = load_json_file(AGENT_RESULTS_DIR / "source_evidence.json", {"evidence": []})
    official_counts = {}
    for item in evidence.get("evidence", []):
        if item.get("authoritative") and item.get("source_type") != "discovery_only":
            official_counts[item["candidate_id"]] = official_counts.get(item["candidate_id"], 0) + 1
    records = []
    for record in proposed.get("records", []):
        identity = record.get("identity", {})
        candidate_id = record.get("candidate_id")
        signature = proposal_signature(candidate_id)
        decision = decisions.get(candidate_id, {})
        stale = bool(decision and decision.get("signature") != signature)
        records.append({
            "candidate_id": candidate_id,
            "program_name": identity.get("program_name"),
            "institution_name": identity.get("institution_name"),
            "match_state": identity.get("match_state"),
            "cycle_year": record.get("cycle_year"),
            "official_sources": official_counts.get(candidate_id, 0),
            "validation_warnings": len(record.get("validation_warnings", [])),
            "signature": signature,
            "decision": "stale" if stale else decision.get("decision", "not_evaluated"),
            "decided_by": decision.get("decided_by"),
            "reasons": decision.get("reasons", []),
        })
    return {
        "validation_errors": [],
        "records": records,
        "decisions": decisions,
        "summary": {
            "generated_at": proposed.get("generated_at") or session_report.get("generated_at"),
            "proposal_count": len(records),
            "approved_count": sum(1 for item in decisions.values() if item.get("decision") == "approved"),
            "blocked_count": sum(1 for item in decisions.values() if item.get("decision") == "needs_more_investigation"),
            "session_counts": session_report.get("counts", {}),
        },
    }


def discovery_progress(output_dir):
    if not output_dir:
        return None
    progress = load_json_file(Path(output_dir) / "progress.json", None)
    if progress:
        return progress
    csv_path = Path(output_dir) / "candidates.csv"
    if not csv_path.exists():
        return None
    with csv_path.open(newline="", encoding="utf-8") as handle:
        count = sum(1 for _ in csv.DictReader(handle))
    return {"discovered_unique": count, "source_errors": []}


def automated_investigation_progress():
    return load_json_file(AUTO_PROGRESS, None)


def full_pipeline_progress():
    return load_json_file(PIPELINE_REPORT, None)


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fellowship Catalog Manager</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#171717;background:#f5f4f2;--red:#c8102e;--line:#d8d3ce}
*{box-sizing:border-box}body{margin:0}header{background:var(--red);color:white;padding:24px clamp(20px,5vw,64px)}h1{margin:0;font-size:clamp(25px,4vw,42px)}header p{margin:8px 0 0;max-width:850px}
main{max-width:1500px;margin:auto;padding:24px;display:grid;gap:20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}.dashboard{display:grid;grid-template-columns:minmax(320px,1.3fr) minmax(300px,.9fr);gap:20px}.actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}.panel{background:white;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 2px 10px #0000000a}
h2{margin:0 0 12px;font-size:19px}h3{margin:0 0 8px;font-size:15px}label{display:block;font-weight:650;margin:12px 0 6px}textarea,input,select{width:100%;padding:10px;border:1px solid #aaa;border-radius:7px;font:inherit}textarea{min-height:110px}button{background:var(--red);color:white;border:0;border-radius:7px;padding:10px 14px;font-weight:700;cursor:pointer;margin-top:12px}button.secondary{background:#222}button:disabled{opacity:.5;cursor:wait}.stats{display:flex;flex-wrap:wrap;gap:10px}.stat{border:1px solid var(--line);border-radius:9px;padding:10px 14px;min-width:110px}.stat strong{display:block;font-size:22px;color:var(--red)}
#message{display:none;padding:12px;border-radius:8px;background:#fff4d7;border:1px solid #d7ad45}.next-box{border:2px solid var(--red);border-radius:10px;padding:14px;background:#fff8f9}.next-box strong{display:block;font-size:18px;margin-bottom:6px}.muted{color:#666}.status-line{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}.status-dot{width:10px;height:10px;border-radius:50%;background:#999}.status-dot.running{background:#d99a00}.status-dot.complete{background:#167333}.status-dot.failed{background:#b00020}.table-wrap{overflow:auto;max-height:560px;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:9px;border-bottom:1px solid #eee;vertical-align:top}th{position:sticky;top:0;background:#f8f7f5;z-index:1}.url{max-width:320px;word-break:break-all}.tag{display:inline-block;padding:3px 7px;border-radius:999px;background:#eee;font-size:11px}.NEW_PROGRAM{background:#ffe2e7;color:#8b0018}.EXISTING_PROGRAM{background:#dff3e4;color:#145d29}.POSSIBLE_DUPLICATE,.AMBIGUOUS{background:#fff0c7;color:#754e00}.stage-list{display:grid;gap:8px;counter-reset:stage}.stage{border:1px solid var(--line);border-radius:8px;padding:9px 11px;display:flex;justify-content:space-between;gap:12px;align-items:center}.stage:before{counter-increment:stage;content:counter(stage) ".";font-weight:800;color:var(--red);margin-right:2px}.stage-name{flex:1}.stage-state{font-size:12px;border-radius:999px;background:#eee;padding:3px 8px}.stage.running .stage-state{background:#fff0c7;color:#754e00}.stage.complete .stage-state{background:#dff3e4;color:#145d29}.stage.failed .stage-state{background:#ffe2e7;color:#8b0018}.job-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}.job-cell{border:1px solid var(--line);border-radius:8px;padding:10px}.job-cell strong{display:block;color:var(--red);font-size:20px}.review-card{border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:10px}.review-actions{display:flex;gap:8px;flex-wrap:wrap}.review-actions button{margin-top:4px}pre{white-space:pre-wrap;background:#171717;color:#eee;padding:12px;border-radius:8px;max-height:300px;overflow:auto}
@media(max-width:900px){.dashboard{grid-template-columns:1fr}}
@media(max-width:650px){main{padding:12px}.panel{padding:15px}header{padding:20px}}
</style></head><body><header><h1>Fellowship Catalog Manager</h1><p>Discover broadly, stage safely, investigate locally, and promote only validated official-source records.</p></header><main>
<div id="message"></div>
<section class="dashboard">
<div class="panel"><h2>Now</h2><div id="now"></div><div id="stats" class="stats"></div><button class="secondary" onclick="refresh()">Refresh</button></div>
<div class="panel"><h2>Next Action</h2><div id="nextAction" class="next-box"></div></div>
</section>
<section class="panel"><h2>Workflow</h2><div id="stages" class="stage-list"></div></section>
<section class="actions">
<div class="panel"><h2>1. Full Automated Update</h2><p>Automated. Processes the discovered queue, validates clean records, promotes them into reviewed inputs, rebuilds SQLite/JSON, and writes source audits.</p><label for="pipelineBatchSize">Batch size</label><select id="pipelineBatchSize"><option>50</option><option selected>100</option><option>200</option></select><button onclick="runJob('full_pipeline',{batch_size:+document.querySelector('#pipelineBatchSize').value})">Run full automated update</button></div>
<div class="panel"><h2>2. Reinvestigate Missing Fields</h2><p>Automated. Rechecks existing catalog rows with N/A optional data and fills newly available official-source values.</p><button onclick="runJob('reinvestigate_updates',{})">Reinvestigate N/A updates</button></div>
<div class="panel"><h2>3. Discovery</h2><p>Automated. Finds candidates from approved discovery sources and stages them locally.</p><label for="minutes">Time budget</label><select id="minutes"><option>15</option><option selected>30</option><option>60</option><option>120</option><option>240</option></select><button onclick="runJob('discover',{minutes:+document.querySelector('#minutes').value})">Start discovery session</button></div>
<div class="panel"><h2>4. Candidate Links</h2><p>Optional. Add links you already know about; they enter the same investigation queue.</p><label for="links">One URL per line</label><textarea id="links" placeholder="https://university.edu/research/summer-program"></textarea><label for="notes">Notes</label><input id="notes" placeholder="Why this may be relevant"><button onclick="addLinks()">Add to queue</button></div>
<div class="panel"><h2>5. Automated Investigation</h2><p>Automated batch-only step. Use this if you do not want to run the full pipeline yet.</p><label for="autoBatchSize">Batch size</label><select id="autoBatchSize"><option>25</option><option selected>50</option><option>100</option><option>200</option></select><button onclick="runJob('automated_investigate',{limit:+document.querySelector('#autoBatchSize').value})">Run automated investigation batch</button></div>
<div class="panel"><h2>6. Optional Handoff</h2><p>Optional fallback only. Creates a Desktop Codex packet for records automation cannot resolve.</p><label for="batchSize">Batch size</label><select id="batchSize"><option selected>25</option><option>50</option><option>75</option><option>100</option></select><button class="secondary" onclick="runJob('export_batch',{limit:+document.querySelector('#batchSize').value})">Generate fallback task bundle</button><button class="secondary" onclick="runJob('export_queue',{})">Generate full queue bundle</button></div>
<div class="panel"><h2>7. Agent Results</h2><p>Automated. Re-validates the current result files and records strict agent approvals.</p><button onclick="runJob('validate_results',{})">Validate and agent-approve current results</button></div>
<div class="panel"><h2>8. Promotion Report</h2><p>Automated guard. Checks approved records and writes promotion reports before any catalog rebuild.</p><button onclick="runJob('promote',{})">Run approved-only promotion report</button></div>
<div class="panel"><h2>9. Rebuild</h2><p>Automated after approved records have been promoted into reviewed inputs.</p><button onclick="runJob('rebuild',{})">Rebuild and validate</button></div>
</section>
<section class="panel"><h2>Job Details</h2><div id="job"></div><pre id="jobOutput">No job running.</pre></section>
<section class="panel"><h2>Current Agent Results</h2><div id="review"></div></section>
<section class="panel"><h2>Candidate investigation queue</h2><div class="table-wrap"><table><thead><tr><th>Status</th><th>Match</th><th>Program / link</th><th>Institution</th><th>Source</th><th>Action</th></tr></thead><tbody id="candidates"></tbody></table></div></section>
</main><script>
const token='__TOKEN__';
async function api(path,options={}){options.headers={...(options.headers||{}),'Content-Type':'application/json','X-Local-Token':token};const r=await fetch(path,options);const data=await r.json();if(!r.ok)throw new Error(data.error||r.statusText);return data}
function msg(text){const el=document.querySelector('#message');el.textContent=text;el.style.display='block';setTimeout(()=>el.style.display='none',6000)}
function fmt(seconds){seconds=Math.max(0,Math.floor(seconds||0));const h=Math.floor(seconds/3600),m=Math.floor((seconds%3600)/60),s=seconds%60;return h?`${h}h ${m}m ${s}s`:m?`${m}m ${s}s`:`${s}s`}
function renderStages(pipeline){document.querySelector('#stages').innerHTML=pipeline.stages.map(s=>`<div class="stage ${esc(s.status)}"><span class=stage-name>${esc(s.name)}</span><span class=stage-state>${esc(s.status)}</span></div>`).join('')}
function renderJob(job){if(!job){document.querySelector('#job').innerHTML='<p>No job running.</p>';document.querySelector('#jobOutput').textContent='No job running.';return}const p=job.progress||{};const found=p.discovered_unique??p.approved_candidates??0;const checked=p.checked!==undefined?`${p.checked}/${p.total}`:'N/A';const cells=[['Kind',job.kind],['Status',job.status],['Elapsed',fmt(job.elapsed_seconds)],['Found/approved',found],['Checked',checked],['Errors',(p.source_errors||[]).length],['Source',p.current_source||p.current_candidate||'N/A']];document.querySelector('#job').innerHTML=`<div class=job-grid>${cells.map(c=>`<div class=job-cell><span>${esc(c[0])}</span><strong>${esc(c[1])}</strong></div>`).join('')}</div>`;document.querySelector('#jobOutput').textContent=job.output||JSON.stringify(p,null,2)||''}
function stage(pipeline,name){return (pipeline.stages||[]).find(s=>s.name===name)||{}}
function nextAction(data,reviewData){const counts=data.investigation.by_review_status||{}, pending=counts.pending||0, needs=counts.needs_review||0, investigating=counts.investigating||0;const summary=reviewData.summary||{}, proposals=summary.proposal_count||0, approved=summary.approved_count||0, blocked=summary.blocked_count||0;if(data.job&&data.job.status==='running')return [`${data.job.kind} is running`,`Watch Job Details for elapsed time, checked count, approved/rejected/unresolved counts, and errors. This part is automated.`];if(pending===0&&needs===0&&investigating===0&&proposals===0)return ['Start discovery','Choose a time budget in Discovery and start a session.'];if(pending>0||needs>0)return ['Run full automated update',`${pending+needs} candidate(s) are waiting. This will process the queue, promote validated records, rebuild the database, and write the source list.`];if(proposals>0&&approved+blocked<proposals)return ['Validate and agent-approve current results',`${proposals} current proposal(s) are in agent_results. Clean records will be approved automatically.`];if(approved>0)return ['Run promotion report',`${approved} approved proposal(s) are ready for promotion/rebuild.`];if(investigating>0)return ['Resume automation',`${investigating} candidate(s) are marked investigating. Run the full automated update to resume.`];return ['Refresh','No running job is visible. Refresh to reload local state.']}
function renderNow(data,reviewData){const job=data.job, dot=job?job.status:'idle';document.querySelector('#now').innerHTML=`<div class=status-line><span class="status-dot ${esc(dot)}"></span><strong>${job?esc(job.kind)+' '+esc(job.status):'Idle'}</strong></div><p class=muted>${job&&job.status==='running'?'An automated job is active.':'No automated job is running inside the GUI.'}</p>`;const review=data.investigation.by_review_status||{};document.querySelector('#stats').innerHTML=`<div class=stat><strong>${data.canonical_programs}</strong>canonical</div><div class=stat><strong>${data.staging.total}</strong>candidates</div><div class=stat><strong>${review.pending??0}</strong>pending</div><div class=stat><strong>${review.needs_review??0}</strong>unresolved retry</div><div class=stat><strong>${review.investigating??0}</strong>investigating</div><div class=stat><strong>${(reviewData.summary||{}).proposal_count??0}</strong>current proposals</div><div class=stat><strong>${data.git_changes}</strong>repo changes</div>`}
function renderNext(data,reviewData){const action=nextAction(data,reviewData);document.querySelector('#nextAction').innerHTML=`<strong>${esc(action[0])}</strong><span>${esc(action[1])}</span>`}
async function refresh(){try{const data=await api('/api/status');const reviewData=await api('/api/review');renderNow(data,reviewData);renderNext(data,reviewData);renderStages(data.pipeline);renderJob(data.job);document.querySelector('#candidates').innerHTML=data.candidates.map(c=>`<tr><td>${esc(c.review_status)}</td><td><span class="tag ${esc(c.match_state)}">${esc(c.match_state)}</span>${c.matched_public_id?'<br>'+esc(c.matched_public_id):''}</td><td>${esc(c.observed_name||'Manual link')}<br><span class=url>${link(c.observed_url)}</span></td><td>${esc(c.observed_institution||'')}</td><td>${esc(c.discovery_source)}</td><td><select onchange="setStatus('${esc(c.candidate_id)}',this.value)">${['pending','investigating','needs_review','approved','rejected','included'].map(s=>`<option ${s===c.review_status?'selected':''}>${s}</option>`).join('')}</select></td></tr>`).join('');renderReview(reviewData)}catch(e){msg(e.message)}}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function link(v){return v?`<a href="${esc(v)}" target=_blank rel=noopener>${esc(v)}</a>`:''}
async function addLinks(){const urls=document.querySelector('#links').value.split(/\n/).map(x=>x.trim()).filter(Boolean);try{const d=await api('/api/links',{method:'POST',body:JSON.stringify({urls,notes:document.querySelector('#notes').value})});document.querySelector('#links').value='';msg(`Added ${d.added.length} link(s)`);refresh()}catch(e){msg(e.message)}}
async function setStatus(id,status){try{await api('/api/candidate/status',{method:'POST',body:JSON.stringify({candidate_id:id,status})});refresh()}catch(e){msg(e.message)}}
async function runJob(kind,args){try{await api('/api/jobs',{method:'POST',body:JSON.stringify({kind,args})});msg(`${kind} started`);poll()}catch(e){msg(e.message)}}
function renderReview(data){const el=document.querySelector('#review');const s=data.summary||{};const counts=s.session_counts||{};const summary=`<div class=stats><div class=stat><strong>${esc(s.proposal_count??0)}</strong>current proposals</div><div class=stat><strong>${esc(s.approved_count??0)}</strong>agent approved</div><div class=stat><strong>${esc(s.blocked_count??0)}</strong>needs investigation</div><div class=stat><strong>${esc(counts.unresolved??0)}</strong>unresolved in report</div></div><p>Generated: ${esc(s.generated_at||'N/A')}</p>`;if(data.validation_errors.length){el.innerHTML=summary+`<p>Current agent results are not ready for approval.</p><pre>${esc(data.validation_errors.join('\n'))}</pre>`;return}if(!data.records.length){el.innerHTML=summary+'<p>No proposed records found yet. Run automated investigation or the full automated update.</p>';return}el.innerHTML=summary+data.records.map(r=>`<div class=review-card><strong>${esc(r.program_name||r.candidate_id)}</strong><br>${esc(r.institution_name||'')} | ${esc(r.match_state||'')} | cycle ${esc(r.cycle_year??'N/A')}<br>Official evidence: ${esc(r.official_sources)} source(s)<br>Warnings: ${esc(r.validation_warnings)}<br>Agent decision: <span class="tag">${esc(r.decision)}</span>${r.decided_by?' by '+esc(r.decided_by):''}${r.reasons&&r.reasons.length?'<pre>'+esc(r.reasons.join('\n'))+'</pre>':''}</div>`).join('')}
async function poll(){await refresh();const d=await api('/api/status');if(d.job&&d.job.status==='running')setTimeout(poll,1500)}refresh();
</script></body></html>"""


class JobState:
    def __init__(self):
        self.lock = threading.Lock()
        self.current = None

    def snapshot(self):
        with self.lock:
            if not self.current:
                return None
            snapshot = dict(self.current)
        started_at = snapshot.get("started_at")
        if started_at:
            started = datetime.fromisoformat(started_at)
            ended = datetime.fromisoformat(snapshot["completed_at"]) if snapshot.get("completed_at") else datetime.now(timezone.utc)
            snapshot["elapsed_seconds"] = max(0, int((ended - started).total_seconds()))
        if snapshot.get("kind") == "discover":
            snapshot["progress"] = discovery_progress(snapshot.get("output_dir"))
        if snapshot.get("kind") == "automated_investigate":
            snapshot["progress"] = automated_investigation_progress()
        if snapshot.get("kind") == "full_pipeline":
            progress = full_pipeline_progress()
            if progress:
                batches = progress.get("batches", [])
                progress["checked"] = sum(batch.get("checked", 0) for batch in batches)
                progress["total"] = "all pending"
                progress["approved_candidates"] = sum(batch.get("approved", 0) for batch in batches)
                progress["source_errors"] = []
            snapshot["progress"] = progress
        return snapshot

    def start(self, kind, target, metadata=None):
        with self.lock:
            if self.current and self.current["status"] == "running":
                raise RuntimeError("Another job is already running")
            self.current = {"kind": kind, "status": "running", "started_at": now_utc(), "output": ""}
            if metadata:
                self.current.update(metadata)
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
    return discovery_job_with_session(minutes, session_id, output)


def discovery_job_with_session(minutes, session_id, output):
    update_pipeline_stage("Discovery", "running", f"{minutes} minute budget")
    result = run_commands([[sys.executable, "scripts/run_discovery_session.py", "--session-id", session_id,
                            "--time-budget-minutes", str(minutes), "--output", str(output)]])
    count = import_discovery_csv(output / "candidates.csv", session_id, output / "report.json")
    update_pipeline_stage("Discovery", "complete", f"Imported {count} candidate(s)")
    update_pipeline_stage("Identity matching/deduplication", "complete", "Candidate identities classified during discovery")
    return f"{result}\nImported {count} candidates into local staging.\nReport: {output / 'summary.md'}"


def export_queue_job():
    update_pipeline_stage("Codex investigation bundle generation", "running")
    queue_dir = ROOT / "database" / "local" / "agent_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    AGENT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = [row for row in list_candidates(limit=10000) if row["review_status"] in {"pending", "investigating", "needs_review"}]
    csv_path = queue_dir / "candidate_investigation_queue.csv"
    fields = list(rows[0]) if rows else ["candidate_id", "observed_name", "observed_institution", "observed_url", "match_state", "notes"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    brief = queue_dir / "CODEX_TASK.md"
    brief.write_text("""# Catalog discovery and investigation task

Work on the `Summer-REU-Database` branch. Read `AGENTS.md`, `database/README.md`, `docs/data_sources.md`, and `docs/database_update_process.md` before changing anything.

Investigate the candidates in `candidate_investigation_queue.csv` and continue broad opportunity discovery using the repository rules.

Search NSF, ETAP, official university research offices, departments, medical schools, research institutes, government programs, and official program networks. Follow university hub pages to distinct program pages, but compare every discovery against canonical stable identities before deep retrieval. Reuse fresh existing evidence instead of repeatedly scraping unchanged pages.

Use official program, host-institution, government, official network, or explicitly delegated opportunity-specific application sources only. Social posts, aggregators, search snippets, forums, and third-party summaries are discovery-only. Preserve absent and conditional facts as unknown unless official wording supports a structured value. Record field-level source evidence for every proposed canonical fact.

Write structured results into:

- `database/local/agent_results/proposed_records.json`
- `database/local/agent_results/source_evidence.json`
- `database/local/agent_results/session_report.json`

Use contract version `1.0` and validate against the schemas in `schema/agent_results/`. Then run:

```bash
python3 scripts/validate_agent_results.py
```

Never edit canonical SQLite or generated JSON directly. Do not write student profiles, questionnaire answers, essays, transcripts, or application materials. Finish with discovered, existing, ambiguous, verified, rejected, and included counts plus the files changed.
""", encoding="utf-8")
    update_pipeline_stage("Codex investigation bundle generation", "complete", f"Exported {len(rows)} candidate(s)")
    update_pipeline_stage("Waiting for agent results", "running", str(AGENT_RESULTS_DIR))
    return f"Exported {len(rows)} candidates.\nQueue: {csv_path}\nCodex brief: {brief}"


def export_batch_job(limit):
    update_pipeline_stage("Codex investigation bundle generation", "running", f"Batch size {limit}")
    batch = create_batch(limit)
    update_pipeline_stage("Codex investigation bundle generation", "complete", f"{batch['batch_id']}: {batch['count']} candidate(s)")
    update_pipeline_stage("Waiting for agent results", "running", batch["queue_task"])
    return (
        f"Created {batch['batch_id']} with {batch['count']} candidate(s).\n"
        f"Task: {batch['queue_task']}\n"
        f"Queue: {batch['queue_csv']}\n"
        "Open this repository in Desktop Codex and ask it to execute database/local/agent_queue/CODEX_TASK.md."
    )


def validate_results_job():
    update_pipeline_stage("Waiting for agent results", "running", str(AGENT_RESULTS_DIR))
    errors = validate_results(AGENT_RESULTS_DIR)
    if errors:
        update_pipeline_stage("Waiting for agent results", "failed", f"{len(errors)} validation error(s)")
        return "\n".join(f"ERROR: {error}" for error in errors)
    update_pipeline_stage("Waiting for agent results", "complete", "Agent results validated")
    result = auto_approve_agent_results()
    update_pipeline_stage("Agent validation/approval", "complete", f"Approved {len(result['approved'])}; needs investigation {len(result['blocked'])}")
    lines = [
        f"Agent result validation passed: {AGENT_RESULTS_DIR}",
        f"Agent-approved {len(result['approved'])} record(s).",
        f"Sent {len(result['blocked'])} record(s) back for more investigation.",
    ]
    lines.extend(f"- {item['candidate_id']}: {', '.join(item['reasons'])}" for item in result["blocked"])
    return "\n".join(lines)


def automated_investigation_job(limit):
    update_pipeline_stage("Agent validation/approval", "running", f"Automated investigation batch size {limit}")
    result = run_automated_investigation(limit=limit)
    approval = auto_approve_agent_results()
    update_pipeline_stage(
        "Agent validation/approval",
        "complete",
        f"Checked {result['checked']}; approved {len(approval['approved'])}; rejected {result['rejected']}; unresolved {result['unresolved']}",
    )
    return (
        f"Automated investigation checked {result['checked']} candidate(s).\n"
        f"Agent-approved {len(approval['approved'])} clean proposal(s).\n"
        f"Rejected {result['rejected']} obvious non-opportunit(ies).\n"
        f"Finalized {result['unresolved']} unresolved candidate(s) as rejected for insufficient official evidence.\n"
        f"Source errors: {result['errors']}"
    )


def auto_approve_job():
    result = auto_approve_agent_results()
    lines = [f"Agent-approved {len(result['approved'])} record(s)."]
    if result["blocked"]:
        lines.append(f"Blocked {len(result['blocked'])} record(s):")
        lines.extend(f"- {item['candidate_id']}: {', '.join(item['reasons'])}" for item in result["blocked"])
    return "\n".join(lines)


def rebuild_job():
    update_pipeline_stage("SQLite/JSON rebuild", "running")
    output = run_commands([
        [sys.executable, "scripts/rebuild_database.py"],
        [sys.executable, "scripts/validate_catalog.py"],
        [sys.executable, "scripts/test_catalog.py"],
        [sys.executable, "scripts/export_review_xlsx.py"],
        ["git", "diff", "--check"],
    ])
    update_pipeline_stage("SQLite/JSON rebuild", "complete")
    update_pipeline_stage("Validation/testing", "complete")
    update_pipeline_stage("Git diff review", "complete", "Diff whitespace check passed; review changed files before committing")
    return output


def promote_job():
    update_pipeline_stage("Approved-only promotion", "running")
    output = run_commands([[sys.executable, "scripts/promote_catalog_candidates.py", "--approved-only"]])
    update_pipeline_stage("Approved-only promotion", "complete")
    return output


def reinvestigate_updates_job():
    update_pipeline_stage("Agent validation/approval", "running", "Rechecking existing N/A fields")
    output = run_commands([[sys.executable, "scripts/reinvestigate_catalog_updates.py"]])
    update_pipeline_stage("Agent validation/approval", "complete", "Existing records rechecked for new official values")
    update_pipeline_stage("SQLite/JSON rebuild", "complete")
    update_pipeline_stage("Validation/testing", "complete")
    update_pipeline_stage("Git diff review", "complete", "Review changed files before committing")
    return output


def full_pipeline_job(batch_size):
    update_pipeline_stage("Agent validation/approval", "running", f"Full automated pipeline, batch size {batch_size}")
    report = run_pipeline(batch_size=batch_size, delay=0.05)
    if report["status"] != "complete":
        update_pipeline_stage("Agent validation/approval", "failed", f"Pipeline failed; see {PIPELINE_REPORT}")
        raise RuntimeError(f"Full automated pipeline failed; see {PIPELINE_REPORT}")
    update_pipeline_stage("Agent validation/approval", "complete", f"Processed {sum(batch['checked'] for batch in report['batches'])} candidate(s)")
    update_pipeline_stage("Approved-only promotion", "complete")
    update_pipeline_stage("SQLite/JSON rebuild", "complete")
    update_pipeline_stage("Validation/testing", "complete")
    update_pipeline_stage("Git diff review", "complete", "Diff whitespace check passed; review changed files before committing")
    return (
        f"Full automated pipeline {report['status']}.\n"
        f"Checked {sum(batch['checked'] for batch in report['batches'])} candidate(s).\n"
        f"Approved {sum(batch['approved'] for batch in report['batches'])}; "
        f"rejected {sum(batch['rejected'] for batch in report['batches'])}; "
        f"unresolved {sum(batch['unresolved'] for batch in report['batches'])}.\n"
        f"Source audit: {report['source_audit']['markdown']}\n"
        f"Pipeline report: {PIPELINE_REPORT}"
    )


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
                                   "investigation": investigation_counts(),
                                   "candidates": list_candidates(), "git_changes": len(git.stdout.splitlines()),
                                   "pipeline": load_pipeline_state(), "job": JOBS.snapshot()})
        if path == "/api/review":
            if not self.authorized(): return self.send_json({"error": "Unauthorized"}, HTTPStatus.FORBIDDEN)
            return self.send_json(agent_review_payload())
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
            if path == "/api/review/decision":
                return self.send_json(save_review_decision(data["candidate_id"], data["decision"], data["signature"]))
            if path == "/api/jobs":
                kind, args = data.get("kind"), data.get("args") or {}
                if kind == "discover":
                    minutes = int(args.get("minutes", 30))
                    if minutes not in {15, 30, 60, 120, 240}: raise ValueError("Unsupported time budget")
                    session_id = datetime.now(timezone.utc).strftime("local-%Y%m%dT%H%M%SZ")
                    output = ROOT / "database" / "local" / "sessions" / session_id
                    JOBS.start(kind, lambda: discovery_job_with_session(minutes, session_id, output),
                               {"output_dir": str(output), "time_budget_minutes": minutes})
                elif kind == "export_queue": JOBS.start(kind, export_queue_job)
                elif kind == "export_batch":
                    limit = int(args.get("limit", 25))
                    if limit not in {25, 50, 75, 100}: raise ValueError("Unsupported batch size")
                    JOBS.start(kind, lambda: export_batch_job(limit))
                elif kind == "automated_investigate":
                    limit = int(args.get("limit", 50))
                    if limit not in {25, 50, 100, 200}: raise ValueError("Unsupported automated batch size")
                    JOBS.start(kind, lambda: automated_investigation_job(limit))
                elif kind == "full_pipeline":
                    batch_size = int(args.get("batch_size", 100))
                    if batch_size not in {50, 100, 200}: raise ValueError("Unsupported pipeline batch size")
                    JOBS.start(kind, lambda: full_pipeline_job(batch_size))
                elif kind == "validate_results": JOBS.start(kind, validate_results_job)
                elif kind == "auto_approve": JOBS.start(kind, auto_approve_job)
                elif kind == "promote": JOBS.start(kind, promote_job)
                elif kind == "reinvestigate_updates": JOBS.start(kind, reinvestigate_updates_job)
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
