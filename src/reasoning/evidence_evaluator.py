from typing import List, Dict, Any, Tuple
from src.models.context import InvestigationContext
from src.models.reasoning import ReasoningFactor

class DeterministicEvidenceEvaluator:
    """
    Evaluates investigation context across 6 deterministic dimensions:
    1. Direct Transaction Evidence
    2. Behavioral Evidence
    3. Network & Syndicate Evidence
    4. Historical Precedent Evidence
    5. Bank Policy Directives
    6. Contradictory / Benign Explanations
    """
    def evaluate(self, ctx: InvestigationContext) -> Tuple[List[ReasoningFactor], float, float, List[str]]:
        factors: List[ReasoningFactor] = []
        suspicion_points = 0.0
        max_possible_points = 0.0
        confidence_points = 0.0
        suspected_patterns: List[str] = []

        # -------------------------------------------------------------
        # A. Direct Transaction Evidence
        # -------------------------------------------------------------
        max_possible_points += 15.0
        if ctx.trigger_type == "customer_report":
            suspicion_points += 15.0
            confidence_points += 35.0
            factors.append(
                ReasoningFactor(
                    dimension="transaction",
                    factor=f"Direct customer report: {ctx.trigger_text}",
                    impact="increases_suspicion",
                    weight=3.0,
                    source_id=f"case_trigger:{ctx.case_id}"
                )
            )
        elif ctx.trigger_type == "customer_confirmed":
            suspicion_points = 0.0
            confidence_points += 35.0
            factors.append(
                ReasoningFactor(
                    dimension="transaction",
                    factor=f"Customer confirmed authorized purchase: {ctx.trigger_text}",
                    impact="decreases_suspicion",
                    weight=5.0,
                    source_id=f"customer_response:{ctx.flagged_txn_id}"
                )
            )
        elif ctx.trigger_type == "analyst_request":
            suspicion_points += 6.0
            confidence_points += 8.0
            factors.append(
                ReasoningFactor(
                    dimension="transaction",
                    factor=f"Analyst manual inquiry: {ctx.trigger_text}",
                    impact="increases_suspicion",
                    weight=1.5,
                    source_id=f"case_trigger:{ctx.case_id}"
                )
            )
        elif ctx.trigger_type == "risk_score":
            score = ctx.model_risk_score
            if score >= 0.80:
                suspicion_points += 10.0
                confidence_points += 8.0
                factors.append(
                    ReasoningFactor(
                        dimension="transaction",
                        factor=f"Elevated model risk score ({score:.2f}) triggered triage alert",
                        impact="increases_suspicion",
                        weight=2.0,
                        source_id=f"model_score:{ctx.flagged_txn_id}"
                    )
                )
            elif score < 0.40:
                suspicion_points += 2.0
                factors.append(
                    ReasoningFactor(
                        dimension="transaction",
                        factor=f"Low model risk score ({score:.2f}) suggests potential false positive",
                        impact="decreases_suspicion",
                        weight=1.5,
                        source_id=f"model_score:{ctx.flagged_txn_id}"
                    )
                )

        # -------------------------------------------------------------
        # B. Behavioral & Velocity Evidence
        # -------------------------------------------------------------
        max_possible_points += 20.0
        for pattern_info in ctx.detected_patterns:
            pat = pattern_info.get("pattern", "none")
            conf = pattern_info.get("heuristic_confidence", 0.0)
            if pat != "none" and conf > 0.5:
                suspected_patterns.append(pat)
                suspicion_points += 8.0 * conf
                confidence_points += 6.0 * conf
                factors.append(
                    ReasoningFactor(
                        dimension="behavioral",
                        factor=f"Detected pattern '{pat}' (heuristic confidence: {conf:.2f}): {pattern_info.get('rationale', '')}",
                        impact="increases_suspicion",
                        weight=2.5,
                        source_id=f"graph:pattern:{pat}"
                    )
                )

        # -------------------------------------------------------------
        # C. Network & Syndicate Evidence
        # -------------------------------------------------------------
        max_possible_points += 20.0
        has_shared_device = any("shared across" in b for b in ctx.graph_evidence_summary)
        has_connected_cards = any("secondary connected cards" in b for b in ctx.graph_evidence_summary)
        
        if has_shared_device:
            suspicion_points += 15.0
            confidence_points += 12.0
            factors.append(
                ReasoningFactor(
                    dimension="network",
                    factor="Online device profile is shared across multiple distinct cardholders, indicating organized syndicate ring (Rule R6)",
                    impact="increases_suspicion",
                    weight=3.0,
                    source_id="graph:device_sharing"
                )
            )

        if has_connected_cards:
            suspicion_points += 5.0
            factors.append(
                ReasoningFactor(
                    dimension="network",
                    factor="Customer/card has connected secondary card entities requiring monitoring",
                    impact="increases_suspicion",
                    weight=1.5,
                    source_id="graph:connected_cards"
                )
            )

        # -------------------------------------------------------------
        # D. Historical Precedent Evidence
        # -------------------------------------------------------------
        max_possible_points += 15.0
        if ctx.historical_cases_confirmed_fraud:
            top_hc = ctx.historical_cases_confirmed_fraud[0]
            suspicion_points += 10.0
            confidence_points += 10.0
            factors.append(
                ReasoningFactor(
                    dimension="historical",
                    factor=f"Customer/card has prior confirmed fraud history ({top_hc.case_id}: {top_hc.pattern}, ${top_hc.exposure_usd:.2f})",
                    impact="increases_suspicion",
                    weight=2.0,
                    source_id=f"closed_case:{top_hc.case_id}"
                )
            )

        # -------------------------------------------------------------
        # E. Policy Evidence
        # -------------------------------------------------------------
        max_possible_points += 10.0
        for pol in ctx.applicable_policies:
            factors.append(
                ReasoningFactor(
                    dimension="policy",
                    factor=f"Policy {pol.rule_id} ({pol.name}) applies: {pol.applicable_condition}",
                    impact="neutral",
                    weight=1.0,
                    source_id=f"policy:{pol.rule_id}"
                )
            )

        # -------------------------------------------------------------
        # F. Contradictory & Benign Evidence
        # -------------------------------------------------------------
        for ce in ctx.contradictory_evidence:
            suspicion_points = max(0.0, suspicion_points - (5.0 * ce.weight))
            factors.append(
                ReasoningFactor(
                    dimension="contradictory",
                    factor=f"Benign indicator: {ce.evidence} ({ce.benign_explanation})",
                    impact="decreases_suspicion",
                    weight=ce.weight * 2.0,
                    source_id=ce.source_id
                )
            )

        # Normalize scores between 0.0 and 1.0
        suspicion_score = min(1.0, max(0.0, suspicion_points / max_possible_points)) if max_possible_points > 0 else 0.5
        confidence_score = min(0.95, max(0.30, confidence_points / (max_possible_points * 0.8)))

        # Deduplicate patterns
        suspected_patterns = list(dict.fromkeys(suspected_patterns))
        if not suspected_patterns:
            suspected_patterns = ["none"]

        return factors, round(suspicion_score, 3), round(confidence_score, 3), suspected_patterns
