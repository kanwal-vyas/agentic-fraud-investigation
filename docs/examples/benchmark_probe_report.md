# Benchmark 20-Case GSQL Investigation Probe Report

**Execution Mode:** `SampleGraphClient (Offline Adapter)`  
**Total Cases Probed:** 20  

| Case | Flagged Txn | Customer | Card | Amount | Channel | Model Risk Score | Detected Pattern | Conf | Shared Device | Hist Cases |
|---|---|---|---|---|---|---|---|---|---|---|
| `HHG-001` | `3514030` | `C12382` | `C12382-K1` | $77.07 | `in_person` | 0.61 | `out_of_region_use` | 0.85 | No | 3 |
| `HHG-002` | `3478782` | `C11891` | `C11891-K1` | $292.36 | `online` | 0.79 | `card_not_present_fraud` | 0.72 | No | 1 |
| `HHG-003` | `3530164` | `C08623` | `C08623-K2` | $49.00 | `in_person` | 0.40 | `out_of_region_use` | 0.85 | No | 3 |
| `HHG-004` | `3583227` | `C08106` | `C08106-K1` | $128.33 | `online` | 0.34 | `card_not_present_fraud` | 0.72 | No | 3 |
| `HHG-005` | `3523199` | `C02923` | `C02923-K1` | $100.07 | `online` | 0.54 | `undocumented` | 0.88 | Yes | 3 |
| `HHG-006` | `3476682` | `C07297` | `C07297-K1` | $482.12 | `online` | 0.25 | `undocumented` | 0.88 | Yes | 3 |
| `HHG-007` | `3514948` | `C09933` | `C09933-K2` | $111.92 | `in_person` | 0.87 | `none` | 0.90 | No | 3 |
| `HHG-008` | `3558054` | `C13171` | `C13171-K2` | $55.68 | `online` | 0.38 | `none` | 0.90 | Yes | 3 |
| `HHG-009` | `3581141` | `C08299` | `C08299-K1` | $30.02 | `online` | 0.28 | `none` | 0.90 | Yes | 3 |
| `HHG-010` | `3506725` | `C10434` | `C10434-K1` | $1000.03 | `online` | 0.90 | `undocumented` | 0.88 | Yes | 1 |
| `HHG-011` | `3583368` | `C11923` | `C11923-K2` | $131.30 | `online` | 0.39 | `card_not_present_fraud` | 0.72 | No | 3 |
| `HHG-012` | `3553342` | `C05876` | `C05876-K2` | $30.91 | `in_person` | 0.55 | `none` | 0.90 | No | 2 |
| `HHG-013` | `3526826` | `C07671` | `C07671-K2` | $35.66 | `online` | 0.76 | `none` | 0.90 | Yes | 3 |
| `HHG-014` | `3478561` | `C13487` | `C13487-K1` | $74.96 | `online` | 0.05 | `undocumented` | 0.88 | Yes | 3 |
| `HHG-015` | `3464869` | `C03042` | `C03042-K1` | $599.94 | `online` | 0.77 | `undocumented` | 0.88 | Yes | 3 |
| `HHG-016` | `3534820` | `C09988` | `C09988-K1` | $59.67 | `online` | 0.37 | `none` | 0.90 | Yes | 3 |
| `HHG-017` | `3450629` | `C04570` | `C04570-K1` | $100.09 | `online` | 0.57 | `undocumented` | 0.88 | Yes | 1 |
| `HHG-018` | `3491361` | `C02354` | `C02354-K2` | $39.08 | `in_person` | 0.48 | `out_of_region_use` | 0.85 | No | 3 |
| `HHG-019` | `3503878` | `C07987` | `C07987-K2` | $99.92 | `online` | 0.90 | `card_not_present_new_device` | 0.78 | No | 3 |
| `HHG-020` | `3509359` | `C12265` | `C12265-K2` | $125.08 | `online` | 0.52 | `undocumented` | 0.88 | Yes | 2 |

## Detailed Case Breakdown

### HHG-001 (risk_score)
- **Flagged Txn:** `3514030` ($77.07, `in_person`)
- **Customer & Card:** `C12382` / `C12382-K1`
- **Model Risk Score (Input):** `0.61`
- **Top Pattern:** `out_of_region_use` (Heuristic Confidence: `0.85`)
- **Graph Claims:**
  - In-person transaction in remote billing region 444.0
  - Cardholder historical baseline established in home region 204.0 (18 prior transactions)
- **Historical Case Memory References:** `CC-1066, CC-1673, CC-2964`

### HHG-002 (risk_score)
- **Flagged Txn:** `3478782` ($292.36, `online`)
- **Customer & Card:** `C11891` / `C11891-K1`
- **Model Risk Score (Input):** `0.79`
- **Top Pattern:** `card_not_present_fraud` (Heuristic Confidence: `0.72`)
- **Graph Claims:**
  - Burst of online transactions ($292.36) on card C11891-K1
  - Model input risk score: 0.79
- **Historical Case Memory References:** `CC-4160`

### HHG-003 (customer_report)
- **Flagged Txn:** `3530164` ($49.00, `in_person`)
- **Customer & Card:** `C08623` / `C08623-K2`
- **Model Risk Score (Input):** `0.40`
- **Top Pattern:** `out_of_region_use` (Heuristic Confidence: `0.85`)
- **Graph Claims:**
  - In-person transaction in remote billing region 330.0
  - Cardholder historical baseline established in home region 158.0 (3 prior transactions)
- **Historical Case Memory References:** `CC-1589, CC-2817, CC-2935`
- **Connected Cards Found:** `C08623-K1, C02354-K1, C11464-K1, C09933-K1, C08945-K1, C11227-K1, C07987-K1, C05876-K1, C03575-K1, C06208-K1, C04570-K1, C13440-K1`

### HHG-004 (customer_report)
- **Flagged Txn:** `3583227` ($128.33, `online`)
- **Customer & Card:** `C08106` / `C08106-K1`
- **Model Risk Score (Input):** `0.34`
- **Top Pattern:** `card_not_present_fraud` (Heuristic Confidence: `0.72`)
- **Graph Claims:**
  - Burst of online transactions ($128.33) on card C08106-K1
  - Model input risk score: 0.34
- **Historical Case Memory References:** `CC-0696, CC-1736, CC-2121`

### HHG-005 (risk_score)
- **Flagged Txn:** `3523199` ($100.07, `online`)
- **Customer & Card:** `C02923` / `C02923-K1`
- **Model Risk Score (Input):** `0.54`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile iOS Device | iOS 9.3.5 | mobile safari 9.0 | 1024x768 is shared across 9 distinct cards
  - Connected customers: C02354, C08299, C07987, C13440, C06208, C03575, C07847, C02923, C12267
- **Historical Case Memory References:** `CC-2400, CC-2717, CC-2857`
- **Connected Cards Found:** `C02354-K1, C08299-K1, C07987-K1, C13440-K1, C06208-K1, C03575-K1, C07847-K1, C12267-K1, C11227-K1, C09998-K1, C09933-K1, C06403-K1, C08945-K1, C05876-K1`

### HHG-006 (customer_report)
- **Flagged Txn:** `3476682` ($482.12, `online`)
- **Customer & Card:** `C07297` / `C07297-K1`
- **Model Risk Score (Input):** `0.25`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile Trident/7.0 | Windows 7 | ie 11.0 for desktop | 1920x1080 is shared across 9 distinct cards
  - Connected customers: C07987, C02354, C07297, C08945, C11227, C12267, C09933, C06208, C06800
- **Historical Case Memory References:** `CC-0008, CC-0013, CC-0020`

### HHG-007 (risk_score)
- **Flagged Txn:** `3514948` ($111.92, `in_person`)
- **Customer & Card:** `C09933` / `C09933-K2`
- **Model Risk Score (Input):** `0.87`
- **Top Pattern:** `none` (Heuristic Confidence: `0.90`)
- **Graph Claims:**
  - Transaction consistent with cardholder normal spending profile
  - Billing region 264.0 matches established home baseline
- **Historical Case Memory References:** `CC-0104, CC-0657, CC-0765`
- **Connected Cards Found:** `C09933-K1, C02354-K1, C08945-K1, C10434-K1`

### HHG-008 (customer_report)
- **Flagged Txn:** `3558054` ($55.68, `online`)
- **Customer & Card:** `C13171` / `C13171-K2`
- **Model Risk Score (Input):** `0.38`
- **Top Pattern:** `none` (Heuristic Confidence: `0.90`)
- **Graph Claims:**
  - Transaction consistent with cardholder normal spending profile
  - Billing region  matches established home baseline
- **Historical Case Memory References:** `CC-0056, CC-0467, CC-0772`
- **Connected Cards Found:** `C13171-K1`

### HHG-009 (customer_report)
- **Flagged Txn:** `3581141` ($30.02, `online`)
- **Customer & Card:** `C08299` / `C08299-K1`
- **Model Risk Score (Input):** `0.28`
- **Top Pattern:** `none` (Heuristic Confidence: `0.90`)
- **Graph Claims:**
  - Transaction consistent with cardholder normal spending profile
  - Billing region 203.0 matches established home baseline
- **Historical Case Memory References:** `CC-0008, CC-0013, CC-0020`
- **Connected Cards Found:** `C02354-K1, C06208-K1, C04570-K1, C09933-K1, C12267-K1, C07987-K1, C13440-K1, C03575-K1, C07847-K1, C02923-K1, C08945-K1, C11082-K1, C02354-K2, C11227-K1, C03042-K1, C03651-K1, C05876-K1, C11464-K1, C07671-K1, C10434-K1, C08962-K1`

### HHG-010 (risk_score)
- **Flagged Txn:** `3506725` ($1000.03, `online`)
- **Customer & Card:** `C10434` / `C10434-K1`
- **Model Risk Score (Input):** `0.90`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile Windows | Windows 10 | edge 16.0 | 1366x768 is shared across 5 distinct cards
  - Connected customers: C07987, C06208, C03528, C02354, C10434
- **Historical Case Memory References:** `CC-0873`
- **Connected Cards Found:** `C07987-K1, C06208-K1, C03528-K1, C02354-K1, C03042-K1, C08945-K1, C09933-K1, C09933-K2, C11464-K1, C11227-K1, C12311-K1, C03277-K1, C03575-K1, C12267-K1, C07847-K1, C08623-K1, C07671-K1, C08299-K1, C08962-K1, C05876-K1, C13440-K1, C03651-K1, C06059-K1, C12265-K1`

### HHG-011 (customer_report)
- **Flagged Txn:** `3583368` ($131.30, `online`)
- **Customer & Card:** `C11923` / `C11923-K2`
- **Model Risk Score (Input):** `0.39`
- **Top Pattern:** `card_not_present_fraud` (Heuristic Confidence: `0.72`)
- **Graph Claims:**
  - Burst of online transactions ($131.30) on card C11923-K2
  - Model input risk score: 0.39
- **Historical Case Memory References:** `CC-0031, CC-0290, CC-1056`
- **Connected Cards Found:** `C11923-K1`

### HHG-012 (risk_score)
- **Flagged Txn:** `3553342` ($30.91, `in_person`)
- **Customer & Card:** `C05876` / `C05876-K2`
- **Model Risk Score (Input):** `0.55`
- **Top Pattern:** `none` (Heuristic Confidence: `0.90`)
- **Graph Claims:**
  - Transaction consistent with cardholder normal spending profile
  - Billing region 494.0 matches established home baseline
- **Historical Case Memory References:** `CC-0003, CC-2370`
- **Connected Cards Found:** `C05876-K1`

### HHG-013 (risk_score)
- **Flagged Txn:** `3526826` ($35.66, `online`)
- **Customer & Card:** `C07671` / `C07671-K2`
- **Model Risk Score (Input):** `0.76`
- **Top Pattern:** `none` (Heuristic Confidence: `0.90`)
- **Graph Claims:**
  - Transaction consistent with cardholder normal spending profile
  - Billing region  matches established home baseline
- **Historical Case Memory References:** `CC-1475, CC-3216, CC-3761`
- **Connected Cards Found:** `C07671-K1, C11227-K1`

### HHG-014 (analyst_request)
- **Flagged Txn:** `3478561` ($74.96, `online`)
- **Customer & Card:** `C13487` / `C13487-K1`
- **Model Risk Score (Input):** `0.05`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile SM-G935F Build/NRD90M | Android 7.0 | chrome 62.0 for android | 1920x1080 is shared across 6 distinct cards
  - Connected customers: C06617, C03528, C09998, C09733, C13487, C11082
- **Historical Case Memory References:** `CC-0008, CC-0013, CC-0020`
- **Connected Cards Found:** `C06617-K1, C03528-K1, C09998-K1, C09733-K1, C11082-K1, C09933-K1, C11464-K1, C07987-K1, C06208-K1, C12267-K1, C03575-K1, C11227-K1`

### HHG-015 (risk_score)
- **Flagged Txn:** `3464869` ($599.94, `online`)
- **Customer & Card:** `C03042` / `C03042-K1`
- **Model Risk Score (Input):** `0.77`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile Trident/7.0 | Windows 8.1 | ie 11.0 for desktop | 1680x1050 is shared across 2 distinct cards
  - Connected customers: C11227, C03042
- **Historical Case Memory References:** `CC-0615, CC-1313, CC-3886`
- **Connected Cards Found:** `C08945-K1, C09933-K1, C02354-K1, C03575-K1, C12267-K1, C08623-K1, C10434-K1, C11227-K1, C11464-K1, C13440-K1, C06208-K1, C05876-K1, C03277-K1, C08299-K1, C07987-K1, C06059-K1, C07297-K1, C04570-K1`

### HHG-016 (customer_report)
- **Flagged Txn:** `3534820` ($59.67, `online`)
- **Customer & Card:** `C09988` / `C09988-K1`
- **Model Risk Score (Input):** `0.37`
- **Top Pattern:** `none` (Heuristic Confidence: `0.90`)
- **Graph Claims:**
  - Transaction consistent with cardholder normal spending profile
  - Billing region  matches established home baseline
- **Historical Case Memory References:** `CC-0008, CC-0013, CC-0020`

### HHG-017 (risk_score)
- **Flagged Txn:** `3450629` ($100.09, `online`)
- **Customer & Card:** `C04570` / `C04570-K1`
- **Model Risk Score (Input):** `0.57`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile Windows | Windows 10 | chrome 65.0 | 1920x1080 is shared across 13 distinct cards
  - Connected customers: C04570, C07987, C07847, C02354, C03575, C06208, C11227, C13440, C11464, C09933, C12267, C05876, C08945
- **Historical Case Memory References:** `CC-1383`
- **Connected Cards Found:** `C11227-K1, C02354-K1, C07987-K1, C07847-K1, C03575-K1, C06208-K1, C13440-K1, C11464-K1, C09933-K1, C12267-K1, C05876-K1, C08945-K1, C03042-K1, C03651-K1, C08299-K1, C06059-K1, C07297-K1, C08623-K2, C08623-K1`

### HHG-018 (customer_report)
- **Flagged Txn:** `3491361` ($39.08, `in_person`)
- **Customer & Card:** `C02354` / `C02354-K2`
- **Model Risk Score (Input):** `0.48`
- **Top Pattern:** `out_of_region_use` (Heuristic Confidence: `0.85`)
- **Graph Claims:**
  - In-person transaction in remote billing region 126.0
  - Cardholder historical baseline established in home region 325.0 (84 prior transactions)
- **Historical Case Memory References:** `CC-0255, CC-0405, CC-0454`
- **Connected Cards Found:** `C02354-K1`

### HHG-019 (risk_score)
- **Flagged Txn:** `3503878` ($99.92, `online`)
- **Customer & Card:** `C07987` / `C07987-K2`
- **Model Risk Score (Input):** `0.90`
- **Top Pattern:** `card_not_present_new_device` (Heuristic Confidence: `0.78`)
- **Graph Claims:**
  - Online transaction from previously unseen device profile (Windows | other | chrome 61.0 | 1280x720)
  - Transaction amount $99.92 online under product code R
- **Historical Case Memory References:** `CC-2011, CC-2087, CC-2860`
- **Connected Cards Found:** `C07987-K1, C11227-K1, C02354-K1`

### HHG-020 (risk_score)
- **Flagged Txn:** `3509359` ($125.08, `online`)
- **Customer & Card:** `C12265` / `C12265-K2`
- **Model Risk Score (Input):** `0.52`
- **Top Pattern:** `undocumented` (Heuristic Confidence: `0.88`)
- **Graph Claims:**
  - Device profile Trident/7.0 | Windows 10 | ie 11.0 for desktop | 1920x1080 is shared across 7 distinct cards
  - Connected customers: C02354, C11227, C13440, C02923, C03575, C12265, C06208
- **Historical Case Memory References:** `CC-2277, CC-2447`
- **Connected Cards Found:** `C12265-K1, C02354-K1, C11227-K1, C13440-K1, C02923-K1, C03575-K1, C06208-K1`

