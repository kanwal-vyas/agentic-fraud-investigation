from typing import List
from src.models.context import InvestigationContext
from src.models.reasoning import (
    EvidenceSufficiencyState,
    UncertaintyAssessment,
    UncertaintyLevel,
    ReasoningFactor
)

class EvidenceSufficiencyEvaluator:
    """
    Determines whether evidence is sufficient to execute the next policy action,
    separating evidence completeness from fraud suspicion.
    """
    def evaluate(
        self,
        ctx: InvestigationContext,
        factors: List[ReasoningFactor],
        uncertainty: UncertaintyAssessment
    ) -> EvidenceSufficiencyState:
        # 1. Check for conflicting evidence
        if uncertainty.conflicting_factors and uncertainty.level in [UncertaintyLevel.MATERIAL, UncertaintyLevel.HIGH]:
            # If customer reported fraud explicitly, customer denial overrides minor baseline matches
            if ctx.trigger_type == "customer_report":
                return EvidenceSufficiencyState.SUFFICIENT
            return EvidenceSufficiencyState.CONFLICTING

        # 2. Check customer report: direct customer report is authoritative under Rule R2
        if ctx.trigger_type == "customer_report":
            return EvidenceSufficiencyState.SUFFICIENT

        # 3. Check for high-urgency unresolved evidence gaps
        high_urgency_gaps = [g for g in ctx.evidence_gaps if g.urgency == "high"]
        
        # If policy Rule R1 applies (weak signal < 0.70) and customer verification is unresolved
        if any(p.rule_id == "R1" for p in ctx.applicable_policies) and ctx.trigger_type != "customer_report":
            if high_urgency_gaps:
                return EvidenceSufficiencyState.INSUFFICIENT

        # 4. Check if we have strong corroborating graph evidence (e.g. shared syndicate or testing)
        has_strong_graph_signal = any(
            f.dimension in ["behavioral", "network"] and f.weight >= 2.5
            for f in factors
        )

        if has_strong_graph_signal and uncertainty.level in [UncertaintyLevel.LOW, UncertaintyLevel.MODERATE]:
            return EvidenceSufficiencyState.SUFFICIENT

        # Default check based on uncertainty level
        if uncertainty.level == UncertaintyLevel.HIGH:
            return EvidenceSufficiencyState.INSUFFICIENT
        elif uncertainty.level == UncertaintyLevel.MATERIAL:
            return EvidenceSufficiencyState.CONFLICTING if uncertainty.conflicting_factors else EvidenceSufficiencyState.INSUFFICIENT

        return EvidenceSufficiencyState.SUFFICIENT
