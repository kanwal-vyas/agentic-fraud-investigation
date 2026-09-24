# FinCEN Suspicious Activity Report (SAR) — Preparation Package
**Case Reference:** `HHG-010` | **Generated:** 2026-09-25T03:51:37.505278
**Regulatory Framework:** FinCEN 31 CFR § 1020.320 / Bank Secrecy Act
**NOTICE:** PREPARATION AND SUPERVISORY RECOMMENDATION ONLY — NOT TRANSMITTED TO REGULATORS.

---

## 1. Subject & Target Entity Information
- **Primary Customer ID:** `C10434`
- **Primary Account / Card ID:** `C10434-K1`
- **Flagged Transaction ID:** `3506725`
- **Total Aggregated Exposure:** `$1000.03 USD`

---

## 2. Suspicious Activity Characterization
- **Suspected Fraud Pattern:** `undocumented`
- **Investigation Assessment:** `SUSPICIOUS_BUT_UNCERTAIN` (Confidence: `0.55`)
- **Uncertainty Rating:** `HIGH`
- **SAR Trigger Rationale:** Organized multi-card fraud syndicate / account takeover pattern detected across graph entities.; Policy Rule R8 high-exposure escalation triggered supervisory review.

---

## 3. Supporting Evidence Summary
- Elevated model risk score (0.90) triggered triage alert
- Detected pattern 'FraudPattern.UNDOCUMENTED' (heuristic confidence: 0.88): Coordinated syndicate: identical device profile shared across multiple cardholders in a short window.
- Online device profile is shared across multiple distinct cardholders, indicating organized syndicate ring (Rule R6)
- Customer/card has connected secondary card entities requiring monitoring
- Customer/card has prior confirmed fraud history (CC-3748: undocumented, $1905.21)

## 4. Contradictory / Exculpatory Evidence
- Benign indicator: Customer C10434 has previously cleared investigation CC-0873: Case CC-0873: model scored a $50.05 transaction at 0.93. Cardholder confirmed travel to the billing region in ... (Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.)
- Benign indicator: Customer C01128 has previously cleared investigation CC-4158: Case CC-4158: model scored a $944.02 transaction at 0.88. Cardholder confirmed the purchase. Amount unusual fo... (Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.)
- Benign indicator: Customer C05670 has previously cleared investigation CC-4437: Case CC-4437: model scored a $663.99 transaction at 0.90. Cardholder confirmed the purchase. Amount unusual fo... (Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.)

---

## 5. Regulatory Filing & Approval Metadata
- **SAR Recommendation:** `RECOMMENDED`
- **Mandatory Supervisory Approval Route:** `Level L2`
- **Filing Status:** `UNFILED`
- **Statutory Threshold:** Exceeds $5,000 threshold or involves coordinated multi-entity structuring/syndicate activity.

---

## 6. Narrative for FinCEN Form 111
```
SUSPICIOUS ACTIVITY NARRATIVE — CASE HHG-010
The automated graph investigation agent identified suspicious transactions on account C10434-K1 associated with customer C10434.
Analysis of the transactional neighborhood and topological graph entities revealed undocumented with exposure totaling $1000.03.
Summary of findings: Elevated model risk score (0.90) triggered triage alert; Detected pattern 'FraudPattern.UNDOCUMENTED' (heuristic confidence: 0.88): Coordinated syndicate: identical device profile shared across multiple cardholders in a short window.; Online device profile is shared across multiple distinct cardholders, indicating organized syndicate ring (Rule R6); Customer/card has connected secondary card entities requiring monitoring; Customer/card has prior confirmed fraud history (CC-3748: undocumented, $1905.21).
Policy evaluation confirmed mandatory reporting criteria under FinCEN 31 CFR 1020.320, Bank Secrecy Act (BSA) 31 U.S.C. 5318(g), Federal Reserve Regulation SR 11-7.
This document represents an internal compliance preparation package pending Bank Secrecy Act (BSA) Officer sign-off.
```
