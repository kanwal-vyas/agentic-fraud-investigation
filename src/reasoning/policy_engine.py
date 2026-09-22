from typing import Dict, Any, List, Optional
from src.core.constants import PolicyAction, ApprovalRoute, ACTION_DEFAULT_ROUTES
from src.models.context import InvestigationContext
from src.models.reasoning import (
    FraudAssessmentOutcome,
    EvidenceSufficiencyState,
    UncertaintyAssessment
)

class PolicyDecisionEngine:
    """
    Evaluates policy constraints, approval tiers, mandatory prerequisites,
    and proportional safeguards under official bank rules R1 through R10.
    """
    def evaluate_policy_compliance(
        self,
        action: PolicyAction,
        ctx: InvestigationContext,
        assessment: FraudAssessmentOutcome,
        sufficiency: EvidenceSufficiencyState,
        uncertainty: UncertaintyAssessment
    ) -> Dict[str, Any]:
        """
        Determines whether an action is permitted, what approval route is required,
        and what mandatory policy rules apply.
        """
        amount_usd = 0.0
        # Determine exposure amount from context
        for bullet in ctx.graph_evidence_summary:
            if f"Transaction {ctx.flagged_txn_id}" in bullet and "$" in bullet:
                try:
                    part = bullet.split("$")[1].split(",")[0].split(" ")[0]
                    amount_usd = float(part)
                except Exception:
                    pass

        applicable_rule_ids = [p.rule_id for p in ctx.applicable_policies]
        violations = []
        prerequisites = []

        # -------------------------------------------------------------
        # Rule R1: Verify before you block on weak single signal
        # -------------------------------------------------------------
        if action in [PolicyAction.BLOCK_CARD, PolicyAction.BLOCK_ALL_CARDS]:
            if ctx.trigger_type != "customer_report" and sufficiency != EvidenceSufficiencyState.SUFFICIENT:
                if ctx.model_risk_score < 0.70:
                    violations.append("Rule R1 Violation: Attempting to block card on weak uncorroborated score without customer verification.")
                    prerequisites.append("Mandatory Customer Verification via Out-of-Band SMS / STEP_UP_AUTH (Rule R1).")

        # -------------------------------------------------------------
        # Rule R10: Proportional Blocking Safeguard
        # -------------------------------------------------------------
        if action == PolicyAction.BLOCK_ALL_CARDS:
            has_multi_card_fraud = any(
                p.get("pattern") in ["account_takeover", "undocumented"] and p.get("heuristic_confidence", 0) > 0.8
                for p in ctx.detected_patterns
            )
            if not has_multi_card_fraud:
                violations.append("Rule R10 Violation: BLOCK_ALL_CARDS is prohibited unless >=2 cards show confirmed fraud or credential compromise.")

        # -------------------------------------------------------------
        # Determine Approval Level & Routing
        # -------------------------------------------------------------
        default_route = ACTION_DEFAULT_ROUTES.get(action, ApprovalRoute.AUTO)
        approval_required = default_route != ApprovalRoute.AUTO
        route = default_route

        # Rule R8: High Exposure Escalation (> $500 with uncertainty -> L1/L2)
        if amount_usd > 500.0 and uncertainty.level.value in ["material", "high"]:
            approval_required = True
            route = ApprovalRoute.L1 if amount_usd <= 2500.0 else ApprovalRoute.L2

        # SAR Reporting Thresholds (FinCEN / Rule R2 / Rule R6)
        if action == PolicyAction.FILE_REPORT:
            approval_required = True
            route = ApprovalRoute.L2

        # Large Card Blocks (> $2,500 require L2 Fraud Manager)
        if action == PolicyAction.BLOCK_CARD and amount_usd > 2500.0:
            route = ApprovalRoute.L2

        is_permitted = len(violations) == 0

        return {
            "action": action.value,
            "is_permitted": is_permitted,
            "approval_required": approval_required,
            "approval_route": route.value,
            "violations": violations,
            "prerequisites": prerequisites,
            "governing_rules": applicable_rule_ids
        }
