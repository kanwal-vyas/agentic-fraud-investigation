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
    <title>TigerGraph Agentic Fraud Investigation Dashboard</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --danger: #f43f5e;
            --warning: #fbbf24;
            --success: #34d399;
            --border: #475569;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: var(--bg-primary); color: var(--text-primary); display: flex; height: 100vh; overflow: hidden; }
        
        #sidebar { width: 320px; background: var(--bg-secondary); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
        .sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); }
        .sidebar-header h1 { font-size: 1.1rem; color: var(--accent); display: flex; align-items: center; gap: 8px; }
        .sidebar-header p { font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; }
        
        #case-list { flex: 1; overflow-y: auto; padding: 10px; }
        .case-item { padding: 12px; margin-bottom: 8px; border-radius: 8px; background: var(--bg-card); cursor: pointer; border: 1px solid transparent; transition: all 0.2s; }
        .case-item:hover { border-color: var(--accent); transform: translateX(3px); }
        .case-item.active { border-color: var(--accent); background: #1e3a5f; box-shadow: 0 0 10px var(--accent-glow); }
        .case-header-row { display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 0.9rem; }
        .case-meta-row { font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px; display: flex; justify-content: space-between; }
        
        .badge { padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }
        .badge-fraud { background: rgba(244, 63, 94, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .badge-benign { background: rgba(52, 211, 153, 0.2); color: var(--success); border: 1px solid var(--success); }
        .badge-uncertain { background: rgba(251, 191, 36, 0.2); color: var(--warning); border: 1px solid var(--warning); }
        
        #main-content { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }
        .top-navbar { height: 60px; background: var(--bg-secondary); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 25px; }
        .top-navbar .case-title { font-size: 1.2rem; font-weight: bold; }
        
        .dashboard-grid { padding: 25px; display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }
        .card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-8 { grid-column: span 8; }
        .col-12 { grid-column: span 12; }
        
        .card h3 { font-size: 0.95rem; color: var(--accent); margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
        .stat-val { font-size: 1.5rem; font-weight: bold; color: var(--text-primary); margin: 4px 0; }
        .stat-sub { font-size: 0.8rem; color: var(--text-secondary); }
        
        .evidence-list { list-style: none; }
        .evidence-item { padding: 10px; border-radius: 6px; background: var(--bg-card); margin-bottom: 8px; font-size: 0.85rem; border-left: 3px solid var(--accent); }
        .evidence-item.historical { border-left-color: #a855f7; }
        .evidence-tag { font-size: 0.7rem; font-weight: bold; color: var(--accent); margin-bottom: 3px; }
        
        .timeline-step { padding: 10px; border-left: 2px solid var(--border); margin-left: 10px; position: relative; font-size: 0.85rem; }
        .timeline-step::before { content: ''; position: absolute; left: -6px; top: 12px; width: 10px; height: 10px; border-radius: 50%; background: var(--accent); }
        .timeline-tool { font-weight: bold; color: var(--accent); }
        
        pre { background: var(--bg-card); padding: 12px; border-radius: 6px; font-size: 0.8rem; overflow-x: auto; color: #e2e8f0; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="sidebar-header">
            <h1>⚡ TigerGraph Investigator</h1>
            <p>Agentic Fraud Console (20 Benchmark Cases)</p>
        </div>
        <div id="case-list">Loading cases...</div>
    </div>
    <div id="main-content">
        <div class="top-navbar">
            <div class="case-title" id="active-case-title">Select a Case</div>
            <div id="active-case-status"></div>
        </div>
        <div class="dashboard-grid" id="dashboard-body">
            <div class="card col-12"><p>Select a benchmark case from the left sidebar to view structured investigation evidence, GraphRAG precedents, NBA policy evaluation, and TigerGraph writeback.</p></div>
        </div>
    </div>

    <script>
        let allCases = [];
        let activeCaseId = "HHG-003";

        async function fetchCases() {
            try {
                const res = await fetch("/api/cases");
                allCases = await res.json();
                renderSidebar();
                if (allCases.length > 0) {
                    selectCase(activeCaseId);
                }
            } catch (err) {
                document.getElementById("case-list").innerHTML = "<p style='color:var(--danger);'>Error loading cases. Please ensure generator was run.</p>";
            }
        }

        function renderSidebar() {
            const listEl = document.getElementById("case-list");
            listEl.innerHTML = "";
            allCases.forEach(c => {
                const item = document.createElement("div");
                item.className = `case-item ${c.case_id === activeCaseId ? 'active' : ''}`;
                item.onclick = () => selectCase(c.case_id);
                
                let badgeClass = "badge-uncertain";
                if (c.fraud_assessment === "likely_fraud") badgeClass = "badge-fraud";
                if (c.fraud_assessment === "likely_benign") badgeClass = "badge-benign";

                item.innerHTML = `
                    <div class="case-header-row">
                        <span>${c.case_id}</span>
                        <span class="badge ${badgeClass}">${c.fraud_assessment}</span>
                    </div>
                    <div class="case-meta-row">
                        <span>${c.trigger.trigger_type}</span>
                        <span>$${c.transaction_amount.toFixed(2)}</span>
                    </div>
                `;
                listEl.appendChild(item);
            });
        }

        function selectCase(caseId) {
            activeCaseId = caseId;
            renderSidebar();
            const c = allCases.find(x => x.case_id === caseId);
            if (!c) return;

            document.getElementById("active-case-title").innerText = `Case ${c.case_id} — ${c.customer_id} (${c.card_id})`;
            document.getElementById("active-case-status").innerHTML = `<span class="badge badge-fraud" style="font-size:0.85rem;">STATUS: ${c.lifecycle_state}</span>`;

            const db = document.getElementById("dashboard-body");
            db.innerHTML = `
                <div class="card col-4">
                    <h3>🎯 Triage & Assessment</h3>
                    <div class="stat-val" style="color:${c.fraud_assessment === 'likely_fraud' ? 'var(--danger)' : c.fraud_assessment === 'likely_benign' ? 'var(--success)' : 'var(--warning)'};">${c.fraud_assessment.toUpperCase()}</div>
                    <div class="stat-sub">Investigation Confidence: ${(c.confidence * 100).toFixed(0)}% | Uncertainty: ${c.uncertainty_level}</div>
                    <p style="margin-top:10px; font-size:0.8rem; color:var(--text-secondary);">Input Model Risk Score: <strong>${c.trigger.model_risk_score.toFixed(2)}</strong> (Signal only)</p>
                </div>

                <div class="card col-4">
                    <h3>⚖️ Next Best Action & Guardrails</h3>
                    <div class="stat-val" style="font-size:1.2rem; color:var(--accent);">${c.recommended_nba}</div>
                    <div class="stat-sub">Approval Required: <strong>${c.approval_required}</strong> (Route: Level ${c.approval_route})</div>
                    <p style="margin-top:10px; font-size:0.8rem; color:var(--text-secondary);">Execution Status: <strong>${c.execution_status}</strong></p>
                </div>

                <div class="card col-4">
                    <h3>🏛️ FinCEN SAR & Graph Writeback</h3>
                    <div class="stat-val" style="font-size:1.2rem; color:${c.sar_data && c.sar_data.sar_required ? 'var(--danger)' : 'var(--success)'};">${c.sar_data && c.sar_data.sar_required ? 'SAR RECOMMENDED' : 'SAR NOT REQUIRED'}</div>
                    <div class="stat-sub">Total Exposure: $${c.sar_data ? c.sar_data.exposure_usd.toFixed(2) : '0.00'} USD</div>
                    <p style="margin-top:10px; font-size:0.8rem; color:var(--text-secondary);">TigerGraph Writeback: <strong>${c.written_to_graph ? 'SUCCESS (Case Vertex Linked)' : 'OFFLINE'}</strong></p>
                </div>

                <div class="card col-6">
                    <h3>🔎 Live Graph Evidence (${c.current_evidence.length} items)</h3>
                    <ul class="evidence-list">
                        ${c.current_evidence.map(e => `
                            <li class="evidence-item">
                                <div class="evidence-tag">[${e.source_type.toUpperCase()} | ${e.source_id}]</div>
                                <div>${e.statement}</div>
                            </li>
                        `).join('')}
                    </ul>
                </div>

                <div class="card col-6">
                    <h3>📜 GraphRAG Historical Precedents (${c.historical_evidence.length} cases)</h3>
                    <ul class="evidence-list">
                        ${c.historical_evidence.length > 0 ? c.historical_evidence.map(h => `
                            <li class="evidence-item historical">
                                <div class="evidence-tag" style="color:#c084fc;">[HISTORICAL CLOSED CASE | ${h.case_id}]</div>
                                <div>Retrieved prior confirmed investigation precedent from bank memory.</div>
                            </li>
                        `).join('') : '<li class="evidence-item">No historical precedents found.</li>'}
                    </ul>
                </div>

                <div class="card col-12">
                    <h3>⏱️ Investigation Tool Call Timeline (${c.investigation_steps.length} steps)</h3>
                    <div>
                        ${c.investigation_steps.map(s => `
                            <div class="timeline-step">
                                <div class="timeline-tool">Step ${s.step_number}: ${s.tool}</div>
                                <div style="font-size:0.75rem; color:var(--text-secondary); margin:2px 0;">Reason: ${s.reason}</div>
                                <div>${s.result_summary}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="card col-12">
                    <h3>📋 Investigation Summary & Explanation</h3>
                    <p style="font-size:0.9rem; line-height:1.5;">${c.summary}</p>
                </div>
            `;
        }

        window.onload = fetchCases;
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
