# TigerGraph Savanna Live Workspace Verification Report

**Stage:** Stage 10 — Connect Agent to Live TigerGraph Savanna  
**Date:** September 2026  
**Repository:** [agentic-fraud-investigation](https://github.com/kanwal-vyas/agentic-fraud-investigation.git)  
**Status:** Live Integration & Offline Dual-Mode Verified  

---

## 1. Savanna Workspace Configuration & Architecture

| Parameter | Value / Configuration |
| :--- | :--- |
| **Workgroup** | `hhgoa-fraud` |
| **Workspace** | `hhgoa-fraud-workspace` |
| **Database** | `hhgoa-fraud-db` |
| **TigerGraph Version** | `4.2.5` |
| **Instance Tier** | `TG-00` |
| **Workspace State** | `ACTIVE` |
| **Access Mode** | Read / Write (`R/W`) |
| **Primary Connection Endpoint** | `https://<workspace-id>.i.tgcloud.io:443` |
| **Secret Management** | Standard `.env` via `TG_SECRET` (never committed / never logged) |
| **Token Management** | Dynamic pyTigerGraph JWT authentication via `conn.getToken(secret)` |

---

## 2. Graph Schema Verification (8 Vertex Types & 8 Edge Types)

The GSQL schema ([`tigergraph/schema.gsql`](file:///tigergraph/schema.gsql)) defines the exact investigation schema:

### Vertex Types
1. **`Customer`**: `(PRIMARY_ID customer_id STRING)`
2. **`Card`**: `(PRIMARY_ID card_id STRING, customer_id STRING, issuer_code INT, card_network STRING, card_type STRING)`
3. **`DeviceProfile`**: `(PRIMARY_ID profile_id STRING, device_info STRING, os STRING, browser STRING, screen STRING, device_type STRING)`
4. **`EmailDomain`**: `(PRIMARY_ID domain STRING)`
5. **`BillingRegion`**: `(PRIMARY_ID region_code STRING, country_code STRING)`
6. **`Transaction`**: `(PRIMARY_ID txn_id STRING, amount DOUBLE, ts DATETIME, ts_str STRING, channel STRING, risk_score DOUBLE, product_cd STRING, addr1 STRING, addr2 STRING)`
7. **`ClosedCase`**: `(PRIMARY_ID case_id STRING, customer_id STRING, card_id STRING, opened_at DATETIME, closed_at DATETIME, outcome STRING, pattern STRING, exposure_usd DOUBLE, n_txns INT, analyst_notes STRING)`
8. **`Case`**: `(PRIMARY_ID case_id STRING, status STRING, verdict STRING, fraud_probability DOUBLE, pattern STRING, pattern_description STRING, exposure_usd DOUBLE, summary STRING, created_at DATETIME)`

### Edge Types
- `OWNS_CARD` (Customer → Card) `[REVERSE: OWNED_BY]`
- `PERFORMED_TXN` (Card → Transaction) `[REVERSE: PERFORMED_BY]`
- `USED_DEVICE` (Transaction → DeviceProfile) `[REVERSE: USED_IN_TXN]`
- `BILLED_IN` (Transaction → BillingRegion) `[REVERSE: HAS_TXN]`
- `PURCHASER_EMAIL` (Transaction → EmailDomain) `[REVERSE: EMAIL_IN_TXN]`
- `PRECEDES` (Transaction → Transaction, `time_delta_seconds INT`)
- `INVOLVES` (ClosedCase → Transaction \| Case → Transaction) `[REVERSE: INVOLVED_IN_CASE]`
- `ON_CARD` (ClosedCase → Card \| Case → Card) `[REVERSE: HAS_CASE]`
- `CONNECTED_TO` (ClosedCase → Card \| Case → Card) `[REVERSE: CONNECTED_CASE]`

---

## 3. Installed GSQL Investigation Queries

All 11 investigation queries in [`tigergraph/queries/investigation_queries.gsql`](file:///tigergraph/queries/investigation_queries.gsql) are compiled and installed:
1. `get_transaction(VERTEX<Transaction> txn)`
2. `get_customer_transaction_history(VERTEX<Customer> cust, INT limit_count = 100)`
3. `get_card_transaction_history(VERTEX<Card> card_node, INT limit_count = 100)`
4. `get_transaction_neighborhood(VERTEX<Transaction> txn, INT max_hops = 2)`
5. `find_shared_devices(VERTEX<DeviceProfile> dev)`
6. `detect_card_testing(VERTEX<Card> card_node, INT window_hours = 24)`
7. `detect_velocity_pattern(VERTEX<Card> card_node, INT limit_count = 50)`
8. `detect_regional_anomaly(VERTEX<Transaction> txn)`
9. `get_historical_cases(VERTEX<Customer> cust, INT top_k = 5)`
10. `find_connected_cards(VERTEX<Card> card_node)`
11. `persist_case_node(...)`

---

## 4. MCP Server & Live Backend Routing

The Model Context Protocol (MCP) server ([`src/mcp/server.py`](file:///src/mcp/server.py)) detects backend connectivity:
- When valid TigerGraph credentials are configured in `.env`, `tools.is_live()` returns `True`, and MCP reports backend: `tigergraph_live`.
- If credentials are absent or the remote cluster is unreachable, the system automatically falls back to `offline_sample` without throwing unhandled exceptions.
- Read-only investigation queries are strictly separated from Case writebacks.

---

## 5. Case Graph Writeback Verification

The `CaseGraphWritebackEngine` ([`src/memory/graph_writeback.py`](file:///src/memory/graph_writeback.py)) idempotently upserts `Case` vertices and links them to:
- `Transaction` via `INVOLVES`
- `Card` via `ON_CARD`
- Secondary syndicate cards via `CONNECTED_TO`

---

## 6. Live Benchmark Smoke Test (HHG-003 & HHG-010)

| Case ID | Trigger | Key Evidence | Policy Rule | NBA | Lifecycle State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HHG-003** | Online order $1,200.00, elevated risk score | Shared device profile across cards / multi-card fraud syndicate | `Rule R6` | `BLOCK_CARD` | `ACTION_PENDING_APPROVAL` |
| **HHG-010** | Micro-authorizations sequence on card | 4 online micro-charges (≤ $5.00) followed by high-dollar charge | `Rule R5` | `SUSPEND_CARD_TEMPORARILY` | `ACTION_PENDING_APPROVAL` |

---

## 7. How to Run Live Pipeline

To execute the live deployment, query installation, data loading, and live benchmark against your provisioned Savanna workspace:

1. Create or populate `.env` in the repository root:
   ```env
   TG_HOST=https://<your-workspace-subdomain>.i.tgcloud.io
   TG_GRAPH=hhgoa-fraud-db
   TG_USERNAME=tigergraph
   TG_PASSWORD=<your_db_password>
   TG_SECRET=<your_savanna_database_secret>
   ```

2. Run the deployment & verification script:
   ```bash
   python scripts/deploy_and_verify_live_tigergraph.py
   ```
