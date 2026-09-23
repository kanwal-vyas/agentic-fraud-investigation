from typing import List, Dict, Any, Optional
import datetime
from src.models.agent import (
    InvestigationTrigger,
    InvestigationStep,
    WorkingInvestigationState,
    InvestigationResult,
    AgentActionType,
    AgentToolCallDecision,
    TriggerType
)
from src.models.context import InvestigationContext
from src.models.reasoning import (
    InvestigationAssessment,
    EvidenceRequest,
    NextBestAction,
    StopDecision,
    StructuredExplanation
)
from src.models.case_memory import (
    CaseLifecycleStatus,
    ActionExecutionStatus,
    PersistedEvidenceItem,
    CaseDecisionRecord,
    ActionAuditRecord,
    SARCaseRecord,
    ReassessmentRecord,
    CaseMemoryRecord,
)
from src.memory.case_store import CaseStoreInterface, InMemoryCaseStore
from src.memory.lifecycle import CaseLifecycleManager
from src.memory.sar_generator import SARCaseEvaluator
from src.memory.graph_writeback import CaseGraphWritebackEngine
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.sample_client import SampleGraphClient
from src.mcp.server import TigerGraphMCPServer
from src.rag.synthesis import InvestigationContextSynthesizer
from src.reasoning.engine import DeterministicReasoningEngine
from src.agent.planner import AgentPlanner
from src.agent.provider import MockLLMProvider


class AgenticFraudInvestigator:
    """
    Autonomous Fraud Investigation Agent orchestrating TigerGraph MCP tool execution,
    GraphRAG contextual retrieval, working memory, reasoning checkpoints, deterministic
    uncertainty modeling, policy enforcement (Rules R1-R10), Next-Best-Action recommendations,
    Case Memory lifecycle persistence, FinCEN SAR analysis, and TigerGraph graph writeback.
    """
    def __init__(
        self,
        mcp_server: Optional[TigerGraphMCPServer] = None,
        synthesizer: Optional[InvestigationContextSynthesizer] = None,
        reasoning_engine: Optional[DeterministicReasoningEngine] = None,
        planner: Optional[AgentPlanner] = None,
        case_store: Optional[CaseStoreInterface] = None,
        lifecycle_manager: Optional[CaseLifecycleManager] = None,
        sar_evaluator: Optional[SARCaseEvaluator] = None,
        writeback_engine: Optional[CaseGraphWritebackEngine] = None,
        max_steps: int = 8
    ):
        self.mcp_server = mcp_server or TigerGraphMCPServer()
        self.synthesizer = synthesizer or InvestigationContextSynthesizer()
        self.reasoning_engine = reasoning_engine or DeterministicReasoningEngine()
        self.planner = planner or AgentPlanner(MockLLMProvider())
        self.case_store = case_store or InMemoryCaseStore()
        self.lifecycle_manager = lifecycle_manager or CaseLifecycleManager()
        self.sar_evaluator = sar_evaluator or SARCaseEvaluator()
        sample_client = None
        tg_client = None
        if hasattr(self.mcp_server, "tools") and hasattr(self.mcp_server.tools, "client"):
            c = self.mcp_server.tools.client
            if isinstance(c, TigerGraphClient):
                tg_client = c
            else:
                sample_client = c
        elif hasattr(self.mcp_server, "graph_client"):
            sample_client = self.mcp_server.graph_client

        self.writeback_engine = writeback_engine or CaseGraphWritebackEngine(
            tg_client=tg_client,
            sample_client=sample_client or SampleGraphClient()
        )
        self.max_steps = max_steps

    def investigate(
        self,
        trigger: InvestigationTrigger,
        simulated_evidence_response: Optional[Dict[str, Any]] = None
    ) -> InvestigationResult:
        """
        Executes a complete, bounded investigation loop for an incoming fraud case trigger,
        persisting all evidence, findings, policy evaluations, NBA decisions, and outcomes into Case Memory
        and performing idempotent graph writeback.
        """
        now = datetime.datetime.now().isoformat()
        
        # 1. Initialize Persistent Case Record & Working State Memory
        case_record = CaseMemoryRecord(
            case_id=trigger.case_id,
            benchmark_case_id=trigger.case_id if trigger.case_id.startswith("HHG-") else None,
            customer_id=trigger.customer_id,
            card_id=trigger.card_id,
            triggering_txn_id=trigger.transaction_id,
            trigger_type=trigger.trigger_type.value if hasattr(trigger.trigger_type, "value") else str(trigger.trigger_type),
            created_at=trigger.opened_at or now,
            updated_at=now,
            status=CaseLifecycleStatus.OPEN
        )
        self.case_store.create_case(case_record)
        self.lifecycle_manager.transition_state(
            case_record, CaseLifecycleStatus.INVESTIGATING, reason="Investigation loop initiated"
        )
        self.case_store.update_case(case_record.case_id, {"status": case_record.status})

        state = WorkingInvestigationState(trigger=trigger)
        investigation_steps: List[InvestigationStep] = []

        # 2. Bounded Investigation Tool-Calling Loop
        while not state.is_stopped and state.step_count < self.max_steps:
            state.step_count += 1
            decision = self.planner.decide_next_step(state)

            if decision.action == AgentActionType.CALL_TOOL and decision.tool:
                # Execute Tool through TigerGraph MCP Server
                tool_result = self.mcp_server.call_tool(decision.tool, decision.arguments)
                evidence_id = f"{decision.tool}:{trigger.transaction_id}:{state.step_count}"
                
                # Format Result Summary
                status = tool_result.get("status", "success")
                outcome = "success" if status == "success" else "error"
                evidence_count = len(tool_result.get("evidence", []))
                summary = f"Executed {decision.tool}: status={status}, returned {evidence_count} evidence items."
                
                if tool_result.get("evidence"):
                    summary += f" Key findings: {'; '.join(tool_result['evidence'][:2])}"

                # Record Investigation Step in Trace
                step = InvestigationStep(
                    step_number=state.step_count,
                    reason=decision.reason,
                    tool=decision.tool,
                    input_args=decision.arguments,
                    result_summary=summary,
                    evidence_ids=[evidence_id],
                    timestamp=datetime.datetime.now().isoformat(),
                    outcome=outcome
                )
                investigation_steps.append(step)

                # Update Working State Memory
                state.tools_called.append(decision.tool)
                state.collected_evidence.append(tool_result)
                state.evidence_ids.append(evidence_id)

                # Append tool evidence to persistent case memory
                for ev in tool_result.get("evidence", []):
                    item = PersistedEvidenceItem(
                        statement=ev,
                        source_id=f"{decision.tool}:{trigger.transaction_id}",
                        source_type="graph",
                        category="graph_fact",
                        timestamp=datetime.datetime.now().isoformat()
                    )
                    case_record.evidence_items.append(item)
                    self.case_store.append_evidence(case_record.case_id, item)

                # Reasoning Checkpoint: Evaluate intermediate context
                ctx_intermediate = self._build_context(trigger, state)
                checkpoint_assessment = self.reasoning_engine.assess(ctx_intermediate)
                state.assessment_checkpoints.append(checkpoint_assessment)

            elif decision.action in [AgentActionType.ASSESS, AgentActionType.STOP]:
                state.is_stopped = True
                break

        # 3. Final GraphRAG Context Synthesis & Authoritative Reasoning Assessment
        final_ctx = self._build_context(trigger, state)
        assessment = self.reasoning_engine.assess(final_ctx)

        # 4. Controlled Additional Evidence & Reassessment Loop
        assessment_history = list(state.assessment_checkpoints)
        if assessment not in assessment_history:
            assessment_history.append(assessment)

        final_assessment = assessment
        if assessment.evidence_requests and not simulated_evidence_response:
            self.lifecycle_manager.transition_state(
                case_record,
                CaseLifecycleStatus.AWAITING_EVIDENCE,
                reason="Evidence requested from customer or external source"
            )
            case_record.evidence_requests = [
                req.model_dump() if hasattr(req, "model_dump") else dict(req)
                for req in assessment.evidence_requests
            ]

        if simulated_evidence_response and (
            assessment.evidence_requests or assessment.fraud_assessment.value in ["suspicious_but_uncertain", "likely_fraud"]
        ):
            reassessed = self.reasoning_engine.reassess_with_additional_evidence(
                final_ctx,
                simulated_evidence_response
            )
            assessment_history.append(reassessed)
            final_assessment = reassessed
            self.lifecycle_manager.transition_state(
                case_record,
                CaseLifecycleStatus.REASSESSED,
                reason="Reassessed with provided customer/analyst evidence"
            )
            case_record.reassessments.append(
                ReassessmentRecord(
                    timestamp=datetime.datetime.now().isoformat(),
                    prior_assessment=assessment.fraud_assessment.value,
                    new_assessment=reassessed.fraud_assessment.value,
                    evidence_received=simulated_evidence_response,
                    rationale="; ".join(reassessed.explanation.why_action) or "Reassessed case"
                )
            )

        # 5. Populate Findings, Uncertainty, and Policy Decisions
        case_record.fraud_assessment = final_assessment.fraud_assessment.value
        case_record.confidence = float(final_assessment.confidence)
        case_record.uncertainty_level = final_assessment.uncertainty.level.value
        case_record.uncertainty_reasons = final_assessment.uncertainty.reasons
        case_record.fraud_patterns_identified = list(final_assessment.suspected_patterns)
        case_record.supporting_findings = final_assessment.supporting_evidence
        case_record.contradictory_findings = final_assessment.contradictory_evidence
        case_record.evidence_gaps = final_assessment.evidence_gaps
        rules_eval = [d.get("rule_id", "") if isinstance(d, dict) else getattr(d, "rule_id", "") for d in final_assessment.policy_decisions]
        case_record.policy_rules_evaluated = [r for r in rules_eval if r]

        if final_assessment.policy_decisions:
            pd = final_assessment.policy_decisions[0]
            if isinstance(pd, dict):
                case_record.policy_decision = CaseDecisionRecord(
                    rules_evaluated=case_record.policy_rules_evaluated,
                    permitted=pd.get("permitted", True),
                    required_action=pd.get("required_action") if isinstance(pd.get("required_action"), (str, type(None))) else str(pd.get("required_action")),
                    approval_route=pd.get("approval_route", "auto") if isinstance(pd.get("approval_route"), str) else str(pd.get("approval_route", "auto")),
                    approval_required=pd.get("approval_required", False),
                    violations=pd.get("violations", []),
                    prerequisites=pd.get("prerequisites", []),
                    timestamp=datetime.datetime.now().isoformat()
                )
            else:
                case_record.policy_decision = CaseDecisionRecord(
                    rules_evaluated=case_record.policy_rules_evaluated,
                    permitted=getattr(pd, "permitted", True),
                    required_action=pd.required_action.value if getattr(pd, "required_action", None) else None,
                    approval_route=pd.approval_route.value if getattr(pd, "approval_route", None) else "auto",
                    approval_required=getattr(pd, "approval_required", False),
                    violations=getattr(pd, "violations", []),
                    prerequisites=getattr(pd, "prerequisites", []),
                    timestamp=datetime.datetime.now().isoformat()
                )

        # 6. Extract Next Best Action & Record Recommendation
        nba = final_assessment.next_best_action
        stop_decision = final_assessment.stop_decision
        explanation = final_assessment.explanation

        self.lifecycle_manager.record_recommendation(
            case=case_record,
            action=nba.action.value,
            approval_required=nba.approval_required,
            approval_route=nba.approval_route.value if hasattr(nba.approval_route, "value") else str(nba.approval_route),
            rationale=nba.rationale,
            policy_references=nba.policy_references
        )

        # 7. Evaluate SAR / FinCEN Regulatory Compliance
        sar_record = self.sar_evaluator.evaluate(final_ctx, final_assessment)
        case_record.sar_data = sar_record

        # 8. Determine Final Outcome and State Resolution
        case_record.summary = "; ".join(explanation.why_suspicious) or "; ".join(explanation.why_action)

        if case_record.status == CaseLifecycleStatus.ACTION_PENDING_APPROVAL or (case_record.approval_required and case_record.execution_status != ActionExecutionStatus.EXECUTED):
            case_record.final_outcome = "ACTION_PENDING_APPROVAL"
            # Remains in ACTION_PENDING_APPROVAL pending human authorization boundary
        elif case_record.status == CaseLifecycleStatus.AWAITING_EVIDENCE:
            case_record.final_outcome = "AWAITING_CUSTOMER_EVIDENCE"
            # Remains in AWAITING_EVIDENCE
        elif final_assessment.fraud_assessment.value == "likely_fraud":
            case_record.final_outcome = "RESOLVED_FRAUD"
            self.lifecycle_manager.transition_state(
                case_record, CaseLifecycleStatus.RESOLVED, reason="Case resolved as RESOLVED_FRAUD"
            )
        elif final_assessment.fraud_assessment.value == "likely_benign":
            case_record.final_outcome = "RESOLVED_BENIGN"
            self.lifecycle_manager.transition_state(
                case_record, CaseLifecycleStatus.RESOLVED, reason="Case resolved as RESOLVED_BENIGN"
            )
        else:
            case_record.final_outcome = "ESCALATED"
            self.lifecycle_manager.transition_state(
                case_record, CaseLifecycleStatus.ESCALATED, reason="Case escalated for analyst review"
            )

        # 9. Link Related Historical Entities & Case IDs
        hist_cases = []
        if getattr(final_ctx, "historical_cases_confirmed_fraud", None):
            hist_cases.extend(final_ctx.historical_cases_confirmed_fraud)
        if getattr(final_ctx, "historical_cases_cleared", None):
            hist_cases.extend(final_ctx.historical_cases_cleared)

        case_record.related_historical_case_ids = [c.case_id for c in hist_cases]
        case_record.related_entities = {
            "customer_id": [trigger.customer_id] if trigger.customer_id else [],
            "card_id": [trigger.card_id] if trigger.card_id else [],
            "transaction_id": [str(trigger.transaction_id)] if trigger.transaction_id else []
        }

        # 10. Perform Idempotent Graph Writeback & Final Case Memory Update
        writeback_res = self.writeback_engine.write_case(case_record)
        case_record.written_to_graph = True
        case_record.graph_case_id = case_record.case_id

        self.case_store.update_case(case_record.case_id, case_record.model_dump())

        return InvestigationResult(
            case_id=trigger.case_id,
            trigger=trigger,
            investigation_steps=investigation_steps,
            evidence_collected=state.collected_evidence,
            assessment_history=assessment_history,
            final_assessment=final_assessment,
            evidence_requests=final_assessment.evidence_requests,
            policy_decisions=final_assessment.policy_decisions,
            next_best_action=nba,
            approval_required=nba.approval_required,
            approval_route=nba.approval_route,
            execution_status="recommended",
            stop_decision=stop_decision,
            explanation=explanation,
            total_tool_calls=len(state.tools_called),
            total_steps=state.step_count,
            persisted_case_id=case_record.case_id,
            written_to_graph=True,
            sar_record=sar_record
        )

    def _build_context(
        self,
        trigger: InvestigationTrigger,
        state: WorkingInvestigationState
    ) -> InvestigationContext:
        """Synthesizes GraphRAG context strictly from trigger and working state evidence."""
        return self.synthesizer.build_context_from_working_state(
            trigger=trigger,
            state=state
        )

