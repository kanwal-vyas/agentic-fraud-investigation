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
from src.mcp.server import TigerGraphMCPServer
from src.rag.synthesis import InvestigationContextSynthesizer
from src.reasoning.engine import DeterministicReasoningEngine
from src.agent.planner import AgentPlanner
from src.agent.provider import MockLLMProvider

class AgenticFraudInvestigator:
    """
    Autonomous Fraud Investigation Agent orchestrating TigerGraph MCP tool execution,
    GraphRAG contextual retrieval, working memory, reasoning checkpoints, deterministic
    uncertainty modeling, policy enforcement (Rules R1-R10), and Next-Best-Action recommendations.
    """
    def __init__(
        self,
        mcp_server: Optional[TigerGraphMCPServer] = None,
        synthesizer: Optional[InvestigationContextSynthesizer] = None,
        reasoning_engine: Optional[DeterministicReasoningEngine] = None,
        planner: Optional[AgentPlanner] = None,
        max_steps: int = 8
    ):
        self.mcp_server = mcp_server or TigerGraphMCPServer()
        self.synthesizer = synthesizer or InvestigationContextSynthesizer()
        self.reasoning_engine = reasoning_engine or DeterministicReasoningEngine()
        self.planner = planner or AgentPlanner(MockLLMProvider())
        self.max_steps = max_steps

    def investigate(
        self,
        trigger: InvestigationTrigger,
        simulated_evidence_response: Optional[Dict[str, Any]] = None
    ) -> InvestigationResult:
        """
        Executes a complete, bounded investigation loop for an incoming fraud case trigger.
        """
        # 1. Initialize Working Investigation State
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
        if simulated_evidence_response and (
            assessment.evidence_requests or assessment.fraud_assessment.value in ["suspicious_but_uncertain", "likely_fraud"]
        ):
            reassessed = self.reasoning_engine.reassess_with_additional_evidence(
                final_ctx,
                simulated_evidence_response
            )
            assessment_history.append(reassessed)
            final_assessment = reassessed

        # 5. Extract Final Decisions & Ensure Recommendation Separation
        nba = final_assessment.next_best_action
        stop_decision = final_assessment.stop_decision
        explanation = final_assessment.explanation

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
            total_steps=state.step_count
        )

    def _build_context(
        self,
        trigger: InvestigationTrigger,
        state: WorkingInvestigationState
    ) -> InvestigationContext:
        """Synthesizes GraphRAG context from trigger and working state."""
        return self.synthesizer.build_context_for_case(
            case_id=trigger.case_id,
            opened_at=trigger.opened_at or "2016-12-05 01:55:28",
            trigger_type=trigger.trigger_type.value,
            trigger_text=trigger.trigger_details,
            flagged_txn_id=trigger.transaction_id,
            card_id=trigger.card_id,
            customer_id=trigger.customer_id,
            risk_score=trigger.model_risk_score
        )
