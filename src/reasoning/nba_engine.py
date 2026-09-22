from typing import List, Dict, Any, Tuple, Optional
from src.core.constants import PolicyAction, ApprovalRoute
from src.models.context import InvestigationContext
from src.models.reasoning import (
    NextBestAction,
    FraudAssessmentOutcome,
    EvidenceSufficiencyState,
    UncertaintyAssessment,
    UncertaintyLevel
)
from src.reasoning.policy_engine import PolicyDecisionEngine

class NextBestActionEngine:
    """
    Determines the optimal next-best-action (NBA) based on investigation assessment,
    evidence sufficiency, uncertainty level, and bank policy rules R1-R10.
    Strictly preserves the distinction between Recommendation and Execution.
    """
    def __init__(self, policy_engine: Optional[PolicyDecisionEngine] = None):
        self.policy_engine = policy_engine or PolicyDecisionEngine()

    def determine_next_best_action(
        self,
        ctx: InvestigationContext,
        assessment: FraudAssessmentOutcome,
        sufficiency: EvidenceSufficiencyState,
        uncertainty: UncertaintyAssessment,
        confidence: float
    ) -> NextBestAction:
        alternatives: List[str] = []
        policy_refs: List[str] = [p.rule_id for p in ctx.applicable_policies]
        evidence_ids = [s.source_id for s in ctx.source_attributions[:4]]

        # -------------------------------------------------------------
        # 0. Customer Confirmed Trigger (Rule R3: Customer Confirms)
        # -------------------------------------------------------------
        if ctx.trigger_type == "customer_confirmed":
            primary_action = PolicyAction.CLOSE_NO_FRAUD
            rationale = "Customer directly confirmed transaction authorization under Rule R3. Case resolved as non-fraud."
            alternatives = ["ALLOW_TRANSACTION", "MONITOR_CARD"]
            policy_refs.append("R3")

        # -------------------------------------------------------------
        # 1. Customer Report Trigger (Rule R2: Customer Denies)
        # -------------------------------------------------------------
        elif ctx.trigger_type == "customer_report":
            primary_action = PolicyAction.BLOCK_CARD
            rationale = "Customer directly reported unauthorized transaction (Rule R2). Mandates immediate card block and case creation."
            alternatives = ["MONITOR_CARD", "STEP_UP_AUTH", "VERIFY_WITH_CUSTOMER"]
            policy_refs.append("R2")

        # -------------------------------------------------------------
        # 2. Conflicting / Cleared Precedent (Rule R7: Recurring / Travel)
        # -------------------------------------------------------------
        elif sufficiency == EvidenceSufficiencyState.CONFLICTING or (ctx.historical_cases_cleared and assessment == FraudAssessmentOutcome.SUSPICIOUS_BUT_UNCERTAIN):
            primary_action = PolicyAction.VERIFY_WITH_CUSTOMER
            rationale = "Conflicting evidence or prior cleared travel history present (Rule R7). Verify authorization with customer before blocking card."
            alternatives = ["MONITOR_CARD", "ESCALATE_TO_ANALYST", "BLOCK_CARD"]
            policy_refs.append("R7")

        # -------------------------------------------------------------
        # 3. Insufficient Evidence / Weak Signal (Rule R1)
        # -------------------------------------------------------------
        elif sufficiency == EvidenceSufficiencyState.INSUFFICIENT or assessment == FraudAssessmentOutcome.INSUFFICIENT_EVIDENCE:
            primary_action = PolicyAction.STEP_UP_AUTH
            rationale = "Evidence is insufficient to warrant irreversible card blocking (Rule R1). Challenge subsequent transactions with Out-of-Band 2FA."
            alternatives = ["VERIFY_WITH_CUSTOMER", "MONITOR_CARD", "ESCALATE_TO_ANALYST"]
            policy_refs.append("R1")

        # -------------------------------------------------------------
        # 4. Likely Benign Activity (Rule R3 / Baseline Match)
        # -------------------------------------------------------------
        elif assessment == FraudAssessmentOutcome.LIKELY_BENIGN:
            primary_action = PolicyAction.CLOSE_NO_FRAUD
            rationale = "Transaction matches established cardholder baseline with low risk score and no graph anomaly signals."
            alternatives = ["ALLOW_TRANSACTION", "MONITOR_CARD"]
            policy_refs.append("R3")

        # -------------------------------------------------------------
        # 5. Shared Syndicate / Coordinated Attack (Rule R6 / R9)
        # -------------------------------------------------------------
        elif any("shared across" in b for b in ctx.graph_evidence_summary):
            primary_action = PolicyAction.MONITOR_CONNECTED_CARDS
            rationale = "Device fingerprint is shared across multiple cardholder accounts in graph (Rule R6). Place all secondary linked cards under monitoring."
            alternatives = ["BLOCK_CARD", "ESCALATE_TO_ANALYST", "FILE_REPORT"]
            policy_refs.append("R6")

        # -------------------------------------------------------------
        # 6. High Uncertainty with High Exposure (Rule R8)
        # -------------------------------------------------------------
        elif uncertainty.level in [UncertaintyLevel.MATERIAL, UncertaintyLevel.HIGH] and ctx.model_risk_score > 0.50:
            primary_action = PolicyAction.ESCALATE_TO_ANALYST
            rationale = "High uncertainty remains on elevated-risk transaction (Rule R8). Escalate to fraud analyst supervisor for manual review."
            alternatives = ["VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH", "MONITOR_CARD"]
            policy_refs.append("R8")

        # -------------------------------------------------------------
        # 7. Card Testing Sequence (Rule R5)
        # -------------------------------------------------------------
        elif any("card_testing" in p.get("pattern", "") for p in ctx.detected_patterns):
            primary_action = PolicyAction.DECLINE_TRANSACTION
            rationale = "Card testing sequence detected on card (Rule R5). Decline suspicious micro-authorizations and challenge with STEP_UP_AUTH."
            alternatives = ["BLOCK_CARD", "STEP_UP_AUTH"]
            policy_refs.append("R5")

        # -------------------------------------------------------------
        # Default Fallback: Monitor Card
        # -------------------------------------------------------------
        else:
            primary_action = PolicyAction.MONITOR_CARD
            rationale = "Standard proactive monitoring on flagged transaction to observe subsequent cardholder activity."
            alternatives = ["VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH"]

        # Evaluate policy compliance and approval tier
        pol_eval = self.policy_engine.evaluate_policy_compliance(
            action=primary_action,
            ctx=ctx,
            assessment=assessment,
            sufficiency=sufficiency,
            uncertainty=uncertainty
        )

        evaluated_rules = set(pol_eval.get("rules_evaluated", []))
        is_permitted = pol_eval.get("permitted", pol_eval.get("is_permitted", False))

        destructive_actions = {
            PolicyAction.BLOCK_CARD,
            PolicyAction.BLOCK_ALL_CARDS,
            PolicyAction.DECLINE_TRANSACTION,
            PolicyAction.FILE_REPORT
        }

        # Hard Invariant Enforcement:
        # 1. Destructive actions MUST be permitted by policy.
        # 2. Destructive actions MUST have policy_references as a non-empty subset of evaluated_rules.
        # If invariant fails, reject destructive action and fallback safely.
        if primary_action in destructive_actions:
            matching_refs = [r for r in policy_refs if r in evaluated_rules]
            if not is_permitted or not matching_refs:
                # Rejection & Safe Fallback
                violations_str = "; ".join(pol_eval.get("violations", ["Policy invariant check failed"]))
                primary_action = PolicyAction.STEP_UP_AUTH if ctx.trigger_type != "customer_report" else PolicyAction.VERIFY_WITH_CUSTOMER
                rationale = f"Policy conflict/violation rejected destructive action: {violations_str}. Fallback to non-destructive verification."
                policy_refs = ["R1"]
                # Re-evaluate policy for fallback action
                pol_eval = self.policy_engine.evaluate_policy_compliance(
                    action=primary_action,
                    ctx=ctx,
                    assessment=assessment,
                    sufficiency=sufficiency,
                    uncertainty=uncertainty
                )
                evaluated_rules = set(pol_eval.get("rules_evaluated", []))

        # Ensure policy_references are valid evaluated rules
        final_policy_refs = [r for r in policy_refs if r in evaluated_rules]
        if not final_policy_refs and evaluated_rules:
            final_policy_refs = list(evaluated_rules)[:2]

        approval_route = ApprovalRoute(pol_eval["approval_route"])
        approval_req = pol_eval["approval_required"]

        return NextBestAction(
            action=primary_action,
            rationale=rationale,
            supporting_evidence_ids=evidence_ids,
            policy_references=final_policy_refs,
            confidence=confidence,
            approval_required=approval_req,
            approval_route=approval_route,
            execution_status="recommended",  # Never auto-executed without explicit authorization flow
            alternatives_considered=alternatives
        )
