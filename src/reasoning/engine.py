from typing import List, Dict, Any, Optional
from src.models.context import InvestigationContext
from src.models.reasoning import (
    InvestigationAssessment,
    FraudAssessmentOutcome,
    EvidenceSufficiencyState,
    UncertaintyAssessment,
    UncertaintyLevel,
    EvidenceRequest,
    NextBestAction,
    StopDecision,
    StructuredExplanation
)
from src.reasoning.base import ReasoningEngineInterface
from src.reasoning.evidence_evaluator import DeterministicEvidenceEvaluator
from src.reasoning.uncertainty_evaluator import UncertaintyEvaluator
from src.reasoning.sufficiency_evaluator import EvidenceSufficiencyEvaluator
from src.reasoning.evidence_planner import ControlledEvidencePlanner
from src.reasoning.policy_engine import PolicyDecisionEngine
from src.reasoning.nba_engine import NextBestActionEngine
from src.reasoning.stop_evaluator import StopConditionEvaluator
from src.reasoning.explanation_engine import ExplanationEngine

class DeterministicReasoningEngine(ReasoningEngineInterface):
    """
    Deterministic reference implementation of the ReasoningEngineInterface.
    Evaluates fraud suspicion, epistemic uncertainty, evidence sufficiency,
    policy constraints, Next Best Actions, and human approval boundaries.
    """
    def __init__(
        self,
        evidence_evaluator: Optional[DeterministicEvidenceEvaluator] = None,
        uncertainty_evaluator: Optional[UncertaintyEvaluator] = None,
        sufficiency_evaluator: Optional[EvidenceSufficiencyEvaluator] = None,
        evidence_planner: Optional[ControlledEvidencePlanner] = None,
        policy_engine: Optional[PolicyDecisionEngine] = None,
        nba_engine: Optional[NextBestActionEngine] = None,
        stop_evaluator: Optional[StopConditionEvaluator] = None,
        explanation_engine: Optional[ExplanationEngine] = None
    ):
        self.evidence_evaluator = evidence_evaluator or DeterministicEvidenceEvaluator()
        self.uncertainty_evaluator = uncertainty_evaluator or UncertaintyEvaluator()
        self.sufficiency_evaluator = sufficiency_evaluator or EvidenceSufficiencyEvaluator()
        self.evidence_planner = evidence_planner or ControlledEvidencePlanner()
        self.policy_engine = policy_engine or PolicyDecisionEngine()
        self.nba_engine = nba_engine or NextBestActionEngine(self.policy_engine)
        self.stop_evaluator = stop_evaluator or StopConditionEvaluator()
        self.explanation_engine = explanation_engine or ExplanationEngine()

    def assess(self, ctx: InvestigationContext) -> InvestigationAssessment:
        # 1. Evaluate Evidence Dimensions
        factors, suspicion_score, confidence, patterns = self.evidence_evaluator.evaluate(ctx)

        # 2. Evaluate Epistemic Uncertainty
        uncertainty = self.uncertainty_evaluator.evaluate(ctx, factors)

        # 3. Determine Fraud Assessment Outcome
        if ctx.trigger_type == "customer_confirmed":
            outcome = FraudAssessmentOutcome.LIKELY_BENIGN
        elif ctx.trigger_type == "customer_report":
            outcome = FraudAssessmentOutcome.LIKELY_FRAUD
        elif suspicion_score >= 0.70 and uncertainty.level != UncertaintyLevel.HIGH:
            outcome = FraudAssessmentOutcome.LIKELY_FRAUD
        elif suspicion_score >= 0.35 or uncertainty.level in [UncertaintyLevel.MATERIAL, UncertaintyLevel.HIGH]:
            outcome = FraudAssessmentOutcome.SUSPICIOUS_BUT_UNCERTAIN
        elif suspicion_score < 0.25 and not any("Detected graph pattern" in b and "none" not in b for b in ctx.graph_evidence_summary):
            outcome = FraudAssessmentOutcome.LIKELY_BENIGN
        else:
            outcome = FraudAssessmentOutcome.INSUFFICIENT_EVIDENCE

        # 4. Determine Evidence Sufficiency
        sufficiency = self.sufficiency_evaluator.evaluate(ctx, factors, uncertainty)

        # 5. Plan Controlled Evidence Requests
        evidence_requests = self.evidence_planner.plan_requests(ctx, sufficiency, uncertainty)

        # 6. Determine Next Best Action
        nba = self.nba_engine.determine_next_best_action(
            ctx=ctx,
            assessment=outcome,
            sufficiency=sufficiency,
            uncertainty=uncertainty,
            confidence=confidence
        )

        # 7. Evaluate Policy Decisions
        policy_eval = self.policy_engine.evaluate_policy_compliance(
            action=nba.action,
            ctx=ctx,
            assessment=outcome,
            sufficiency=sufficiency,
            uncertainty=uncertainty
        )

        # 8. Evaluate Stop Condition
        stop_decision = self.stop_evaluator.evaluate_stop(
            ctx=ctx,
            sufficiency=sufficiency,
            uncertainty=uncertainty,
            nba=nba
        )

        # 9. Generate Structured Explanation
        explanation = self.explanation_engine.generate_explanation(
            ctx=ctx,
            assessment=outcome,
            factors=factors,
            sufficiency=sufficiency,
            uncertainty=uncertainty,
            nba=nba,
            stop_dec=stop_decision,
            evidence_requests=evidence_requests
        )

        return InvestigationAssessment(
            case_id=ctx.case_id,
            fraud_assessment=outcome,
            suspected_patterns=patterns,
            confidence=confidence,
            uncertainty=uncertainty,
            evidence_sufficiency=sufficiency,
            supporting_evidence=[f.factor for f in factors if f.impact == "increases_suspicion"],
            contradictory_evidence=[f.factor for f in factors if f.impact == "decreases_suspicion"],
            evidence_gaps=[g.missing_information for g in ctx.evidence_gaps],
            reasoning_factors=factors,
            evidence_requests=evidence_requests,
            policy_decisions=[policy_eval],
            next_best_action=nba,
            stop_decision=stop_decision,
            explanation=explanation,
            requires_human_approval=nba.approval_required
        )

    def plan_evidence(self, ctx: InvestigationContext) -> List[EvidenceRequest]:
        factors, _, _, _ = self.evidence_evaluator.evaluate(ctx)
        uncertainty = self.uncertainty_evaluator.evaluate(ctx, factors)
        sufficiency = self.sufficiency_evaluator.evaluate(ctx, factors, uncertainty)
        return self.evidence_planner.plan_requests(ctx, sufficiency, uncertainty)

    def recommend_action(self, ctx: InvestigationContext) -> NextBestAction:
        assessment = self.assess(ctx)
        return assessment.next_best_action

    def reassess_with_additional_evidence(
        self,
        ctx: InvestigationContext,
        additional_evidence: Dict[str, Any]
    ) -> InvestigationAssessment:
        """
        Re-evaluates an investigation after simulated or real additional evidence is supplied.
        """
        # Create a modified context copy
        ctx_copy = ctx.model_copy(deep=True)

        if "customer_response" in additional_evidence:
            resp = additional_evidence["customer_response"]
            if resp == "denied":
                ctx_copy.trigger_type = "customer_report"
                ctx_copy.trigger_text = "Cardholder responded to 2FA inquiry: Transaction NOT authorized."
            elif resp == "confirmed":
                ctx_copy.trigger_type = "customer_confirmed"
                ctx_copy.trigger_text = "Cardholder responded to 2FA inquiry: Transaction CONFIRMED legitimate."
                # Add strong contradictory evidence
                from src.models.context import ContradictoryEvidenceItem
                ctx_copy.contradictory_evidence.append(
                    ContradictoryEvidenceItem(
                        evidence="Customer confirmed authorization via Out-of-Band SMS response",
                        benign_explanation="Cardholder verified legitimate purchase under Rule R3.",
                        source_id=f"customer_response:{ctx.flagged_txn_id}",
                        weight=1.0
                    )
                )

        return self.assess(ctx_copy)
