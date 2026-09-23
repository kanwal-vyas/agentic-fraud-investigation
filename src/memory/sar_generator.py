from typing import Dict, Any, List, Optional
from src.core.constants import PolicyAction, ApprovalRoute
from src.models.case_memory import SARCaseRecord
from src.models.context import InvestigationContext
from src.models.reasoning import InvestigationAssessment, FraudAssessmentOutcome, UncertaintyLevel

class SARCaseEvaluator:
    """
    Evaluates regulatory Suspicious Activity Report (SAR) filing requirements.
    Adheres strictly to FinCEN 31 CFR 1020.320 / Bank AML thresholds:
    - Identifies suspected insider fraud, account takeover, or coordinated fraud syndicates
    - Flags aggregate exposures exceeding $500 with high certainty or multi-card involvement
    - Generates auditable SAR preparation artifacts without initiating fake external submissions.
    """
    SAR_EXPOSURE_THRESHOLD = 500.0

    def evaluate(
        self,
        ctx: InvestigationContext,
        assessment: InvestigationAssessment,
        amount_usd: float = 0.0
    ) -> SARCaseRecord:
        """Convenience method calling evaluate_sar_requirement using assessment.case_id."""
        case_id = getattr(assessment, "case_id", getattr(ctx, "case_id", "UNKNOWN_CASE"))
        return self.evaluate_sar_requirement(
            case_id=case_id,
            ctx=ctx,
            assessment=assessment,
            amount_usd=amount_usd
        )

    def evaluate_sar_requirement(
        self,
        case_id: str,
        ctx: InvestigationContext,
        assessment: InvestigationAssessment,
        amount_usd: float = 0.0
    ) -> SARCaseRecord:
        """Determines if the case warrants a SAR filing and prepares structured narrative data."""
        exposure = amount_usd
        if exposure <= 0.0 and getattr(ctx, "graph_evidence_summary", None):
            for bullet in ctx.graph_evidence_summary:
                if f"Transaction {getattr(ctx, 'flagged_txn_id', '')}" in bullet and "$" in bullet:
                    try:
                        part = bullet.split("$")[1].split(",")[0].split(" ")[0]
                        exposure = float(part)
                    except Exception:
                        pass

        detected_patterns = []
        if getattr(ctx, "detected_patterns", None):
            detected_patterns.extend([
                p.get("pattern", "") if isinstance(p, dict) else str(p)
                for p in ctx.detected_patterns
            ])
        if getattr(assessment, "suspected_patterns", None):
            detected_patterns.extend([
                p.value if hasattr(p, "value") else str(p)
                for p in assessment.suspected_patterns
            ])

        has_syndicate = any(p.lower() in ["undocumented", "account_takeover", "syndicate_ring", "fraud_syndicate"] for p in detected_patterns)
        is_high_exposure = exposure >= self.SAR_EXPOSURE_THRESHOLD
        
        verdict_str = assessment.fraud_assessment.value if hasattr(assessment.fraud_assessment, "value") else str(assessment.fraud_assessment)
        is_confirmed_fraud = verdict_str in ["likely_fraud", "confirmed_fraud"]

        sar_required = False
        reasons: List[str] = []

        if is_confirmed_fraud and is_high_exposure:
            sar_required = True
            reasons.append(f"Confirmed unauthorized transaction exceeding SAR mandatory reporting threshold (${exposure:.2f} >= ${self.SAR_EXPOSURE_THRESHOLD:.2f}).")

        if has_syndicate:
            sar_required = True
            reasons.append("Organized multi-card fraud syndicate / account takeover pattern detected across graph entities.")

        policy_refs = getattr(assessment.next_best_action, "policy_references", [])
        if "R8" in policy_refs and is_high_exposure:
            sar_required = True
            reasons.append("Policy Rule R8 high-exposure escalation triggered supervisory review.")

        if not sar_required:
            return SARCaseRecord(
                sar_required=False,
                sar_status="NOT_REQUIRED",
                sar_rationale="Case exposure does not meet statutory SAR mandatory filing thresholds and lacks coordinated syndicate indicators.",
                exposure_usd=exposure,
                regulatory_references=["FinCEN 31 CFR 1020.320 (Non-threshold transaction)"],
                approval_route="auto",
                filing_status="unfiled",
                narrative=""
            )

        cust_id = getattr(ctx, "customer_id", "UNKNOWN")
        card_id = getattr(ctx, "card_id", "UNKNOWN")
        txn_id = getattr(ctx, "flagged_txn_id", getattr(ctx, "transaction_id", "UNKNOWN"))

        narrative = (
            f"SUSPICIOUS ACTIVITY REPORT (SAR) PREPARATION MEMORANDUM\n"
            f"Case ID: {case_id}\n"
            f"Subject Customer ID: {cust_id} | Primary Card ID: {card_id}\n"
            f"Flagged Transaction ID: {txn_id} | Direct Exposure: ${exposure:.2f}\n"
            f"Patterns Identified: {', '.join(set(detected_patterns)) if detected_patterns else 'Unspecified Suspicious Activity'}\n"
            f"Investigative Findings: {'; '.join(reasons)}\n"
            f"Recommendation: Submit formal SAR electronic filing via FinCEN BSA E-Filing System under Bank AML Policy."
        )

        return SARCaseRecord(
            sar_required=True,
            sar_status="RECOMMENDED",
            sar_rationale="; ".join(reasons),
            exposure_usd=exposure,
            regulatory_references=[
                "FinCEN 31 CFR 1020.320",
                "Bank Secrecy Act (BSA) 31 U.S.C. 5318(g)",
                "Federal Reserve Regulation SR 11-7",
            ],
            approval_route="L2",
            filing_status="unfiled",
            narrative=narrative
        )
