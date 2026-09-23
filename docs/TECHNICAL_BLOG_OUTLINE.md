# Technical Blog: Building an Autonomous Fraud Investigation Agent with TigerGraph, MCP & GraphRAG

**Author:** Kanwal Vyas  
**Target Publication:** Towards Data Science / Medium / TigerGraph Developer Portal  
**Topic:** Agentic AI, Graph Databases, GraphRAG, FinTech Compliance  

---

## Blog Outline & Key Sections

### 1. Introduction: The False Positive Dilemma in Modern FinTech
- **The Problem:** Modern fraud models output risk scores (e.g., `0.91`), but cannot explain *why* or perform forensic investigation.
- **The Reality:** 90%+ of flagged alerts in retail banking turn out to be legitimate travel, shared devices, or benign anomalies.
- **The Solution:** An autonomous investigation agent that gathers topological evidence, reasons over uncertainty, and writes findings back to a connected graph.

---

### 2. Why Graph Databases are Mandatory for Fraud Investigations
- Relational tables and isolated document stores cannot efficiently compute multi-hop relationships (e.g., 5 cards sharing 1 device across 3 distinct billing regions).
- **TigerGraph Advantage:** Native parallel graph processing and parametrized GSQL queries allowing sub-second neighborhood traversals and syndicate ring detection.
- Graph schema design: `Transaction`, `Card`, `Customer`, `DeviceInfo`, `Merchant`, `Case`.

---

### 3. Architecture: Integrating TigerGraph with the Model Context Protocol (MCP)
- What is MCP and why it solves the agent-database integration problem.
- Exposing 10 GSQL queries as structured, type-safe MCP tools.
- Handling data hygiene: Strict NaN/Null filtering to prevent phantom entity hallucinations (e.g., never creating a device profile named `"nan"`).

---

### 4. GraphRAG: Fusing Topological Graph Facts with Historical Case Precedents
- Beyond naive vector search: Why pure text retrieval fails in fraud compliance.
- Structured GraphRAG context synthesis:
  - Live graph topological facts (`[GRAPH | tool:id]`)
  - Historical closed cases and prior fraud precedents (`[HISTORICAL CLOSED CASE | CC-XXXX]`)
  - Statutory bank policy rules (Rules R1–R8).
- Maintaining clear source attribution and avoiding contamination.

---

### 5. Deterministic Reasoning, Uncertainty & The Controlled Evidence Loop
- The importance of quantified uncertainty (`LOW`, `MEDIUM`, `HIGH`) in safety-critical systems.
- Evaluating contradictory evidence (e.g., anomalous purchase vs. history of cleared travel).
- **The Controlled Evidence Loop:** Pausing before destructive action to request customer 2FA confirmation, followed by automated reassessment.

---

### 6. Safety Guardrails & Human Authorization Boundaries
- The cardinal rule of AI governance: `RECOMMENDED != AUTHORIZED != EXECUTED`.
- Enforcing Level L1/L2 supervisor approval routes for destructive actions (`BLOCK_CARD`).
- Deterministic policy engine preventing unreferenced actions or rule bypasses.

---

### 7. Bi-Directional Case Memory & TigerGraph Graph Writeback
- Closing the loop: Persisting investigation results, findings, and Next Best Actions.
- Idempotent upsert of `Case` vertices and `INVOLVES` / `ON_CARD` edges into TigerGraph.
- Making today's completed investigation part of tomorrow's GraphRAG precedent memory.

---

### 8. Regulatory Compliance: Automated FinCEN SAR Preparation
- Automating Suspicious Activity Report (SAR) preparation under FinCEN 31 CFR § 1020.320.
- Structuring exposure calculations, timeline extraction, and Form 111 narratives.
- Clear compliance disclaimers (internal preparation only).

---

### 9. Benchmarking & Lessons Learned
- Evaluating 20 real-world benchmark cases across diverse modalities.
- Achieving 0 policy violations, 0 duplicate calls, and 100% test pass rate.
- Key takeaways for engineers building enterprise agentic systems.

---

### 10. Conclusion & Open-Source Code
- Links to GitHub repository: [https://github.com/kanwal-vyas/agentic-fraud-investigation.git](https://github.com/kanwal-vyas/agentic-fraud-investigation.git)
- Quickstart guide and reproduction instructions.
