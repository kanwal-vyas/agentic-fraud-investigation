# GSQL Investigation Query Library & Fraud Patterns

## 1. Overview
The TigerGraph GSQL investigation query library provides native graph traversals, entity neighborhood expansions, velocity aggregations, and pattern detection capabilities for the Agentic Fraud Investigation system.

---

## 2. Query Reference

### 1. `get_transaction(VERTEX<Transaction> txn)`
- **Input:** `txn` (Transaction vertex primary ID, e.g. `"3514030"`)
- **Traversal:** `Transaction` -(PERFORMED_BY)→ `Card` -(OWNED_BY)→ `Customer`, `Transaction` -(USED_DEVICE)→ `DeviceProfile`, `Transaction` -(BILLED_IN)→ `BillingRegion`, `Transaction` -(PURCHASER_EMAIL)→ `EmailDomain`.
- **Purpose:** Core lookup to inspect amount, timestamp, channel, input model risk score, card, customer, device, region, and email.
- **Example Output:**
```json
{
  "txn_id": "3514030",
  "amount": 77.07,
  "ts": "2016-12-04 19:55:28",
  "channel": "in_person",
  "risk_score": 0.61,
  "product_cd": "W",
  "card_id": "C12382-K1",
  "customer_id": "C12382",
  "addr1": "444.0"
}
```

---

### 2. `get_customer_transaction_history(VERTEX<Customer> cust, INT limit_count = 100)`
- **Input:** `cust` (`Customer` vertex ID, e.g. `"C12382"`)
- **Traversal:** `Customer` -(OWNS_CARD)→ `Card` -(PERFORMED_TXN)→ `Transaction` -(USED_DEVICE)→ `DeviceProfile`.
- **Purpose:** Analyzes historical spending baseline, total exposure, channel breakdown, and all cards/devices used by the cardholder.

---

### 3. `get_card_transaction_history(VERTEX<Card> card_node, INT limit_count = 100)`
- **Input:** `card_node` (`Card` vertex ID, e.g. `"C12382-K1"`)
- **Traversal:** `Card` -(PERFORMED_TXN)→ `Transaction` ordered by `ts DESC`.
- **Purpose:** Establishes card velocity, average transaction amount, max transaction amount, and chronological transaction sequence.

---

### 4. `get_transaction_neighborhood(VERTEX<Transaction> txn, INT max_hops = 2)`
- **Input:** `txn` (Transaction ID), `max_hops` (integer)
- **Traversal:** 1-hop and 2-hop ego network expanding to Card, Customer, DeviceProfile, BillingRegion, EmailDomain, ClosedCase, and sibling transactions on the same device.
- **Purpose:** Powers the interactive Graph visualizer in the Analyst Dashboard UI and provides grounded context for GraphRAG.

---

### 5. `find_shared_devices(VERTEX<DeviceProfile> dev)`
- **Input:** `dev` (DeviceProfile composite ID)
- **Traversal:** `DeviceProfile` -(USED_IN_TXN)→ `Transaction` -(PERFORMED_BY)→ `Card` -(OWNED_BY)→ `Customer`.
- **Purpose:** Identifies shared-device fraud rings, multi-account syndicates, and compromised credentials (Rule R6).

---

### 6. `detect_card_testing(VERTEX<Card> card_node, INT window_hours = 24)`
- **Input:** `card_node` (Card ID)
- **Traversal:** Scans card transactions for ≥3 micro-authorizations (`amount <= $5.00` on `channel == "online"`) within a tight window followed by larger authorizations (`amount >= $50.00`).
- **Purpose:** Detects card testing fraud (Rule R5).

---

### 7. `detect_velocity_pattern(VERTEX<Card> card_node, INT limit_count = 50)`
- **Input:** `card_node` (Card ID)
- **Traversal:** Aggregates transaction count, total sum, average amount, and time intervals.
- **Purpose:** Detects sudden velocity bursts and card-not-present fraud clusters within 48 hours.

---

### 8. `detect_regional_anomaly(VERTEX<Transaction> txn)`
- **Input:** `txn` (Transaction ID)
- **Traversal:** Compares `addr1` of transaction with historical mode `addr1` across card's history.
- **Purpose:** Detects out-of-region card-present purchases vs legitimate travel (Rule R4 / R7).

---

### 9. `get_historical_cases(VERTEX<Customer> cust, INT top_k = 5)`
- **Input:** `cust` (Customer ID)
- **Traversal:** `Customer` -(OWNS_CARD)→ `Card` -(HAS_CASE)→ `ClosedCase` + connected cases via shared device profiles.
- **Purpose:** Core case memory retrieval providing past analyst decisions, outcomes (`confirmed_fraud` vs `cleared`), and patterns.

---

### 10. `find_connected_cards(VERTEX<Card> card_node)`
- **Input:** `card_node` (Card ID)
- **Traversal:** Identifies all other cards owned by the same customer or used on the same DeviceProfile.
- **Purpose:** Informs monitoring of connected cards (`MONITOR_CONNECTED_CARDS`) under Rule R6.

---

## 3. Fraud Pattern Detection Framework

The detector outputs structured evidence for the 7 official patterns:

| Pattern | Detection Criteria | Supporting Signals |
|---|---|---|
| `card_testing` | ≥3 online micro-auths (< $5) followed by purchase > $50 within 24h | `detect_card_testing` |
| `card_not_present_fraud` | Burst of online purchases > $100 conflicting with historical baseline | `detect_velocity`, `get_card_history` |
| `card_not_present_new_device` | Online purchase from unseen device profile (`id_15` = New) | `get_transaction`, `get_card_history` |
| `out_of_region_use` | In-person transaction in remote `addr1` while normal home activity exists | `detect_regional_anomaly` |
| `account_takeover` | Cross-channel dissonance, credentials & card data both used, device shift | `get_customer_history`, `find_connected_cards` |
| `undocumented` | Device profile shared across ≥2 distinct customers in short window | `find_shared_devices`, `find_connected_cards` |
| `none` | Transaction consistent with normal cardholder baseline and home region | Baseline matching |
