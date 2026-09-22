# Implementation Plan: TigerGraph Agentic Fraud Investigation System

## Stages & Milestones

### Stage 1: Repository Setup, Environment, & Dataset Preprocessing
- **Goal:** Prepare project directory structure, python dependencies, and preprocessed loader data for TigerGraph.
- **Tasks:**
  - Setup virtualenv and install core requirements (`fastapi`, `uvicorn`, `pyTigerGraph`, `pydantic`, `sentence-transformers` / `google-genai` / `openai`, `pandas`).
  - Implement data preprocessing utility to extract unique vertices (`Customer`, `Card`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `Transaction`, `ClosedCase`) and edges.
  - Setup unified config and environment variables (`.env`).
- **Verification:** Unit tests verifying data integrity, vertex extraction counts, and CSV schema validation.

### Stage 2: TigerGraph Schema Definition & Data Ingestion
- **Goal:** Create TigerGraph GSQL schema and batch load the dataset into Savanna / Community Edition.
- **Tasks:**
  - Write `tigergraph/schema.gsql` (defining vertices `Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `ClosedCase`, `Case` and connecting edges).
  - Write `tigergraph/loading_jobs.gsql` for high-throughput batch loading.
  - Write Python ingestion script with connection validation, schema deployment, and verification queries.
- **Verification:** Query vertex/edge counts in TigerGraph and verify all 590k+ transactions and 5.5k+ closed cases are accurately loaded.

### Stage 3: GSQL Investigation Queries & Graph Algorithms
- **Goal:** Implement domain-specific GSQL investigation queries and pattern detection algorithms.
- **Tasks:**
  - Implement GSQL queries:
    - `get_transaction_neighborhood(vertex<Transaction> t)`
    - `get_card_activity_window(vertex<Card> c, string start_time, string end_time)`
    - `find_shared_device_ring(vertex<DeviceProfile> d)`
    - `detect_card_testing_sequence(vertex<Card> c)`
    - `detect_out_of_region_anomaly(vertex<Transaction> t)`
    - `find_similar_closed_cases(vertex<Card> c, vertex<DeviceProfile> d)`
  - Compile and test GSQL queries.
- **Verification:** Run standalone query tests against sample flagged transactions from `case_pack.csv` and verify expected subgraphs.

### Stage 4: TigerGraph MCP Tool Suite
- **Goal:** Implement the Model Context Protocol (MCP) tool interface for the LLM agent.
- **Tasks:**
  - Implement tool handlers mapping agent requests to TigerGraph GSQL queries.
  - Expose standard MCP endpoints / tool schemas (`get_transaction`, `get_card_history`, `find_shared_device_rings`, `find_similar_cases`, `write_case_to_graph`).
  - Add input validation and structured return formatting.
- **Verification:** MCP tool integration test suite verifying end-to-end execution of all tools.

### Stage 5: GraphRAG & Context Synthesis Engine
- **Goal:** Build GraphRAG grounding combining graph ego-networks, regulatory typologies, and historical case memory.
- **Tasks:**
  - Implement document indexing for regulatory guidelines (FinCEN, FATF) and bank policy rules (R1–R10).
  - Implement hybrid retriever (Graph traversal + semantic embedding / BM25 search over 5,565 closed cases).
  - Format grounded context with explicit citation anchors (`entity_ids`, query `ref`).
- **Verification:** Test context extraction on sample cases, verifying relevant past cases and rules are correctly surfaced.

### Stage 6: Agentic State Machine & Reasoning Loop
- **Goal:** Implement the core autonomous investigation agent with tool selection and uncertainty handling.
- **Tasks:**
  - Implement investigation state machine (`Trigger` → `Investigate` → `Evidence Gathering` → `Uncertainty Check` → `Evidence Request` → `Re-assessment` → `Conclusion`).
  - Implement calibrated uncertainty estimator (evaluating signal strength, conflicting flags, missing context).
  - Implement simulated evidence feedback loops (customer validation, step-up auth, analyst queries).
- **Verification:** Test agent on initial test cases, ensuring tool invocations and state transitions proceed logically.

### Stage 7: Case Memory & Graph Persistence
- **Goal:** Enable bi-directional case memory where resolved cases are written back into TigerGraph and retrieved by future investigations.
- **Tasks:**
  - Implement GSQL upsert query for `Case` vertices and `INVOLVES`, `ON_CARD`, `CONNECTED_TO` edges.
  - Update memory index dynamically when a case closes.
- **Verification:** Run consecutive case evaluations and confirm that newly closed cases appear in memory retrieval for subsequent cases.

### Stage 8: Next-Best-Action Recommendation & Deterministic Policy Engine
- **Goal:** Enforce Policy Rules R1–R10 and approval routing (`auto`, `L1`, `L2`).
- **Tasks:**
  - Implement deterministic policy rule checker evaluating agent proposals against strict rules.
  - Implement SAR narrative generator adhering to FinCEN standards (who, what, when, where, how, why).
  - Record dual recommendations (`initial` before evidence request vs. `final` after evidence response).
- **Verification:** Test all 10 policy rules (R1–R10) with targeted unit test cases.

### Stage 9: Analyst Dashboard UI (React / Vite)
- **Goal:** Build a sleek, interactive analyst dashboard visualizing the entire investigation.
- **Tasks:**
  - Build UI layout:
    - Case Selector (all 20 benchmark cases + live trigger simulator).
    - Interactive Graph Explorer (showing transaction subgraphs, shared device rings, connected cards).
    - Live Agent Investigation Stream (showing thoughts, tool calls, and state progression).
    - Evidence & Uncertainty Ledger (calibrated probability gauge, evidence sources, citation list).
    - Recommendation & Approval Panel (Initial vs Final actions, approval routing tags).
    - Regulatory SAR Narrative Panel with one-click export.
  - Connect UI to FastAPI backend via REST and streaming SSE.
- **Verification:** Visual verification of UI responsiveness, graph rendering, and end-to-end case playback.

### Stage 10: 20-Case Benchmark Evaluation & Deliverables Generation
- **Goal:** Execute the full pipeline on all 20 cases from `case_pack.csv` and validate output.
- **Tasks:**
  - Run `evaluation/evaluate_cases.py` across all 20 cases.
  - Validate each output JSON file in `cases/<case_id>.json` against the official Answer Format schema.
  - Generate comprehensive evaluation summary `docs/EVALUATION_REPORT.md`.
- **Verification:** Automated JSON schema validator checking 100% compliance across all 20 case files.

### Stage 11: Demo Hardening, Technical Blog, & Video Assets
- **Goal:** Finalize documentation, end-to-end demo script, blog post, and social post.
- **Tasks:**
  - Write technical blog post covering architecture, TigerGraph usage, agentic design, and insights.
  - Prepare 3-5 minute demo recording script and walkthrough.
  - Write social post draft for X / LinkedIn tagging `@TigerGraphDB`.
- **Verification:** Complete end-to-end rehearsal and final git repository verification.
