# TigerGraph Autonomous Agentic Fraud Investigator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TigerGraph](https://img.shields.io/badge/TigerGraph-3.9+-orange.svg)](https://www.tigergraph.com/)
[![MCP](https://img.shields.io/badge/MCP-Standard-green.svg)](https://modelcontextprotocol.io/)
[![Tests Passing](https://img.shields.io/badge/tests-100%20passed-brightgreen.svg)]()

An autonomous, production-grade fraud investigation agent powered by **TigerGraph GSQL algorithms**, **TigerGraph Model Context Protocol (MCP)**, **GraphRAG hybrid retrieval**, **quantified uncertainty assessment**, **deterministic policy guardrails (Rules R1–R8)**, and **bi-directional TigerGraph case graph writeback**.

Built for the **HHGOA TigerGraph AI Hackathon Task 4**.

---

## 🌟 Key Capabilities & Highlights

1. **Multi-Step Agentic Investigation Loop:** Dynamically selects investigative tools up to an 8-step budget (average 4.25 tool calls per case, 0 duplicate calls).
2. **TigerGraph MCP Tool Suite:** 10 standardized MCP tools exposing GSQL queries for transactions, card velocity, card testing, shared device syndicate clusters, and connected card blast radius.
3. **GraphRAG Context Synthesis:** Fuses live graph topological facts with historical closed cases and bank policy rules, maintaining strict source provenance.
4. **Reasoning & Uncertainty Engine:** Evaluates contradictory indicators, computes quantified uncertainty (`LOW`, `MEDIUM`, `HIGH`), and pauses for customer 2FA verification when evidence is incomplete.
5. **Policy Guardrails & Human Authorization Boundary:** Strictly enforces `RECOMMENDED != AUTHORIZED != EXECUTED`. Destructive actions (`BLOCK_CARD`) are held in `ACTION_PENDING_APPROVAL` for supervisor signoff.
6. **FinCEN SAR Automated Preparation:** Generates complete Form 111 Suspicious Activity Report preparation packages under 31 CFR § 1020.320.
7. **TigerGraph Case Graph Writeback:** Idempotently writes `Case` vertices and `INVOLVES`, `ON_CARD`, and `CONNECTED_TO` edges back into the graph to power future investigation memory.
8. **Interactive Web UI Console:** Dedicated dashboard in FastAPI for analysts to explore cases, graph relations, evidence provenance, and SAR filings.

---

## 📐 Architecture Overview

```
                          [ TRIGGER ]
            (Customer Report / Model Risk Score / Analyst Alert)
                                 │
                                 ▼
              [ AGENTIC INVESTIGATION ORCHESTRATOR ]
             (State Machine, Dynamic Tool Selection Loop)
                                 │
         ┌───────────────────────┴────────────────────────┐
         ▼                                                ▼
[ TIGERGRAPH MCP SERVER ]                       [ GRAPHRAG CONTEXT SYNTHESIS ]
 • get_transaction                               • Live Graph Topological Facts
 • get_card_history                              • Historical Closed Cases (Vector/Text)
 • get_customer_history                          • Regulatory Rules & Policies (R1–R8)
 • get_transaction_neighborhood                  • Source Attribution & Provenance
 • find_shared_devices (NaN-Filtered)
 • detect_card_testing / velocity
 • find_connected_cards
         │                                                │
         └───────────────────────┬────────────────────────┘
                                 ▼
             [ REASONING, UNCERTAINTY & POLICY ENGINE ]
              • Hypothesis Scoring & Contradictory Evidence
              • Quantified Uncertainty Assessment
              • Evidence Sufficiency Evaluation
              • Policy Guardrail Enforcement (Rules R1–R8)
                                 │
                                 ▼
                     [ NEXT BEST ACTION (NBA) ]
           (BLOCK_CARD / MONITOR / VERIFY / FILE_REPORT)
                                 │
                                 ▼
               [ HUMAN AUTHORIZATION BOUNDARY ]
            (RECOMMENDED vs PENDING_APPROVAL vs EXECUTED)
                                 │
                                 ▼
             [ CASE MEMORY & GRAPH WRITEBACK ENGINE ]
              • Persistent Case Store Indexing
              • Idempotent Graph Writeback (Case Vertices & Edges)
              • FinCEN SAR Compliance Package Generation
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+
- (Optional) A live TigerGraph instance (Cloud or on-prem). The system operates seamlessly in both **LIVE** and **OFFLINE** high-fidelity graph simulation modes out of the box.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/kanwal-vyas/agentic-fraud-investigation.git
cd agentic-fraud-investigation

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```

If connecting to a live TigerGraph instance:
```ini
TIGERGRAPH_HOST=https://your-instance.i.tgcloud.io
TIGERGRAPH_GRAPH_NAME=FraudGraph
TIGERGRAPH_USERNAME=tigergraph
TIGERGRAPH_PASSWORD=your_password
TIGERGRAPH_SECRET=your_secret
```
*Note: If these variables are not set or the server is unreachable, the system automatically runs in offline mode using the high-fidelity graph engine.*

---

## 🧪 Verification & Running the System

### 1. Run Automated Tests
```bash
pytest -q
```
*All 100 tests pass, covering MCP tools, GSQL queries, GraphRAG, policy guardrails, lifecycle transitions, writeback idempotency, and benchmark invariants.*

### 2. Run the 20-Case Agent Benchmark
```bash
python scripts/run_agent_benchmark.py
```
*Evaluates all 20 standard HHG benchmark cases and prints detailed audit traces for HHG-003 and HHG-010 with 0 invariant violations.*

### 3. Generate All Submission Artifacts & Case Files
```bash
python scripts/generate_submission_artifacts.py
```
*Produces:*
- `artifacts/case_files/HHG-001.md` ... `artifacts/case_files/HHG-020.md`
- `artifacts/sar/SAR_HHG-*.md`
- `artifacts/benchmark/evaluation_results.json`
- `artifacts/benchmark/benchmark_summary.md`

### 4. Launch the Interactive Web Dashboard
```bash
python src/ui/app.py
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser to explore investigation cases interactively.

---

## 📊 Benchmark Summary (20 Cases)

| Metric | Measured Value | Target | Status |
|---|---|---|:---:|
| **Total Cases Evaluated** | `20 / 20` | `20` | **[PASS]** |
| **Persisted Case Records** | `20 / 20` | `20` | **[PASS]** |
| **Average Tool Calls / Case** | `4.25` | `≤ 8.0` | **[PASS]** |
| **Budget Compliance (≤ 8 Steps)** | `100.0%` | `100.0%` | **[PASS]** |
| **Duplicate Tool Call Rate** | `0.0%` | `0.0%` | **[PASS]** |
| **Missing-Entity / NaN Contamination** | `0` | `0` | **[PASS]** |
| **Policy Reference Mismatches** | `0` | `0` | **[PASS]** |
| **Unreferenced Destructive Actions** | `0` | `0` | **[PASS]** |
| **Denied Destructive Actions Emitted** | `0` | `0` | **[PASS]** |
| **Lifecycle / Outcome Inconsistencies** | `0` | `0` | **[PASS]** |

---

## 📁 Repository Structure

```
├── artifacts/
│   ├── benchmark/           # Machine-readable JSON and Markdown benchmark summaries
│   ├── case_files/          # Complete human-readable case files (HHG-001 to HHG-020)
│   └── sar/                 # FinCEN SAR preparation packages
├── docs/
│   ├── REQUIREMENTS_TRACEABILITY.md  # Official brief requirement mapping matrix
│   ├── FINAL_EVALUATION_REPORT.md    # 17-section comprehensive evaluation report
│   ├── DEMO_SCRIPT.md                # 3-5 minute presentation demo script
│   ├── TECHNICAL_BLOG_OUTLINE.md     # Hackathon technical article outline
│   └── SUBMISSION_CHECKLIST.md       # Audit checklist verifying all requirements
├── scripts/
│   ├── generate_submission_artifacts.py  # End-to-end artifact generator
│   ├── run_agent_benchmark.py           # 20-case benchmark runner
│   ├── test_mcp_tools.py               # MCP server test suite
│   ├── test_graphrag.py                # GraphRAG verification script
│   └── validate_tigergraph.py          # TigerGraph connection & schema validator
├── src/
│   ├── agent/               # Agentic orchestrator and state management
│   ├── analysis/            # Pattern detectors (velocity, card testing, syndicates)
│   ├── mcp/                 # TigerGraph MCP Server and tool definitions
│   ├── memory/              # Case store, lifecycle manager, SAR evaluator, writeback
│   ├── models/              # Pydantic schemas for cases, context, and reasoning
│   ├── rag/                 # GraphRAG context synthesizer and retrievers
│   ├── reasoning/           # Hypothesis scoring, uncertainty, policy engine (R1-R8), NBA
│   ├── tigergraph/          # Live & offline TigerGraph clients
│   └── ui/                  # FastAPI interactive web dashboard
├── tests/                   # 100 comprehensive pytest unit and integration tests
├── tigergraph/              # GSQL schema, queries, and data loading jobs
└── README.md
```

---

## ⚖️ License
MIT License. Created for the HHGOA TigerGraph AI Hackathon.