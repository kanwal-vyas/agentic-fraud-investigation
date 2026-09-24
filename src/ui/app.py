import os
import sys
import json
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from src.agent.orchestrator import AgenticFraudInvestigator
from src.models.agent import InvestigationTrigger, TriggerType
from src.mcp.server import TigerGraphMCPServer

app = FastAPI(
    title="TigerGraph Autonomous Fraud Investigation Console",
    description="Interactive Agentic Fraud Investigation UI for Hackathon Submission",
    version="1.0.0"
)

# Load cached evaluation results if available
EVAL_RESULTS_PATH = os.path.join("artifacts", "benchmark", "evaluation_results.json")

def load_evaluation_data() -> Dict[str, Any]:
    if os.path.exists(EVAL_RESULTS_PATH):
        with open(EVAL_RESULTS_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
            return {r["case_id"]: r for r in records}
    return {}

@app.get("/api/cases", response_class=JSONResponse)
def get_all_cases():
    data = load_evaluation_data()
    return list(data.values())

@app.get("/api/case/{case_id}", response_class=JSONResponse)
def get_case(case_id: str):
    data = load_evaluation_data()
    if case_id not in data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found in evaluation artifacts.")
    return data[case_id]

@app.get("/", response_class=HTMLResponse)
def index_page():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TigerGraph Agentic Fraud Investigation</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg-0:#080c14;--bg-1:#0d1117;--bg-2:#161b22;--bg-3:#1c2333;--bg-4:#242d3d;
  --tx-0:#e6edf3;--tx-1:#c9d1d9;--tx-2:#8b949e;--tx-3:#6e7681;
  --red:#da3633;--red-dim:rgba(218,54,51,.12);
  --amber:#d29922;--amber-dim:rgba(210,153,34,.12);
  --green:#3fb950;--green-dim:rgba(63,185,80,.12);
  --blue:#58a6ff;--blue-dim:rgba(88,166,255,.08);
  --purple:#bc8cff;--purple-dim:rgba(188,140,255,.12);
  --cyan:#39d2c0;--cyan-dim:rgba(57,210,192,.1);
  --border:#21262d;--border-emphasis:#30363d;
  --font-sans:'Inter',system-ui,-apple-system,sans-serif;
  --font-mono:'JetBrains Mono','Consolas',monospace;
  --radius:6px;
}
html,body{height:100%;overflow:hidden;background:var(--bg-0);color:var(--tx-0);font-family:var(--font-sans);font-size:13px;line-height:1.5;-webkit-font-smoothing:antialiased}

/* === SYSTEM BAR === */
.sysbar{height:40px;background:var(--bg-1);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:16px;flex-shrink:0;z-index:100}
.sysbar-brand{font-weight:600;font-size:13px;color:var(--tx-1);letter-spacing:.3px;display:flex;align-items:center;gap:8px}
.sysbar-brand svg{width:16px;height:16px;fill:var(--cyan)}
.sysbar-sep{width:1px;height:20px;background:var(--border)}
.sysbar-tag{font-size:11px;font-weight:500;padding:2px 8px;border-radius:10px;letter-spacing:.3px}
.sysbar-tag.live{background:var(--green-dim);color:var(--green);border:1px solid rgba(63,185,80,.25)}
.sysbar-tag.info{background:var(--blue-dim);color:var(--blue);border:1px solid rgba(88,166,255,.15)}
.sysbar-right{margin-left:auto;display:flex;align-items:center;gap:12px;font-size:11px;color:var(--tx-3)}

/* === LAYOUT === */
.layout{display:flex;height:calc(100vh - 40px)}

/* === CASE NAV === */
.case-nav{width:220px;background:var(--bg-1);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0}
.case-nav-head{padding:12px 14px 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:var(--tx-3)}
.case-scroll{flex:1;overflow-y:auto;padding:0 6px 6px}
.case-scroll::-webkit-scrollbar{width:4px}
.case-scroll::-webkit-scrollbar-thumb{background:var(--border-emphasis);border-radius:4px}
.ci{padding:8px 10px;border-radius:var(--radius);cursor:pointer;margin-bottom:2px;display:flex;align-items:center;justify-content:space-between;transition:background .15s}
.ci:hover{background:var(--bg-2)}
.ci.active{background:var(--bg-3);box-shadow:inset 2px 0 0 var(--blue)}
.ci-id{font-weight:600;font-size:12px;font-family:var(--font-mono)}
.ci-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.ci-dot.fraud{background:var(--red)}.ci-dot.benign{background:var(--green)}.ci-dot.uncertain{background:var(--amber)}

/* === MAIN === */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* === CASE HEADER === */
.case-head{padding:16px 24px 12px;background:var(--bg-1);border-bottom:1px solid var(--border);flex-shrink:0}
.case-head-top{display:flex;align-items:baseline;gap:14px;margin-bottom:6px}
.case-head-id{font-size:22px;font-weight:700;font-family:var(--font-mono);letter-spacing:-.5px}
.case-head-label{font-size:12px;font-weight:500;padding:3px 10px;border-radius:10px}
.case-head-label.fraud{background:var(--red-dim);color:var(--red)}.case-head-label.benign{background:var(--green-dim);color:var(--green)}.case-head-label.uncertain{background:var(--amber-dim);color:var(--amber)}
.case-head-meta{display:flex;gap:20px;font-size:12px;color:var(--tx-2)}
.case-head-meta span{display:flex;align-items:center;gap:4px}
.case-head-meta .mono{font-family:var(--font-mono);color:var(--tx-1)}

/* === WORKSPACE TABS === */
.ws-tabs{display:flex;background:var(--bg-1);border-bottom:1px solid var(--border);padding:0 24px;flex-shrink:0}
.ws-tab{padding:10px 16px;font-size:12px;font-weight:500;color:var(--tx-3);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;background:none;border-top:none;border-left:none;border-right:none}
.ws-tab:hover{color:var(--tx-1)}
.ws-tab.active{color:var(--tx-0);border-bottom-color:var(--blue)}

/* === WORKSPACE CONTENT === */
.ws-body{flex:1;overflow-y:auto;overflow-x:hidden}
.ws-body::-webkit-scrollbar{width:6px}
.ws-body::-webkit-scrollbar-thumb{background:var(--border-emphasis);border-radius:4px}
.ws-panel{display:none;padding:20px 24px}
.ws-panel.active{display:block}

/* === INVESTIGATION TAB === */
.inv-layout{display:grid;grid-template-columns:280px 1fr 260px;gap:20px;min-height:600px}
.inv-col{display:flex;flex-direction:column;gap:16px}

/* Agent Workflow */
.trigger-block{background:var(--bg-2);border-radius:var(--radius);padding:14px 16px;border-left:3px solid var(--amber)}
.trigger-type{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--amber);margin-bottom:4px}
.trigger-text{font-size:12px;color:var(--tx-1);font-style:italic;line-height:1.6}

.step{position:relative;padding:10px 14px;background:var(--bg-2);border-radius:var(--radius);cursor:pointer;transition:background .15s}
.step:hover{background:var(--bg-3)}
.step-num{font-size:10px;font-weight:600;color:var(--blue);font-family:var(--font-mono);margin-bottom:2px}
.step-tool{font-size:12px;font-weight:600;color:var(--tx-0);margin-bottom:2px}
.step-brief{font-size:11px;color:var(--tx-2);display:flex;align-items:center;gap:6px}
.step-brief .live-dot{width:5px;height:5px;border-radius:50%;background:var(--green);display:inline-block}
.step-detail{display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;color:var(--tx-2);line-height:1.6}
.step.open .step-detail{display:block}
.step-connector{width:1px;height:12px;background:var(--border-emphasis);margin:0 auto}

/* Graph Canvas */
.graph-wrap{background:var(--bg-2);border-radius:var(--radius);border:1px solid var(--border);flex:1;min-height:0;position:relative;overflow:hidden}
.graph-wrap canvas{display:block}
.graph-title{position:absolute;top:10px;left:14px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--tx-3);z-index:2}
.graph-legend{position:absolute;bottom:10px;left:14px;display:flex;gap:10px;z-index:2}
.graph-legend span{font-size:10px;color:var(--tx-3);display:flex;align-items:center;gap:4px}
.graph-legend .ldot{width:8px;height:8px;border-radius:50%}

/* Decision Rail */
.decision-section{margin-bottom:16px}
.decision-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--tx-3);margin-bottom:6px}
.decision-value{font-size:14px;font-weight:700;margin-bottom:4px}
.decision-sub{font-size:11px;color:var(--tx-2);line-height:1.5}
.decision-divider{height:1px;background:var(--border);margin:12px 0}
.approval-flow{display:flex;flex-direction:column;gap:0;align-items:flex-start}
.af-step{display:flex;align-items:center;gap:8px;font-size:11px;padding:4px 0}
.af-icon{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0}
.af-icon.done{background:var(--green-dim);color:var(--green)}.af-icon.pending{background:var(--amber-dim);color:var(--amber)}.af-icon.wait{background:var(--bg-3);color:var(--tx-3)}
.af-line{width:1px;height:10px;background:var(--border-emphasis);margin-left:9px}
.confidence-bar-wrap{margin-top:12px}
.confidence-bar-bg{height:4px;background:var(--bg-4);border-radius:2px;overflow:hidden}
.confidence-bar-fill{height:100%;border-radius:2px;transition:width .4s}

/* === REASONING TAB === */
.reason-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.reason-full{grid-column:1/-1}
.signal-group{margin-bottom:16px}
.signal-head{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.signal-head .sdot{width:6px;height:6px;border-radius:50%}
.signal-item{font-size:12px;color:var(--tx-1);padding:6px 0;border-bottom:1px solid var(--border);line-height:1.5}
.signal-item:last-child{border-bottom:none}
.hist-case{padding:10px 14px;background:var(--bg-2);border-radius:var(--radius);margin-bottom:8px;cursor:pointer;transition:background .15s}
.hist-case:hover{background:var(--bg-3)}
.hist-case-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.hist-case-id{font-weight:600;font-family:var(--font-mono);font-size:12px}
.hist-case-tag{font-size:10px;font-weight:500;padding:2px 6px;border-radius:8px}
.hist-case-tag.fraud{background:var(--red-dim);color:var(--red)}.hist-case-tag.cleared{background:var(--green-dim);color:var(--green)}
.hist-case-detail{font-size:11px;color:var(--tx-2);display:none;margin-top:6px;padding-top:6px;border-top:1px solid var(--border);line-height:1.5}
.hist-case.open .hist-case-detail{display:block}
.hist-case-meta{font-size:11px;color:var(--tx-2);display:flex;gap:12px}
.relevance-bar{width:60px;height:4px;background:var(--bg-4);border-radius:2px;overflow:hidden;display:inline-block;vertical-align:middle}
.relevance-fill{height:100%;background:var(--blue);border-radius:2px}

/* metrics row */
.metrics-row{display:flex;gap:24px;padding:16px 0;border-bottom:1px solid var(--border);margin-bottom:16px}
.metric{display:flex;flex-direction:column;gap:2px}
.metric-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--tx-3)}
.metric-value{font-size:18px;font-weight:700}

/* === COMPLIANCE TAB === */
.compliance-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}
.compliance-section{background:var(--bg-2);border-radius:var(--radius);padding:16px}
.comp-head{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--tx-3);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.policy-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px}
.policy-check{color:var(--green);font-size:11px}
.lifecycle-flow{display:flex;flex-direction:column;gap:0}
.lf-step{padding:6px 0;font-size:12px;display:flex;align-items:center;gap:8px}
.lf-step .lf-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.lf-step .lf-dot.done{background:var(--green)}.lf-step .lf-dot.current{background:var(--amber);box-shadow:0 0 6px var(--amber)}.lf-step .lf-dot.future{background:var(--bg-4)}
.lf-line{width:1px;height:8px;background:var(--border-emphasis);margin-left:3.5px}
.wb-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px}
.wb-check{color:var(--green);font-size:11px}
.sar-status{font-size:16px;font-weight:600;margin-bottom:8px}
.sar-detail{font-size:11px;color:var(--tx-2);line-height:1.6}
.comp-note{margin-top:12px;padding:10px;background:var(--bg-3);border-radius:var(--radius);font-size:11px;color:var(--tx-2);line-height:1.5;border-left:2px solid var(--amber)}

/* Evidence panel in reasoning */
.evidence-section{background:var(--bg-2);border-radius:var(--radius);padding:16px}
.ev-head{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--tx-3);margin-bottom:10px}
.ev-item{padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--tx-1);line-height:1.5}
.ev-item:last-child{border-bottom:none}
.ev-source{font-size:10px;color:var(--tx-3);font-family:var(--font-mono);margin-top:2px}

@media(max-width:1280px){
  .inv-layout{grid-template-columns:240px 1fr 240px}
  .case-nav{width:200px}
}

/* Graph SVG Elements */
.svg-edge{stroke:var(--border-emphasis);stroke-width:1.5px;transition:stroke 0.2s}
.svg-edge.interactive{cursor:pointer}
.svg-edge:hover{stroke:var(--tx-2);stroke-width:2.5px}
.svg-edge-label-bg{fill:var(--bg-2)}
.svg-edge-label{fill:var(--tx-3);font-size:9px;font-weight:500;font-family:var(--font-sans);text-anchor:middle;dominant-baseline:central;pointer-events:none}
.svg-node{cursor:pointer}
.svg-node-circle{stroke-width:2px;transition:all 0.2s}
.svg-node:hover .svg-node-circle{filter:brightness(1.3);stroke-width:3px}
.svg-node.selected .svg-node-circle{stroke:var(--tx-0) !important;stroke-dasharray:4;animation:dash 10s linear infinite}
@keyframes dash { to { stroke-dashoffset: 100; } }
.svg-node-label{fill:var(--tx-0);font-size:11px;font-family:var(--font-mono);font-weight:500;text-anchor:middle;pointer-events:none}
.svg-node-sub{fill:var(--tx-3);font-size:9px;font-family:var(--font-sans);text-anchor:middle;pointer-events:none}

/* Graph Tooltip */
.graph-tooltip{position:absolute;background:var(--bg-2);border:1px solid var(--border-emphasis);border-radius:var(--radius);padding:10px 14px;color:var(--tx-0);font-size:12px;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:100;box-shadow:0 8px 24px rgba(0,0,0,0.5);transform:translate(-50%,-100%);margin-top:-10px;white-space:nowrap}
.tt-type{font-size:10px;color:var(--tx-3);text-transform:uppercase;margin-bottom:4px;font-weight:600}
.tt-id{font-size:13px;font-family:var(--font-mono);font-weight:600;margin-bottom:6px}
.tt-meta{display:flex;flex-direction:column;gap:2px;font-size:11px;color:var(--tx-1)}

/* Entity Details Panel (floating below) */
.entity-details{background:var(--bg-1);border-top:1px solid var(--border);padding:16px;min-height:140px;display:flex;flex-direction:column;position:absolute;bottom:0;left:0;right:0;z-index:50}
.ed-empty{color:var(--tx-3);font-size:12px;font-style:italic;margin:auto;text-align:center}
.ed-content{display:none;flex-direction:column;height:100%}
.ed-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.ed-type{font-size:10px;font-weight:600;color:var(--tx-3);text-transform:uppercase;letter-spacing:.5px}
.ed-id{font-size:16px;font-weight:600;font-family:var(--font-mono);color:var(--tx-0);margin-top:2px}
.ed-body{display:flex;gap:32px;font-size:12px}
.ed-col{display:flex;flex-direction:column;gap:8px;flex:1}
.ed-lbl{color:var(--tx-3)}
.ed-val{color:var(--tx-1)}
.ed-nav-btn{background:var(--bg-2);border:1px solid var(--border);color:var(--tx-1);padding:4px 10px;border-radius:var(--radius);font-size:11px;cursor:pointer;transition:background 0.1s;display:inline-block;margin-top:8px}
.ed-nav-btn:hover{background:var(--bg-3);color:var(--tx-0)}

/* Auth States */
.auth-title{font-size:11px;font-weight:600}
.text-red{color:var(--red)}
.text-green{color:var(--green)}
.text-amber{color:var(--amber)}
</style>
</head>
<body>

<!-- SYSTEM BAR -->
<div class="sysbar">
  <div class="sysbar-brand">
    <svg viewBox="0 0 24 24"><polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="12" y1="2" x2="12" y2="22" stroke="currentColor" stroke-width="1"/><line x1="2" y1="8.5" x2="22" y2="8.5" stroke="currentColor" stroke-width="1"/><line x1="2" y1="15.5" x2="22" y2="15.5" stroke="currentColor" stroke-width="1"/></svg>
    TigerGraph Agentic Investigation
  </div>
  <div class="sysbar-sep"></div>
  <span class="sysbar-tag" id="sys-live">Loading...</span>
  <span class="sysbar-tag info" id="sys-graph">FraudGraph</span>
  <div class="sysbar-right">
    <span id="sys-count">—</span>
  </div>
</div>

<!-- LAYOUT -->
<div class="layout">

  <!-- CASE NAV -->
  <div class="case-nav">
    <div class="case-nav-head">Investigations</div>
    <div class="case-scroll" id="case-list"></div>
  </div>

  <!-- MAIN -->
  <div class="main">
    <div class="case-head" id="case-head">
      <div class="case-head-top">
        <span class="case-head-id" id="ch-id">—</span>
        <span class="case-head-label" id="ch-label">—</span>
      </div>
      <div class="case-head-meta" id="ch-meta"></div>
    </div>

    <div class="ws-tabs">
      <button class="ws-tab active" data-tab="t-inv">Investigation</button>
      <button class="ws-tab" data-tab="t-reason">Reasoning</button>
      <button class="ws-tab" data-tab="t-comply">Compliance</button>
    </div>

    <div class="ws-body">
      <div class="ws-panel active" id="t-inv"></div>
      <div class="ws-panel" id="t-reason"></div>
      <div class="ws-panel" id="t-comply"></div>
    </div>
  </div>
</div>

<script>
let allCases=[], activeId='HHG-003', selectedNodeId=null, svgNodes=[], currentCase=null;

async function init(){
  try{
    const r=await fetch('/api/cases');
    allCases=await r.json();
    const liveCount=allCases.filter(c=>c.written_to_graph).length;
    document.getElementById('sys-live').textContent=liveCount===allCases.length?'LIVE':'PARTIAL';
    document.getElementById('sys-live').className='sysbar-tag '+(liveCount===allCases.length?'live':'info');
    document.getElementById('sys-count').textContent=allCases.length+'/20 benchmark cases';
    renderNav();
    selectCase(activeId);
  }catch(e){
    document.getElementById('case-list').innerHTML=`<div style="padding:20px;color:var(--red);word-break:break-all">${e.message}<br><br>${e.stack}</div>`;
  }
}

function renderNav(){
  const el=document.getElementById('case-list');
  el.innerHTML='';
  allCases.forEach(c=>{
    const d=document.createElement('div');
    d.className='ci'+(c.case_id===activeId?' active':'');
    d.onclick=()=>selectCase(c.case_id);
    let dc='uncertain';
    if(c.fraud_assessment==='likely_fraud')dc='fraud';
    if(c.fraud_assessment==='likely_benign')dc='benign';
    d.innerHTML=`<span class="ci-id">${c.case_id}</span><span class="ci-dot ${dc}"></span>`;
    el.appendChild(d);
  });
}

function switchTab(tabId){
  document.querySelectorAll('.ws-tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.ws-panel').forEach(p=>p.classList.remove('active'));
  document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

document.querySelectorAll('.ws-tab').forEach(t=>{
  t.addEventListener('click',()=>switchTab(t.dataset.tab));
});

function selectCase(id){
  activeId=id;
  renderNav();
  const c=allCases.find(x=>x.case_id===id); currentCase=c;
  if(!c)return;

  // Header
  document.getElementById('ch-id').textContent=c.case_id;
  const lbl=document.getElementById('ch-label');
  let la='uncertain',lt=c.fraud_assessment.replace(/_/g,' ').toUpperCase();
  if(c.fraud_assessment==='likely_fraud'){la='fraud'}
  if(c.fraud_assessment==='likely_benign'){la='benign'}
  lbl.className='case-head-label '+la;lbl.textContent=lt;
  document.getElementById('ch-meta').innerHTML=
    `<span>Customer <span class="mono">${c.customer_id}</span></span>`+
    `<span>Card <span class="mono">${c.card_id}</span></span>`+
    `<span>TXN <span class="mono">${c.transaction_id}</span></span>`+
    `<span>${c.written_to_graph?'<span style="color:var(--green)">&#9679;</span> Live Writeback':'<span style="color:var(--tx-3)">&#9675;</span> Offline'}</span>`;

  renderInvestigation(c);
  renderReasoning(c);
  renderCompliance(c);
  switchTab('t-inv');
}

/* ===== TAB 1: INVESTIGATION ===== */
function renderInvestigation(c){
  const el=document.getElementById('t-inv');

  // Parse a short result from result_summary
  function briefResult(s){
    const m=s.match(/returned (\\d+) evidence items/);
    const k=s.match(/Key findings: (.{0,80})/);
    return (m?m[1]+' evidence items':'')+(k?' — '+k[1]+'…':'');
  }

  // Build steps
  let stepsHtml=`
    <div class="trigger-block">
      <div class="trigger-type">${c.trigger.trigger_type.replace(/_/g,' ')}</div>
      <div class="trigger-text">${c.trigger.trigger_text}</div>
    </div>`;

  c.investigation_steps.forEach((s,i)=>{
    stepsHtml+=`<div class="step-connector"></div>
    <div class="step" onclick="this.classList.toggle('open')">
      <div class="step-num">STEP ${String(s.step_number).padStart(2,'0')}</div>
      <div class="step-tool">${s.tool.replace(/_/g,' ')}</div>
      <div class="step-brief"><span class="live-dot"></span> ${briefResult(s.result_summary)}</div>
      <div class="step-detail">${s.result_summary}<br><br><em style="color:var(--tx-3)">Reason: ${s.reason}</em></div>
    </div>`;
  });

  // Decision rail
  let assessClass='uncertain';
  if(c.fraud_assessment==='likely_fraud')assessClass='fraud';
  if(c.fraud_assessment==='likely_benign')assessClass='benign';
  let nbaColor=c.recommended_nba==='BLOCK_CARD'?'var(--red)':c.recommended_nba==='VERIFY_WITH_CUSTOMER'?'var(--amber)':'var(--tx-0)';
  let confPct=Math.round(c.confidence*100);
  let confColor=confPct>=70?'var(--red)':confPct>=50?'var(--amber)':'var(--tx-2)';
  let uncColor=c.uncertainty_level==='high'?'var(--amber)':c.uncertainty_level==='low'?'var(--green)':'var(--tx-1)';

  let decisionHtml=`
    <div class="decision-section">
      <div class="decision-label">Assessment</div>
      <div class="decision-value" style="color:${assessClass==='fraud'?'var(--red)':assessClass==='benign'?'var(--green)':'var(--amber)'}">${c.fraud_assessment.replace(/_/g,' ').toUpperCase()}</div>
      <div class="confidence-bar-wrap">
        <div style="font-size:10px;color:var(--tx-3);margin-bottom:3px">Confidence ${confPct}%</div>
        <div class="confidence-bar-bg"><div class="confidence-bar-fill" style="width:${confPct}%;background:${confColor}"></div></div>
      </div>
      <div style="font-size:11px;color:${uncColor};margin-top:6px">Uncertainty: ${c.uncertainty_level.toUpperCase()}</div>
    </div>
    <div class="decision-divider"></div>
    <div class="decision-section">
      <div class="decision-label">Next Best Action</div>
      <div class="decision-value" style="color:${nbaColor}">${c.recommended_nba.replace(/_/g,' ')}</div>
      <div class="decision-sub">Target: ${c.card_id}</div>
    </div>
    <div class="decision-divider"></div>
    <div class="decision-section">
      <div class="decision-label">Authorization</div>
      <div class="approval-flow">
        <div class="af-step"><div class="af-icon done">&#10003;</div><span class="auth-title">Agent Recommendation</span></div>
        <div class="af-line"></div>
        ${c.approval_required 
            ? '<div class="af-step"><div class="af-icon pending">!</div><span class="auth-title text-amber">L1 Human Approval Required</span></div>' 
            : '<div class="af-step"><div class="af-icon done">&#10003;</div><span class="auth-title text-green">Auto-Approved</span></div>'}
        <div class="af-line"></div>
        ${c.execution_status === 'EXECUTED' 
            ? '<div class="af-step"><div class="af-icon done">&#10003;</div><span class="auth-title text-green">Action Executed</span></div>'
            : c.execution_status === 'DENIED'
            ? '<div class="af-step"><div class="af-icon wait" style="color:var(--red)">&#10005;</div><span class="auth-title text-red">Execution Denied</span></div>'
            : c.approval_required
            ? '<div class="af-step"><div class="af-icon wait">○</div><span class="auth-title" style="color:var(--tx-2)">Pending Approval</span></div>'
            : '<div class="af-step"><div class="af-icon wait">○</div><span class="auth-title" style="color:var(--tx-2)">Ready for Execution</span></div>'}
      </div>
    </div>
    <div class="decision-divider"></div>
    <div class="decision-section">
      <div class="decision-label">Lifecycle</div>
      <div style="font-size:12px;font-weight:500;color:var(--tx-1)">${c.lifecycle_state.replace(/_/g,' ')}</div>
    </div>`;

  el.innerHTML=`
  <div class="inv-layout">
    <div class="inv-col">${stepsHtml}</div>
    <div class="inv-col" style="min-height:0">
      <div class="graph-wrap" id="graph-canvas-wrap" style="padding-bottom:140px;">
        <div class="graph-title">TigerGraph Investigation Subgraph</div>
        <svg id="main-svg" style="position:absolute;top:0;left:0;width:100%;height:100%;"></svg>
        <div class="graph-tooltip" id="graph-tooltip"></div>
        <div class="graph-legend">
          <span><span class="ldot" style="background:var(--blue)"></span>Customer</span>
          <span><span class="ldot" style="background:var(--cyan)"></span>Card</span>
          <span><span class="ldot" style="background:var(--amber)"></span>Transaction</span>
          <span><span class="ldot" style="background:var(--red)"></span>Case</span>
          <span><span class="ldot" style="background:var(--purple)"></span>History</span>
        </div>
        <div class="entity-details">
          <div class="ed-empty" id="ed-empty">Select a node or edge in the graph to view details.</div>
          <div class="ed-content" id="ed-content">
            <div class="ed-head">
              <div>
                <div class="ed-type" id="ed-type">Type</div>
                <div class="ed-id" id="ed-id">ID</div>
              </div>
            </div>
            <div class="ed-body" id="ed-body"></div>
          </div>
        </div>
      </div>
    </div>
    <div class="inv-col">${decisionHtml}</div>
  </div>`;

  requestAnimationFrame(()=>drawGraph(c));
}

/* ===== GRAPH DRAWING ===== */
function drawGraph(c){
  const wrap=document.getElementById('graph-canvas-wrap');
  const svg=document.getElementById('main-svg');
  if(!wrap||!svg)return;
  
  const W=wrap.clientWidth, H=wrap.clientHeight;
  svg.innerHTML='';
  svgNodes=[];
  let svgEdges=[];
  
  const cx=W/2, cy=(H-140)/2; // offset for details pane
  
  const startX = cx; 
  const startY = cy - 80;
  const spacingY = 90;

  svgNodes.push({id:c.customer_id,label:c.customer_id,type:'Customer',x:startX,y:startY,r:24,color:'#58a6ff'});
  svgNodes.push({id:c.card_id,label:c.card_id,type:'Card',x:startX,y:startY+spacingY,r:20,color:'#39d2c0'});
  svgNodes.push({id:String(c.transaction_id),label:'$'+(c.sar_data?c.sar_data.exposure_usd.toFixed(0):'?'),type:'Transaction',x:startX,y:startY+spacingY*2,r:18,color:'#d29922'});
  
  // Case node offset to the left of the transaction
  svgNodes.push({id:c.case_id,label:c.case_id,type:'Case',x:startX-120,y:startY+spacingY*1.5,r:20,color:'#da3633'});
  
  svgEdges.push({from:c.customer_id,to:c.card_id,label:'HAS_CARD'});
  svgEdges.push({from:c.card_id,to:String(c.transaction_id),label:'USED_FOR'});
  svgEdges.push({from:String(c.transaction_id),to:c.case_id,label:'INVOLVES'});

  if(c.historical_evidence&&c.historical_evidence.length>0){
    const maxH=c.historical_evidence.length;
    // Historical cases branch out to the RIGHT
    const hStartX = startX + 180;
    const hSpacingY = 70;
    // Vertically center them relative to the main column
    const hStartY = startY + spacingY - ((maxH-1) * hSpacingY) / 2;
    for(let i=0;i<maxH;i++){
      const h=c.historical_evidence[i];
      const hx = hStartX;
      const hy = hStartY + (i * hSpacingY);
      svgNodes.push({id:h.case_id,label:h.case_id,type:'History',x:hx,y:hy,r:14,color:'#bc8cff'});
      svgEdges.push({from:c.customer_id,to:h.case_id,label:'PRIOR'});
    }
  }

  const nodeMap={};
  svgNodes.forEach(n=>nodeMap[n.id]=n);

  svgEdges.forEach(e=>{
    const n1=nodeMap[e.from],n2=nodeMap[e.to];
    if(!n1||!n2)return;
    const mx=(n1.x+n2.x)/2,my=(n1.y+n2.y)/2;
    
    const g=document.createElementNS('http://www.w3.org/2000/svg','g');
    g.style.cursor='pointer';
    
    const line=document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1',n1.x);line.setAttribute('y1',n1.y);
    line.setAttribute('x2',n2.x);line.setAttribute('y2',n2.y);
    line.setAttribute('class','svg-edge');
    
    const hit=document.createElementNS('http://www.w3.org/2000/svg','line');
    hit.setAttribute('x1',n1.x);hit.setAttribute('y1',n1.y);
    hit.setAttribute('x2',n2.x);hit.setAttribute('y2',n2.y);
    hit.setAttribute('stroke','transparent');hit.setAttribute('stroke-width','15');
    
    const text=document.createElementNS('http://www.w3.org/2000/svg','text');
    text.setAttribute('x',mx);text.setAttribute('y',my);
    text.setAttribute('class','svg-edge-label');
    text.textContent=e.label;
    
    const bg=document.createElementNS('http://www.w3.org/2000/svg','rect');
    const tw=e.label.length*6;
    bg.setAttribute('x',mx-tw/2);bg.setAttribute('y',my-8);
    bg.setAttribute('width',tw);bg.setAttribute('height',16);
    bg.setAttribute('class','svg-edge-label-bg');bg.setAttribute('rx',3);
    
    g.appendChild(line);g.appendChild(hit);g.appendChild(bg);g.appendChild(text);
    
    g.addEventListener('mouseenter',(ev)=>showEdgeTooltip(ev,e));
    g.addEventListener('mouseleave',hideTooltip);
    g.addEventListener('click',()=>showEdgeDetails(e));
    
    svg.appendChild(g);
  });

  svgNodes.forEach(n=>{
    const g=document.createElementNS('http://www.w3.org/2000/svg','g');
    g.setAttribute('class','svg-node');
    g.setAttribute('id','node-'+n.id);
    g.setAttribute('transform',`translate(${n.x}, ${n.y})`);
    
    const bg=document.createElementNS('http://www.w3.org/2000/svg','circle');
    bg.setAttribute('r',n.r);bg.setAttribute('fill',n.color);bg.setAttribute('fill-opacity','0.15');
    
    const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');
    circle.setAttribute('class','svg-node-circle');
    circle.setAttribute('r',n.r);circle.setAttribute('stroke',n.color);circle.setAttribute('fill','transparent');
    
    const label=document.createElementNS('http://www.w3.org/2000/svg','text');
    label.setAttribute('class','svg-node-label');label.setAttribute('y',4);
    let disp=n.label;
    if(disp.length>8&&n.type!=='Transaction')disp=disp.substring(0,6)+'..';
    label.textContent=disp;
    
    const sub=document.createElementNS('http://www.w3.org/2000/svg','text');
    sub.setAttribute('class','svg-node-sub');sub.setAttribute('y',n.r+14);
    sub.textContent=n.type;
    
    g.appendChild(bg);g.appendChild(circle);g.appendChild(label);g.appendChild(sub);
    
    g.addEventListener('mouseenter',(ev)=>showNodeTooltip(ev,n));
    g.addEventListener('mouseleave',hideTooltip);
    g.addEventListener('click',()=>selectNode(n.id));
    
    svg.appendChild(g);
  });
}

function showNodeTooltip(ev, n) {
  const tt=document.getElementById('graph-tooltip');
  const wrap=document.getElementById('graph-canvas-wrap');
  const rect=wrap.getBoundingClientRect();
  tt.innerHTML=`<div class="tt-type">${n.type}</div><div class="tt-id" style="color:${n.color}">${n.label}</div><div class="tt-meta">Click to view details</div>`;
  tt.style.left=(ev.clientX-rect.left)+'px';
  tt.style.top=(ev.clientY-rect.top-15)+'px';
  tt.style.opacity='1';
}

function showEdgeTooltip(ev, e) {
  const tt=document.getElementById('graph-tooltip');
  const wrap=document.getElementById('graph-canvas-wrap');
  const rect=wrap.getBoundingClientRect();
  tt.innerHTML=`<div class="tt-type">Relationship</div><div class="tt-id" style="color:var(--tx-1)">${e.from} &rarr; ${e.to}</div><div class="tt-meta">${e.label}</div>`;
  tt.style.left=(ev.clientX-rect.left)+'px';
  tt.style.top=(ev.clientY-rect.top-15)+'px';
  tt.style.opacity='1';
}

function hideTooltip() {
  document.getElementById('graph-tooltip').style.opacity='0';
}

function selectNode(id) {
  const n=svgNodes.find(x=>x.id===id);
  if(!n)return;
  selectedNodeId=id;
  document.querySelectorAll('.svg-node').forEach(el=>el.classList.remove('selected'));
  const el=document.getElementById('node-'+id);
  if(el)el.classList.add('selected');
  showDetails(n);
}

function showEdgeDetails(e) {
  document.querySelectorAll('.svg-node').forEach(el=>el.classList.remove('selected'));
  selectedNodeId=null;
  document.getElementById('ed-empty').style.display='none';
  document.getElementById('ed-content').style.display='flex';
  document.getElementById('ed-type').textContent='Relationship';
  document.getElementById('ed-id').innerHTML=`<span style="color:var(--tx-3)">${e.from}</span> &rarr; <span style="color:var(--tx-3)">${e.to}</span>`;
  document.getElementById('ed-body').innerHTML=`
    <div class="ed-col">
      <div><span class="ed-lbl">Label:</span> <span class="ed-val">${e.label}</span></div>
    </div>
  `;
}

function hideDetails() {
  document.getElementById('ed-empty').style.display='block';
  document.getElementById('ed-content').style.display='none';
  document.querySelectorAll('.svg-node').forEach(el=>el.classList.remove('selected'));
}

function showDetails(n) {
  document.getElementById('ed-empty').style.display='none';
  document.getElementById('ed-content').style.display='flex';
  document.getElementById('ed-type').textContent=n.type;
  document.getElementById('ed-id').textContent=n.id;
  document.getElementById('ed-id').style.color=n.color;
  
  const c=currentCase;
  if(!c)return;
  
  let bodyHtml='<div class="ed-col">';
  if(n.type==='Customer'){
    bodyHtml+=`<div><span class="ed-lbl">Total Cards:</span> <span class="ed-val">1 (observed)</span></div>`;
    bodyHtml+=`<div><span class="ed-lbl">Prior Cases:</span> <span class="ed-val">${c.historical_evidence?c.historical_evidence.length:0}</span></div>`;
    bodyHtml+=`</div><div class="ed-col"><button class="ed-nav-btn" onclick="switchTab('t-reason')">View Evidence &rarr;</button>`;
  }else if(n.type==='Card'){
    bodyHtml+=`<div><span class="ed-lbl">Owning Customer:</span> <span class="ed-val">${c.customer_id}</span></div>`;
    bodyHtml+=`<div><span class="ed-lbl">Target of NBA:</span> <span class="ed-val">${c.card_id===c.card_id?'Yes':'No'}</span></div>`;
    bodyHtml+=`</div><div class="ed-col"><button class="ed-nav-btn" onclick="switchTab('t-comply')">View Writeback &rarr;</button>`;
  }else if(n.type==='Transaction'){
    bodyHtml+=`<div><span class="ed-lbl">Amount:</span> <span class="ed-val">$${c.sar_data?c.sar_data.exposure_usd.toFixed(2):'??'}</span></div>`;
    bodyHtml+=`<div><span class="ed-lbl">Involved Card:</span> <span class="ed-val">${c.card_id}</span></div>`;
    bodyHtml+=`</div><div class="ed-col"><button class="ed-nav-btn" onclick="switchTab('t-reason')">View Txn Reason &rarr;</button>`;
  }else if(n.type==='Case'){
    bodyHtml+=`<div><span class="ed-lbl">Assessment:</span> <span class="ed-val">${c.fraud_assessment.replace(/_/g,' ')}</span></div>`;
    bodyHtml+=`<div><span class="ed-lbl">NBA:</span> <span class="ed-val">${c.recommended_nba.replace(/_/g,' ')}</span></div>`;
    bodyHtml+=`</div><div class="ed-col"><button class="ed-nav-btn" onclick="switchTab('t-reason')">View Reasoning &rarr;</button>`;
  }else if(n.type==='History'){
    let status='KNOWN', patt='N/A';
    (c.current_evidence||[]).forEach(e=>{
      if(e.statement.includes(n.id)) {
        const m=e.statement.match(/Case [^\(]+\(([^,]+), ([^,]+)/);
        if(m){status=m[1];patt=m[2];}
      }
    });
    bodyHtml+=`<div><span class="ed-lbl">Status:</span> <span class="ed-val" style="color:${status==='CONFIRMED_FRAUD'?'var(--red)':'var(--tx-1)'}">${status.replace(/_/g,' ')}</span></div>`;
    bodyHtml+=`<div><span class="ed-lbl">Pattern:</span> <span class="ed-val">${patt.replace(/_/g,' ')}</span></div>`;
    bodyHtml+=`</div><div class="ed-col"><button class="ed-nav-btn" onclick="switchTab('t-reason')">View GraphRAG Precedents &rarr;</button>`;
  }
  bodyHtml+='</div>';
  document.getElementById('ed-body').innerHTML=bodyHtml;
}

/* ===== TAB 2: REASONING ===== */
function renderReasoning(c){
  const el=document.getElementById('t-reason');
  let confPct=Math.round(c.confidence*100);

  // Evidence by source
  let evBySource={};
  (c.current_evidence||[]).forEach(e=>{
    let src=e.source_id.split(':')[0];
    if(!evBySource[src])evBySource[src]=[];
    evBySource[src].push(e);
  });

  let evHtml='';
  Object.keys(evBySource).forEach(src=>{
    evHtml+=`<div class="ev-head" style="margin-top:12px">${src.replace(/_/g,' ').toUpperCase()} (${evBySource[src].length})</div>`;
    evBySource[src].forEach(e=>{
      evHtml+=`<div class="ev-item">${e.statement}<div class="ev-source">${e.source_id}</div></div>`;
    });
  });

  // Historical cases
  let histHtml='';
  // Extract historical case details from current_evidence
  const histDetails={};
  (c.current_evidence||[]).forEach(e=>{
    const m=e.statement.match(/Case (CC-\\d+) \\(([^,]+), ([^,]+), Exposure: \\$(\\S+)\\)/);
    if(m){histDetails[m[1]]={status:m[2],pattern:m[3],exposure:m[4]};}
  });

  (c.historical_evidence||[]).forEach(h=>{
    const d=histDetails[h.case_id]||{};
    const isFraud=d.status==='CONFIRMED_FRAUD';
    const tagClass=isFraud?'fraud':'cleared';
    const tagText=d.status?d.status.replace(/_/g,' '):'RELATED';
    histHtml+=`
    <div class="hist-case" onclick="this.classList.toggle('open')">
      <div class="hist-case-head">
        <span class="hist-case-id">${h.case_id}</span>
        <span class="hist-case-tag ${tagClass}">${tagText}</span>
      </div>
      <div class="hist-case-meta">
        ${d.pattern?'<span>'+d.pattern.replace(/_/g,' ')+'</span>':''}
        ${d.exposure?'<span>$'+d.exposure+'</span>':''}
      </div>
      <div class="hist-case-detail">Retrieved via GraphRAG from bank case memory.<br>Source: ${h.source}</div>
    </div>`;
  });

  el.innerHTML=`
  <div class="metrics-row">
    <div class="metric"><div class="metric-label">Confidence</div><div class="metric-value">${confPct}%</div></div>
    <div class="metric"><div class="metric-label">Uncertainty</div><div class="metric-value" style="color:${c.uncertainty_level==='high'?'var(--amber)':'var(--tx-0)'}">${c.uncertainty_level.toUpperCase()}</div></div>
    <div class="metric"><div class="metric-label">Evidence Items</div><div class="metric-value">${(c.current_evidence||[]).length}</div></div>
    <div class="metric"><div class="metric-label">Tools Used</div><div class="metric-value">${c.tool_call_count}</div></div>
    <div class="metric"><div class="metric-label">Prior Cases</div><div class="metric-value">${(c.historical_evidence||[]).length}</div></div>
  </div>

  <div class="reason-grid">
    <div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--red)"></span> Strong Signals</div>
        ${(c.supporting_findings||[]).map(f=>`<div class="signal-item">${f}</div>`).join('')||'<div class="signal-item" style="color:var(--tx-3)">None</div>'}
      </div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--green)"></span> Counter-Signals</div>
        ${(c.contradictory_findings||[]).map(f=>`<div class="signal-item">${f}</div>`).join('')||'<div class="signal-item" style="color:var(--tx-3)">None</div>'}
      </div>
    </div>
    <div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--amber)"></span> Uncertainty Factors</div>
        ${(c.uncertainty_reasons||[]).map(r=>`<div class="signal-item">${r}</div>`).join('')}
        ${(c.evidence_gaps||[]).map(g=>`<div class="signal-item" style="color:var(--amber)">Gap: ${g}</div>`).join('')}
      </div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--blue)"></span> Explanation</div>
        ${c.explanation&&c.explanation.why_suspicious?(c.explanation.why_suspicious.map(r=>`<div class="signal-item">${r}</div>`).join('')):''}
        ${c.explanation&&c.explanation.why_action?(c.explanation.why_action.map(r=>`<div class="signal-item" style="color:var(--tx-2)">${r}</div>`).join('')):''}
      </div>
    </div>
    <div>
      <div class="signal-head" style="margin-bottom:10px"><span class="sdot" style="background:var(--purple)"></span> GraphRAG Historical Precedents</div>
      ${histHtml||'<div style="font-size:12px;color:var(--tx-3)">No historical cases found.</div>'}
    </div>
    <div>
      <div class="evidence-section">
        <div class="ev-head">Live Graph Evidence</div>
        <div style="max-height:400px;overflow-y:auto">${evHtml}</div>
      </div>
    </div>
  </div>`;
}

/* ===== TAB 3: COMPLIANCE ===== */
function renderCompliance(c){
  const el=document.getElementById('t-comply');

  // Policy rules from explanation
  let policyRules=[];
  if(c.explanation&&c.explanation.why_action){
    c.explanation.why_action.forEach(a=>{
      const m=a.match(/Policy Rules?: ([R\\d, ]+)/);
      if(m){policyRules=m[1].split(',').map(s=>s.trim());}
    });
  }

  // Lifecycle stages
  const stages=['OPEN','INVESTIGATING','AWAITING_EVIDENCE','ACTION_PENDING_APPROVAL','EXECUTED','CLOSED'];
  const currentIdx=stages.indexOf(c.lifecycle_state);

  let lifecycleHtml='';
  stages.forEach((s,i)=>{
    let dotClass=i<currentIdx?'done':i===currentIdx?'current':'future';
    lifecycleHtml+=`<div class="lf-step"><span class="lf-dot ${dotClass}"></span>${s.replace(/_/g,' ')}</div>`;
    if(i<stages.length-1)lifecycleHtml+=`<div class="lf-line"></div>`;
  });

  el.innerHTML=`
  <div class="compliance-grid">
    <div class="compliance-section">
      <div class="comp-head">Policy Evaluation</div>
      ${policyRules.length>0?policyRules.map(r=>`<div class="policy-row"><span class="policy-check">&#10003;</span>${r}</div>`).join(''):'<div style="font-size:12px;color:var(--tx-3)">No policy rules explicitly recorded.</div>'}
      <div style="margin-top:12px;font-size:11px;color:var(--tx-2)">
        Approval Route: <strong>${c.approval_route||'auto'}</strong><br>
        Approval Required: <strong>${c.approval_required?'Yes':'No'}</strong>
      </div>
    </div>

    <div class="compliance-section">
      <div class="comp-head">Case Lifecycle</div>
      <div class="lifecycle-flow">${lifecycleHtml}</div>
    </div>

    <div class="compliance-section">
      <div class="comp-head">TigerGraph Writeback</div>
      ${c.written_to_graph?`
        <div class="wb-row"><span class="wb-check">&#10003;</span> InvestigationCase / ${c.case_id}</div>
        <div class="wb-row"><span class="wb-check">&#10003;</span> INVOLVES &rarr; ${c.transaction_id}</div>
        <div class="wb-row"><span class="wb-check">&#10003;</span> ON_CARD &rarr; ${c.card_id}</div>
        <div class="wb-row"><span class="wb-check">&#10003;</span> CONNECTED_TO &rarr; ${c.customer_id}</div>
      `:`<div style="font-size:12px;color:var(--tx-3)">Writeback not performed (offline mode).</div>`}
    </div>

    <div class="compliance-section" style="grid-column:1/-1">
      <div class="comp-head">SAR Preparation & Compliance</div>
      <div class="sar-status" style="color:${c.sar_data&&c.sar_data.sar_required?'var(--red)':'var(--green)'}">${c.sar_data&&c.sar_data.sar_required?'SAR PREPARATION REQUIRED':'SAR NOT REQUIRED'}</div>
      <div class="sar-detail">
        <strong>Exposure:</strong> $${c.sar_data?c.sar_data.exposure_usd.toFixed(2):'0.00'} USD<br>
        <strong>Status:</strong> ${c.sar_data?c.sar_data.sar_status:'N/A'}<br>
        <strong>Rationale:</strong> ${c.sar_data?c.sar_data.sar_rationale:'N/A'}<br>
        <strong>Regulatory References:</strong> ${c.sar_data&&c.sar_data.regulatory_references?c.sar_data.regulatory_references.join(', '):'None'}
      </div>
      <div class="comp-note">
        This system prepares SAR documentation according to internal bank policy thresholds. All FinCEN filings require external human compliance officer review and approval before submission.
      </div>
    </div>
  </div>`;
}

window.addEventListener('load',init);
window.addEventListener('resize',()=>{
  const c=allCases.find(x=>x.case_id===activeId);
  if(c)drawGraph(c);
});
</script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
