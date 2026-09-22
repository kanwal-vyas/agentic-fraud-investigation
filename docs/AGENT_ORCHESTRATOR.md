# Agentic Fraud Investigation Orchestrator Architecture (Stage 7)

## 1. Overview
The **Agentic Fraud Investigation Orchestrator** connects TigerGraph MCP tools, GraphRAG multi-perspective retrieval, in-case working memory, dynamic tool planning, reasoning checkpoints, deterministic uncertainty evaluation, bank policy guardrails (Rules R1–R10), and Next-Best-Action recommendations into an auditable investigation lifecycle.

```mermaid
graph TD
    Trigger[Trigger Ingestion: Risk Score / Customer Report / Analyst] --> InitState[Initialize Working Investigation State]
    InitState --> LoopStart{Step Count < Max (8) & Not Stopped?}
    
    LoopStart -->|Yes| LLMPlan[LLM / Agent Planner: Gap-Driven Tool Selection]
    LLMPlan --> SchemaVal{Valid MCP Tool & No Duplicate?}
    SchemaVal -->|Yes| ExecMCP[Execute TigerGraph MCP Tool]
    SchemaVal -->|No / Dup| InterceptSafe[Intercept: Proceed to Assess]
    
    ExecMCP --> TraceStep[Record InvestigationStep in Trace]
    TraceStep --> UpState[Update Working Memory Evidence]
    UpState --> Checkpoint[Reasoning Checkpoint Assessment]
    Checkpoint --> LoopStart
    
    LoopStart -->|No / Assess| GraphRAGCtx[Synthesize Full GraphRAG Context]
    InterceptSafe --> GraphRAGCtx
    
    GraphRAGCtx --> DetReason[Deterministic Reasoning Engine]
    DetReason --> EvSuff{Evidence Sufficient?}
    
    EvSuff -->|Insufficient / Conflicting| PlanEvReq[Plan Controlled EvidenceRequest]
    PlanEvReq --> Reassess[Reassessment Loop: Simulated Customer 2FA]
    Reassess --> DetReason
    
    EvSuff -->|Sufficient| PolicyEngine[Policy Decision Engine: Rules R1-R10]
    PolicyEngine --> NBAEngine[Next-Best-Action Determination]
    NBAEngine --> Boundary[Recommendation vs Execution Boundary]
    Boundary --> StopEval[Stop Condition Evaluator]
    StopEval --> ExplEngine[5-Part Structured Explanation Engine]
    ExplEngine --> InvResult[Emit InvestigationResult]
```

---

## 2. Dynamic Tool Selection & Planning

The agent selects investigation tools dynamically according to trigger modalities and active evidence gaps rather than executing a hardcoded universal sequence:

| Trigger Modality | Primary Initial Goal | Dynamic Tool Calling Progression |
| :--- | :--- | :--- |
| **`customer_report`** | Establish transaction attributes & baseline | `get_transaction` $\rightarrow$ `get_card_history` $\rightarrow$ `find_shared_devices` $\rightarrow$ `get_historical_cases` |
| **`risk_score`** | Verify burst velocity, testing & region | `get_transaction` $\rightarrow$ `detect_velocity` $\rightarrow$ `detect_regional_anomaly` $\rightarrow$ `find_shared_devices` $\rightarrow$ `get_historical_cases` |
| **`analyst_request`** | Uncover syndicate rings & connected cards | `get_transaction` $\rightarrow$ `find_shared_devices` $\rightarrow$ `find_connected_cards` $\rightarrow$ `get_card_history` |

### Guardrails in Tool Planning:
1. **Registered Tool Validation**: Every requested tool must exist in `MCP_INVESTIGATION_TOOLS`. Unregistered or unauthorized tools are intercepted and defaulted to safe assessment.
2. **Duplicate Tool Call Suppression**: Tools already called with identical primary arguments are suppressed (`Duplicate tool call rate = 0.0%`).
3. **Bounded Iteration**: Loop has a hard limit of `max_steps = 8` (`100.0%` cases stop within limit).

---

## 3. Working Memory (`WorkingInvestigationState`)

The orchestrator maintains an active state across each case investigation:
- **`trigger`**: Initial trigger payload with case ID, transaction ID, customer ID, card ID, model risk score, and opening timestamp.
- **`tools_called`**: Ordered history of tools invoked.
- **`collected_evidence`**: Raw and parsed structured responses from MCP tool executions.
- **`evidence_ids`**: Provenance references (`tool:txn_id:step_number`).
- **`assessment_checkpoints`**: Intermediate `InvestigationAssessment` evaluations recorded after each step.
- **`requested_evidence`**: Active and planned `EvidenceRequest` objects.
- **`policy_decisions`**: Rules R1–R10 evaluations.

---

## 4. Reasoning Checkpoints

To demonstrate cognitive progression in the UI and audit logs, the agent evaluates a reasoning checkpoint after each tool call:
- **Checkpoint 1 (Initial Txn)**: Evaluates single-signal suspicion, uncertainty level, and initial gaps.
- **Checkpoint 2 (Baseline / Velocity)**: Incorporates card history or transaction velocity.
- **Checkpoint 3 (Graph Network)**: Incorporates shared device rings or connected card findings.
- **Checkpoint 4 (Precedent & Context)**: Integrates historical closed case precedent and policy rules.

---

## 5. Controlled Evidence Requests & Reassessment Loop

When evidence is `INSUFFICIENT` or `CONFLICTING`:
1. The planner formulates a prioritized `EvidenceRequest` (e.g. `CUSTOMER_VALIDATION`, `SECONDARY_CARD_CHECK`) ranked by information gain.
2. The agent executes a reassessment cycle when simulated or real additional evidence is provided (e.g. `customer_response: confirmed` $\rightarrow$ transitions from `SUSPICIOUS_BUT_UNCERTAIN` to `LIKELY_BENIGN` and NBA `CLOSE_NO_FRAUD`).

---

## 6. Policy Boundary & Execution Separation

- **Authoritative Deterministic Engine**: The LLM provides investigative planning and reasoning suggestions, but the deterministic `PolicyDecisionEngine` enforces bank rules R1–R10.
- **Recommendation Separation**: All emitted actions have `execution_status = "recommended"`. The system never automatically blocks cards or freezes accounts without explicit authorization through the assigned route (`auto`, `L1`, `L2`).
- **Unsupported Action Rate**: Strictly `0.0%`.

---

## 7. Orchestration Quality Metrics

Evaluation across 12 benchmark cases (`scripts/run_agent_benchmark.py`):
- **Total Cases Evaluated**: 12
- **Average Tool Calls / Case**: 4.17
- **Duplicate Tool Call Rate**: 0.0%
- **Cases Stopping Within Limit**: 100.0%
- **Evidence Request Rate**: 91.7%
- **Reassessment Rate**: 8.3%
- **Policy Conflict Rate**: 0.0%
- **Unsupported Action Rate**: 0.0%
