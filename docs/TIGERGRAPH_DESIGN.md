# TigerGraph Design & Loading Documentation

## 1. Schema Architecture
The graph schema for `FraudGraph` is designed around the verified entities and relationships in the IEEE-CIS Fraud dataset.

### Vertex Types

| Vertex | Primary Key | Attributes | Description |
|---|---|---|---|
| `Customer` | `customer_id` (STRING) | — | Bank cardholder entity (e.g., `C12382`) |
| `Card` | `card_id` (STRING) | `customer_id` (STRING), `issuer_code` (INT), `card_network` (STRING), `card_type` (STRING) | Specific payment card held by a customer (e.g. `C12382-K1`, `C09933-K2`) |
| `DeviceProfile` | `profile_id` (STRING) | `device_info` (STRING), `os` (STRING), `browser` (STRING), `screen` (STRING), `device_type` (STRING) | Composite device fingerprint for online transactions |
| `EmailDomain` | `domain` (STRING) | — | Purchaser email domain (e.g., `gmail.com`) |
| `BillingRegion` | `region_code` (STRING) | `country_code` (STRING) | Card billing region (`addr1`) and country code (`addr2`) |
| `Transaction` | `txn_id` (STRING) | `amount` (DOUBLE), `ts` (DATETIME), `ts_str` (STRING), `channel` (STRING), `risk_score` (DOUBLE), `product_cd` (STRING), `addr1` (STRING), `addr2` (STRING) | Payment authorization event |
| `ClosedCase` | `case_id` (STRING) | `customer_id` (STRING), `card_id` (STRING), `opened_at` (DATETIME), `closed_at` (DATETIME), `outcome` (STRING), `pattern` (STRING), `exposure_usd` (DOUBLE), `n_txns` (INT), `analyst_notes` (STRING) | Resolved historical investigations (Case Memory) |
| `Case` | `case_id` (STRING) | `status` (STRING), `verdict` (STRING), `fraud_probability` (DOUBLE), `pattern` (STRING), `pattern_description` (STRING), `exposure_usd` (DOUBLE), `summary` (STRING), `created_at` (DATETIME) | Live / active case vertex persisted back to graph |

---

### Edge Types

| Edge | Source Vertex | Target Vertex | Directed | Reverse Edge | Meaning |
|---|---|---|---|---|---|
| `OWNS_CARD` | `Customer` | `Card` | Yes | `OWNED_BY` | Customer holds/owns the card |
| `PERFORMED_TXN` | `Card` | `Transaction` | Yes | `PERFORMED_BY` | Transaction was charged to this card |
| `USED_DEVICE` | `Transaction` | `DeviceProfile` | Yes | `USED_IN_TXN` | Online transaction connection environment |
| `BILLED_IN` | `Transaction` | `BillingRegion` | Yes | `HAS_TXN` | Billing address region for the transaction |
| `PURCHASER_EMAIL` | `Transaction` | `EmailDomain` | Yes | `EMAIL_IN_TXN` | Email domain associated with the purchase |
| `PRECEDES` | `Transaction` | `Transaction` | Yes | — | Sequential ordering within a card account |
| `ON_CARD` | `ClosedCase` / `Case` | `Card` | Yes | `HAS_CASE` | Investigation opened against a card |
| `INVOLVES` | `ClosedCase` / `Case` | `Transaction` | Yes | `INVOLVED_IN_CASE` | Specific transactions included in the fraud episode |
| `CONNECTED_TO` | `ClosedCase` / `Case` | `Card` | Yes | `CONNECTED_CASE` | Connected cards caught in the same syndicate |

---

## 2. Card Mapping & Lifecycle Semantics
- **Issuer Code Alignment:** Every customer in `transactions.csv` has a unique issuer identifier in `card1`.
- **Primary Card Designation:** The default primary card is indexed as `CXXXXX-K1`.
- **Card Replacement / Reissue:** Suffixes `-K2` or `-K3` represent reissued cards following an earlier compromise. 16 of the 20 benchmark case customers had earlier closed cases in `closed_cases_history.csv` where earlier cards were closed or reissued.
- **Referential Integrity:** 100% of the 20 benchmark case pack transactions (`flagged_txn_id`) resolve cleanly to the active card and customer.

---

## 3. Streaming Preprocessing & Loading Pipeline
- Script: [`scripts/preprocess_for_tigergraph.py`](file:///c:/Users/kaval%20vyas/OneDrive/Desktop/Projects/hh-goa-task4/scripts/preprocess_for_tigergraph.py)
  - Processes `transactions.csv` in streaming chunks (e.g. 100k rows/chunk) ensuring < 500MB memory footprint.
  - Generates normalized tabular files ready for GSQL loading jobs:
    - `customers.csv`
    - `cards.csv`
    - `device_profiles.csv`
    - `email_domains.csv`
    - `billing_regions.csv`
    - `transactions.csv`
    - `closed_cases.csv`
- GSQL Schema: [`tigergraph/schema.gsql`](file:///c:/Users/kaval%20vyas/OneDrive/Desktop/Projects/hh-goa-task4/tigergraph/schema.gsql)
- Loading Job: [`tigergraph/loading_jobs.gsql`](file:///c:/Users/kaval%20vyas/OneDrive/Desktop/Projects/hh-goa-task4/tigergraph/loading_jobs.gsql)
- Validation Queries: [`tigergraph/queries/validation_queries.gsql`](file:///c:/Users/kaval%20vyas/OneDrive/Desktop/Projects/hh-goa-task4/tigergraph/queries/validation_queries.gsql)
- Validation Script: [`scripts/validate_tigergraph.py`](file:///c:/Users/kaval%20vyas/OneDrive/Desktop/Projects/hh-goa-task4/scripts/validate_tigergraph.py)
