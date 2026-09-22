from typing import List
from src.models.context import InvestigationContext
from src.models.reasoning import (
    EvidenceRequest,
    EvidenceSufficiencyState,
    UncertaintyAssessment,
    UncertaintyLevel
)

class ControlledEvidencePlanner:
    """
    Plans and prioritizes controlled, policy-grounded requests for additional evidence
    to resolve specific evidence gaps and reduce investigative uncertainty.
    """
    def plan_requests(
        self,
        ctx: InvestigationContext,
        sufficiency: EvidenceSufficiencyState,
        uncertainty: UncertaintyAssessment
    ) -> List[EvidenceRequest]:
        requests: List[EvidenceRequest] = []

        # 1. Customer Validation Request (Rule R1 / R7)
        if ctx.trigger_type != "customer_report":
            requests.append(
                EvidenceRequest(
                    request_id=f"req_cust_val_{ctx.flagged_txn_id}",
                    request_type="customer_validation",
                    reason="Customer authorization status is unknown; required before taking irreversible card-blocking action.",
                    evidence_gap_addressed="Cardholder authorization confirmation",
                    expected_information_gain=0.95,
                    rationale="Direct customer confirmation or denial deterministically resolves whether transaction is fraud (Rule R2) or authorized (Rule R3).",
                    policy_reference="Rule R1 (Weak Signal Triage & Verification) & Rule R7",
                    approval_required=False,
                    status="planned"
                )
            )

        # 2. Secondary Card & Device Syndicate Check (Rule R6)
        has_shared_device = any("shared across" in b for b in ctx.graph_evidence_summary)
        if has_shared_device:
            requests.append(
                EvidenceRequest(
                    request_id=f"req_sec_card_{ctx.card_id}",
                    request_type="secondary_card_check",
                    reason="Device profile is shared across multiple cardholder accounts in graph.",
                    evidence_gap_addressed="Secondary card activity confirmation across linked customer accounts",
                    expected_information_gain=0.85,
                    rationale="Evaluating activity and velocity across connected secondary cards determines the blast radius of syndicate fraud (Rule R6).",
                    policy_reference="Rule R6 (Shared Device / Syndicate Ring)",
                    approval_required=False,
                    status="planned"
                )
            )

        # 3. Step-Up Authentication Challenge (Rule R5 / NIST SP 800-63B)
        if any("card_testing" in p.get("pattern", "") for p in ctx.detected_patterns):
            requests.append(
                EvidenceRequest(
                    request_id=f"req_stepup_{ctx.card_id}",
                    request_type="step_up_auth",
                    reason="Card testing sequence detected on card.",
                    evidence_gap_addressed="Transaction-level authentication challenge",
                    expected_information_gain=0.80,
                    rationale="Mandating Out-of-Band 2FA challenges automated card-testing scripts without disrupting legitimate cardholders.",
                    policy_reference="Rule R5 (Card Testing Rapid Reaction) & NIST SP 800-63B",
                    approval_required=False,
                    status="planned"
                )
            )

        # 4. Analyst Manual Review Request (Rule R8 / R9)
        if uncertainty.level in [UncertaintyLevel.MATERIAL, UncertaintyLevel.HIGH] and ctx.model_risk_score > 0.50:
            requests.append(
                EvidenceRequest(
                    request_id=f"req_analyst_rev_{ctx.case_id}",
                    request_type="analyst_info",
                    reason="Investigative uncertainty remains material with high exposure or conflicting baseline evidence.",
                    evidence_gap_addressed="Human forensic and supervisor review",
                    expected_information_gain=0.75,
                    rationale="Expert human judgment is required to evaluate conflicting travel vs. syndicate evidence.",
                    policy_reference="Rule R8 (High Exposure Escalation) & Rule R9",
                    approval_required=True,
                    status="planned"
                )
            )

        # Sort by expected information gain descending
        requests.sort(key=lambda r: r.expected_information_gain, reverse=True)
        return requests
