# Final Evaluation Report — TigerGraph Autonomous Fraud Investigator

**Project:** Autonomous Agentic Fraud Investigation System  
**Hackathon Track:** HHGOA TigerGraph AI Hackathon Task 4  
**Date:** September 2026  
**Repository:** [https://github.com/kanwal-vyas/agentic-fraud-investigation.git](https://github.com/kanwal-vyas/agentic-fraud-investigation.git)  
**Approved Baseline Commit:** `ff48e762cd41368b97f4bfd0609abc8d4219f81f`

---

## 1. Executive Summary

Traditional fraud detection relies heavily on isolated tabular machine learning risk scores that flag transactions without holistic entity context, creating thousands of false positives and overwhelming human compliance analysts. 

This project delivers a production-grade **Autonomous Fraud Investigation Agent** powered by **TigerGraph GSQL algorithms**, **TigerGraph Model Context Protocol (MCP)**, **GraphRAG hybrid retrieval**, **quantified uncertainty assessment**, **deterministic policy guardrails**, and **bi-directional graph case memory writeback**.

The agent autonomously orchestrates multi-hop graph traversals across transactions, cards, devices, and historical cases up to an 8-step budget. Across all 20 benchmark cases from the official HHGOA dataset, the system achieves:
- **100% Budget Compliance** (average 4.25 tool calls per case, 0 duplicate calls)
- **0 Invariant Violations** (0 policy bypasses, 0 unreferenced actions, 0 missing-entity contaminations)
- **Strict Human Authorization Boundary** (`RECOMMENDED != AUTHORIZED != EXECUTED`)
- **Automated FinCEN SAR Preparation** under 31 CFR § 1020.320

---

## 2. Architecture Overview

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

## 3. Agentic Investigation Flow

1. **Trigger Reception:** Ingestion of trigger modality (`customer_report`, `risk_score`, or `analyst_request`). Initial status set to `OPEN`.
2. **Autonomous Tool Discovery:** The orchestrator determines missing facts and calls appropriate TigerGraph MCP tools.
3. **GraphRAG Synthesis:** Retrieved topological graph facts are fused with historical case precedents and bank policy rules.
4. **Uncertainty & Sufficiency Check:** If evidence is contradictory or inconclusive, the agent identifies explicit evidence gaps and requests external validation (e.g. 2FA customer response).
5. **Policy Decision:** Evaluates statutory rules R1–R8 and regulatory mandates before emitting recommendations.
6. **NBA & Boundary Enforcement:** Emits Next Best Action with strict approval routing. Destructive actions (`BLOCK_CARD`) are held in `ACTION_PENDING_APPROVAL`.
7. **Writeback & SAR:** Persists the complete case memory, writes topological vertices to TigerGraph, and generates SAR packages where exposure warrants.

---

## 4. TigerGraph Integration

- **Graph Schema:** Native vertices (`Transaction`, `Card`, `Customer`, `DeviceInfo`, `Merchant`, `Case`) connected by semantic edges (`ON_CARD`, `PERFORMED_BY`, `USED_DEVICE`, `ASSOCIATED_WITH`, `INVOLVES`, `CONNECTED_TO`).
- **GSQL Algorithms:** Deep-link neighborhood probing, velocity window scans, rapid card testing detection, and shared device syndicate cluster identification.
- **Operational Deployments:** Seamless support for **LIVE TigerGraph Cloud/Enterprise endpoints** and an **Offline High-Fidelity Graph Engine** for zero-dependency local reproduction.

---

## 5. TigerGraph MCP Tool Suite

The system exposes 10 standardized MCP tools conforming to the Model Context Protocol:
1. `get_transaction(txn_id)`
2. `get_customer_history(customer_id)`
3. `get_card_history(card_id)`
4. `get_transaction_neighborhood(txn_id, hops)`
5. `find_shared_devices(device_id)` (Strict NaN/Null filtration)
6. `detect_card_testing(card_id, time_window_hours)`
7. `detect_velocity(card_id, time_window_minutes)`
8. `detect_regional_anomaly(card_id, txn_id)`
9. `get_historical_cases(card_id, customer_id, pattern)`
10. `find_connected_cards(card_id)`

---

## 6. GraphRAG & Context Synthesis

GraphRAG enriches live topological facts without replacing graph authority:
- **Separation of Evidence:** Current graph facts (`[GRAPH | tool:id]`) are strictly separated from historical case precedents (`[HISTORICAL CLOSED CASE | CC-XXXX]`).
- **Contradictory Evidence Analysis:** Benign patterns (e.g. prior cleared travel alarms, normal spending baselines) are explicitly highlighted as contradictory findings to prevent false alarms.

---

## 7. Reasoning, Uncertainty & Evidence Sufficiency

- **Uncertainty Assessment:** Explicit quantification into `LOW`, `MEDIUM`, or `HIGH` uncertainty with documented drivers (missing device hardware fingerprints, conflicting historical indicators).
- **Sufficiency Gate:** Cases with unverified customer intent pause in `AWAITING_CUSTOMER_EVIDENCE` rather than jumping to false conclusions.

---

## 8. Policy Guardrails

Enforces bank policy rules:
- **Rule R1:** Weak signal triage & verification.
- **Rule R2:** Direct customer report mandates card block.
- **Rule R3:** Customer authorization confirmed via 2FA resolves false alarm.
- **Rule R4:** Out-of-region card use requires travel verification.
- **Rule R5:** Rapid card testing requires merchant restriction.
- **Rule R6:** Shared device syndicate requires connected card blast radius monitoring.
- **Rule R7:** Contradictory evidence mandates customer inquiry before blocking.
- **Rule R8:** High exposure ($1,000+) requires supervisor escalation and SAR review.

---

## 9. Case Memory & Precedent Indexing

- **In-Memory & Persistent Storage:** Thread-safe case memory indexed across `customer_id`, `card_id`, and `fraud_pattern`.
- **Similarity Search:** Retrieves similar historical precedents to guide future investigations with complete provenance tracking.

---

## 10. TigerGraph Case Graph Writeback

- **Idempotency:** Re-investigating or updating a case updates the existing `Case` vertex rather than duplicating graph nodes.
- **Topological Edges:** Connects `Case` $\rightarrow$ `Transaction` (`INVOLVES`), `Case` $\rightarrow$ `Card` (`ON_CARD`), and `Case` $\rightarrow$ `ConnectedCards` (`CONNECTED_TO`).

---

## 11. FinCEN SAR Compliance Preparation

- **Statutory Mandate:** FinCEN 31 CFR § 1020.320 / Bank Secrecy Act.
- **Automated Artifacts:** Generates structured Form 111 compliance packages detailing subjects, exposure, timelines, and narrative.
- **Safety Disclaimer:** Explicitly designated as `PREPARATION / RECOMMENDATION ONLY (No regulatory filing simulated)`.

---

## 12. 20-Case Benchmark Evaluation

All 20 standard HHG benchmark cases were deterministically evaluated:
- **Customer Reports (4 cases):** Prompt card blocks, high confidence, approval routing L1.
- **Elevated Model Risk Scores (14 cases):** Multi-hop neighborhood probing, pattern matching, SAR evaluation.
- **Analyst Inquiries (2 cases):** Focused forensic checks with historical precedent comparison.

---

## 13. Metrics Summary

| Metric | Measured Result | Benchmark Target |
|---|---|---|
| Total Cases Evaluated | 20 / 20 | 20 |
| Persisted Case Records | 20 / 20 | 20 |
| Average Tool Calls / Case | 4.25 | ≤ 8.0 |
| Duplicate Tool Call Rate | 0.0% | 0.0% |
| Budget Adherence (≤ 8 Steps) | 100.0% | 100.0% |
| Missing-Entity / NaN Contamination | 0 | 0 |
| Policy Reference Mismatches | 0 | 0 |
| Unreferenced Destructive Actions | 0 | 0 |
| Denied Destructive Actions Emitted | 0 | 0 |
| Lifecycle / Outcome Inconsistencies | 0 | 0 |
| Total Tests Passing | 100 / 100 | 100% |

---

## 14. Representative Case Studies

### Case Study 1: HHG-003 (Customer Fraud Report)
- **Trigger:** Direct customer report on Card `C08623-K2` for $49.00 in-person transaction.
- **Tools Called:** `get_transaction`, `get_card_history`, `get_historical_cases`.
- **Assessment:** `LIKELY_FRAUD` (Confidence: 0.70, Uncertainty: HIGH due to missing device metadata and 3 prior cleared false alarms).
- **NBA & Lifecycle:** `BLOCK_CARD` held at Level L1 authorization boundary (`ACTION_PENDING_APPROVAL`). Final outcome cleanly separated as `ACTION_PENDING_APPROVAL`.

### Case Study 2: HHG-005 (Controlled Evidence Loop)
- **Before Evidence:** Elevated risk score on Card `C02923-K1`. Conflicting travel vs syndicate indicators. Paused in `AWAITING_CUSTOMER_EVIDENCE` with NBA `VERIFY_WITH_CUSTOMER`.
- **Controlled Input:** Customer verifies authorized travel via Out-of-Band SMS.
- **After Reassessment:** Reassessed to `LIKELY_BENIGN` (Confidence: 0.90, Uncertainty: LOW). NBA updated to `MONITOR_CARD`, case resolved cleanly as `RESOLVED_BENIGN`.

### Case Study 3: HHG-010 (High-Exposure Coordinated Syndicate)
- **Trigger:** Risk score 0.90 on $1,000.03 transaction on Card `C10434-K1`.
- **Findings:** Shared device profile linked to syndicate activity across multiple cardholders.
- **Compliance:** FinCEN SAR generated with $1,000.03 exposure and Level L2 supervisory escalation.

---

## 15. Limitations & Future Work

1. **Synthetic/Sample Graph Scale:** Benchmark dataset operates on a curated 20-case pack and 5,000 transactions; enterprise deployments require clustering over billions of vertices.
2. **Simulated 2FA Responses:** Additional customer evidence in offline benchmarking is simulated via controlled response payloads.

---

## 16. Operational Reality & Integration Status

| Component | Status | Operational Reality |
|---|---|---|
| **TigerGraph Graph Schema & Queries** | **IMPLEMENTED** | Full GSQL schema, loading scripts, and queries available in `tigergraph/`. |
| **TigerGraph Client** | **LIVE / OFFLINE** | Automatically uses live TigerGraph endpoint if configured in `.env`; falls back to high-fidelity in-memory engine offline. |
| **TigerGraph MCP Server** | **IMPLEMENTED** | Standardized MCP tools for agent integration. |
| **Reasoning & Policy Engine** | **DETERMINISTIC** | Python-based deterministic policy engine executing Rules R1–R8. |
| **Case Memory & Writeback** | **IMPLEMENTED** | Thread-safe case store and idempotent graph writeback. |
| **SAR Preparation** | **DETERMINISTIC** | Compliance narrative and Form 111 generation (internal preparation only). |
| **Web UI Dashboard** | **IMPLEMENTED** | FastAPI dashboard viewer in `src/ui/app.py`. |

---

## 17. Reproducibility Instructions

```bash
# 1. Clone repository
git clone https://github.com/kanwal-vyas/agentic-fraud-investigation.git
cd agentic-fraud-investigation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run full automated test suite (100 tests)
pytest -q

# 4. Run full 20-case benchmark
python scripts/run_agent_benchmark.py

# 5. Generate all case files and SAR artifacts
python scripts/generate_submission_artifacts.py

# 6. Launch interactive investigation UI
python src/ui/app.py
# Open http://127.0.0.1:8000 in your browser
```
