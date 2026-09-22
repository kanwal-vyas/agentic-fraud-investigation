from typing import List
from src.models.context import InvestigationContext
from src.models.reasoning import (
    StopDecision,
    EvidenceSufficiencyState,
    UncertaintyAssessment,
    UncertaintyLevel,
    NextBestAction
)

class StopConditionEvaluator:
    """
    Evaluates whether the fraud investigation should conclude or continue
    gathering additional evidence under official challenge stop criteria.
    """
    def evaluate_stop(
        self,
        ctx: InvestigationContext,
        sufficiency: EvidenceSufficiencyState,
        uncertainty: UncertaintyAssessment,
        nba: NextBestAction
    ) -> StopDecision:
        unresolved_gaps = [g.missing_information for g in ctx.evidence_gaps]

        # 1. Stop Condition: Customer report confirmed
        if ctx.trigger_type == "customer_report":
            return StopDecision(
                should_stop=True,
                reason="Direct customer report provides conclusive authorization denial (Rule R2). Mandatory actions recommended.",
                remaining_uncertainty=UncertaintyLevel.LOW,
                unresolved_gaps=[],
                next_step=f"Submit {nba.action.value} recommendation for L1 approval and proceed with card reissue."
            )

        # 2. Stop Condition: Clear benign resolution
        if nba.action.value in ["CLOSE_NO_FRAUD", "ALLOW_TRANSACTION"]:
            return StopDecision(
                should_stop=True,
                reason="Evidence demonstrates transaction is consistent with established cardholder baseline with zero fraud anomalies.",
                remaining_uncertainty=UncertaintyLevel.LOW,
                unresolved_gaps=[],
                next_step="Close case as non-fraud with zero financial exposure."
            )

        # 3. Stop Condition: Human Escalation Required
        if nba.action.value == "ESCALATE_TO_ANALYST":
            return StopDecision(
                should_stop=True,
                reason="Investigative uncertainty requires human expert adjudication under Rule R8.",
                remaining_uncertainty=uncertainty.level,
                unresolved_gaps=unresolved_gaps,
                next_step=f"Transfer case to Level {nba.approval_route.value} fraud analyst queue for forensic review."
            )

        # 4. Continuation Condition: Evidence is Insufficient or Conflicting (Customer inquiry pending)
        if sufficiency in [EvidenceSufficiencyState.INSUFFICIENT, EvidenceSufficiencyState.CONFLICTING]:
            return StopDecision(
                should_stop=False,
                reason=f"Evidence is {sufficiency.value}. Awaiting response to Out-of-Band verification request before finalizing verdict.",
                remaining_uncertainty=uncertainty.level,
                unresolved_gaps=unresolved_gaps,
                next_step="Execute planned customer verification request and re-assess upon response."
            )

        # 5. Default Stop Condition: Action recommended and policy requirements satisfied
        return StopDecision(
            should_stop=True,
            reason="Sufficient graph and historical evidence gathered to support the recommended policy action.",
            remaining_uncertainty=uncertainty.level,
            unresolved_gaps=unresolved_gaps,
            next_step=f"Await human authorization for {nba.action.value}."
        )
