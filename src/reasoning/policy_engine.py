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

        rules_evaluated: List[str] = []
        violations = []
        prerequisites = []
        required_action: Optional[str] = None

        # -------------------------------------------------------------
        # Rule R2: Customer Direct Denial Mandate
        # -------------------------------------------------------------
        if ctx.trigger_type == "customer_report":
            rules_evaluated.append("R2")
            required_action = "BLOCK_CARD"

        # -------------------------------------------------------------
        # Rule R3: Customer Direct Confirmation Mandate
        # -------------------------------------------------------------
        if ctx.trigger_type == "customer_confirmed":
            rules_evaluated.append("R3")
            required_action = "CLOSE_NO_FRAUD"

        # -------------------------------------------------------------
        # Rule R1: Verify before you block on weak single signal
        # -------------------------------------------------------------
        if action in [PolicyAction.BLOCK_CARD, PolicyAction.BLOCK_ALL_CARDS]:
            rules_evaluated.append("R1")
            if ctx.trigger_type != "customer_report" and sufficiency != EvidenceSufficiencyState.SUFFICIENT:
                if ctx.model_risk_score < 0.70:
                    violations.append("Rule R1 Violation: Attempting to block card on weak uncorroborated score without customer verification.")
                    prerequisites.append("Mandatory Customer Verification via Out-of-Band SMS / STEP_UP_AUTH (Rule R1).")
        elif action in [PolicyAction.STEP_UP_AUTH, PolicyAction.VERIFY_WITH_CUSTOMER]:
            rules_evaluated.append("R1")

        # -------------------------------------------------------------
        # Rule R4: Low Risk Score Baseline Alignment
        # -------------------------------------------------------------
        if ctx.model_risk_score < 0.20 and assessment == FraudAssessmentOutcome.LIKELY_BENIGN:
            rules_evaluated.append("R4")

        # -------------------------------------------------------------
        # Rule R5: Card Testing Sequence
        # -------------------------------------------------------------
        if action == PolicyAction.DECLINE_TRANSACTION or any("card_testing" in p.get("pattern", "") for p in ctx.detected_patterns):
            rules_evaluated.append("R5")

        # -------------------------------------------------------------
        # Rule R6: Shared Device Syndicate Scope
        # -------------------------------------------------------------
        if action == PolicyAction.MONITOR_CONNECTED_CARDS or any(p.get("pattern") in ["undocumented", "account_takeover"] for p in ctx.detected_patterns):
            rules_evaluated.append("R6")

        # -------------------------------------------------------------
        # Rule R7: Recurring Cleared Precedent / Travel Verification
        # -------------------------------------------------------------
        if action == PolicyAction.VERIFY_WITH_CUSTOMER and (sufficiency == EvidenceSufficiencyState.CONFLICTING or ctx.historical_cases_cleared):
            rules_evaluated.append("R7")

        # -------------------------------------------------------------
        # Rule R10: Proportional Blocking Safeguard
        # -------------------------------------------------------------
        if action == PolicyAction.BLOCK_ALL_CARDS:
            rules_evaluated.append("R10")
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
            rules_evaluated.append("R8")
            approval_required = True
            route = ApprovalRoute.L1 if amount_usd <= 2500.0 else ApprovalRoute.L2

        # SAR Reporting Thresholds (FinCEN / Rule R2 / Rule R6)
        if action == PolicyAction.FILE_REPORT:
            approval_required = True
            route = ApprovalRoute.L2

        # Large Card Blocks (> $2,500 require L2 Fraud Manager)
        if action == PolicyAction.BLOCK_CARD and amount_usd > 2500.0:
            route = ApprovalRoute.L2

        # Ingest applicable policies from context
        for pol in ctx.applicable_policies:
            if pol.rule_id not in rules_evaluated:
                rules_evaluated.append(pol.rule_id)

        # Deduplicate
        rules_evaluated = list(dict.fromkeys(rules_evaluated))
        is_permitted = len(violations) == 0

        return {
            "action": action.value,
            "permitted": is_permitted,
            "is_permitted": is_permitted,
            "required_action": required_action,
            "approval_required": approval_required,
            "approval_route": route.value,
            "violations": violations,
            "prerequisites": prerequisites,
            "rules_evaluated": rules_evaluated,
            "governing_rules": rules_evaluated
        }
