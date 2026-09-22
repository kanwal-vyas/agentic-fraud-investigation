# TigerGraph MCP Tool Suite (Stage 4)

## 1. Overview & Architecture

The **TigerGraph MCP (Model Context Protocol) Suite** serves as the standard interface layer between AI fraud investigation agents and graph analytics backends. Rather than issuing direct database queries or raw Python code, autonomous agents discover and invoke typed, evidence-oriented tools conforming to the MCP specification.

### Layered Architecture

```
                       ┌────────────────────────┐
                       │  AI Fraud Agent (LLM)  │
                       └───────────┬────────────┘
                                   │ (MCP Tool Calls)
                                   ▼
                       ┌────────────────────────┐
                       │  TigerGraphMCPServer   │
                       │ (Validation & Schemas) │
                       └───────────┬────────────┘
                                   │ (Typed Method Invocations)
                                   ▼
                       ┌────────────────────────┐
                       │TigerGraphInvestigation-│
                       │         Tools          │
                       └───────────┬────────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
          (Credentials Set)                 (No Credentials)
                 ▼                                   ▼
     ┌──────────────────────┐             ┌──────────────────────┐
     │   TigerGraphClient   │             │  SampleGraphClient   │
     │   (Live TigerGraph)  │             │   (Offline Adapter)  │
     └──────────┬───────────┘             └──────────┬───────────┘
                │ GSQL Queries                       │ Fast Memory Indexes
                ▼                                    ▼
     ┌──────────────────────┐             ┌──────────────────────┐
     │ Live Graph Database  │             │ Offline Sample Graph │
     │  (REST++ Endpoint)   │             │   (CSV Benchmarks)   │
     └──────────────────────┘             └──────────────────────┘
```

---

## 2. Key Design Principles

1. **Zero-Logic Duplication:** The MCP server strictly acts as a routing and validation boundary. All graph analytics, pattern matching, and traversal logic reside in `TigerGraphInvestigationTools` (Stage 3).
2. **Deterministic Evidence vs. Verdicts:** Heuristic detections (e.g., `detect_card_testing`, `detect_regional_anomaly`) output `heuristic_confidence` as an investigative evidence signal. They **never** emit automated fraud verdicts.
3. **Strict Model Score Separation:** `model_risk_score` is clearly preserved as an input ML prediction signal (0.0 to 1.0) and is explicitly distinct from the agent's graph investigation assessment.
4. **Transparent Backend Reporting:** Every payload explicitly identifies its backend provider (`tigergraph_live` or `offline_sample`) to prevent confusing simulated data with live graph deployments.
5. **Compact Agent-Facing Format:** Responses summarize essential nodes, metrics, and evidence sentences to keep context compact and fit within LLM context windows.
6. **Read-Only Safety:** All Stage 4 tools are strictly read-only (`GET`/query operations). State-mutating actions (card blocking, customer SMS, SAR filing) are isolated for subsequent policy stages.

---

## 3. Standard Evidence Response Contract

All MCP tool invocations return a structured dictionary conforming to the standard evidence envelope:

```json
{
  "tool": "<tool_name>",
  "status": "success | not_found | error",
  "backend": "tigergraph_live | offline_sample",
  "subject": {
    "key_entity_id": "...",
    "primary_attribute": "..."
  },
  "evidence": [
    "Human-readable evidence bullet 1 grounded in graph facts",
    "Human-readable evidence bullet 2 grounded in graph facts"
  ],
  "metrics": {
    "numerical_metric_1": 0.0,
    "count_metric_2": 10
  },
  "limitations": [
    "Important boundary condition or policy disclaimer"
  ],
  "error": "Optional error string if status == 'error'"
}
```

---

## 4. Exposed MCP Tools Catalog

| # | Tool Name | Target Entity | Core Purpose |
|---|---|---|---|
| 1 | `get_transaction` | `txn_id` | Full transaction attributes, channels, amounts, ML risk score, and connected entity links. |
| 2 | `get_customer_history` | `customer_id` | Customer spending volume, cards held, device profiles, and baseline transaction history. |
| 3 | `get_card_history` | `card_id` | Card metadata (network, type, issuer), normal transaction cadence, and spending baseline. |
| 4 | `get_transaction_neighborhood` | `txn_id`, `max_hops` | Multi-hop ego-network around a transaction (Card, Customer, Device, Region, Domain nodes & edges). |
| 5 | `find_shared_devices` | `profile_id` | Detect if a composite device fingerprint is shared across multiple distinct cards or customers. |
| 6 | `detect_card_testing` | `card_id`, `window_hours` | Identify micro-authorizations ($\le \$5.00$) followed by larger purchases ($\ge \$50.00$) within a time window. |
| 7 | `detect_velocity` | `card_id`, `window_hours` | Measure transaction frequency spikes and rapid spending bursts on a card. |
| 8 | `detect_regional_anomaly` | `txn_id` | Check if an in-person transaction occurred in a billing region discordant from established home baseline. |
| 9 | `get_historical_cases` | `customer_id`, `card_id`, `pattern` | Retrieve resolved past bank investigations and precedent notes from case memory. |
| 10 | `find_connected_cards` | `card_id` | Discover secondary cards associated via common cardholder identity or shared device profiles. |

---

## 5. Tool Specifications & Examples

### 1. `get_transaction`
- **Input Parameters:**
  - `txn_id` (string, required): Unique transaction ID (e.g. `"3514030"`).
- **Example Response:**
```json
{
  "tool": "get_transaction",
  "status": "success",
  "backend": "offline_sample",
  "subject": {
    "txn_id": "3514030",
    "customer_id": "C12382",
    "card_id": "C12382-K1",
    "amount_usd": 77.07,
    "ts": "2017-11-27 10:17:15",
    "channel": "W",
    "model_risk_score": 0.85,
    "addr1": "315.0",
    "profile_id": "Windows | Windows 10 | edge 16.0 | 1366x768"
  },
  "evidence": [
    "Transaction 3514030 for $77.07 occurred at 2017-11-27 10:17:15 via channel 'W' under product code 'W'",
    "Associated with customer C12382 on card C12382-K1 (visa debit)",
    "Input model risk score: 0.85 (Note: model signal only, not a confirmed verdict)",
    "Billed in region code 315.0 (country code: 87.0)",
    "Executed from online device profile: Windows | Windows 10 | edge 16.0 | 1366x768",
    "Purchaser email domain: gmail.com"
  ],
  "metrics": {
    "amount_usd": 77.07,
    "model_risk_score": 0.85
  },
  "limitations": [
    "model_risk_score is a model prediction signal and must be corroborated with graph evidence."
  ]
}
```

---

### 2. `get_customer_history`
- **Input Parameters:**
  - `customer_id` (string, required): Customer identifier (e.g. `"C12382"`).
  - `limit` (integer, optional, default: 50): Maximum number of recent transactions to return.
- **Example Response:**
```json
{
  "tool": "get_customer_history",
  "status": "success",
  "backend": "offline_sample",
  "subject": {
    "customer_id": "C12382",
    "cards_held": ["C12382-K1"]
  },
  "evidence": [
    "Customer C12382 has 12 total historical transactions in record",
    "Total historical spend: $894.50 (Average transaction: $74.54)",
    "Active cards held: C12382-K1",
    "Recognized device profiles used: 2 distinct profiles"
  ],
  "metrics": {
    "total_transactions": 12,
    "total_spend_usd": 894.50,
    "avg_amount_usd": 74.54,
    "recent_sample": [
      "Txn 3514030: $77.07 (2017-11-27 10:17:15, W, score 0.85)",
      "Txn 3513901: $65.00 (2017-11-27 09:45:00, W, score 0.12)"
    ]
  },
  "limitations": [
    "Recent transaction list capped at top 5 sample."
  ]
}
```

---

### 3. `detect_card_testing`
- **Input Parameters:**
  - `card_id` (string, required): Card identifier (e.g. `"C12382-K1"`).
  - `window_hours` (integer, optional, default: 24): Detection window.
- **Example Response:**
```json
{
  "tool": "detect_card_testing",
  "status": "success",
  "backend": "offline_sample",
  "subject": {
    "card_id": "C12382-K1",
    "testing_detected": true
  },
  "evidence": [
    "Card testing sequence detected on C12382-K1: 3 online micro-authorizations (≤ $5.00) followed by larger purchases",
    "Heuristic confidence: 0.90",
    "  Micro-auth 3513101: $1.00 (2017-11-27 08:12:00)",
    "  Micro-auth 3513105: $1.50 (2017-11-27 08:14:22)",
    "  Micro-auth 3513110: $2.00 (2017-11-27 08:19:05)"
  ],
  "metrics": {
    "is_testing_detected": true,
    "micro_auth_count": 3,
    "rapid_sequence_count": 3,
    "heuristic_confidence": 0.90
  },
  "limitations": [
    "Heuristic confidence represents statistical pattern match and is NOT an automated fraud verdict. Follow Policy Rule R5."
  ]
}
```

---

### 4. `find_shared_devices`
- **Input Parameters:**
  - `profile_id` (string, required): Composite device profile string.
- **Example Response:**
```json
{
  "tool": "find_shared_devices",
  "status": "success",
  "backend": "offline_sample",
  "subject": {
    "profile_id": "Windows | Windows 10 | edge 16.0 | 1366x768",
    "is_shared": true
  },
  "evidence": [
    "Device profile 'Windows | Windows 10 | edge 16.0 | 1366x768' is shared across 3 distinct cards and 3 customers",
    "Linked card IDs: C12382-K1, C04112-K1, C09933-K2",
    "Total transaction count observed from this device profile: 14"
  ],
  "metrics": {
    "connected_cards_count": 3,
    "connected_customers_count": 3,
    "total_txns_on_device": 14,
    "connected_cards": ["C12382-K1", "C04112-K1", "C09933-K2"]
  },
  "limitations": [
    "Shared device indicates common hardware footprint or network proxy; requires policy evaluation under Rule R6."
  ]
}
```

---

## 6. Error Handling & Edge Cases

The MCP server handles all failures gracefully by emitting structured error envelopes without throwing unhandled exceptions:

1. **Missing Required Argument:**
   ```json
   {
     "tool": "get_transaction",
     "status": "error",
     "backend": "offline_sample",
     "error": "Missing required argument 'txn_id'",
     "subject": {},
     "evidence": [],
     "metrics": {},
     "limitations": []
   }
   ```
2. **Entity Not Found in Graph:**
   ```json
   {
     "tool": "get_transaction",
     "status": "not_found",
     "backend": "offline_sample",
     "subject": {"txn_id": "999999999"},
     "evidence": ["Transaction ID 999999999 does not exist in graph."],
     "metrics": {},
     "limitations": ["Entity not found in graph database."]
   }
   ```
3. **Unknown Tool Name:**
   ```json
   {
     "tool": "unknown_tool",
     "status": "error",
     "backend": "offline_sample",
     "error": "Unknown tool 'unknown_tool'. Available tools: ['get_transaction', ...]",
     "subject": {},
     "evidence": [],
     "metrics": {},
     "limitations": []
   }
   ```

---

## 7. Backend Configuration & Startup

### Environment Variables
Configure the live TigerGraph cluster via environment variables:

```bash
# Live TigerGraph Cluster Connection
export TG_HOST="https://your-instance.tigergraph.io"
export TG_GRAPHNAME="FraudInvestigationGraph"
export TG_USERNAME="tigergraph"
export TG_PASSWORD="your-password"
export TG_SECRET="your-restpp-secret"
export TG_API_TOKEN="your-api-token"
```

### Backend Resolution Logic
1. If `TG_HOST` (or `TG_PASSWORD`/`TG_SECRET`) is present in the environment:
   - `TigerGraphInvestigationTools` instantiates `TigerGraphClient`.
   - MCP Server reports `backend: "tigergraph_live"`.
   - Tool calls invoke compiled GSQL query endpoints.
2. If credentials are unset:
   - `TigerGraphInvestigationTools` defaults to `SampleGraphClient`.
   - MCP Server reports `backend: "offline_sample"`.
   - Tool calls query fast pre-indexed CSV tables (`data/sample/`).

### Checking Server Status Programmatically
```python
from src.mcp.server import TigerGraphMCPServer

server = TigerGraphMCPServer()
status = server.get_server_status()

print(status)
# Output:
# {
#   'status': 'online',
#   'backend': 'offline_sample',
#   'is_live_tigergraph': False,
#   'tools_registered': 10,
#   'tool_names': ['get_transaction', 'get_customer_history', ...]
# }
```

---

## 8. Verification & Smoke Testing

To execute the automated MCP smoke test across benchmark cases:

```bash
python scripts/test_mcp_tools.py
```

To run the complete automated test suite:

```bash
pytest -v tests/test_mcp_server.py
```
