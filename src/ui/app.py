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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

/* === THEME TOKENS === */
:root, [data-theme="light"] {
  --bg-page: #f8eef7;
  --bg-surface: #fff9fd;
  --bg-surface-secondary: #f8eff8;
  --bg-surface-tertiary: #f3e5f2;
  --bg-inset: #e8d5e9;
  --border: #dcc9dc;
  --border-emphasis: #c8b1c8;
  --tx-primary: #302333;
  --tx-secondary: #6f6073;
  --tx-muted: #8c7e90;
  --tx-faint: #ad9eb1;
  --danger: #c6284a;
  --danger-dim: rgba(198, 40, 74, .08);
  --warning: #c58a00;
  --warning-dim: rgba(197, 138, 0, .08);
  --success: #2e7d52;
  --success-dim: rgba(46, 125, 82, .08);
  --info: #3b82c4;
  --info-dim: rgba(59, 130, 196, .08);
  --history: #8064a2;
  --history-dim: rgba(128, 100, 162, .08);
  --node-customer: #3b82c4;
  --node-card: #2a9d8f;
  --node-transaction: #d8902f;
  --node-case: #c94c5c;
  --node-history: #8064a2;
  --graph-edge: #c2b0c2;
  --graph-edge-hover: #a692a6;
  --graph-node-fill-opacity: 0.12;
  --graph-label-bg: #fff9fd;
  --tooltip-bg: #fff9fd;
  --tooltip-border: #dcc9dc;
  --tooltip-shadow: 0 8px 24px rgba(109, 59, 114, 0.1);
  --tab-active-border: #6d3b72;
  --sidebar-active-bg: #f8eff8;
  --sidebar-active-border: #6d3b72;
  --confidence-track: #f3e5f2;
  --selection-ring: #6d3b72;
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-display: 'Source Serif 4', 'Georgia', serif;
  --font-mono: 'JetBrains Mono', 'Consolas', monospace;
  --radius: 5px;
}

[data-theme="dark"] {
  --bg-page: #24141d;
  --bg-surface: #351d2b;
  --bg-surface-secondary: #402235;
  --bg-surface-tertiary: #4a273e;
  --bg-inset: #2d1824;
  --border: #5b394b;
  --border-emphasis: #754a61;
  --tx-primary: #f8eaf2;
  --tx-secondary: #cbb7c4;
  --tx-muted: #9f8795;
  --tx-faint: #7a6372;
  --danger: #f05d78;
  --danger-dim: rgba(240, 93, 120, .12);
  --warning: #e5b84b;
  --warning-dim: rgba(229, 184, 75, .12);
  --success: #6fcf8b;
  --success-dim: rgba(111, 207, 139, .12);
  --info: #569cd6;
  --info-dim: rgba(86, 156, 214, .12);
  --history: #a885c9;
  --history-dim: rgba(168, 133, 201, .12);
  --node-customer: #569cd6;
  --node-card: #4ec9b0;
  --node-transaction: #e5a85b;
  --node-case: #e06c75;
  --node-history: #a885c9;
  --graph-edge: #634857;
  --graph-edge-hover: #8c6d80;
  --graph-node-fill-opacity: 0.15;
  --graph-label-bg: #351d2b;
  --tooltip-bg: #402235;
  --tooltip-border: #5b394b;
  --tooltip-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  --tab-active-border: #b77bc0;
  --sidebar-active-bg: #402235;
  --sidebar-active-border: #b77bc0;
  --confidence-track: #402235;
  --selection-ring: #f8eaf2;
}

html,body{height:100%;overflow:hidden;background:var(--bg-page);color:var(--tx-primary);font-family:var(--font-sans);font-size:13px;line-height:1.55;-webkit-font-smoothing:antialiased;transition:background .2s,color .2s}

/* === SYSTEM BAR === */
.sysbar{height:44px;background:var(--bg-surface);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:16px;flex-shrink:0;z-index:100;transition:background .2s,border-color .2s}
.sysbar-brand{font-weight:600;font-size:13px;color:var(--tx-primary);letter-spacing:.2px;display:flex;align-items:center;gap:8px}
.sysbar-brand svg{width:16px;height:16px;fill:var(--info);stroke:var(--info)}
.sysbar-sep{width:1px;height:20px;background:var(--border)}
.sysbar-tag{font-size:11px;font-weight:500;padding:2px 8px;border-radius:10px;letter-spacing:.3px}
.sysbar-tag.live{background:var(--success-dim);color:var(--success);border:1px solid transparent}
.sysbar-tag.info{background:var(--info-dim);color:var(--info);border:1px solid transparent}
.sysbar-right{margin-left:auto;display:flex;align-items:center;gap:14px;font-size:11px;color:var(--tx-muted)}

/* Theme toggle */
.theme-toggle{background:none;border:1px solid var(--border);color:var(--tx-secondary);padding:4px 10px;border-radius:16px;cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px;transition:all .15s;font-family:var(--font-sans);line-height:1}
.theme-toggle:hover{border-color:var(--border-emphasis);color:var(--tx-primary);background:var(--bg-surface-secondary)}
.theme-toggle:focus-visible{outline:2px solid var(--info);outline-offset:2px}
.theme-toggle .theme-icon{font-size:14px;line-height:1}

/* === LAYOUT === */
.layout{display:flex;height:calc(100vh - 44px)}

/* === CASE NAV === */
.case-nav{width:220px;background:var(--bg-surface);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;transition:background .2s,border-color .2s}
.case-nav-head{padding:14px 16px 10px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--tx-muted)}
.case-scroll{flex:1;overflow-y:auto;padding:0 8px 8px}
.case-scroll::-webkit-scrollbar{width:4px}
.case-scroll::-webkit-scrollbar-thumb{background:var(--border-emphasis);border-radius:4px}
.ci{padding:8px 12px;border-radius:var(--radius);cursor:pointer;margin-bottom:2px;display:flex;align-items:center;justify-content:space-between;transition:background .15s}
.ci:hover{background:var(--bg-surface-secondary)}
.ci.active{background:var(--sidebar-active-bg);box-shadow:inset 2px 0 0 var(--sidebar-active-border)}
.ci-id{font-weight:500;font-size:12px;font-family:var(--font-mono);color:var(--tx-primary)}
.ci-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.ci-dot.fraud{background:var(--danger)}.ci-dot.benign{background:var(--success)}.ci-dot.uncertain{background:var(--warning)}

/* === MAIN === */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* === CASE HEADER === */
.case-head{padding:18px 28px 14px;background:var(--bg-surface);border-bottom:1px solid var(--border);flex-shrink:0;transition:background .2s,border-color .2s}
.case-head-top{display:flex;align-items:baseline;gap:14px;margin-bottom:6px}
.case-head-id{font-size:22px;font-weight:700;font-family:var(--font-display);letter-spacing:-.3px;color:var(--tx-primary)}
.case-head-label{font-size:11px;font-weight:500;padding:3px 10px;border-radius:10px}
.case-head-label.fraud{background:var(--danger-dim);color:var(--danger)}.case-head-label.benign{background:var(--success-dim);color:var(--success)}.case-head-label.uncertain{background:var(--warning-dim);color:var(--warning)}
.case-head-meta{display:flex;gap:20px;font-size:12px;color:var(--tx-muted)}
.case-head-meta span{display:flex;align-items:center;gap:4px}
.case-head-meta .mono{font-family:var(--font-mono);font-size:11px;color:var(--tx-secondary)}

/* === WORKSPACE TABS === */
.ws-tabs{display:flex;background:var(--bg-surface);border-bottom:1px solid var(--border);padding:0 28px;flex-shrink:0;transition:background .2s,border-color .2s}
.ws-tab{padding:10px 16px;font-size:12px;font-weight:500;color:var(--tx-muted);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;background:none;border-top:none;border-left:none;border-right:none;font-family:var(--font-sans)}
.ws-tab:hover{color:var(--tx-secondary)}
.ws-tab.active{color:var(--tx-primary);border-bottom-color:var(--tab-active-border)}
.ws-tab:focus-visible{outline:2px solid var(--info);outline-offset:-2px}

/* === WORKSPACE CONTENT === */
.ws-body{flex:1;overflow-y:auto;overflow-x:hidden;background:var(--bg-page);transition:background .2s}
.ws-body::-webkit-scrollbar{width:6px}
.ws-body::-webkit-scrollbar-thumb{background:var(--border-emphasis);border-radius:4px}
.ws-panel{display:none;padding:24px 28px}
.ws-panel.active{display:block}

/* === INVESTIGATION TAB === */
.inv-layout{display:grid;grid-template-columns:280px 1fr 260px;gap:24px;min-height:600px}
.inv-col{display:flex;flex-direction:column;gap:16px}

/* Agent Workflow */
.trigger-block{background:var(--bg-surface);border-radius:var(--radius);padding:14px 16px;border-left:3px solid var(--warning);transition:background .2s}
.trigger-type{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--warning);margin-bottom:4px}
.trigger-text{font-size:12px;color:var(--tx-secondary);font-style:italic;line-height:1.6}

.step{position:relative;padding:10px 14px;background:var(--bg-surface);border-radius:var(--radius);cursor:pointer;transition:background .15s}
.step:hover{background:var(--bg-surface-secondary)}
.step-num{font-size:10px;font-weight:600;color:var(--info);font-family:var(--font-mono);margin-bottom:2px}
.step-tool{font-size:12px;font-weight:600;color:var(--tx-primary);margin-bottom:2px}
.step-brief{font-size:11px;color:var(--tx-muted);display:flex;align-items:center;gap:6px}
.step-brief .live-dot{width:5px;height:5px;border-radius:50%;background:var(--success);display:inline-block}
.step-detail{display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;color:var(--tx-secondary);line-height:1.6}
.step.open .step-detail{display:block}
.step-connector{width:1px;height:12px;background:var(--border-emphasis);margin:0 auto}

/* Graph Canvas */
.graph-wrap{background:var(--bg-surface);border-radius:var(--radius);border:1px solid var(--border);flex:1;min-height:0;position:relative;overflow:hidden;transition:background .2s,border-color .2s}
.graph-wrap canvas{display:block}
.graph-title{position:absolute;top:10px;left:14px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--tx-muted);z-index:2}
.graph-legend{position:absolute;bottom:10px;left:14px;display:flex;gap:10px;z-index:2}
.graph-legend span{font-size:10px;color:var(--tx-muted);display:flex;align-items:center;gap:4px}
.graph-legend .ldot{width:8px;height:8px;border-radius:50%}

/* Decision Rail */
.decision-section{margin-bottom:16px}
.decision-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--tx-muted);margin-bottom:6px}
.decision-value{font-size:14px;font-weight:700;margin-bottom:4px}
.decision-sub{font-size:11px;color:var(--tx-muted);line-height:1.5}
.decision-divider{height:1px;background:var(--border);margin:12px 0}
.approval-flow{display:flex;flex-direction:column;gap:0;align-items:flex-start}
.af-step{display:flex;align-items:center;gap:8px;font-size:11px;padding:4px 0}
.af-icon{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0}
.af-icon.done{background:var(--success-dim);color:var(--success)}.af-icon.pending{background:var(--warning-dim);color:var(--warning)}.af-icon.wait{background:var(--bg-surface-tertiary);color:var(--tx-muted)}
.af-line{width:1px;height:10px;background:var(--border-emphasis);margin-left:9px}
.confidence-bar-wrap{margin-top:12px}
.confidence-bar-bg{height:4px;background:var(--confidence-track);border-radius:2px;overflow:hidden}
.confidence-bar-fill{height:100%;border-radius:2px;transition:width .4s}

/* === REASONING TAB === */
.reason-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.reason-full{grid-column:1/-1}
.signal-group{margin-bottom:16px}
.signal-head{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;display:flex;align-items:center;gap:6px;color:var(--tx-secondary)}
.signal-head .sdot{width:6px;height:6px;border-radius:50%}
.signal-item{font-size:12px;color:var(--tx-secondary);padding:6px 0;border-bottom:1px solid var(--border);line-height:1.5}
.signal-item:last-child{border-bottom:none}
.hist-case{padding:10px 14px;background:var(--bg-surface);border-radius:var(--radius);margin-bottom:8px;cursor:pointer;transition:background .15s}
.hist-case:hover{background:var(--bg-surface-secondary)}
.hist-case-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.hist-case-id{font-weight:600;font-family:var(--font-mono);font-size:12px;color:var(--tx-primary)}
.hist-case-tag{font-size:10px;font-weight:500;padding:2px 6px;border-radius:8px}
.hist-case-tag.fraud{background:var(--danger-dim);color:var(--danger)}.hist-case-tag.cleared{background:var(--success-dim);color:var(--success)}
.hist-case-detail{font-size:11px;color:var(--tx-muted);display:none;margin-top:6px;padding-top:6px;border-top:1px solid var(--border);line-height:1.5}
.hist-case.open .hist-case-detail{display:block}
.hist-case-meta{font-size:11px;color:var(--tx-muted);display:flex;gap:12px}
.relevance-bar{width:60px;height:4px;background:var(--confidence-track);border-radius:2px;overflow:hidden;display:inline-block;vertical-align:middle}
.relevance-fill{height:100%;background:var(--info);border-radius:2px}

/* metrics row */
.metrics-row{display:flex;gap:24px;padding:16px 0;border-bottom:1px solid var(--border);margin-bottom:16px}
.metric{display:flex;flex-direction:column;gap:2px}
.metric-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--tx-muted)}
.metric-value{font-size:18px;font-weight:700;color:var(--tx-primary)}

/* === COMPLIANCE TAB === */
.compliance-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}
.compliance-section{background:var(--bg-surface);border-radius:var(--radius);padding:16px;transition:background .2s}
.comp-head{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--tx-muted);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.policy-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;color:var(--tx-secondary)}
.policy-check{color:var(--success);font-size:11px}
.lifecycle-flow{display:flex;flex-direction:column;gap:0}
.lf-step{padding:6px 0;font-size:12px;display:flex;align-items:center;gap:8px;color:var(--tx-secondary)}
.lf-step .lf-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.lf-step .lf-dot.done{background:var(--success)}.lf-step .lf-dot.current{background:var(--warning);box-shadow:0 0 6px var(--warning)}.lf-step .lf-dot.future{background:var(--confidence-track)}
.lf-line{width:1px;height:8px;background:var(--border-emphasis);margin-left:3.5px}
.wb-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;color:var(--tx-secondary)}
.wb-check{color:var(--success);font-size:11px}
.sar-status{font-size:16px;font-weight:600;margin-bottom:8px}
.sar-detail{font-size:11px;color:var(--tx-secondary);line-height:1.6}
.comp-note{margin-top:12px;padding:10px;background:var(--bg-surface-secondary);border-radius:var(--radius);font-size:11px;color:var(--tx-muted);line-height:1.5;border-left:2px solid var(--warning)}

/* Evidence panel in reasoning */
.evidence-section{background:var(--bg-surface);border-radius:var(--radius);padding:16px;transition:background .2s}
.ev-head{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--tx-muted);margin-bottom:10px}
.ev-item{padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--tx-secondary);line-height:1.5}
.ev-item:last-child{border-bottom:none}
.ev-source{font-size:10px;color:var(--tx-muted);font-family:var(--font-mono);margin-top:2px}

@media(max-width:1280px){
  .inv-layout{grid-template-columns:240px 1fr 240px}
  .case-nav{width:200px}
}

/* Graph SVG Elements */
.svg-edge{stroke:var(--graph-edge);stroke-width:1.5px;transition:stroke 0.2s}
.svg-edge.interactive{cursor:pointer}
.svg-edge:hover{stroke:var(--graph-edge-hover);stroke-width:2.5px}
.svg-edge-label-bg{fill:var(--graph-label-bg)}
.svg-edge-label{fill:var(--tx-muted);font-size:9px;font-weight:500;font-family:var(--font-sans);text-anchor:middle;dominant-baseline:central;pointer-events:none}
.svg-node{cursor:pointer}
.svg-node-circle{stroke-width:2px;transition:all 0.2s}
.svg-node:hover .svg-node-circle{filter:brightness(1.15);stroke-width:3px}
.svg-node.selected .svg-node-circle{stroke-width:3px !important;stroke-dasharray:4;animation:dash 10s linear infinite;filter:brightness(1.15)}
@keyframes dash { to { stroke-dashoffset: 100; } }
.svg-node-label{fill:var(--tx-primary);font-size:11px;font-family:var(--font-mono);font-weight:500;text-anchor:middle;pointer-events:none}
.svg-node-sub{fill:var(--tx-muted);font-size:9px;font-family:var(--font-sans);text-anchor:middle;pointer-events:none}

/* Graph Tooltip */
.graph-tooltip{position:absolute;background:var(--tooltip-bg);border:1px solid var(--tooltip-border);border-radius:var(--radius);padding:10px 14px;color:var(--tx-primary);font-size:12px;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:100;box-shadow:var(--tooltip-shadow);transform:translate(-50%,-100%);margin-top:-10px;white-space:nowrap}
.tt-type{font-size:10px;color:var(--tx-muted);text-transform:uppercase;margin-bottom:4px;font-weight:600}
.tt-id{font-size:13px;font-family:var(--font-mono);font-weight:600;margin-bottom:6px}
.tt-meta{display:flex;flex-direction:column;gap:2px;font-size:11px;color:var(--tx-secondary)}

/* Entity Details Panel (floating below) */
.entity-details{background:var(--bg-surface);border-top:1px solid var(--border);padding:16px;min-height:140px;display:flex;flex-direction:column;position:absolute;bottom:0;left:0;right:0;z-index:50;transition:background .2s,border-color .2s}
.ed-empty{color:var(--tx-muted);font-size:12px;font-style:italic;margin:auto;text-align:center}
.ed-content{display:none;flex-direction:column;height:100%}
.ed-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.ed-type{font-size:10px;font-weight:600;color:var(--tx-muted);text-transform:uppercase;letter-spacing:.5px}
.ed-id{font-size:16px;font-weight:600;font-family:var(--font-mono);color:var(--tx-primary);margin-top:2px}
.ed-body{display:flex;gap:32px;font-size:12px}
.ed-col{display:flex;flex-direction:column;gap:8px;flex:1}
.ed-lbl{color:var(--tx-muted)}
.ed-val{color:var(--tx-secondary)}
.ed-nav-btn{background:var(--bg-surface-secondary);border:1px solid var(--border);color:var(--tx-secondary);padding:4px 10px;border-radius:var(--radius);font-size:11px;cursor:pointer;transition:background 0.1s;display:inline-block;margin-top:8px;font-family:var(--font-sans)}
.ed-nav-btn:hover{background:var(--bg-surface-tertiary);color:var(--tx-primary)}
.ed-nav-btn:focus-visible{outline:2px solid var(--info);outline-offset:2px}

/* Auth States */
.auth-title{font-size:11px;font-weight:600}
.text-red{color:var(--danger)}
.text-green{color:var(--success)}
.text-amber{color:var(--warning)}
</style>
</head>
<body data-theme="dark">

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
    <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" aria-label="Switch theme">
      <span class="theme-icon" id="theme-icon">☀</span>
    </button>
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

/* === THEME SYSTEM === */
function getTheme(){return document.body.getAttribute('data-theme')||'dark'}
function setTheme(t){
  document.body.setAttribute('data-theme',t);
  localStorage.setItem('hhg-theme',t);
  const icon=document.getElementById('theme-icon');
  const btn=document.getElementById('theme-toggle');
  if(icon)icon.textContent=t==='dark'?'\u2600':'\u25D1';
  if(btn)btn.setAttribute('aria-label',t==='dark'?'Switch to light mode':'Switch to dark mode');
  // Redraw graph with new theme colors
  const c=allCases.find(x=>x.case_id===activeId);
  if(c)requestAnimationFrame(()=>drawGraph(c));
}
function toggleTheme(){setTheme(getTheme()==='dark'?'light':'dark')}
// Apply saved theme
(function(){const saved=localStorage.getItem('hhg-theme');if(saved)document.body.setAttribute('data-theme',saved);const icon=document.getElementById('theme-icon');if(icon)icon.textContent=(saved||'dark')==='dark'?'\u2600':'\u25D1';})();

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
    document.getElementById('case-list').innerHTML=`<div style="padding:20px;color:var(--danger);word-break:break-all">${e.message}<br><br>${e.stack}</div>`;
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
    `<span>${c.written_to_graph?'<span style="color:var(--success)">&#9679;</span> Live Writeback':'<span style="color:var(--tx-faint)">&#9675;</span> Offline'}</span>`;

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
      <div class="step-detail">${s.result_summary}<br><br><em style="color:var(--tx-faint)">Reason: ${s.reason}</em></div>
    </div>`;
  });

  // Decision rail
  let assessClass='uncertain';
  if(c.fraud_assessment==='likely_fraud')assessClass='fraud';
  if(c.fraud_assessment==='likely_benign')assessClass='benign';
  let nbaColor=c.recommended_nba==='BLOCK_CARD'?'var(--danger)':c.recommended_nba==='VERIFY_WITH_CUSTOMER'?'var(--warning)':'var(--tx-primary)';
  let confPct=Math.round(c.confidence*100);
  let confColor=confPct>=70?'var(--danger)':confPct>=50?'var(--warning)':'var(--tx-muted)';
  let uncColor=c.uncertainty_level==='high'?'var(--warning)':c.uncertainty_level==='low'?'var(--success)':'var(--tx-secondary)';

  let decisionHtml=`
    <div class="decision-section">
      <div class="decision-label">Assessment</div>
      <div class="decision-value" style="color:${assessClass==='fraud'?'var(--danger)':assessClass==='benign'?'var(--success)':'var(--warning)'}">${c.fraud_assessment.replace(/_/g,' ').toUpperCase()}</div>
      <div class="confidence-bar-wrap">
        <div style="font-size:10px;color:var(--tx-faint);margin-bottom:3px">Confidence ${confPct}%</div>
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
            ? '<div class="af-step"><div class="af-icon wait" style="color:var(--danger)">&#10005;</div><span class="auth-title text-red">Execution Denied</span></div>'
            : c.approval_required
            ? '<div class="af-step"><div class="af-icon wait">○</div><span class="auth-title" style="color:var(--tx-muted)">Execution: Pending Approval</span></div>'
            : '<div class="af-step"><div class="af-icon wait">○</div><span class="auth-title" style="color:var(--tx-muted)">Ready for Execution</span></div>'}
      </div>
    </div>
    <div class="decision-divider"></div>
    <div class="decision-section">
      <div class="decision-label">Lifecycle</div>
      <div style="font-size:12px;font-weight:500;color:var(--tx-secondary)">${c.lifecycle_state.replace(/_/g,' ')}</div>
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
          <span><span class="ldot" style="background:var(--node-customer)"></span>Customer</span>
          <span><span class="ldot" style="background:var(--node-card)"></span>Card</span>
          <span><span class="ldot" style="background:var(--node-transaction)"></span>Transaction</span>
          <span><span class="ldot" style="background:var(--node-case)"></span>Case</span>
          <span><span class="ldot" style="background:var(--node-history)"></span>History</span>
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

  const cs=getComputedStyle(document.documentElement);
  const nodeColors={customer:cs.getPropertyValue('--node-customer').trim(),card:cs.getPropertyValue('--node-card').trim(),transaction:cs.getPropertyValue('--node-transaction').trim(),case_:cs.getPropertyValue('--node-case').trim(),history:cs.getPropertyValue('--node-history').trim()};

  svgNodes.push({id:c.customer_id,label:c.customer_id,type:'Customer',x:startX,y:startY,r:24,color:nodeColors.customer});
  svgNodes.push({id:c.card_id,label:c.card_id,type:'Card',x:startX,y:startY+spacingY,r:20,color:nodeColors.card});
  svgNodes.push({id:String(c.transaction_id),label:'$'+(c.sar_data?c.sar_data.exposure_usd.toFixed(0):'?'),type:'Transaction',x:startX,y:startY+spacingY*2,r:18,color:nodeColors.transaction});
  
  // Case node offset to the left of the transaction
  svgNodes.push({id:c.case_id,label:c.case_id,type:'Case',x:startX-120,y:startY+spacingY*1.5,r:20,color:nodeColors.case_});
  
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
      svgNodes.push({id:h.case_id,label:h.case_id,type:'History',x:hx,y:hy,r:14,color:nodeColors.history});
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
    const fillOp=getComputedStyle(document.documentElement).getPropertyValue('--graph-node-fill-opacity').trim()||'0.12';
    bg.setAttribute('r',n.r);bg.setAttribute('fill',n.color);bg.setAttribute('fill-opacity',fillOp);
    
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
  tt.innerHTML=`<div class="tt-type">Relationship</div><div class="tt-id" style="color:var(--tx-secondary)">${e.from} &rarr; ${e.to}</div><div class="tt-meta">${e.label}</div>`;
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
  document.getElementById('ed-id').innerHTML=`<span style="color:var(--tx-faint)">${e.from}</span> &rarr; <span style="color:var(--tx-faint)">${e.to}</span>`;
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
    bodyHtml+=`<div><span class="ed-lbl">Status:</span> <span class="ed-val" style="color:${status==='CONFIRMED_FRAUD'?'var(--danger)':'var(--tx-secondary)'}">${status.replace(/_/g,' ')}</span></div>`;
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
      <div class="hist-case-detail">${h.graphrag_selected ? 'Retrieved via GraphRAG from bank case memory.' : 'Historical case linked via graph.'}<br>Source: ${h.source}</div>
    </div>`;
  });

  el.innerHTML=`
  <div class="metrics-row">
    <div class="metric"><div class="metric-label">Confidence</div><div class="metric-value">${confPct}%</div></div>
    <div class="metric"><div class="metric-label">Uncertainty</div><div class="metric-value" style="color:${c.uncertainty_level==='high'?'var(--warning)':'var(--tx-primary)'}">${c.uncertainty_level.toUpperCase()}</div></div>
    <div class="metric"><div class="metric-label">Evidence Items</div><div class="metric-value">${(c.current_evidence||[]).length}</div></div>
    <div class="metric"><div class="metric-label">Tools Used</div><div class="metric-value">${c.tool_call_count}</div></div>
    <div class="metric"><div class="metric-label">Prior Cases</div><div class="metric-value">${(c.historical_evidence||[]).length}</div></div>
  </div>

  <div class="reason-grid">
    <div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--danger)"></span> Strong Signals</div>
        ${(c.supporting_findings||[]).map(f=>`<div class="signal-item">${f}</div>`).join('')||'<div class="signal-item" style="color:var(--tx-faint)">None</div>'}
      </div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--success)"></span> Counter-Signals</div>
        ${(c.contradictory_findings||[]).map(f=>`<div class="signal-item">${f}</div>`).join('')||'<div class="signal-item" style="color:var(--tx-faint)">None</div>'}
      </div>
    </div>
    <div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--warning)"></span> Uncertainty Factors</div>
        ${(c.uncertainty_reasons||[]).map(r=>`<div class="signal-item">${r}</div>`).join('')}
        ${(c.evidence_gaps||[]).map(g=>`<div class="signal-item" style="color:var(--warning)">Gap: ${g}</div>`).join('')}
      </div>
      <div class="signal-group">
        <div class="signal-head"><span class="sdot" style="background:var(--info)"></span> Explanation</div>
        ${c.explanation&&c.explanation.why_suspicious?(c.explanation.why_suspicious.map(r=>`<div class="signal-item">${r}</div>`).join('')):''}
        ${c.explanation&&c.explanation.why_action?(c.explanation.why_action.map(r=>`<div class="signal-item" style="color:var(--tx-muted)">${r}</div>`).join('')):''}
      </div>
    </div>
    <div>
      <div class="signal-head" style="margin-bottom:10px"><span class="sdot" style="background:var(--history)"></span> Historical Case Links</div>
      ${histHtml||'<div style="font-size:12px;color:var(--tx-faint)">No historical cases found.</div>'}
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
      ${policyRules.length>0?policyRules.map(r=>`<div class="policy-row"><span class="policy-check">&#10003;</span>${r}</div>`).join(''):'<div style="font-size:12px;color:var(--tx-faint)">No policy rules explicitly recorded.</div>'}
      <div style="margin-top:12px;font-size:11px;color:var(--tx-muted)">
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
      `:`<div style="font-size:12px;color:var(--tx-faint)">Writeback not performed (offline mode).</div>`}
    </div>

    <div class="compliance-section" style="grid-column:1/-1">
      <div class="comp-head">SAR Preparation & Compliance</div>
      <div class="sar-status" style="color:${c.sar_data&&c.sar_data.sar_required?'var(--danger)':'var(--success)'}">${c.sar_data&&c.sar_data.sar_required?'SAR PREPARATION REQUIRED':'SAR NOT REQUIRED'}</div>
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
