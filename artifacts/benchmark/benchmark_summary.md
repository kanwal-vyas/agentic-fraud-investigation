# Benchmark Summary — 20 Hackathon Cases

**Evaluation Date:** 2026-09-23T13:22:06.813810
**Target Suite:** 20 HHG Benchmark Cases (Customer Report, Risk Score, Analyst Request)

---

## 1. Executive Performance Metrics

| Metric | Measured Value | Brief / Invariant Target | Status |
|---|---|---|---|
| **Total Cases Evaluated** | `20` | `20` | **[PASS]** |
| **Persisted Case Records** | `20` | `20` | **[PASS]** |
| **Average Tool Calls / Case** | `4.25` | `≤ 8.0` | **[PASS]** |
| **Cases Stopping Within Budget** | `100.0%` | `100.0%` | **[PASS]** |
| **Duplicate Tool Call Rate** | `0.0%` | `0.0%` | **[PASS]** |
| **Missing-Entity / NaN Contamination** | `0` | `0` | **[PASS]** |
| **Policy Reference Mismatches** | `0` | `0` | **[PASS]** |
| **Unreferenced Destructive Actions** | `0` | `0` | **[PASS]** |
| **Denied Destructive Actions Emitted** | `0` | `0` | **[PASS]** |
| **Lifecycle / Outcome Inconsistencies** | `0` | `0` | **[PASS]** |
| **SAR Preparation Packages Generated** | `10` | Accurate FinCEN Evaluation | **[PASS]** |

---

## 2. Case Distribution & Outcomes

| Case ID | Trigger Modality | Risk Score | Fraud Assessment | Conf. | NBA | Approval Req. | Final Lifecycle | Final Outcome | SAR Req. |
|---|---|---|---|---|---|---|---|---|---|
| `HHG-001` | `RISK_SCORE` | `0.61` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.30` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `False` |
| `HHG-002` | `RISK_SCORE` | `0.79` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.30` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `False` |
| `HHG-003` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.70` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `False` |
| `HHG-004` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.84` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `False` |
| `HHG-005` | `RISK_SCORE` | `0.54` | `LIKELY_BENIGN` | `0.95` | `CLOSE_NO_FRAUD` | `False` | `RESOLVED` | `RESOLVED_BENIGN` | `True` |
| `HHG-006` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.95` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `True` |
| `HHG-007` | `RISK_SCORE` | `0.87` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.30` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `False` |
| `HHG-008` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.95` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `True` |
| `HHG-009` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.70` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `False` |
| `HHG-010` | `RISK_SCORE` | `0.90` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.55` | `VERIFY_WITH_CUSTOMER` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `True` |
| `HHG-011` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.84` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `False` |
| `HHG-012` | `RISK_SCORE` | `0.55` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.30` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `False` |
| `HHG-013` | `RISK_SCORE` | `0.76` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.43` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `True` |
| `HHG-014` | `ANALYST_REQUEST` | `0.00` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.55` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `True` |
| `HHG-015` | `RISK_SCORE` | `0.77` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.43` | `VERIFY_WITH_CUSTOMER` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `True` |
| `HHG-016` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.95` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `True` |
| `HHG-017` | `RISK_SCORE` | `0.57` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.43` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `True` |
| `HHG-018` | `CUSTOMER_REPORT` | `0.00` | `LIKELY_FRAUD` | `0.70` | `BLOCK_CARD` | `True` | `ACTION_PENDING_APPROVAL` | `ACTION_PENDING_APPROVAL` | `False` |
| `HHG-019` | `RISK_SCORE` | `0.90` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.30` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `False` |
| `HHG-020` | `RISK_SCORE` | `0.52` | `SUSPICIOUS_BUT_UNCERTAIN` | `0.43` | `VERIFY_WITH_CUSTOMER` | `False` | `AWAITING_EVIDENCE` | `AWAITING_CUSTOMER_EVIDENCE` | `True` |

---

## 3. Controlled Additional Evidence Case Study (HHG-005)

When conflicting evidence or unverified travel indicators are detected, the investigator halts before destructive action and requests customer verification.

```
BEFORE ADDITIONAL EVIDENCE:
- Fraud Assessment: SUSPICIOUS_BUT_UNCERTAIN (Confidence: 0.60)
- Uncertainty Level: HIGH
- Evidence Gaps: ['unverified_cardholder_travel', 'customer_spending_confirmation']
- Requested Evidence: ['customer_travel_verification']
- Recommended NBA: VERIFY_WITH_CUSTOMER
- Lifecycle State: AWAITING_CUSTOMER_EVIDENCE

EVIDENCE RECEIVED (SIMULATED):
- Content: {'customer_response': 'confirmed', 'travel_verified': True}
- Channel: simulated_customer_verification_channel

AFTER ADDITIONAL EVIDENCE (REASSESSMENT):
- Fraud Assessment: LIKELY_BENIGN (Updated Confidence: 0.90)
- Uncertainty Level: LOW
- Updated NBA: MONITOR_CARD
- Final Lifecycle State: RESOLVED
- Final Outcome: RESOLVED_BENIGN
```

---

## 4. Verification & Reproducibility

Run full benchmark:
```bash
python scripts/run_agent_benchmark.py
```

Run test suite:
```bash
pytest -q
```
