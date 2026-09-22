from typing import List
from src.models.context import InvestigationContext
from src.models.reasoning import (
    StructuredExplanation,
    FraudAssessmentOutcome,
    ReasoningFactor,
    EvidenceSufficiencyState,
    UncertaintyAssessment,
    NextBestAction,
    StopDecision,
    EvidenceRequest
)

class ExplanationEngine:
    """
    Constructs auditable, 5-part structured natural-language explanations
    grounded strictly in graph evidence, policy rules, and uncertainty factors.
    """
    def generate_explanation(
        self,
        ctx: InvestigationContext,
        assessment: FraudAssessmentOutcome,
        factors: List[ReasoningFactor],
        sufficiency: EvidenceSufficiencyState,
        uncertainty: UncertaintyAssessment,
        nba: NextBestAction,
        stop_dec: StopDecision,
        evidence_requests: List[EvidenceRequest]
    ) -> StructuredExplanation:
        # 1. Why Suspicious
        why_suspicious = [
            f.factor for f in factors if f.impact == "increases_suspicion"
        ]
        if not why_suspicious:
            why_suspicious.append("No material suspicious anomalies detected in graph or transaction history.")

        # 2. Why Not Certain
        why_not_certain = list(uncertainty.reasons)
        for ce in ctx.contradictory_evidence:
            why_not_certain.append(f"Benign signal: {ce.evidence} ({ce.benign_explanation})")
        if not why_not_certain:
            why_not_certain.append("Evidence is highly conclusive with no observed contradictory indicators.")

        # 3. Why Request More Evidence
        why_request_more_evidence = []
        if evidence_requests:
            for req in evidence_requests[:2]:
                why_request_more_evidence.append(
                    f"Request '{req.request_type}': {req.reason} (Expected Information Gain: {req.expected_information_gain:.2f}) -> {req.rationale}"
                )
        else:
            why_request_more_evidence.append("No additional evidence requests required; current evidence is adequate for policy routing.")

        # 4. Why Action
        why_action = [
            f"Recommended NBA '{nba.action.value}': {nba.rationale}",
            f"Governed by Policy Rules: {', '.join(nba.policy_references) if nba.policy_references else 'Standard Fraud Triage'}",
            f"Approval Tier: Level {nba.approval_route.value} (Human Approval Required: {nba.approval_required})"
        ]

        # 5. Why Stop
        why_stop = [
            f"Investigation Stop Status: {'CONCLUDED' if stop_dec.should_stop else 'AWAITING ADDITIONAL EVIDENCE'}",
            f"Rationale: {stop_dec.reason}",
            f"Next Step: {stop_dec.next_step}"
        ]

        return StructuredExplanation(
            why_suspicious=why_suspicious,
            why_not_certain=why_not_certain,
            why_request_more_evidence=why_request_more_evidence,
            why_action=why_action,
            why_stop=why_stop
        )
