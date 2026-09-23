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
    <title>TigerGraph Agentic Fraud Investigation Console</title>
    <style>
        :root {
            --bg-primary: #0B1120;
            --bg-secondary: #111827;
            --bg-card: #1F2937;
            --text-primary: #F9FAFB;
            --text-secondary: #9CA3AF;
            --accent-blue: #3B82F6;
            --accent-cyan: #06B6D4;
            --danger: #EF4444;
            --warning: #F59E0B;
            --success: #10B981;
            --border: #374151;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, sans-serif; }
        body { background: var(--bg-primary); color: var(--text-primary); display: flex; height: 100vh; overflow: hidden; }
        
        #sidebar { width: 340px; background: var(--bg-secondary); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
        .sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); }
        .sidebar-header h1 { font-size: 1.1rem; color: var(--accent-cyan); display: flex; align-items: center; gap: 8px; }
        .sidebar-header p { font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; }
        
        #case-list { flex: 1; overflow-y: auto; padding: 10px; }
        .case-item { padding: 12px; margin-bottom: 8px; border-radius: 6px; background: var(--bg-card); cursor: pointer; border: 1px solid transparent; transition: all 0.2s; }
        .case-item:hover { border-color: var(--accent-cyan); }
        .case-item.active { border-color: var(--accent-cyan); background: #1e3a5f; }
        .case-header-row { display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 0.9rem; }
        .case-meta-row { font-size: 0.75rem; color: var(--text-secondary); margin-top: 6px; display: flex; justify-content: space-between; }
        
        .badge { padding: 3px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: bold; text-transform: uppercase; border: 1px solid; }
        .badge-fraud { background: rgba(239, 68, 68, 0.1); color: var(--danger); border-color: rgba(239, 68, 68, 0.3); }
        .badge-benign { background: rgba(16, 185, 129, 0.1); color: var(--success); border-color: rgba(16, 185, 129, 0.3); }
        .badge-uncertain { background: rgba(245, 158, 11, 0.1); color: var(--warning); border-color: rgba(245, 158, 11, 0.3); }
        .badge-live { background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); border-color: var(--accent-blue); }
        .badge-offline { background: rgba(156, 163, 175, 0.1); color: var(--text-secondary); border-color: var(--text-secondary); }
        
        #main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg-primary); }
        
        .top-navbar { height: 70px; background: var(--bg-secondary); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 25px; flex-shrink: 0; }
        .case-title { font-size: 1.3rem; font-weight: 600; }
        .system-status { display: flex; gap: 10px; }
        
        .tab-bar { display: flex; background: var(--bg-secondary); border-bottom: 1px solid var(--border); padding: 0 25px; flex-shrink: 0; }
        .tab-btn { padding: 15px 20px; color: var(--text-secondary); background: none; border: none; font-size: 0.9rem; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab-btn:hover { color: var(--text-primary); }
        .tab-btn.active { color: var(--accent-cyan); border-bottom-color: var(--accent-cyan); }
        
        #dashboard-body { flex: 1; overflow-y: auto; padding: 25px; }
        
        .grid-container { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }
        .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-8 { grid-column: span 8; }
        .col-12 { grid-column: span 12; }
        
        .card-header { font-size: 1rem; color: var(--accent-cyan); margin-bottom: 15px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
        
        .stat-val { font-size: 1.6rem; font-weight: 600; margin-bottom: 5px; }
        .stat-sub { font-size: 0.85rem; color: var(--text-secondary); }
        
        .timeline-step { padding: 12px 15px; border-left: 2px solid var(--border); margin-left: 10px; position: relative; font-size: 0.85rem; background: rgba(0,0,0,0.2); border-radius: 0 6px 6px 0; margin-bottom: 10px; }
        .timeline-step::before { content: ''; position: absolute; left: -7px; top: 16px; width: 12px; height: 12px; border-radius: 50%; background: var(--accent-cyan); border: 2px solid var(--bg-card); }
        .timeline-tool { font-weight: 600; color: var(--accent-blue); font-size: 0.95rem; margin-bottom: 4px; }
        .timeline-reason { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 8px; font-style: italic; }
        
        .evidence-list { list-style: none; }
        .evidence-item { padding: 12px; border-radius: 6px; background: rgba(0,0,0,0.2); margin-bottom: 10px; font-size: 0.85rem; border-left: 3px solid var(--accent-blue); line-height: 1.4; }
        .evidence-item.historical { border-left-color: #8B5CF6; }
        .evidence-tag { font-size: 0.7rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 5px; text-transform: uppercase; }
        
        .list-group { margin-bottom: 15px; }
        .list-group li { font-size: 0.85rem; margin-bottom: 6px; margin-left: 18px; color: #D1D5DB; }
        
        .graph-container { width: 100%; height: 350px; background: #0F172A; border-radius: 6px; border: 1px solid var(--border); position: relative; overflow: hidden; }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="sidebar-header">
            <h1>&#x2B21; TigerGraph Investigator</h1>
            <p>Agentic Fraud Console</p>
        </div>
        <div id="case-list">Loading cases...</div>
    </div>
    <div id="main-content">
        <div class="top-navbar">
            <div class="case-title" id="active-case-title">Select a Case</div>
            <div class="system-status" id="system-badges">
                <span class="badge badge-offline">System Loading</span>
            </div>
        </div>
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchTab('tab1')">1. Investigation & Workflow</button>
            <button class="tab-btn" onclick="switchTab('tab2')">2. Deep Reasoning</button>
            <button class="tab-btn" onclick="switchTab('tab3')">3. Compliance & Memory</button>
        </div>
        <div id="dashboard-body">
            <!-- Dynamic Content Injected Here -->
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
                document.getElementById("case-list").innerHTML = "<p style='color:var(--danger); padding:20px;'>Error loading cases.</p>";
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
                        <span class="badge ${badgeClass}">${c.fraud_assessment.replace(/_/g, ' ')}</span>
                    </div>
                    <div class="case-meta-row">
                        <span>${c.customer_id} | ${c.card_id}</span>
                        <span>$${c.transaction_amount.toFixed(2)}</span>
                    </div>
                `;
                listEl.appendChild(item);
            });
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            
            // Assuming this is triggered by a click event
            if(window.event && window.event.currentTarget) {
                window.event.currentTarget.classList.add('active');
            } else {
                // Fallback: manually find and set active btn if called programmatically
                if(tabId === 'tab1') document.querySelectorAll('.tab-btn')[0].classList.add('active');
                if(tabId === 'tab2') document.querySelectorAll('.tab-btn')[1].classList.add('active');
                if(tabId === 'tab3') document.querySelectorAll('.tab-btn')[2].classList.add('active');
            }
            
            document.getElementById(tabId).classList.add('active');
        }

        function renderGraphSVG(c) {
            let nodes = [
                { id: c.customer_id, label: 'Customer', sub: c.customer_id, type: 'customer', x: 250, y: 50 },
                { id: c.card_id, label: 'Card', sub: c.card_id, type: 'card', x: 250, y: 150 },
                { id: c.transaction_id, label: 'Transaction', sub: c.transaction_id, type: 'transaction', x: 250, y: 250 },
                { id: c.case_id, label: 'Investigation Case', sub: c.case_id, type: 'case', x: 80, y: 150 }
            ];
            
            let edges = [
                { source: c.customer_id, target: c.card_id, label: 'owns' },
                { source: c.card_id, target: c.transaction_id, label: 'charged' },
                { source: c.transaction_id, target: c.case_id, label: 'investigates' },
                { source: c.customer_id, target: c.case_id, label: 'investigates' }
            ];
            
            if (c.historical_evidence && c.historical_evidence.length > 0) {
                const maxDisplay = 3;
                const toDisplay = c.historical_evidence.slice(0, maxDisplay);
                toDisplay.forEach((h, i) => {
                    let yPos = 50 + (i * 90);
                    nodes.push({ id: h.case_id, label: 'Closed Case', sub: h.case_id, type: 'history', x: 450, y: yPos });
                    edges.push({ source: c.customer_id, target: h.case_id, label: 'prior' });
                });
            }

            let svg = `<svg width="100%" height="100%" viewBox="0 0 600 300">
                <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
                    </marker>
                </defs>`;
                
            edges.forEach(e => {
                let n1 = nodes.find(n => n.id === e.source);
                let n2 = nodes.find(n => n.id === e.target);
                if(n1 && n2) {
                    svg += `<line x1="${n1.x}" y1="${n1.y}" x2="${n2.x}" y2="${n2.y}" stroke="#475569" stroke-width="2" marker-end="url(#arrow)" />`;
                }
            });

            nodes.forEach(n => {
                let fill = n.type === 'customer' ? '#2563EB' : 
                           n.type === 'card' ? '#06B6D4' : 
                           n.type === 'transaction' ? '#F59E0B' : 
                           n.type === 'case' ? '#EF4444' : '#8B5CF6';
                svg += `
                    <g transform="translate(${n.x}, ${n.y})">
                        <circle r="22" fill="${fill}" stroke="#1E293B" stroke-width="3" />
                        <text y="-30" text-anchor="middle" fill="#F9FAFB" font-size="11" font-weight="bold">${n.label}</text>
                        <text y="35" text-anchor="middle" fill="#9CA3AF" font-size="10">${n.sub}</text>
                    </g>`;
            });

            svg += `</svg>`;
            return svg;
        }

        function selectCase(caseId) {
            activeCaseId = caseId;
            renderSidebar();
            const c = allCases.find(x => x.case_id === caseId);
            if (!c) return;

            document.getElementById("active-case-title").innerText = `Case ${c.case_id}`;
            
            let writebackStatus = c.written_to_graph ? '<span class="badge badge-live">LIVE TIGERGRAPH</span> <span class="badge badge-live">GSQL REST++</span> <span class="badge badge-live">DYNAMIC GRAPH RESOLUTION</span>' : '<span class="badge badge-offline">OFFLINE / CACHED</span>';
            document.getElementById("system-badges").innerHTML = writebackStatus;

            let fraudColor = c.fraud_assessment === 'likely_fraud' ? 'var(--danger)' : c.fraud_assessment === 'likely_benign' ? 'var(--success)' : 'var(--warning)';

            const db = document.getElementById("dashboard-body");
            db.innerHTML = `
                <!-- TAB 1: Investigation & Workflow -->
                <div id="tab1" class="tab-content active">
                    <div class="grid-container">
                        <div class="card col-4">
                            <div class="card-header">Triage Assessment</div>
                            <div class="stat-val" style="color: ${fraudColor}">${c.fraud_assessment.toUpperCase().replace(/_/g, ' ')}</div>
                            <div class="stat-sub">Model Trigger Risk Score: ${c.trigger.model_risk_score.toFixed(2)}</div>
                            <div style="margin-top:15px; font-size:0.85rem; color:var(--text-secondary);">
                                <strong>Trigger Context:</strong><br/>${c.trigger.trigger_text}
                            </div>
                        </div>
                        
                        <div class="card col-4">
                            <div class="card-header">Next Best Action</div>
                            <div class="stat-val" style="color: var(--accent-cyan)">${c.recommended_nba.replace(/_/g, ' ')}</div>
                            <div class="stat-sub">Approval Required: ${c.approval_required ? 'YES (Human Analyst)' : 'NO (Auto-Route)'}</div>
                            <div style="margin-top:15px; font-size:0.85rem; color:var(--text-secondary);">
                                <strong>Execution State:</strong> ${c.execution_status} <br/>
                                <strong>Lifecycle:</strong> ${c.lifecycle_state}
                            </div>
                        </div>

                        <div class="card col-4">
                            <div class="card-header">Workflow Summary</div>
                            <p style="font-size: 0.85rem; line-height: 1.5; color: #D1D5DB;">${c.summary}</p>
                        </div>

                        <div class="card col-6">
                            <div class="card-header">TigerGraph Subgraph Resolution</div>
                            <div class="graph-container">
                                ${renderGraphSVG(c)}
                            </div>
                        </div>

                        <div class="card col-6">
                            <div class="card-header">Agent Execution Timeline</div>
                            <div style="max-height: 350px; overflow-y: auto; padding-right:10px;">
                                ${c.investigation_steps.map(s => `
                                    <div class="timeline-step">
                                        <div class="timeline-tool">[${s.step_number}] Tool: ${s.tool}</div>
                                        <div class="timeline-reason">${s.reason}</div>
                                        <div>${s.result_summary}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- TAB 2: Deep Reasoning -->
                <div id="tab2" class="tab-content">
                    <div class="grid-container">
                        <div class="card col-12">
                            <div class="card-header">Reasoning & Confidence</div>
                            <div style="display:flex; gap: 40px; margin-bottom: 20px;">
                                <div><span style="color:var(--text-secondary); font-size:0.8rem; display:block;">CONFIDENCE</span><strong style="font-size:1.2rem;">${(c.confidence * 100).toFixed(1)}%</strong></div>
                                <div><span style="color:var(--text-secondary); font-size:0.8rem; display:block;">UNCERTAINTY</span><strong style="font-size:1.2rem;">${c.uncertainty_level.toUpperCase()}</strong></div>
                            </div>
                            
                            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                                <div>
                                    <h4 style="color:var(--accent-blue); margin-bottom:10px; font-size:0.9rem;">Why Suspicious</h4>
                                    <ul class="list-group">
                                        ${c.explanation && c.explanation.why_suspicious ? c.explanation.why_suspicious.map(r => `<li>${r}</li>`).join('') : '<li>No specific suspicious signals.</li>'}
                                    </ul>
                                </div>
                                <div>
                                    <h4 style="color:var(--accent-cyan); margin-bottom:10px; font-size:0.9rem;">Why Action / Guardrails</h4>
                                    <ul class="list-group">
                                        ${c.explanation && c.explanation.why_action ? c.explanation.why_action.map(r => `<li>${r}</li>`).join('') : '<li>No specific action reasoning.</li>'}
                                    </ul>
                                </div>
                                <div>
                                    <h4 style="color:var(--warning); margin-bottom:10px; font-size:0.9rem;">Why Not Certain / Stop</h4>
                                    <ul class="list-group">
                                        ${c.uncertainty_reasons.map(r => `<li>${r}</li>`).join('')}
                                        ${c.evidence_gaps.map(g => `<li>Gap: ${g}</li>`).join('')}
                                    </ul>
                                </div>
                            </div>
                        </div>

                        <div class="card col-6">
                            <div class="card-header">Supporting / Contradictory Evidence</div>
                            <h4 style="color:var(--danger); margin-bottom:10px; font-size:0.85rem;">Supporting Findings</h4>
                            <ul class="list-group">
                                ${c.supporting_findings && c.supporting_findings.length > 0 ? c.supporting_findings.map(f => `<li>${f}</li>`).join('') : '<li>None</li>'}
                            </ul>
                            
                            <h4 style="color:var(--success); margin-bottom:10px; font-size:0.85rem; margin-top:15px;">Contradictory Findings</h4>
                            <ul class="list-group">
                                ${c.contradictory_findings && c.contradictory_findings.length > 0 ? c.contradictory_findings.map(f => `<li>${f}</li>`).join('') : '<li>None</li>'}
                            </ul>
                        </div>

                        <div class="card col-6">
                            <div class="card-header">GraphRAG Historical Precedents</div>
                            <ul class="evidence-list" style="max-height: 400px; overflow-y: auto;">
                                ${c.historical_evidence.length > 0 ? c.historical_evidence.map(h => `
                                    <li class="evidence-item historical">
                                        <div class="evidence-tag">[CLOSED CASE | ${h.case_id}]</div>
                                        <div>Retrieved via GraphRAG: ${h.source}</div>
                                    </li>
                                `).join('') : '<li class="evidence-item">No historical precedents found for this entity.</li>'}
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- TAB 3: Compliance & Memory -->
                <div id="tab3" class="tab-content">
                    <div class="grid-container">
                        <div class="card col-6">
                            <div class="card-header">SAR Preparation & Compliance</div>
                            <div class="stat-val" style="color: ${c.sar_data && c.sar_data.sar_required ? 'var(--danger)' : 'var(--success)'}">
                                ${c.sar_data && c.sar_data.sar_required ? 'SAR PREPARATION REQUIRED' : 'SAR NOT REQUIRED'}
                            </div>
                            <div class="stat-sub" style="margin-bottom:15px;">Filing Status: ${c.sar_data ? c.sar_data.filing_status.toUpperCase() : 'N/A'} (Requires Human Approval)</div>
                            
                            <ul class="list-group">
                                <li><strong>Exposure USD:</strong> $${c.sar_data ? c.sar_data.exposure_usd.toFixed(2) : '0.00'}</li>
                                <li><strong>Rationale:</strong> ${c.sar_data ? c.sar_data.sar_rationale : 'N/A'}</li>
                                <li><strong>Regulatory References:</strong> ${c.sar_data && c.sar_data.regulatory_references ? c.sar_data.regulatory_references.join(', ') : 'None'}</li>
                            </ul>
                            
                            <div style="margin-top: 20px; padding: 10px; background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--warning); font-size: 0.8rem; color: #D1D5DB;">
                                <strong>Compliance Note:</strong> This system automatically prepares Suspicious Activity Reports (SARs) according to internal policy thresholds. Final FinCEN filing always requires external human compliance officer approval.
                            </div>
                        </div>

                        <div class="card col-6">
                            <div class="card-header">TigerGraph Writeback Status</div>
                            <div class="stat-val" style="color: ${c.written_to_graph ? 'var(--accent-blue)' : 'var(--text-secondary)'}">
                                ${c.written_to_graph ? 'SUCCESS' : 'PENDING / OFFLINE'}
                            </div>
                            <div class="stat-sub" style="margin-bottom:15px;">Case Vertex Persistence</div>
                            
                            <p style="font-size:0.85rem; color:#D1D5DB; line-height:1.5;">
                                The Agentic Investigator persists completed case states, reasoning summaries, and compliance decisions back to the live TigerGraph cluster as a <strong>InvestigationCase</strong> vertex, establishing edges to the associated Transaction, Customer, and Card for future GraphRAG retrieval.
                            </p>
                        </div>
                    </div>
                </div>
            `;
            
            // Switch back to tab1 on case change
            switchTab('tab1');
        }

        window.onload = fetchCases;
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
