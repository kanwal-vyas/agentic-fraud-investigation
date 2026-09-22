from typing import List
from src.models.context import InvestigationContext
from src.models.reasoning import UncertaintyAssessment, UncertaintyLevel, ReasoningFactor
from src.core.validation import is_valid_entity_id

class UncertaintyEvaluator:
    """
    Evaluates epistemic and aleatoric uncertainty in the investigation.
    Explicitly separates uncertainty from fraud confidence.
    """
    def evaluate(self, ctx: InvestigationContext, factors: List[ReasoningFactor]) -> UncertaintyAssessment:
        reasons: List[str] = []
        conflicts: List[str] = []

        # 1. Missing Customer Authorization on Suspicious Activity
        if ctx.trigger_type not in ["customer_report", "customer_confirmed"] and (
            ctx.model_risk_score >= 0.30 or any(f.impact == "increases_suspicion" for f in factors)
        ):
            reasons.append("Customer authorization has not been directly confirmed or denied (Rule R1).")

        # 2. Conflicting Evidence Signals
        has_suspicious = any(f.impact == "increases_suspicion" for f in factors)
        has_benign = any(f.impact == "decreases_suspicion" for f in factors)
        if has_suspicious and has_benign:
            reasons.append("Conflicting evidence observed: graph anomaly signals conflict with established baseline indicators.")
            for ce in ctx.contradictory_evidence:
                conflicts.append(f"{ce.evidence} -> {ce.benign_explanation}")

        # 3. Cleared Historical Precedent
        if ctx.historical_cases_cleared:
            reasons.append(f"Customer has {len(ctx.historical_cases_cleared)} previously cleared investigation(s) in bank history (potential recurring false positive).")

        # 4. Weak / Single Trigger
        if ctx.trigger_type == "risk_score" and 0.30 <= ctx.model_risk_score < 0.70:
            reasons.append(f"Model risk score ({ctx.model_risk_score:.2f}) is a weak single signal without definitive corroboration.")

        # 5. Device Ambiguity
        if not is_valid_entity_id(ctx.profile_id, "DeviceProfile"):
            reasons.append("Device hardware fingerprint is unavailable/missing, limiting device-level attribution.")

        # Determine Uncertainty Level
        if len(reasons) >= 3 or len(conflicts) >= 2:
            level = UncertaintyLevel.HIGH
        elif len(reasons) == 2 or len(conflicts) == 1:
            level = UncertaintyLevel.MATERIAL
        elif len(reasons) == 1:
            level = UncertaintyLevel.MODERATE
        else:
            level = UncertaintyLevel.LOW

        # If customer explicitly filed a report or confirmed transaction, and no strong conflicts exist, uncertainty is reduced
        if ctx.trigger_type in ["customer_report", "customer_confirmed"] and not conflicts:
            level = UncertaintyLevel.LOW

        return UncertaintyAssessment(
            level=level,
            reasons=reasons,
            conflicting_factors=conflicts
        )
