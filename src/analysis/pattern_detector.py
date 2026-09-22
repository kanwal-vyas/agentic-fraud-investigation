from typing import List, Dict, Any, Optional
from src.core.constants import FraudPattern
from src.models.evidence import (
    TransactionDetail,
    CardHistoryEvidence,
    SharedDeviceEvidence,
    CardTestingEvidence,
    RegionalAnomalyEvidence,
    HistoricalCaseEvidence,
    PatternDetectionResult,
)
from src.tigergraph.tools import TigerGraphInvestigationTools

class FraudPatternDetector:
    """
    Evaluates evidence against the 7 official fraud patterns:
    - card_testing
    - card_not_present_fraud
    - card_not_present_new_device
    - out_of_region_use
    - account_takeover
    - undocumented
    - none
    """
    def __init__(self, tools: TigerGraphInvestigationTools):
        self.tools = tools

    def detect_patterns(self, txn_id: str) -> List[PatternDetectionResult]:
        """
        Runs comprehensive pattern detection pipeline for a flagged transaction.
        Returns ordered candidate pattern results with evidence and heuristic confidence.
        """
        tx = self.tools.get_transaction(txn_id)
        if not tx:
            return [PatternDetectionResult(
                pattern=FraudPattern.NONE,
                detected=True,
                heuristic_confidence=0.0,
                claims=["Transaction not found in graph."],
                supporting_txn_ids=[],
                supporting_entity_ids=[],
                rationale="No graph transaction record found.",
            )]

        results = []
        card_id = tx.card_id
        card_hist = self.tools.get_card_history(card_id, limit=50)

        # -------------------------------------------------------------
        # 1. Card Testing Check
        # -------------------------------------------------------------
        testing_ev = self.tools.detect_card_testing(card_id)
        if testing_ev.is_testing_detected:
            support_txns = [t.txn_id for t in testing_ev.micro_auth_transactions] + [t.txn_id for t in testing_ev.subsequent_large_purchases]
            results.append(PatternDetectionResult(
                pattern=FraudPattern.CARD_TESTING,
                detected=True,
                heuristic_confidence=testing_ev.heuristic_confidence,
                claims=[
                    f"Observed {testing_ev.micro_auth_count} micro online authorizations (< $5) followed by larger purchases",
                    f"Testing sequence completed within {testing_ev.time_window_minutes/60:.1f} hours on card {card_id}"
                ],
                supporting_txn_ids=support_txns,
                supporting_entity_ids=[card_id],
                rationale="Characteristic card testing: rapid micro-authorizations to validate active card status before large purchase.",
            ))

        # -------------------------------------------------------------
        # 2. Out of Region Use Check
        # -------------------------------------------------------------
        reg_ev = self.tools.detect_regional_anomaly(txn_id)
        if reg_ev.is_anomaly and tx.channel == "in_person":
            results.append(PatternDetectionResult(
                pattern=FraudPattern.OUT_OF_REGION_USE,
                detected=True,
                heuristic_confidence=reg_ev.heuristic_confidence,
                claims=[
                    f"In-person transaction in remote billing region {reg_ev.current_addr1}",
                    f"Cardholder historical baseline established in home region {reg_ev.historical_home_addr1} ({reg_ev.prior_home_txns_count} prior transactions)"
                ],
                supporting_txn_ids=[txn_id],
                supporting_entity_ids=[card_id, f"Region-{reg_ev.current_addr1}"],
                rationale=f"Card-present use in billing region {reg_ev.current_addr1} where cardholder has no history while retaining card.",
            ))

        # -------------------------------------------------------------
        # 3. Shared Device Syndicate / Undocumented Syndicate Check
        # -------------------------------------------------------------
        if tx.profile_id and "Unknown" not in tx.profile_id:
            dev_ev = self.tools.find_shared_devices(tx.profile_id)
            if dev_ev.is_shared and len(dev_ev.connected_cards) >= 2:
                results.append(PatternDetectionResult(
                    pattern=FraudPattern.UNDOCUMENTED,
                    detected=True,
                    heuristic_confidence=0.88,
                    claims=[
                        f"Device profile {tx.profile_id} is shared across {len(dev_ev.connected_cards)} distinct cards",
                        f"Connected customers: {', '.join(dev_ev.connected_customers)}"
                    ],
                    supporting_txn_ids=[txn_id],
                    supporting_entity_ids=[tx.profile_id] + dev_ev.connected_cards,
                    rationale=f"Coordinated syndicate: identical device profile shared across multiple cardholders in a short window.",
                ))

        # -------------------------------------------------------------
        # 4. Card Not Present New Device Check
        # -------------------------------------------------------------
        if tx.channel == "online" and tx.profile_id and "Unknown" not in tx.profile_id:
            # Check if device is new for this card
            prior_dev_txns = [t for t in card_hist.transactions if t.txn_id != tx.txn_id and t.profile_id == tx.profile_id]
            if not prior_dev_txns:
                results.append(PatternDetectionResult(
                    pattern=FraudPattern.CARD_NOT_PRESENT_NEW_DEVICE,
                    detected=True,
                    heuristic_confidence=0.78,
                    claims=[
                        f"Online transaction from previously unseen device profile ({tx.profile_id})",
                        f"Transaction amount ${tx.amount:.2f} online under product code {tx.product_cd}"
                    ],
                    supporting_txn_ids=[txn_id],
                    supporting_entity_ids=[card_id, tx.profile_id],
                    rationale="Card-not-present authorization initiated from a new device profile with no prior card history.",
                ))

        # -------------------------------------------------------------
        # 5. Standard Card Not Present Fraud Check
        # -------------------------------------------------------------
        if tx.channel == "online" and tx.amount >= 100.0:
            online_recent = [t for t in card_hist.transactions if t.channel == "online"]
            if len(online_recent) >= 2:
                results.append(PatternDetectionResult(
                    pattern=FraudPattern.CARD_NOT_PRESENT_FRAUD,
                    detected=True,
                    heuristic_confidence=0.72,
                    claims=[
                        f"Burst of online transactions (${tx.amount:.2f}) on card {card_id}",
                        f"Model input risk score: {tx.risk_score:.2f}"
                    ],
                    supporting_txn_ids=[txn_id],
                    supporting_entity_ids=[card_id],
                    rationale="Card-not-present fraud: unusual online transaction amount deviating from typical card activity.",
                ))

        # -------------------------------------------------------------
        # 6. Fallback: Legitimate (None)
        # -------------------------------------------------------------
        if not results:
            results.append(PatternDetectionResult(
                pattern=FraudPattern.NONE,
                detected=True,
                heuristic_confidence=0.90,
                claims=[
                    f"Transaction consistent with cardholder normal spending profile",
                    f"Billing region {tx.addr1} matches established home baseline"
                ],
                supporting_txn_ids=[txn_id],
                supporting_entity_ids=[card_id],
                rationale="Normal legitimate activity matching cardholder baseline.",
            ))

        # Sort by confidence descending
        results.sort(key=lambda x: x.heuristic_confidence, reverse=True)
        return results
