# Dataset Analysis: IEEE-CIS Fraud Detection (HHGOA Edition)

## 1. Overview & Verified Dataset Catalog
The dataset contains six months of card transactions from the IEEE-CIS Fraud Detection dataset (Vesta Corporation) spanning July 2, 2016 through December 31, 2016.

### Catalog of Dataset Files

| File | Size | Rows | Columns | Purpose |
|---|---|---|---|---|
| `transactions.csv` | 707.9 MB | 590,742 | 397 | Main transaction log. All original Vesta columns + `customer_id`, `ts`, `channel`, `risk_score`. |
| `identity.csv` | 26.7 MB | 144,432 | 41 | Device & network connection metadata for online transactions. Joins on `TransactionID`. |
| `closed_cases_history.csv` | 2.7 MB | 5,565 | 15 | Finished investigations (July–Oct 2016). 4,665 confirmed fraud, 900 cleared legitimate cases. Case memory. |
| `case_pack.csv` | 3.5 KB | 20 | 8 | The 20 benchmark test alerts (Nov–Dec 2016) to be evaluated. |
| `README.md` | 38.6 KB | 473 lines | — | Source of truth for task rules, policies (R1–R10), known fraud patterns, and answer schema. |

---

## 2. Verified Entity Mappings & Relationships (Correction 1)

### A. Customer (`customer_id`) to Card (`card_id`) Relationship
- **Customer Structure:** 13,553 unique customers in the dataset (`C00001` to `C13553`).
- **Card Issuer Field (`card1`):** In `transactions.csv`, each customer possesses an issuer-level code in `card1`. Across all 590,742 transactions, each `customer_id` maps to exactly one primary `card1` issuer value.
- **Card ID Suffixes (`-K1`, `-K2`, `-K3`):**
  - Standard customer primary card is designated as `CXXXXX-K1`.
  - In `closed_cases_history.csv` and `case_pack.csv`, cards appear with suffixes like `C12382-K1`, `C09933-K2`, and `C13440-K2`.
  - **Derivation Discovery:** Suffix `-K2` or `-K3` represents a **card reissue event** following an earlier compromise/block or multi-card issuance under the same customer profile. In 16 of the 20 benchmark cases in `case_pack.csv`, the customer had an earlier closed case in `closed_cases_history.csv` where an earlier card was investigated or reissued.

### B. Flagged Transaction to Card & Customer Mapping
- **100% Referential Integrity:** Every single one of the 20 flagged transactions (`flagged_txn_id`) in `case_pack.csv` exists in `transactions.csv`.
- **Customer ID Alignment:** For all 20 benchmark cases, `case_pack.customer_id` matches `transactions.customer_id` on `flagged_txn_id` exactly.
- **Card ID Assignment:**
  - `case_pack.csv` explicitly provides the active `card_id` on which the alert triggered (e.g. `C12382-K1` on `3514030`, `C09933-K2` on `3514948`).
  - `closed_cases_history.csv` explicitly links each past investigation to its active `card_id` and pipe-separated `txn_ids`.
  - For non-case transactions of a customer without documented reissue, transactions map to the customer's primary card `CXXXXX-K1`.

### C. DeviceProfile Composite Identification
`identity.csv` captures device and environment fingerprints for online transactions (`ProductCD` != `W`):
- `DeviceProfile` = `DeviceInfo` + `id_30` (OS) + `id_31` (Browser) + `id_33` (Screen Resolution).
- Example: `"SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080"`.
- This composite profile connects disparate transactions across cards and customers to identify shared syndicates (Rule R6).

---

## 3. Data Separation: Graph Attributes vs Analytical Features vs Raw Data

To ensure high TigerGraph query performance and clean GraphRAG grounding, transaction columns are strictly partitioned into three tiers:

### Tier 1: Graph Structural Entities & Attributes (Loaded into TigerGraph)
- **`Customer`**: `customer_id`
- **`Card`**: `card_id`, `customer_id`, `card1` (issuer code), `card4` (network: visa/mastercard), `card6` (type: debit/credit)
- **`Transaction`**: `txn_id`, `amount`, `ts` (DATETIME), `channel` (`in_person`/`online`), `risk_score` (0.00-1.00), `product_cd`, `addr1` (billing region), `addr2` (country)
- **`DeviceProfile`**: `profile_id`, `device_info`, `os`, `browser`, `screen`, `device_type`
- **`EmailDomain`**: `domain` (from `P_emaildomain`)
- **`BillingRegion`**: `region_code` (from `addr1`), `country_code` (from `addr2`)
- **`ClosedCase`**: `case_id`, `customer_id`, `card_id`, `opened_at`, `closed_at`, `outcome`, `pattern`, `exposure_usd`, `n_txns`, `analyst_notes`
- **`Case`**: `case_id`, `status`, `verdict`, `fraud_probability`, `pattern`, `exposure_usd`, `summary`, `created_at`

### Tier 2: Analytical Features (Used for Uncertainty & Typology Checks)
- `id_15`: Device relationship status (`New` vs `Found` vs `Unknown`).
- `id_23`: Proxy indicators (`IP_PROXY:TRANSPARENT`, `IP_PROXY:ANONYMOUS`, `IP_PROXY:HIDDEN`).
- `M1` to `M9`: Identity/cardholder match flags.
- `D1` to `D15`: Time deltas (days since last transaction/activity).
- `C1` to `C14`: Associated entity counts.

### Tier 3: Raw Model Engineered Data
- `V1` to `V339`: Raw Vesta feature vectors (kept in offline tabular store for specialized signal extraction if needed, not bloated into the graph).

---

## 4. Benchmark 20 Cases Reference Summary

| Case ID | Flagged Txn | Amount | Channel | Customer | Card | Trigger Type | Risk Score |
|---|---|---|---|---|---|---|---|
| `HHG-001` | 3514030 | $77.07 | in_person | C12382 | C12382-K1 | risk_score | 0.61 |
| `HHG-002` | 3478782 | $292.36 | online | C11891 | C11891-K1 | risk_score | 0.79 |
| `HHG-003` | 3530164 | $49.00 | in_person | C08623 | C08623-K2 | customer_report | 0.40 |
| `HHG-004` | 3583227 | $128.33 | online | C08106 | C08106-K1 | customer_report | 0.34 |
| `HHG-005` | 3523199 | $100.07 | online | C02923 | C02923-K1 | risk_score | 0.54 |
| `HHG-006` | 3476682 | $482.12 | in_person | C07297 | C07297-K1 | customer_report | 0.25 |
| `HHG-007` | 3514948 | $111.92 | in_person | C09933 | C09933-K2 | risk_score | 0.87 |
| `HHG-008` | 3558054 | $55.68 | in_person | C13171 | C13171-K2 | customer_report | 0.38 |
| `HHG-009` | 3581141 | $30.02 | online | C08299 | C08299-K1 | customer_report | 0.28 |
| `HHG-010` | 3506725 | $1,000.03 | online | C10434 | C10434-K1 | risk_score | 0.90 |
| `HHG-011` | 3583368 | $131.30 | online | C11923 | C11923-K2 | customer_report | 0.39 |
| `HHG-012` | 3553342 | $30.91 | in_person | C05876 | C05876-K2 | risk_score | 0.55 |
| `HHG-013` | 3526826 | $35.66 | online | C07671 | C07671-K2 | risk_score | 0.76 |
| `HHG-014` | 3478561 | $55.00 | online | C13487 | C13487-K1 | analyst_request | 0.05 |
| `HHG-015` | 3464869 | $599.94 | online | C03042 | C03042-K1 | risk_score | 0.77 |
| `HHG-016` | 3534820 | $59.67 | in_person | C09988 | C09988-K1 | customer_report | 0.37 |
| `HHG-017` | 3450629 | $100.09 | online | C04570 | C04570-K1 | risk_score | 0.57 |
| `HHG-018` | 3491361 | $39.08 | in_person | C02354 | C02354-K2 | customer_report | 0.48 |
| `HHG-019` | 3503878 | $99.92 | online | C07987 | C07987-K2 | risk_score | 0.90 |
| `HHG-020` | 3509359 | $125.08 | online | C12265 | C12265-K2 | risk_score | 0.52 |
