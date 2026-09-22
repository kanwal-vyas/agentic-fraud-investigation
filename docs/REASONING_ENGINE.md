# Reasoning, Uncertainty & Action Policy Engine (Stage 6)

## 1. Executive Summary & Core Objective

The **Reasoning, Uncertainty & Action Policy Engine** transforms GraphRAG-synthesized graph evidence, historical precedents, and regulatory standards into policy-compliant, explainable investigative determinations.

### Key Architectural Principles
1. **Model Score $\ne$ Fraud Verdict:** Input `model_risk_score` (0.0 to 1.0) is strictly treated as an initial ML signal, not ground truth.
2. **Confidence $\ne$ Certainty:** Confidence (strength of pattern match) is decoupled from Epistemic Uncertainty (presence of unresolved gaps or contradictory explanations).
3. **Evidence Sufficiency $\ne$ Fraud Suspicion:** A case may have high suspicion but insufficient evidence to justify an irreversible card block without customer validation.
4. **Recommendation vs. Execution Boundary:** Action recommendations (`execution_status = "recommended"`) are strictly separated from authorization and execution.
5. **No Anonymous Rules:** Every action and decision is explicitly grounded in bank policy rules R1–R10 and regulatory mandates.

---

## 2. End-to-End Reasoning Pipeline

```
                     ┌──────────────────────────────────────────────┐
                     │            InvestigationContext              │
                     │  (Graph Evidence, Closed Cases, Policies)    │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │       DeterministicEvidenceEvaluator         │
                     │  (6 Dimensions: Txn, Behavioral, Network,    │
                     │    Historical, Policy, Contradictory)        │
                     └──────────────────────┬───────────────────────┘
                                            │
                        ┌───────────────────┴───────────────────┐
                        │                                       │
                        ▼                                       ▼
        ┌───────────────────────────────┐       ┌───────────────────────────────┐
        │      UncertaintyEvaluator     │       │ EvidenceSufficiencyEvaluator  │
        │  (Epistemic & Aleatoric Gaps) │       │ (Sufficient/Insufficient/     │
        └───────────────┬───────────────┘       │          Conflicting)         │
                        │                       └───────────────┬───────────────┘
                        │                                       │
                        └───────────────────┬───────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │          ControlledEvidencePlanner           │
                     │   (Expected Information Gain Prioritization) │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │             PolicyDecisionEngine             │
                     │    (Enforces Rules R1-R10, L1/L2 Routing)    │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │            NextBestActionEngine              │
                     │  (Produces Recommendation; Execution PENDING)│
                     └──────────────────────┬───────────────────────┘
                                            │
                        ┌───────────────────┴───────────────────┐
                        │                                       │
                        ▼                                       ▼
        ┌───────────────────────────────┐       ┌───────────────────────────────┐
        │     StopConditionEvaluator    │       │       ExplanationEngine       │
        │  (Formal Investigation Stop)  │       │  (5-Part Auditable Rationale) │
        └───────────────┬───────────────┘       └───────────────┬───────────────┘
                        │                                       │
                        └───────────────────┬───────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │         InvestigationAssessment              │
                     │     (Complete Grounded Agent Payload)        │
                     └──────────────────────────────────────────────┘
```

---

## 3. Evidence Weighting Across 6 Dimensions

The `DeterministicEvidenceEvaluator` evaluates context across 6 deterministic dimensions:

| Dimension | Evaluation Factors | Primary Impact | Weight |
|---|---|---|---|
| **1. Direct Transaction** | Amount, channel (in-person vs. online), merchant product code, input model risk score, trigger type. | Base suspicion baseline | 1.0 – 3.0 |
| **2. Behavioral & Velocity** | Heuristic pattern match (`card_testing`, `out_of_region_use`, `cnp_fraud`), velocity spikes. | Increases suspicion | 2.5 – 3.5 |
| **3. Network & Syndicate** | Multi-card device profile sharing, secondary connected cards, shared customer fingerprints (Rule R6). | High suspicion boost | 3.0 |
| **4. Historical Precedent** | Prior confirmed fraud cases on same customer/card in bank case memory (`closed_cases_history.csv`). | Historical continuity | 2.0 |
| **5. Policy Directives** | Explicit condition matches for Rules R1–R10. | Neutral governance | 1.0 |
| **6. Contradictory & Benign** | Familiar home billing region, normal average spend baseline, unique device profile, prior cleared travel cases. | **Decreases suspicion** | -2.0 – -5.0 |

---

## 4. Uncertainty & Evidence Sufficiency Models

### Controlled Vocabulary

- **`FraudAssessmentOutcome`**:
  - `likely_fraud`: Strong corroboration across graph, behavior, and history without plausible benign explanation.
  - `suspicious_but_uncertain`: Graph anomalies detected, but conflicting baseline evidence or missing customer verification exists.
  - `insufficient_evidence`: Weak initial trigger (< 0.70 score) without secondary graph corroboration.
  - `likely_benign`: Transaction conforms to established cardholder baseline with zero anomaly indicators.

- **`EvidenceSufficiencyState`**:
  - `sufficient`: Evidence meets all mandatory policy prerequisites for recommended NBA.
  - `insufficient`: Policy prerequisite unsatisfied (e.g. Rule R1 requires Out-of-Band verification prior to blocking).
  - `conflicting`: Opposing evidence signals present (e.g., travel alert vs. home region dispute).

- **`UncertaintyLevel`**: `low`, `moderate`, `material`, `high`.

---

## 5. Controlled Evidence Request Planning & Information Gain

When evidence is `insufficient` or `conflicting`, the `ControlledEvidencePlanner` formulates prioritized requests:

| Request Type | Reason / Gap Addressed | Expected Information Gain | Governing Policy |
|---|---|---|---|
| **`customer_validation`** | Cardholder authorization status unknown. Direct Out-of-Band SMS confirmation or denial. | **0.95** | Rule R1 / Rule R7 |
| **`secondary_card_check`** | Device profile shared across $\ge 2$ accounts. Query velocity on connected secondary cards. | **0.85** | Rule R6 |
| **`step_up_auth`** | Card testing sequence detected. Challenge next transaction with 2FA OTP. | **0.80** | Rule R5 / NIST SP 800-63B |
| **`analyst_info`** | Material uncertainty with exposure $> \$500$. Escalate for human forensic review. | **0.75** | Rule R8 / Rule R9 |

---

## 6. Policy Enforcement & Approval Tiers

The `PolicyDecisionEngine` enforces bank rules R1 through R10 and assigns approval routes:

- **Approval Tier `AUTO`:** Low-risk, non-destructive actions (`ALLOW_TRANSACTION`, `MONITOR_CARD`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `CLOSE_NO_FRAUD`).
- **Approval Tier `L1` (Team Lead):** Standard risk actions (`DECLINE_TRANSACTION`, `BLOCK_CARD` for exposure $\le \$2,500$).
- **Approval Tier `L2` (Fraud Manager):** High-impact actions (`BLOCK_ALL_CARDS`, `FILE_REPORT` / SAR, `BLOCK_CARD` for exposure $> \$2,500$, shared syndicate responses under Rule R6).

### Safeguard Rules Enforced
- **Rule R1 Safeguard:** Rejects automated card blocking if model score $< 0.70$ without customer verification.
- **Rule R10 Safeguard:** Strictly prohibits `BLOCK_ALL_CARDS` unless $\ge 2$ cards have confirmed fraud or credential theft.

---

## 7. Recommendation vs. Execution Separation

To guarantee safety and human-in-the-loop control:
1. Every Next Best Action is emitted with `execution_status = "recommended"`.
2. Actions requiring human sign-off flag `approval_required = True` and specify `approval_route`.
3. The system **never** mutates account status or contacts external parties during the reasoning pass.

---

## 8. Formal Stop Condition

The `StopConditionEvaluator` returns a structured `StopDecision`:
- **Stop = True:** Direct customer denial (Rule R2), confirmed benign activity (Rule R3), or transfer to supervisor queue (Rule R8).
- **Stop = False:** Evidence is insufficient/conflicting and customer verification request is pending.

---

## 9. Pluggable Architecture for Future LLM Reasoner

The engine implements `ReasoningEngineInterface` (`src/reasoning/base.py`):

```python
class ReasoningEngineInterface(ABC):
    @abstractmethod
    def assess(self, ctx: InvestigationContext) -> InvestigationAssessment:
        pass

    @abstractmethod
    def plan_evidence(self, ctx: InvestigationContext) -> List[EvidenceRequest]:
        pass

    @abstractmethod
    def recommend_action(self, ctx: InvestigationContext) -> NextBestAction:
        pass
```

Future LLM-based agent planners can drop in as alternative implementations without modifying any graph, data, or MCP layers.

---

## 10. Verification & Smoke Testing

To run the full reasoning benchmark across 6 diverse test cases:

```bash
python scripts/test_reasoning_engine.py
```

To run all automated reasoning unit tests:

```bash
pytest -v tests/test_reasoning_suite.py
```
