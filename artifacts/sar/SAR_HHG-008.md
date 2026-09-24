# FinCEN Suspicious Activity Report (SAR) — Preparation Package
**Case Reference:** `HHG-008` | **Generated:** 2026-09-25T03:51:34.516940
**Regulatory Framework:** FinCEN 31 CFR § 1020.320 / Bank Secrecy Act
**NOTICE:** PREPARATION AND SUPERVISORY RECOMMENDATION ONLY — NOT TRANSMITTED TO REGULATORS.

---

## 1. Subject & Target Entity Information
- **Primary Customer ID:** `C13171`
- **Primary Account / Card ID:** `C13171-K2`
- **Flagged Transaction ID:** `3558054`
- **Total Aggregated Exposure:** `$55.68 USD`

---

## 2. Suspicious Activity Characterization
- **Suspected Fraud Pattern:** `undocumented, card_not_present_new_device`
- **Investigation Assessment:** `LIKELY_FRAUD` (Confidence: `0.95`)
- **Uncertainty Rating:** `HIGH`
- **SAR Trigger Rationale:** Organized multi-card fraud syndicate / account takeover pattern detected across graph entities.

---

## 3. Supporting Evidence Summary
- Direct customer report: Customer C13171 message: 'I never made this $55.68 purchase. Please check my card.' Refers to 3558054.
- Detected pattern 'FraudPattern.UNDOCUMENTED' (heuristic confidence: 0.88): Coordinated syndicate: identical device profile shared across multiple cardholders in a short window.
- Detected pattern 'FraudPattern.CARD_NOT_PRESENT_NEW_DEVICE' (heuristic confidence: 0.78): Card-not-present authorization initiated from a new device profile with no prior card history.
- Online device profile is shared across multiple distinct cardholders, indicating organized syndicate ring (Rule R6)
- Customer/card has connected secondary card entities requiring monitoring
- Customer/card has prior confirmed fraud history (CC-3566: card_not_present_fraud, $88.07)

## 4. Contradictory / Exculpatory Evidence
- Benign indicator: Customer C13171 has previously cleared investigation CC-4819: Case CC-4819: model scored a $66.52 transaction at 0.92. Cardholder confirmed the purchase from a new phone. D... (Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.)
- Benign indicator: Customer C01128 has previously cleared investigation CC-4158: Case CC-4158: model scored a $944.02 transaction at 0.88. Cardholder confirmed the purchase. Amount unusual fo... (Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.)
- Benign indicator: Customer C08106 has previously cleared investigation CC-0696: Case CC-0696: model scored a $13.68 transaction at 0.83. Cardholder confirmed travel to the billing region in ... (Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.)
- Benign indicator: Flagged amount ($55.68) is consistent with normal average card spend ($50.66) (Transaction amount is not an abnormal monetary outlier compared to established card history.)

---

## 5. Regulatory Filing & Approval Metadata
- **SAR Recommendation:** `RECOMMENDED`
- **Mandatory Supervisory Approval Route:** `Level L2`
- **Filing Status:** `UNFILED`
- **Statutory Threshold:** Exceeds $5,000 threshold or involves coordinated multi-entity structuring/syndicate activity.

---

## 6. Narrative for FinCEN Form 111
```
SUSPICIOUS ACTIVITY NARRATIVE — CASE HHG-008
The automated graph investigation agent identified suspicious transactions on account C13171-K2 associated with customer C13171.
Analysis of the transactional neighborhood and topological graph entities revealed undocumented, card_not_present_new_device with exposure totaling $55.68.
Summary of findings: Direct customer report: Customer C13171 message: 'I never made this $55.68 purchase. Please check my card.' Refers to 3558054.; Detected pattern 'FraudPattern.UNDOCUMENTED' (heuristic confidence: 0.88): Coordinated syndicate: identical device profile shared across multiple cardholders in a short window.; Detected pattern 'FraudPattern.CARD_NOT_PRESENT_NEW_DEVICE' (heuristic confidence: 0.78): Card-not-present authorization initiated from a new device profile with no prior card history.; Online device profile is shared across multiple distinct cardholders, indicating organized syndicate ring (Rule R6); Customer/card has connected secondary card entities requiring monitoring; Customer/card has prior confirmed fraud history (CC-3566: card_not_present_fraud, $88.07).
Policy evaluation confirmed mandatory reporting criteria under FinCEN 31 CFR 1020.320, Bank Secrecy Act (BSA) 31 U.S.C. 5318(g), Federal Reserve Regulation SR 11-7.
This document represents an internal compliance preparation package pending Bank Secrecy Act (BSA) Officer sign-off.
```
