from typing import Dict, Any, List, Optional
from src.models.context import (
    InvestigationContext,
    SourceProvenance,
    HistoricalCaseMatch,
    PolicyRuleMatch,
    RegulatoryReferenceMatch,
    EvidenceItem,
    ContradictoryEvidenceItem,
    EvidenceGapItem
)
from src.core.validation import is_valid_entity_id, clean_entity_id
from src.rag.corpus import GraphRAGCorpus
from src.rag.retriever import GraphRAGRetriever
from src.rag.graph_adapter import GraphEvidenceAdapter
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.analysis.pattern_detector import FraudPatternDetector

class InvestigationContextSynthesizer:
    """
    Synthesizes complete, multi-perspective GraphRAG investigation context.
    Combines authoritative TigerGraph evidence with historical closed case precedent,
    bank policy rules, regulatory mandates, balanced supporting/contradictory evidence,
    and granular provenance.
    """
    def __init__(
        self,
        retriever: Optional[GraphRAGRetriever] = None,
        tools: Optional[TigerGraphInvestigationTools] = None,
        detector: Optional[FraudPatternDetector] = None
    ):
        self.retriever = retriever or GraphRAGRetriever()
        self.tools = tools or TigerGraphInvestigationTools()
        self.detector = detector or FraudPatternDetector(self.tools)
        self.adapter = GraphEvidenceAdapter()

    def build_context_for_case(
        self,
        case_id: str,
        opened_at: str,
        trigger_type: str,
        trigger_text: str,
        flagged_txn_id: int,
        card_id: str,
        customer_id: str,
        risk_score: float = 0.0
    ) -> InvestigationContext:
        """
        Executes end-to-end GraphRAG context synthesis for a specific investigation case.
        """
        txn_str = str(flagged_txn_id)
        
        # 1. Fetch Authoritative Graph Evidence via TigerGraph Tools
        tx = self.tools.get_transaction(txn_str)
        cust_hist = self.tools.get_customer_history(customer_id, limit=50)
        card_hist = self.tools.get_card_history(card_id, limit=50)
        
        profile_id = tx.profile_id if (tx and tx.profile_id) else ""
        shared_devices = None
        if profile_id and is_valid_entity_id(profile_id, "DeviceProfile"):
            shared_devices = self.tools.find_shared_devices(profile_id)
        velocity = self.tools.detect_velocity(card_id, window_hours=48.0)
        regional = self.tools.detect_regional_anomaly(txn_str) if tx else None
        connected_cards = self.tools.find_connected_cards(card_id)

        # 2. Detect Graph Fraud Patterns
        detected_patterns = self.detector.detect_patterns(txn_id=txn_str)

        return self._assemble_context(
            case_id=case_id,
            opened_at=opened_at,
            trigger_type=trigger_type,
            trigger_text=trigger_text,
            flagged_txn_id=flagged_txn_id,
            card_id=card_id,
            customer_id=customer_id,
            risk_score=risk_score,
            tx=tx,
            cust_hist=cust_hist,
            card_hist=card_hist,
            shared_devices=shared_devices,
            velocity=velocity,
            regional=regional,
            connected_cards=connected_cards,
            detected_patterns=detected_patterns
        )

    def build_context_from_working_state(
        self,
        trigger: Any,
        state: Any
    ) -> InvestigationContext:
        """
        Synthesizes GraphRAG context strictly from the evidence collected by the agent.
        Guarantees that unqueried tools do not inject phantom patterns or unverified claims.
        """
        txn_str = str(trigger.transaction_id)
        tools_called = set(state.tools_called)

        # Always resolve core transaction detail for baseline context
        tx = self.tools.get_transaction(txn_str)
        cust_hist = self.tools.get_customer_history(trigger.customer_id, limit=50) if "get_customer_history" in tools_called else None
        card_hist = self.tools.get_card_history(trigger.card_id, limit=50) if "get_card_history" in tools_called else None
        
        shared_devices = None
        if "find_shared_devices" in tools_called and tx and tx.profile_id and is_valid_entity_id(tx.profile_id, "DeviceProfile"):
            shared_devices = self.tools.find_shared_devices(tx.profile_id)

        velocity = self.tools.detect_velocity(trigger.card_id, window_hours=48.0) if "detect_velocity" in tools_called else None
        regional = self.tools.detect_regional_anomaly(txn_str) if ("detect_regional_anomaly" in tools_called and tx) else None
        connected_cards = self.tools.find_connected_cards(trigger.card_id) if "find_connected_cards" in tools_called else None
        testing_ev = self.tools.detect_card_testing(trigger.card_id) if "detect_card_testing" in tools_called else None

        detected_patterns = self.detector.detect_patterns_from_evidence(
            tx=tx,
            card_hist=card_hist,
            shared_devices=shared_devices,
            velocity=velocity,
            regional=regional,
            testing_ev=testing_ev
        )

        return self._assemble_context(
            case_id=trigger.case_id,
            opened_at=trigger.opened_at or "2016-12-05 01:55:28",
            trigger_type=trigger.trigger_type.value,
            trigger_text=trigger.trigger_details,
            flagged_txn_id=trigger.transaction_id,
            card_id=trigger.card_id,
            customer_id=trigger.customer_id,
            risk_score=trigger.model_risk_score,
            tx=tx,
            cust_hist=cust_hist,
            card_hist=card_hist,
            shared_devices=shared_devices,
            velocity=velocity,
            regional=regional,
            connected_cards=connected_cards,
            detected_patterns=detected_patterns
        )

    def _assemble_context(
        self,
        case_id: str,
        opened_at: str,
        trigger_type: str,
        trigger_text: str,
        flagged_txn_id: int,
        card_id: str,
        customer_id: str,
        risk_score: float,
        tx: Optional[Any],
        cust_hist: Optional[Any],
        card_hist: Optional[Any],
        shared_devices: Optional[Any],
        velocity: Optional[Any],
        regional: Optional[Any],
        connected_cards: Optional[Any],
        detected_patterns: List[Any]
    ) -> InvestigationContext:
        txn_str = str(flagged_txn_id)
        profile_id = tx.profile_id if (tx and tx.profile_id) else ""

        # Transform Graph Evidence into GraphRAG Query Payload
        adapted = self.adapter.extract_retrieval_query(
            tx=tx,
            cust_hist=cust_hist,
            card_hist=card_hist,
            shared_devices=shared_devices,
            velocity=velocity,
            regional=regional,
            connected_cards=connected_cards,
            detected_patterns=detected_patterns
        )

        # Historical Case Retrieval (Both Confirmed Fraud & Cleared)
        confirmed_cases = self.retriever.retrieve_historical_cases(
            query_text=adapted["query_text"],
            customer_id=customer_id,
            card_id=card_id,
            outcome="confirmed_fraud",
            top_k=3
        )

        cleared_cases = self.retriever.retrieve_historical_cases(
            query_text=adapted["query_text"],
            customer_id=customer_id,
            outcome="cleared",
            top_k=3
        )

        # Policy Rule Retrieval
        pattern_names = [p.pattern.value if hasattr(p.pattern, "value") else str(p.pattern) for p in detected_patterns]
        amount_val = tx.amount if tx else 0.0
        applicable_policies = self.retriever.retrieve_applicable_policies(
            query_text=f"{trigger_type} {adapted['query_text']}",
            detected_patterns=pattern_names,
            has_shared_devices=adapted["has_shared_devices"],
            exposure_usd=amount_val,
            model_risk_score=risk_score,
            top_k=4
        )

        # Regulatory Reference Retrieval
        reg_references = self.retriever.retrieve_regulatory_references(
            query_text=f"{trigger_type} {' '.join(pattern_names)}",
            exposure_usd=amount_val,
            is_online=(tx.channel == "online" if tx else True),
            top_k=3
        )

        # 7. Synthesize Granular Supporting Evidence
        supporting_evidence: List[EvidenceItem] = []
        source_attributions: List[SourceProvenance] = []

        # Graph Facts
        for bullet in adapted["graph_evidence_bullets"]:
            supporting_evidence.append(
                EvidenceItem(
                    source_id=f"graph:txn:{txn_str}",
                    statement=bullet,
                    confidence=1.0,
                    category="graph_fact"
                )
            )
            source_attributions.append(
                SourceProvenance(
                    source_type="graph",
                    source_id=f"graph:txn:{txn_str}",
                    relevance_score=1.0,
                    content=bullet,
                    metadata={"case_id": case_id, "txn_id": txn_str}
                )
            )

        # Historical Precedents
        for cc in confirmed_cases:
            stmt = f"Prior confirmed fraud case {cc.case_id} on customer {cc.customer_id} ({cc.pattern}, exposure ${cc.exposure_usd:.2f}): {cc.analyst_notes[:100]}..."
            supporting_evidence.append(
                EvidenceItem(
                    source_id=cc.case_id,
                    statement=stmt,
                    confidence=0.85,
                    category="historical_precedent"
                )
            )
            source_attributions.append(
                SourceProvenance(
                    source_type="closed_case",
                    source_id=cc.case_id,
                    relevance_score=cc.relevance_score,
                    content=cc.analyst_notes,
                    metadata={"outcome": "confirmed_fraud", "pattern": cc.pattern}
                )
            )

        # 8. Synthesize Contradictory / Benign Evidence
        contradictory_evidence: List[ContradictoryEvidenceItem] = []

        # Check if customer has prior cleared false positive cases
        for cl in cleared_cases:
            contradictory_evidence.append(
                ContradictoryEvidenceItem(
                    evidence=f"Customer {cl.customer_id} has previously cleared investigation {cl.case_id}: {cl.analyst_notes[:110]}...",
                    benign_explanation="Cardholder has a documented history of legitimate travel or unusual spending that was confirmed authorized.",
                    source_id=cl.case_id,
                    weight=0.8
                )
            )
            source_attributions.append(
                SourceProvenance(
                    source_type="closed_case",
                    source_id=cl.case_id,
                    relevance_score=cl.relevance_score,
                    content=cl.analyst_notes,
                    metadata={"outcome": "cleared", "pattern": cl.pattern}
                )
            )

        # Check if amount is within normal historical baseline
        if tx and card_hist and card_hist.avg_amount_usd > 0:
            if tx.amount <= card_hist.avg_amount_usd * 1.5:
                contradictory_evidence.append(
                    ContradictoryEvidenceItem(
                        evidence=f"Flagged amount (${tx.amount:.2f}) is consistent with normal average card spend (${card_hist.avg_amount_usd:.2f})",
                        benign_explanation="Transaction amount is not an abnormal monetary outlier compared to established card history.",
                        source_id=f"graph:card:{card_id}",
                        weight=0.6
                    )
                )

        # Check if region matches home region
        if regional and not regional.is_anomaly:
            contradictory_evidence.append(
                ContradictoryEvidenceItem(
                    evidence=f"Transaction billing region ({regional.current_addr1}) matches cardholder established home baseline",
                    benign_explanation="Transaction was conducted in the customer's familiar geographic area.",
                    source_id=f"graph:txn:{txn_str}:region",
                    weight=0.7
                )
            )

        # Check if device is unique and not shared
        if shared_devices and not shared_devices.is_shared:
            contradictory_evidence.append(
                ContradictoryEvidenceItem(
                    evidence="Device fingerprint has not been observed on other customer accounts",
                    benign_explanation="Absence of multi-account device sharing reduces likelihood of organized syndicate fraud.",
                    source_id=f"graph:profile:{profile_id}",
                    weight=0.6
                )
            )

        # 9. Identify Evidence Gaps
        evidence_gaps: List[EvidenceGapItem] = []
        if trigger_type != "customer_report":
            evidence_gaps.append(
                EvidenceGapItem(
                    missing_information="Cardholder authorization confirmation",
                    recommended_verification="Initiate Out-of-Band SMS / 2FA inquiry under Rule R1 to confirm or deny transaction authorization.",
                    urgency="high"
                )
            )

        if not tx or not tx.profile_id or "Unknown" in tx.profile_id or "nan" in tx.profile_id:
            evidence_gaps.append(
                EvidenceGapItem(
                    missing_information="Device hardware fingerprint and network IP proxy details",
                    recommended_verification="Inspect web application gateway logs for device session integrity and IP ASN geolocation.",
                    urgency="medium"
                )
            )

        if adapted["has_shared_devices"]:
            evidence_gaps.append(
                EvidenceGapItem(
                    missing_information="Secondary card activity confirmation across linked customer accounts",
                    recommended_verification="Query transaction velocity on all connected cards under Policy Rule R6.",
                    urgency="high"
                )
            )

        # Attributions for Policies and Regulations
        for pol in applicable_policies:
            source_attributions.append(
                SourceProvenance(
                    source_type="policy",
                    source_id=pol.rule_id,
                    relevance_score=0.9,
                    content=pol.description,
                    metadata={"rule_id": pol.rule_id, "actions": pol.recommended_actions}
                )
            )

        for reg in reg_references:
            source_attributions.append(
                SourceProvenance(
                    source_type="regulation",
                    source_id=reg.regulation_id,
                    relevance_score=0.9,
                    content=reg.excerpt,
                    metadata={"section": reg.section, "mandate": reg.mandate_summary}
                )
            )

        patterns_serialized = []
        for p in detected_patterns:
            d = p.model_dump() if hasattr(p, "model_dump") else dict(p)
            pat_val = p.pattern.value if hasattr(p.pattern, "value") else str(p.pattern)
            if pat_val == "card_testing":
                d["source_id"] = "tool:detect_card_testing"
            elif pat_val == "out_of_region_use":
                d["source_id"] = "tool:detect_regional_anomaly"
            elif pat_val == "undocumented":
                d["source_id"] = "tool:find_shared_devices"
            elif pat_val in ["card_not_present_fraud", "card_not_present_new_device"]:
                d["source_id"] = "tool:get_card_history"
            else:
                d["source_id"] = f"graph:txn:{txn_str}"
            patterns_serialized.append(d)

        return InvestigationContext(
            case_id=case_id,
            opened_at=opened_at,
            trigger_type=trigger_type,
            trigger_text=trigger_text,
            flagged_txn_id=flagged_txn_id,
            card_id=card_id,
            customer_id=customer_id,
            profile_id=profile_id,
            model_risk_score=risk_score,
            graph_evidence_summary=adapted["graph_evidence_bullets"],
            detected_patterns=patterns_serialized,
            historical_cases_confirmed_fraud=confirmed_cases,
            historical_cases_cleared=cleared_cases,
            applicable_policies=applicable_policies,
            regulatory_references=reg_references,
            supporting_evidence=supporting_evidence,
            contradictory_evidence=contradictory_evidence,
            evidence_gaps=evidence_gaps,
            source_attributions=source_attributions
        )
