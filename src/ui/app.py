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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg-0:#080c14;--bg-1:#0d1117;--bg-2:#161b22;--bg-3:#1c2333;--bg-4:#242d3d;
  --tx-0:#e6edf3;--tx-1:#c9d1d9;--tx-2:#8b949e;--tx-3:#6e7681;
  --red:#f85149;--red-dim:rgba(248,81,73,.15);
  --amber:#d29922;--amber-dim:rgba(210,153,34,.15);
  --green:#3fb950;--green-dim:rgba(63,185,80,.15);
  --blue:#58a6ff;--blue-dim:rgba(88,166,255,.15);
  --purple:#bc8cff;--purple-dim:rgba(188,140,255,.15);
  --cyan:#39d2c0;--cyan-dim:rgba(57,210,192,.15);
  --border:#30363d;--border-emphasis:#484f58;
  --font-sans:'Inter',system-ui,-apple-system,sans-serif;
  --font-mono:'JetBrains Mono','Consolas',monospace;
  --radius:6px;
}
html,body{height:100%;overflow:hidden;background:var(--bg-0);color:var(--tx-0);font-family:var(--font-sans);font-size:13px;line-height:1.5;-webkit-font-smoothing:antialiased}

/* === SYSTEM BAR === */
.sysbar{height:40px;background:var(--bg-1);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:16px;flex-shrink:0;z-index:100}
.sysbar-brand{font-weight:600;font-size:13px;color:var(--tx-1);letter-spacing:.3px;display:flex;align-items:center;gap:8px}
.sysbar-brand svg{width:16px;height:16px;fill:var(--blue)}
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
.ci-id{font-weight:500;font-size:12px;font-family:var(--font-mono)}
.ci-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.ci-dot.fraud{background:var(--red)}.ci-dot.benign{background:var(--green)}.ci-dot.uncertain{background:var(--amber)}

/* === MAIN === */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* === CASE HEADER === */
.case-head{padding:16px 24px 16px;background:var(--bg-1);border-bottom:1px solid var(--border);flex-shrink:0}
.ch-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.ch-id{font-size:24px;font-weight:600;font-family:var(--font-mono);letter-spacing:-0.5px;color:var(--tx-0)}

/* Header Summary Grid */
.ch-grid{display:flex;gap:32px;align-items:center;}
.ch-stat{display:flex;flex-direction:column;gap:4px}
.ch-stat-lbl{font-size:10px;font-weight:600;text-transform:uppercase;color:var(--tx-3);letter-spacing:.5px}
.ch-stat-val{font-size:13px;font-weight:500;display:flex;align-items:center;gap:6px}
.ch-stat-val.mono{font-family:var(--font-mono)}

/* Status Tags */
.status-tag{font-size:11px;font-weight:600;padding:3px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:0.5px}
.status-tag.fraud{background:var(--red-dim);color:var(--red);border:1px solid rgba(248,81,73,0.3)}
.status-tag.benign{background:var(--green-dim);color:var(--green);border:1px solid rgba(63,185,80,0.3)}
.status-tag.uncertain{background:var(--amber-dim);color:var(--amber);border:1px solid rgba(210,153,34,0.3)}
.status-tag.auth-req{color:var(--amber)}
.status-tag.auth-ok{color:var(--green)}
.status-tag.exec-done{color:var(--green)}
.status-tag.exec-pend{color:var(--amber)}

/* === WORKSPACE TABS === */
.ws-tabs{display:flex;background:var(--bg-1);border-bottom:1px solid var(--border);padding:0 24px;flex-shrink:0}
.ws-tab{padding:12px 16px;font-size:13px;font-weight:500;color:var(--tx-3);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;background:none;border-top:none;border-left:none;border-right:none}
.ws-tab:hover{color:var(--tx-1)}
.ws-tab.active{color:var(--tx-0);border-bottom-color:var(--blue)}

/* === WORKSPACE CONTENT === */
.ws-body{flex:1;overflow-y:auto;overflow-x:hidden}
.ws-body::-webkit-scrollbar{width:6px}
.ws-body::-webkit-scrollbar-thumb{background:var(--border-emphasis);border-radius:4px}
.ws-panel{display:none;padding:20px 24px;height:100%}
.ws-panel.active{display:block}

/* === INVESTIGATION TAB === */
.inv-layout{display:grid;grid-template-columns:300px 1fr 280px;gap:20px;height:100%;min-height:500px}
.inv-col{display:flex;flex-direction:column;gap:16px;height:100%;min-height:0}

/* Timeline */
.timeline-scroll{flex:1;overflow-y:auto;padding-right:8px}
.timeline-scroll::-webkit-scrollbar{width:4px}
.timeline-scroll::-webkit-scrollbar-thumb{background:var(--border-emphasis);border-radius:4px}
.trigger-block{margin-bottom:20px;padding-left:12px;border-left:2px solid var(--tx-3)}
.trigger-type{font-size:10px;font-weight:600;text-transform:uppercase;color:var(--tx-3);margin-bottom:4px}
.trigger-text{font-size:12px;color:var(--tx-1);line-height:1.5}
.step{position:relative;padding:12px 12px 12px 24px;margin-bottom:8px;border-left:2px solid var(--border-emphasis)}
.step::before{content:'';position:absolute;left:-5px;top:16px;width:8px;height:8px;border-radius:50%;background:var(--blue)}
.step-num{font-size:10px;font-weight:600;color:var(--blue);margin-bottom:4px;letter-spacing:1px}
.step-tool{font-size:13px;font-weight:600;color:var(--tx-0);margin-bottom:6px;font-family:var(--font-mono)}
.step-kvs{display:flex;flex-direction:column;gap:4px;font-size:12px}
.step-kv{display:flex;gap:8px}
.step-kv-k{color:var(--tx-3);min-width:50px}
.step-kv-v{color:var(--tx-1);line-height:1.4}

/* Graph Area */
.graph-container{background:var(--bg-1);border-radius:var(--radius);border:1px solid var(--border);flex:1;position:relative;overflow:hidden;display:flex;flex-direction:column}
.graph-svg-wrapper{flex:1;position:relative;cursor:grab}
.graph-svg-wrapper:active{cursor:grabbing}
svg.graph-svg{width:100%;height:100%;display:block}
.graph-header{position:absolute;top:12px;left:16px;z-index:10;pointer-events:none}
.graph-title{font-size:11px;font-weight:600;text-transform:uppercase;color:var(--tx-2);letter-spacing:.5px}
.graph-legend{position:absolute;bottom:12px;left:16px;display:flex;gap:12px;z-index:10;pointer-events:none}
.legend-item{font-size:11px;color:var(--tx-2);display:flex;align-items:center;gap:6px}
.legend-dot{width:8px;height:8px;border-radius:50%}

/* Graph SVG Elements */
.svg-edge{stroke:var(--border-emphasis);stroke-width:1.5px;transition:stroke 0.2s}
.svg-edge.interactive{cursor:pointer}
.svg-edge:hover{stroke:var(--tx-2);stroke-width:2.5px}
.svg-edge-label-bg{fill:var(--bg-1)}
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

/* Entity Details Panel (Bottom of graph) */
.entity-details{background:var(--bg-1);border-top:1px solid var(--border);padding:16px;flex-shrink:0;min-height:160px;display:flex;flex-direction:column}
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

/* Decision / Auth Rail */
.rail-section{margin-bottom:24px}
.rail-lbl{font-size:10px;font-weight:600;color:var(--tx-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.auth-row{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px}
.auth-icon{width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0;margin-top:2px;border:1px solid transparent}
.auth-icon.green{background:var(--green-dim);color:var(--green);border-color:rgba(63,185,80,0.3)}
.auth-icon.amber{background:var(--amber-dim);color:var(--amber);border-color:rgba(210,153,34,0.3)}
.auth-icon.red{background:var(--red-dim);color:var(--red);border-color:rgba(248,81,73,0.3)}
.auth-icon.neutral{background:var(--bg-3);color:var(--tx-3);border-color:var(--border-emphasis)}
.auth-text{display:flex;flex-direction:column;gap:2px}
.auth-title{font-size:13px;font-weight:500;color:var(--tx-0)}
.auth-sub{font-size:11px;color:var(--tx-2)}

.nba-box{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:8px}
.nba-val{font-size:14px;font-weight:600;margin-bottom:4px}
.nba-tgt{font-size:12px;color:var(--tx-2);font-family:var(--font-mono)}

/* === REASONING & COMPLIANCE TABS === */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px}
.panel-section{margin-bottom:24px}
.panel-head{font-size:12px;font-weight:600;color:var(--tx-0);border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.pdot{width:8px;height:8px;border-radius:50%}

/* List Items */
.li-item{font-size:13px;color:var(--tx-1);padding:6px 0;line-height:1.5}
.li-item.amber{color:var(--amber)}
.li-source{font-size:11px;color:var(--tx-3);font-family:var(--font-mono);margin-top:2px}
.ev-item{padding:10px 0;border-bottom:1px solid var(--border)}
.ev-item:last-child{border-bottom:none}

/* GraphRAG Cases */
.gr-case{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:12px}
.gr-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.gr-id{font-family:var(--font-mono);font-size:13px;font-weight:600}
.gr-tag{font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px}
.gr-tag.fraud{background:var(--red-dim);color:var(--red)}
.gr-tag.cleared{background:var(--green-dim);color:var(--green)}
.gr-meta{display:flex;gap:16px;font-size:11px;color:var(--tx-2);margin-bottom:8px}
.gr-meta-item{display:flex;align-items:center;gap:4px}
.gr-desc{font-size:12px;color:var(--tx-1);line-height:1.4}

/* Compliance */
.comp-row{display:flex;align-items:flex-start;gap:10px;padding:6px 0;font-size:13px;color:var(--tx-1)}
.comp-icon{color:var(--green);font-size:12px;margin-top:2px}
.sar-box{background:var(--bg-2);border-left:3px solid var(--tx-3);padding:16px;border-radius:var(--radius)}
.sar-box.req{border-color:var(--red)}
.sar-val{font-size:16px;font-weight:600;margin-bottom:12px}
.sar-kv{display:flex;margin-bottom:6px;font-size:13px}
.sar-k{width:120px;color:var(--tx-3);font-weight:500}
.sar-v{color:var(--tx-0);flex:1}
.comp-note{margin-top:16px;font-size:12px;color:var(--tx-2);line-height:1.5;background:var(--bg-2);padding:12px;border-radius:var(--radius)}

/* Helpers */
.text-red{color:var(--red)}
.text-green{color:var(--green)}
.text-amber{color:var(--amber)}
.text-blue{color:var(--blue)}
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
  <span class="sysbar-tag info">FraudGraph</span>
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
    <!-- CASE HEADER -->
    <div class="case-head" id="case-head">
      <div class="ch-top">
        <div class="ch-id" id="ch-id">—</div>
        <div id="ch-assess-tag" class="status-tag">Uncertain</div>
      </div>
      <div class="ch-grid">
        <div class="ch-stat">
          <div class="ch-stat-lbl">Confidence / Unc.</div>
          <div class="ch-stat-val"><span id="ch-conf">—</span> <span style="color:var(--border-emphasis)">|</span> <span id="ch-unc">—</span></div>
        </div>
        <div class="ch-stat">
          <div class="ch-stat-lbl">Next Best Action</div>
          <div class="ch-stat-val" id="ch-nba">—</div>
        </div>
        <div class="ch-stat">
          <div class="ch-stat-lbl">Authorization</div>
          <div class="ch-stat-val" id="ch-auth">—</div>
        </div>
        <div class="ch-stat">
          <div class="ch-stat-lbl">Lifecycle</div>
          <div class="ch-stat-val" id="ch-life">—</div>
        </div>
      </div>
    </div>

    <!-- TABS -->
    <div class="ws-tabs">
      <button class="ws-tab active" data-tab="t-inv">Investigation Workflow</button>
      <button class="ws-tab" data-tab="t-reason">Evidence & Reasoning</button>
      <button class="ws-tab" data-tab="t-comply">Compliance & Writeback</button>
    </div>

    <!-- BODY -->
    <div class="ws-body">
      <!-- TAB: INVESTIGATION -->
      <div class="ws-panel active" id="t-inv">
        <div class="inv-layout">
          <!-- Timeline -->
          <div class="inv-col">
            <div style="font-size:12px;font-weight:600;color:var(--tx-0);margin-bottom:8px">Agent Timeline</div>
            <div class="timeline-scroll" id="timeline-container"></div>
          </div>
          
          <!-- Graph -->
          <div class="inv-col">
            <div class="graph-container">
              <div class="graph-header">
                <div class="graph-title">Investigation Subgraph</div>
              </div>
              <div class="graph-legend">
                <span class="legend-item"><span class="legend-dot" style="background:var(--blue)"></span>Customer</span>
                <span class="legend-item"><span class="legend-dot" style="background:var(--cyan)"></span>Card</span>
                <span class="legend-item"><span class="legend-dot" style="background:var(--amber)"></span>Transaction</span>
                <span class="legend-item"><span class="legend-dot" style="background:var(--red)"></span>Case</span>
                <span class="legend-item"><span class="legend-dot" style="background:var(--purple)"></span>History</span>
              </div>
              <div class="graph-svg-wrapper" id="svg-wrap">
                <svg class="graph-svg" id="main-svg"></svg>
                <div class="graph-tooltip" id="graph-tooltip"></div>
              </div>
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

          <!-- Decision Rail -->
          <div class="inv-col">
            <div style="font-size:12px;font-weight:600;color:var(--tx-0);margin-bottom:16px">Decision & Execution</div>
            
            <div class="rail-section">
              <div class="rail-lbl">Action Target</div>
              <div class="nba-box" id="nba-box-ui"></div>
            </div>

            <div class="rail-section">
              <div class="rail-lbl">Authorization State</div>
              <div id="auth-flow-ui"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: REASONING -->
      <div class="ws-panel" id="t-reason"></div>

      <!-- TAB: COMPLY -->
      <div class="ws-panel" id="t-comply"></div>
    </div>
  </div>
</div>

<script>
let allCases=[], activeId=null, currentCase=null;
let svgNodes=[], svgEdges=[], selectedNodeId=null;

// Config colors matching legend
const COLORS = {
  Customer: '#58a6ff',
  Card: '#39d2c0',
  Transaction: '#d29922',
  Case: '#f85149',
  History: '#bc8cff'
};

async function init(){
  try{
    const r=await fetch('/api/cases');
    allCases=await r.json();
    const liveCount=allCases.filter(c=>c.written_to_graph).length;
    document.getElementById('sys-live').textContent=liveCount===allCases.length?'LIVE':'PARTIAL';
    document.getElementById('sys-live').className='sysbar-tag '+(liveCount===allCases.length?'live':'info');
    document.getElementById('sys-count').textContent=allCases.length+'/20 benchmark cases';
    renderNav();
    if(allCases.length>0){
        selectCase(allCases[0].case_id);
    }
  }catch(e){
    console.error(e);
    document.getElementById('case-list').innerHTML='<div style="color:var(--red)">Failed to load cases</div>';
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
  currentCase=allCases.find(x=>x.case_id===id);
  if(!currentCase)return;
  renderNav();
  
  const c = currentCase;
  
  // Header values
  document.getElementById('ch-id').textContent=c.case_id;
  
  let ac='uncertain', at=c.fraud_assessment.replace(/_/g,' ').toUpperCase();
  if(c.fraud_assessment==='likely_fraud')ac='fraud';
  if(c.fraud_assessment==='likely_benign')ac='benign';
  const aTag=document.getElementById('ch-assess-tag');
  aTag.className='status-tag '+ac;
  aTag.textContent=at;
  
  let confPct=Math.round(c.confidence*100);
  let uncColor=c.uncertainty_level==='high'?'var(--amber)':c.uncertainty_level==='low'?'var(--green)':'var(--tx-1)';
  document.getElementById('ch-conf').textContent=confPct+'%';
  document.getElementById('ch-unc').innerHTML=`<span style="color:${uncColor}">${c.uncertainty_level.toUpperCase()}</span>`;
  
  let nbaColor=c.recommended_nba==='BLOCK_CARD'?'var(--red)':c.recommended_nba==='VERIFY_WITH_CUSTOMER'?'var(--amber)':'var(--tx-1)';
  document.getElementById('ch-nba').innerHTML=`<span style="color:${nbaColor}">${c.recommended_nba.replace(/_/g,' ')}</span>`;
  
  let authStr = 'Auto';
  let authCol = 'var(--green)';
  if(c.approval_required){ authStr='L1 Required'; authCol='var(--amber)'; }
  document.getElementById('ch-auth').innerHTML=`<span style="color:${authCol}">${authStr}</span>`;
  document.getElementById('ch-life').textContent=c.lifecycle_state.replace(/_/g,' ');

  renderInvestigation(c);
  renderReasoning(c);
  renderCompliance(c);
  selectedNodeId=null;
  hideDetails();
  
  // Ensure the SVG wrapper layout is calculated before drawing
  setTimeout(() => drawSVGGraph(c), 50);
}

/* ===== INVESTIGATION TAB ===== */
function renderInvestigation(c){
  // 1. Timeline
  const tl=document.getElementById('timeline-container');
  let tlHtml=`
    <div class="trigger-block">
      <div class="trigger-type">Trigger: ${c.trigger.trigger_type.replace(/_/g,' ')}</div>
      <div class="trigger-text">${c.trigger.trigger_text}</div>
    </div>`;
    
  c.investigation_steps.forEach((s,i)=>{
    // Attempt to extract brief purpose
    let purp = s.reason;
    if(purp.length>100) purp = purp.substring(0,97)+'...';
    tlHtml+=`
    <div class="step">
      <div class="step-num">STEP ${String(s.step_number).padStart(2,'0')}</div>
      <div class="step-tool">${s.tool}</div>
      <div class="step-kvs">
        <div class="step-kv"><div class="step-kv-k">Purpose</div><div class="step-kv-v">${purp}</div></div>
        <div class="step-kv"><div class="step-kv-k">Result</div><div class="step-kv-v">${s.result_summary}</div></div>
      </div>
    </div>`;
  });
  tl.innerHTML=tlHtml;
  
  // 2. Decision & Auth Rail
  let nbaColor=c.recommended_nba==='BLOCK_CARD'?'var(--red)':c.recommended_nba==='VERIFY_WITH_CUSTOMER'?'var(--amber)':'var(--tx-0)';
  document.getElementById('nba-box-ui').innerHTML = `
    <div class="nba-val" style="color:${nbaColor}">${c.recommended_nba.replace(/_/g,' ')}</div>
    <div class="nba-tgt">Target: ${c.card_id}</div>
  `;
  
  // Authorization Data-Driven Logic
  // Recommendation
  let authHtml = `
    <div class="auth-row">
      <div class="auth-icon green">&#10003;</div>
      <div class="auth-text">
        <div class="auth-title">Agent Recommendation</div>
        <div class="auth-sub">Completed with ${Math.round(c.confidence*100)}% confidence</div>
      </div>
    </div>
  `;
  
  // Approval
  if(c.approval_required){
    authHtml += `
      <div class="auth-row">
        <div class="auth-icon amber">!</div>
        <div class="auth-text">
          <div class="auth-title text-amber">Human Approval Required</div>
          <div class="auth-sub">L1 Compliance Officer review pending</div>
        </div>
      </div>
    `;
  } else {
    authHtml += `
      <div class="auth-row">
        <div class="auth-icon green">&#10003;</div>
        <div class="auth-text">
          <div class="auth-title text-green">Auto-Approved</div>
          <div class="auth-sub">Threshold met, no human review required</div>
        </div>
      </div>
    `;
  }
  
  // Execution
  let execIcon = 'neutral', execSym = '○', execTitleClass = '', execTitle = 'Execution Pending', execSub = 'Waiting for conditions to be met';
  if(c.execution_status === 'EXECUTED'){
    execIcon = 'green'; execSym = '&#10003;'; execTitleClass = 'text-green'; execTitle = 'Action Executed'; execSub = 'Successfully dispatched to backend';
  } else if(c.execution_status === 'DENIED'){
    execIcon = 'red'; execSym = '&#10005;'; execTitleClass = 'text-red'; execTitle = 'Execution Denied'; execSub = 'Action was blocked';
  } else {
    // Pending
    if(c.approval_required) {
      execIcon = 'neutral'; execSym = '○'; execTitle = 'Pending Approval'; execSub = 'Waiting for human authorization';
    } else {
      execIcon = 'neutral'; execSym = '○'; execTitle = 'Ready for Execution'; execSub = 'Action is queued';
    }
  }
  
  authHtml += `
    <div class="auth-row">
      <div class="auth-icon ${execIcon}">${execSym}</div>
      <div class="auth-text">
        <div class="auth-title ${execTitleClass}">${execTitle}</div>
        <div class="auth-sub">${execSub}</div>
      </div>
    </div>
  `;
  
  document.getElementById('auth-flow-ui').innerHTML = authHtml;
}

/* ===== INTERACTIVE SVG GRAPH ===== */
function drawSVGGraph(c){
  const wrap = document.getElementById('svg-wrap');
  const svg = document.getElementById('main-svg');
  if(!wrap || !svg) return;
  
  const W = wrap.clientWidth;
  const H = wrap.clientHeight;
  svg.innerHTML = ''; // clear
  svgNodes = [];
  svgEdges = [];
  
  // Node Layout Logic
  // Customer (Top), Card (Middle-Top), Transaction (Middle), Case (Middle-Right)
  // History (Bottom branch from Customer or Card)
  
  const cx = W/2;
  
  svgNodes.push({id: c.customer_id, label: c.customer_id, type: 'Customer', x: cx, y: 50, r: 24, c: COLORS.Customer});
  svgNodes.push({id: c.card_id, label: c.card_id, type: 'Card', x: cx, y: 140, r: 20, c: COLORS.Card});
  
  let txnLabel = '$' + (c.sar_data ? c.sar_data.exposure_usd.toFixed(0) : '?');
  svgNodes.push({id: String(c.transaction_id), label: txnLabel, type: 'Transaction', x: cx, y: 230, r: 18, c: COLORS.Transaction});
  
  svgNodes.push({id: c.case_id, label: c.case_id, type: 'Case', x: cx + 100, y: 230, r: 22, c: COLORS.Case});
  
  svgEdges.push({from: c.customer_id, to: c.card_id, label: 'HAS_CARD'});
  svgEdges.push({from: c.card_id, to: String(c.transaction_id), label: 'USED_FOR'});
  svgEdges.push({from: String(c.transaction_id), to: c.case_id, label: 'INVOLVES'});

  // Historical
  if(c.historical_evidence && c.historical_evidence.length > 0){
    const maxH = Math.min(c.historical_evidence.length, 3);
    const startX = cx - 120;
    const spacing = 90;
    for(let i=0; i<maxH; i++){
      const h = c.historical_evidence[i];
      const hx = startX + (i*spacing);
      const hy = 320;
      svgNodes.push({id: h.case_id, label: h.case_id, type: 'History', x: hx, y: hy, r: 16, c: COLORS.History});
      // Branch from customer generally
      svgEdges.push({from: c.customer_id, to: h.case_id, label: 'PRIOR_CASE'});
    }
  }

  const nodeMap = {};
  svgNodes.forEach(n => nodeMap[n.id] = n);

  // 1. Draw Edges
  svgEdges.forEach(e => {
    const n1 = nodeMap[e.from], n2 = nodeMap[e.to];
    if(!n1 || !n2) return;
    const mx = (n1.x + n2.x) / 2;
    const my = (n1.y + n2.y) / 2;
    
    // Group
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.style.cursor = 'pointer';
    
    // Line
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', n1.x); line.setAttribute('y1', n1.y);
    line.setAttribute('x2', n2.x); line.setAttribute('y2', n2.y);
    line.setAttribute('class', 'svg-edge');
    
    // Invisible thicker line for easier hover
    const hit = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    hit.setAttribute('x1', n1.x); hit.setAttribute('y1', n1.y);
    hit.setAttribute('x2', n2.x); hit.setAttribute('y2', n2.y);
    hit.setAttribute('stroke', 'transparent');
    hit.setAttribute('stroke-width', '15');
    
    // Label BG (rect) & Text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', mx); text.setAttribute('y', my);
    text.setAttribute('class', 'svg-edge-label');
    text.textContent = e.label;
    
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    const tw = e.label.length * 6; // approx
    bg.setAttribute('x', mx - tw/2); bg.setAttribute('y', my - 8);
    bg.setAttribute('width', tw); bg.setAttribute('height', 16);
    bg.setAttribute('class', 'svg-edge-label-bg');
    bg.setAttribute('rx', 3);
    
    g.appendChild(line);
    g.appendChild(hit);
    g.appendChild(bg);
    g.appendChild(text);
    
    g.addEventListener('mouseenter', (ev) => showEdgeTooltip(ev, e));
    g.addEventListener('mouseleave', hideTooltip);
    g.addEventListener('click', () => showEdgeDetails(e));
    
    svg.appendChild(g);
  });

  // 2. Draw Nodes
  svgNodes.forEach(n => {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'svg-node');
    g.setAttribute('id', 'node-'+n.id);
    g.setAttribute('transform', `translate(${n.x}, ${n.y})`);
    
    // BG Circle (opacity)
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    bg.setAttribute('r', n.r);
    bg.setAttribute('fill', n.c);
    bg.setAttribute('fill-opacity', '0.15');
    
    // Stroke Circle
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('class', 'svg-node-circle');
    circle.setAttribute('r', n.r);
    circle.setAttribute('stroke', n.c);
    circle.setAttribute('fill', 'transparent');
    
    // Label inside
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('class', 'svg-node-label');
    label.setAttribute('y', 4); // vertical center tweak
    
    // For large labels, truncate or show icon. We'll just show initials/short for Transaction/Case if needed,
    // but the prompt asked for clear node labels. Let's show as much as fits or leave it.
    let dispLabel = n.label;
    if(dispLabel.length > 8 && n.type!=='Transaction') {
      dispLabel = dispLabel.substring(0,6)+'..';
    }
    label.textContent = dispLabel;
    
    // Sub-label (Type)
    const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    sub.setAttribute('class', 'svg-node-sub');
    sub.setAttribute('y', n.r + 14);
    sub.textContent = n.type;
    
    g.appendChild(bg);
    g.appendChild(circle);
    g.appendChild(label);
    g.appendChild(sub);
    
    g.addEventListener('mouseenter', (ev) => showNodeTooltip(ev, n));
    g.addEventListener('mouseleave', hideTooltip);
    g.addEventListener('click', () => selectNode(n.id));
    
    svg.appendChild(g);
  });
}

function showNodeTooltip(ev, n) {
  const tt = document.getElementById('graph-tooltip');
  const wrap = document.getElementById('svg-wrap');
  const rect = wrap.getBoundingClientRect();
  tt.innerHTML = `
    <div class="tt-type">${n.type}</div>
    <div class="tt-id" style="color:${n.c}">${n.label}</div>
    <div class="tt-meta">Click to view details</div>
  `;
  tt.style.left = (ev.clientX - rect.left) + 'px';
  tt.style.top = (ev.clientY - rect.top - 15) + 'px';
  tt.style.opacity = '1';
}

function showEdgeTooltip(ev, e) {
  const tt = document.getElementById('graph-tooltip');
  const wrap = document.getElementById('svg-wrap');
  const rect = wrap.getBoundingClientRect();
  tt.innerHTML = `
    <div class="tt-type">Relationship</div>
    <div class="tt-id" style="color:var(--tx-1)">${e.from} &rarr; ${e.to}</div>
    <div class="tt-meta">${e.label}</div>
  `;
  tt.style.left = (ev.clientX - rect.left) + 'px';
  tt.style.top = (ev.clientY - rect.top - 15) + 'px';
  tt.style.opacity = '1';
}

function hideTooltip() {
  document.getElementById('graph-tooltip').style.opacity = '0';
}

function selectNode(id) {
  const n = svgNodes.find(x=>x.id === id);
  if(!n) return;
  selectedNodeId = id;
  
  // Visual state
  document.querySelectorAll('.svg-node').forEach(el => el.classList.remove('selected'));
  const el = document.getElementById('node-'+id);
  if(el) el.classList.add('selected');
  
  showDetails(n);
}

function showEdgeDetails(e) {
  // Clear node selection
  document.querySelectorAll('.svg-node').forEach(el => el.classList.remove('selected'));
  selectedNodeId = null;
  
  document.getElementById('ed-empty').style.display = 'none';
  const cont = document.getElementById('ed-content');
  cont.style.display = 'flex';
  
  document.getElementById('ed-type').textContent = 'Relationship';
  document.getElementById('ed-id').innerHTML = `<span style="color:var(--tx-3)">${e.from}</span> &rarr; <span style="color:var(--tx-3)">${e.to}</span>`;
  
  document.getElementById('ed-body').innerHTML = `
    <div class="ed-col">
      <div><span class="ed-lbl">Edge Label:</span> <span class="ed-val">${e.label}</span></div>
      <div><span class="ed-lbl">Source Entity:</span> <span class="ed-val">${e.from}</span></div>
      <div><span class="ed-lbl">Target Entity:</span> <span class="ed-val">${e.to}</span></div>
    </div>
  `;
}

function hideDetails() {
  document.getElementById('ed-empty').style.display = 'block';
  document.getElementById('ed-content').style.display = 'none';
  document.querySelectorAll('.svg-node').forEach(el => el.classList.remove('selected'));
}

function showDetails(n) {
  document.getElementById('ed-empty').style.display = 'none';
  const cont = document.getElementById('ed-content');
  cont.style.display = 'flex';
  
  document.getElementById('ed-type').textContent = n.type;
  document.getElementById('ed-id').textContent = n.id;
  document.getElementById('ed-id').style.color = n.c;
  
  const c = currentCase;
  let bodyHtml = '<div class="ed-col">';
  
  if(n.type === 'Customer') {
    bodyHtml += `<div><span class="ed-lbl">Total Cards:</span> <span class="ed-val">1 (observed)</span></div>`;
    bodyHtml += `<div><span class="ed-lbl">Prior Cases:</span> <span class="ed-val">${c.historical_evidence?c.historical_evidence.length:0}</span></div>`;
    bodyHtml += `</div><div class="ed-col">`;
    bodyHtml += `<button class="ed-nav-btn" onclick="switchTab('t-reason')">View Evidence &rarr;</button>`;
  } 
  else if (n.type === 'Card') {
    bodyHtml += `<div><span class="ed-lbl">Owning Customer:</span> <span class="ed-val">${c.customer_id}</span></div>`;
    bodyHtml += `<div><span class="ed-lbl">Target of NBA:</span> <span class="ed-val">${c.card_id === c.card_id ? 'Yes':'No'}</span></div>`;
    bodyHtml += `</div><div class="ed-col">`;
    bodyHtml += `<button class="ed-nav-btn" onclick="switchTab('t-comply')">View Writeback &rarr;</button>`;
  }
  else if (n.type === 'Transaction') {
    bodyHtml += `<div><span class="ed-lbl">Amount:</span> <span class="ed-val">$${c.sar_data?c.sar_data.exposure_usd.toFixed(2):'??'}</span></div>`;
    bodyHtml += `<div><span class="ed-lbl">Involved Card:</span> <span class="ed-val">${c.card_id}</span></div>`;
    bodyHtml += `</div><div class="ed-col">`;
    bodyHtml += `<button class="ed-nav-btn" onclick="switchTab('t-reason')">View Txn Reason &rarr;</button>`;
  }
  else if (n.type === 'Case') {
    bodyHtml += `<div><span class="ed-lbl">Assessment:</span> <span class="ed-val">${c.fraud_assessment.replace(/_/g,' ')}</span></div>`;
    bodyHtml += `<div><span class="ed-lbl">NBA:</span> <span class="ed-val">${c.recommended_nba.replace(/_/g,' ')}</span></div>`;
    bodyHtml += `</div><div class="ed-col">`;
    bodyHtml += `<button class="ed-nav-btn" onclick="switchTab('t-reason')">View Full Reasoning &rarr;</button>`;
  }
  else if (n.type === 'History') {
    // Find history details
    let status = 'KNOWN', patt = 'N/A';
    (c.current_evidence||[]).forEach(e=>{
      if(e.statement.includes(n.id)) {
        const m = e.statement.match(/Case [^\(]+\(([^,]+), ([^,]+)/);
        if(m){ status=m[1]; patt=m[2]; }
      }
    });
    bodyHtml += `<div><span class="ed-lbl">Status:</span> <span class="ed-val" style="color:${status==='CONFIRMED_FRAUD'?'var(--red)':'var(--tx-1)'}">${status.replace(/_/g,' ')}</span></div>`;
    bodyHtml += `<div><span class="ed-lbl">Pattern:</span> <span class="ed-val">${patt.replace(/_/g,' ')}</span></div>`;
    bodyHtml += `</div><div class="ed-col">`;
    bodyHtml += `<button class="ed-nav-btn" onclick="switchTab('t-reason')">View GraphRAG Precedents &rarr;</button>`;
  }
  
  bodyHtml += '</div>';
  document.getElementById('ed-body').innerHTML = bodyHtml;
}

/* ===== TAB 2: REASONING ===== */
function renderReasoning(c){
  const el = document.getElementById('t-reason');
  
  // Group live evidence by source
  let evBySource={};
  (c.current_evidence||[]).forEach(e=>{
    let src=e.source_id.split(':')[0];
    if(!evBySource[src])evBySource[src]=[];
    evBySource[src].push(e);
  });
  let evHtml='';
  Object.keys(evBySource).forEach(src=>{
    evHtml+=`<div class="panel-head" style="font-size:11px;color:var(--tx-3)">${src.replace(/_/g,' ').toUpperCase()}</div>`;
    evBySource[src].forEach(e=>{
      evHtml+=`<div class="ev-item"><div style="font-size:13px;color:var(--tx-0);margin-bottom:4px">${e.statement}</div><div class="li-source">${e.source_id}</div></div>`;
    });
  });

  // Historical Precedents formatting
  let histHtml='';
  const histDetails={};
  (c.current_evidence||[]).forEach(e=>{
    const m=e.statement.match(/Case (CC-\d+) \(([^,]+), ([^,]+), Exposure: \$(\S+)\)/);
    if(m){histDetails[m[1]]={status:m[2],pattern:m[3],exposure:m[4]};}
  });

  (c.historical_evidence||[]).forEach(h=>{
    const d=histDetails[h.case_id]||{};
    const isFraud=d.status==='CONFIRMED_FRAUD';
    const tagClass=isFraud?'fraud':'cleared';
    const tagText=d.status?d.status.replace(/_/g,' '):'RELATED';
    histHtml+=`
    <div class="gr-case">
      <div class="gr-head">
        <span class="gr-id">${h.case_id}</span>
        <span class="gr-tag ${tagClass}">${tagText}</span>
      </div>
      <div class="gr-meta">
        ${d.pattern?`<span class="gr-meta-item"><strong>Pattern:</strong> ${d.pattern.replace(/_/g,' ')}</span>`:''}
        ${d.exposure?`<span class="gr-meta-item"><strong>Exposure:</strong> $${d.exposure}</span>`:''}
      </div>
      <div class="gr-desc">Retrieved via GraphRAG context vector search.<br><span class="li-source">Source: ${h.source}</span></div>
    </div>`;
  });

  el.innerHTML=`
  <div class="grid-2">
    <!-- Col 1 -->
    <div>
      <div class="panel-section">
        <div class="panel-head"><span class="pdot" style="background:var(--red)"></span> Strong Fraud Signals</div>
        ${(c.supporting_findings||[]).map(f=>`<div class="li-item">${f}</div>`).join('')||'<div class="li-item" style="color:var(--tx-3)">None identified.</div>'}
      </div>
      <div class="panel-section">
        <div class="panel-head"><span class="pdot" style="background:var(--green)"></span> Counter-Signals</div>
        ${(c.contradictory_findings||[]).map(f=>`<div class="li-item">${f}</div>`).join('')||'<div class="li-item" style="color:var(--tx-3)">None identified.</div>'}
      </div>
      <div class="panel-section">
        <div class="panel-head"><span class="pdot" style="background:var(--amber)"></span> Uncertainty Factors & Gaps</div>
        ${(c.uncertainty_reasons||[]).map(r=>`<div class="li-item amber">${r}</div>`).join('')}
        ${(c.evidence_gaps||[]).map(g=>`<div class="li-item amber">Missing Evidence: ${g}</div>`).join('')}
      </div>
    </div>
    
    <!-- Col 2 -->
    <div>
      <div class="panel-section">
        <div class="panel-head"><span class="pdot" style="background:var(--purple)"></span> GraphRAG Precedents</div>
        ${histHtml||'<div style="font-size:13px;color:var(--tx-3);font-style:italic">No historical cases found in memory.</div>'}
      </div>
      
      <div class="panel-section">
        <div class="panel-head"><span class="pdot" style="background:var(--blue)"></span> Extracted Evidence Stream</div>
        <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;max-height:400px;overflow-y:auto">
          ${evHtml}
        </div>
      </div>
    </div>
  </div>`;
}

/* ===== TAB 3: COMPLIANCE ===== */
function renderCompliance(c){
  const el = document.getElementById('t-comply');
  
  let policyRules=[];
  if(c.explanation&&c.explanation.why_action){
    c.explanation.why_action.forEach(a=>{
      const m=a.match(/Policy Rules?: ([R\d, ]+)/);
      if(m) policyRules=m[1].split(',').map(s=>s.trim());
    });
  }

  el.innerHTML=`
  <div class="grid-3">
    <!-- Col 1 -->
    <div>
      <div class="panel-section">
        <div class="panel-head">Policy Evaluation</div>
        ${policyRules.length>0?policyRules.map(r=>`<div class="comp-row"><span class="comp-icon">&#10003;</span><span>Evaluated rule <strong>${r}</strong> against evidence.</span></div>`).join(''):'<div class="li-item" style="color:var(--tx-3)">No explicit policy rules cited.</div>'}
      </div>
      <div class="panel-section">
        <div class="panel-head">Writeback Transactions</div>
        ${c.written_to_graph?`
          <div class="comp-row"><span class="comp-icon">&#10003;</span><span>UPSERT InvestigationCase(${c.case_id})</span></div>
          <div class="comp-row"><span class="comp-icon">&#10003;</span><span>UPSERT INVOLVES &rarr; ${c.transaction_id}</span></div>
          <div class="comp-row"><span class="comp-icon">&#10003;</span><span>UPSERT ON_CARD &rarr; ${c.card_id}</span></div>
          <div class="comp-row"><span class="comp-icon">&#10003;</span><span>UPSERT CONNECTED_TO &rarr; ${c.customer_id}</span></div>
        `:`<div class="li-item" style="color:var(--tx-3)">No live writebacks performed.</div>`}
      </div>
    </div>
    
    <!-- Col 2 & 3 -->
    <div style="grid-column: span 2">
      <div class="panel-section">
        <div class="panel-head">Suspicious Activity Report (SAR) Output</div>
        <div class="sar-box ${c.sar_data&&c.sar_data.sar_required?'req':''}">
          <div class="sar-val" style="color:${c.sar_data&&c.sar_data.sar_required?'var(--red)':'var(--green)'}">${c.sar_data&&c.sar_data.sar_required?'SAR FILING REQUIRED':'SAR NOT REQUIRED'}</div>
          
          <div class="sar-kv"><div class="sar-k">Total Exposure</div><div class="sar-v font-mono">$${c.sar_data?c.sar_data.exposure_usd.toFixed(2):'0.00'} USD</div></div>
          <div class="sar-kv"><div class="sar-k">Internal Status</div><div class="sar-v">${c.sar_data?c.sar_data.sar_status.replace(/_/g,' '):'N/A'}</div></div>
          <div class="sar-kv"><div class="sar-k">Policy Rationale</div><div class="sar-v">${c.sar_data?c.sar_data.sar_rationale:'N/A'}</div></div>
          <div class="sar-kv"><div class="sar-k">FinCEN Ref</div><div class="sar-v">${c.sar_data&&c.sar_data.regulatory_references?c.sar_data.regulatory_references.join(', '):'None'}</div></div>
        </div>
        <div class="comp-note">
          <strong>Notice:</strong> This interface displays agent-generated SAR preparation data. Actual regulatory filings to FinCEN or equivalent bodies require final human review by an authorized L2 Compliance Officer regardless of the agent's recommendation.
        </div>
      </div>
    </div>
  </div>`;
}

window.addEventListener('load',init);
window.addEventListener('resize', () => {
    if(currentCase) drawSVGGraph(currentCase);
});
</script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
