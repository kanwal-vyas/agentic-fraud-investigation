# GraphRAG & Investigation Context Synthesis Engine (Stage 5)

## 1. Overview & Objectives

The **GraphRAG & Investigation Context Synthesis Engine** provides the foundational reasoning substrate for the autonomous fraud investigation agent. Rather than treating an LLM as a black box or performing superficial vector search over raw text, GraphRAG synthesizes:
1. **Authoritative Graph Evidence:** Structured entity relationships, transaction ego-networks, device sharing metrics, velocity clusters, and geographic baselines from TigerGraph.
2. **Historical Case Memory:** 5,565 resolved bank investigations (July–October 2016) containing both confirmed fraud precedents and cleared false-positive benchmarks.
3. **Official Bank Fraud Policies:** Rules R1 through R10 governing approval thresholds, escalation tiers, customer outreach mandates, and proportional card-blocking safeguards.
4. **Regulatory Compliance Mandates:** FinCEN Suspicious Activity Report (SAR) thresholds (31 CFR § 1020.320), Regulation E consumer protections (12 CFR Part 1005), Payment Card Network Zero Liability rules, and NIST SP 800-63B Step-Up Out-of-Band authentication standards.
5. **Balanced Evidence Architecture:** Dedicated extraction of **contradictory evidence** (benign explanations) alongside fraud signals, preventing confirmation bias.

---

## 2. Layered Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │       TigerGraph Investigation Tools         │
                    │   (Transaction, Customer, Card, Devices)     │
                    └──────────────────────┬───────────────────────┘
                                           │ (Structured Evidence)
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │            GraphEvidenceAdapter              │
                    │   (Dense Feature Extraction & Tokenizer)     │
                    └──────────────────────┬───────────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        │ (Enriched Query & Features)         │
                        ▼                                     ▼
        ┌───────────────────────────────┐     ┌───────────────────────────────┐
        │       BM25 + Metadata         │     │     Rule & Trigger Matcher    │
        │     Historical Case Index     │     │      (Policies R1 - R10 &     │
        │      (5,565 Closed Cases)     │     │     Regulatory Mandates)      │
        └───────────────┬───────────────┘     └───────────────┬───────────────┘
                        │                                     │
                        └──────────────────┬──────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │     InvestigationContextSynthesizer          │
                    │                                              │
                    │  • Supporting Graph & Historical Evidence    │
                    │  • Contradictory / Benign Explanations       │
                    │  • Evidence Gaps & Verification Actions      │
                    │  • Strict Source Provenance Attributions     │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │          InvestigationContext                │
                    │     (Grounding Model for Future Agent)       │
                    └──────────────────────────────────────────────┘
```

---

## 3. Knowledge Corpus Inventory

| Corpus Component | Source File / Origin | Type | Records | Key Schema Fields | Identifier | Purpose |
|---|---|---|---|---|---|---|
| **Closed Case Memory** | `data/raw/closed_cases_history.csv` | `closed_case` | 5,565 (4,527 confirmed fraud, 1,038 cleared) | `case_id`, `customer_id`, `card_id`, `outcome`, `pattern`, `exposure_usd`, `actions_taken`, `analyst_notes` | `case_id` | Grounds reasoning in real historical bank precedents and prior false positive resolutions. |
| **Bank Fraud Policies** | Official Challenge Brief & Policy Manual | `policy` | 10 rules (R1 to R10) | `rule_id`, `name`, `condition`, `actions`, `approval`, `description`, `keywords` | `rule_id` | Enforces regulatory actions, step-up auth, proportional blocking, and supervisor routing. |
| **Regulatory References** | FinCEN, CFPB, NIST, PCI, FFIEC | `regulation` | 5 standards | `regulation_id`, `title`, `section`, `excerpt`, `mandate_summary`, `keywords` | `regulation_id` | Mandates 30-day SAR filing, Reg E liability limits, and NIST AAL2 authentication. |

---

## 4. Retrieval & Ranking Engine

### Pure Offline BM25 Ranking with Exact Metadata Boosts
The engine uses a deterministic implementation of the BM25 probabilistic ranking function ($k_1 = 1.5, b = 0.75$) combined with deterministic metadata boosts:

$$\text{FinalScore}(D, Q) = \text{BM25}(D, Q) + \text{Boost}_{\text{Customer}} + \text{Boost}_{\text{Card}} + \text{Boost}_{\text{Pattern}}$$

- **Exact Customer Match Boost:** $+5.0$ (surfaces past investigations on the same cardholder).
- **Exact Card Match Boost:** $+4.0$ (surfaces card-level fraud history).
- **Exact Fraud Pattern Match Boost:** $+3.0$ (matches heuristic detection outputs).

### Dual-Outcome Retrieval
To prevent one-sided confirmation bias, the engine retrieves two distinct historical pools:
1. `historical_cases_confirmed_fraud`: Past cases where fraud was validated and actions like card blocking or SAR filing were executed.
2. `historical_cases_cleared`: Past cases where flagged alerts were investigated and cleared as legitimate cardholder activity (e.g., travel, authorized family member use).

---

## 5. Policy Rules & Regulatory Alignment

### Official Policy Rules (R1 - R10)
- **Rule R1 (Weak Signal Triage):** Risk score $< 0.70$ requires customer verification (`VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`) before blocking.
- **Rule R2 (Customer Denial):** Customer denies charge $\rightarrow$ `BLOCK_CARD`, `CREATE_CASE`, `FILE_REPORT` (if exposure $> \$1,000$).
- **Rule R3 (Customer Confirmation):** Customer confirms charge $\rightarrow$ `CLOSE_NO_FRAUD`, `ALLOW_TRANSACTION`.
- **Rule R4 (Unresponsive Customer):** No reply within 24h $\rightarrow$ `MONITOR_CARD`, `DECLINE_TRANSACTION`.
- **Rule R5 (Card Testing Rapid Reaction):** $\ge 3$ micro-authorizations ($\le \$5$) $\rightarrow$ `DECLINE_TRANSACTION`, `STEP_UP_AUTH`, `BLOCK_CARD`.
- **Rule R6 (Shared Origin / Device Syndicate):** Device shared across $\ge 2$ customer accounts $\rightarrow$ `CREATE_CASE`, `FILE_REPORT`, `MONITOR_CONNECTED_CARDS`.
- **Rule R7 (Disputed Recurring Baseline):** Matches home region/recurring merchant $\rightarrow$ `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` (do not block immediately).
- **Rule R8 (High Exposure / Uncertainty):** Exposure $> \$500$ or conflicting evidence $\rightarrow$ `ESCALATE_TO_ANALYST`.
- **Rule R9 (Undocumented Coordinated Pattern):** Novel multi-card anomaly $\rightarrow$ `CREATE_CASE`, `FILE_REPORT`, `ESCALATE_TO_ANALYST`.
- **Rule R10 (Proportional Blocking Safeguard):** Never `BLOCK_ALL_CARDS` unless $\ge 2$ cards show confirmed fraud or credentials compromised.

### Regulatory Standards
- **FinCEN 31 CFR § 1020.320:** Mandatory Suspicious Activity Report (SAR) filing for confirmed fraud exposure $\ge \$2,000$ within 30 days.
- **CFPB Regulation E (12 CFR Part 1005):** Consumer liability limits ($\$50 / \$500$) and 10-day provisional credit obligation.
- **PCI Zero Liability & CNP Rules:** Cardholder protection against unauthorized online transactions; merchant liability shift.
- **NIST SP 800-63B (Section 5.1.4):** Out-of-Band (OOB) authentication requirements for step-up verification.
- **FFIEC Layered Security Guidance:** Multi-account anomaly detection and velocity monitoring.

---

## 6. Synthesis Model: `InvestigationContext`

The `InvestigationContext` Pydantic model is the structured payload delivered to the agent:

```json
{
  "case_id": "HHG-001",
  "opened_at": "2016-12-04 19:55:28",
  "trigger_type": "customer_report",
  "trigger_text": "Cardholder reported unauthorized transaction in unfamiliar city.",
  "flagged_txn_id": 3514030,
  "card_id": "C12382-K1",
  "customer_id": "C12382",
  "model_risk_score": 0.61,
  "graph_evidence_summary": [
    "Transaction 3514030 ($77.07, in_person) on C12382-K1 for customer C12382",
    "Detected graph pattern 'out_of_region_use' (heuristic confidence: 0.85)",
    "Regional anomaly: billed in remote region 444.0 vs home region 204.0"
  ],
  "historical_cases_confirmed_fraud": [
    {
      "case_id": "CC-1066",
      "customer_id": "C12382",
      "card_id": "C12382-K1",
      "outcome": "confirmed_fraud",
      "pattern": "out_of_region_use",
      "exposure_usd": 170.98,
      "relevance_score": 12.45,
      "similarity_reasons": ["Same customer C12382", "Same card C12382-K1", "Matching pattern 'out_of_region_use'"],
      "actions_taken": "BLOCK_CARD; CREATE_CASE",
      "analyst_notes": "Case CC-1066: cardholder C12382 reported unrecognized activity..."
    }
  ],
  "historical_cases_cleared": [],
  "applicable_policies": [
    {
      "rule_id": "R2",
      "name": "Customer Denies Transaction",
      "triggering_evidence": ["Matched rule criteria on investigative context: Customer Denies Transaction"],
      "applicable_condition": "Cardholder explicitly denies authorizing the transaction upon verification",
      "recommended_actions": ["BLOCK_CARD", "CREATE_CASE", "FILE_REPORT"],
      "approval_level": "L1"
    }
  ],
  "contradictory_evidence": [
    {
      "evidence": "Flagged amount ($77.07) is consistent with normal average card spend ($113.36)",
      "benign_explanation": "Transaction amount is not an abnormal monetary outlier compared to established card history.",
      "source_id": "graph:card:C12382-K1",
      "weight": 0.6
    }
  ],
  "evidence_gaps": [
    {
      "missing_information": "Device hardware fingerprint and network IP proxy details",
      "recommended_verification": "Inspect web application gateway logs for device session integrity and IP ASN geolocation.",
      "urgency": "medium"
    }
  ],
  "source_attributions": [
    {
      "source_type": "graph",
      "source_id": "graph:txn:3514030",
      "relevance_score": 1.0,
      "content": "Transaction 3514030 ($77.07, in_person) on C12382-K1 for customer C12382",
      "metadata": {"case_id": "HHG-001", "txn_id": "3514030"}
    }
  ]
}
```

---

## 7. Strict Provenance & Safety Safeguards

1. **Every Snippet Has Provenance:** Every evidence item, historical case, policy directive, and regulatory mandate contains a strongly-typed `SourceProvenance` link (`source_type`, `source_id`, `relevance_score`, `content`, `metadata`).
2. **Zero Fabricated Probability:** GraphRAG outputs structured evidence, precedent, and policies. It **never** outputs synthetic claims like "Fraud probability = 94%".
3. **Offline Determinism:** Indexing and retrieval run with zero dependencies on third-party cloud APIs, external embedding models, or non-deterministic generators.

---

## 8. Verification & Smoke Testing

To test the GraphRAG benchmark probe across diverse triggers:

```bash
python scripts/test_graphrag.py
```

To run all automated GraphRAG unit tests:

```bash
pytest -v tests/test_graphrag.py
```
