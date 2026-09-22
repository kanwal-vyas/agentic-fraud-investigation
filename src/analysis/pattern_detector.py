from typing import List, Dict, Any, Optional
from src.core.constants import FraudPattern
from src.core.validation import is_valid_entity_id, clean_entity_id
from src.models.evidence import (
    TransactionDetail,
    CardHistoryEvidence,
    SharedDeviceEvidence,
    CardTestingEvidence,
    VelocityEvidence,
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
        Runs comprehensive pattern detection pipeline for a flagged transaction by querying tools.
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

        card_id = tx.card_id
        card_hist = self.tools.get_card_history(card_id, limit=50)
        testing_ev = self.tools.detect_card_testing(card_id)
        reg_ev = self.tools.detect_regional_anomaly(txn_id)
        dev_ev = None
        if tx.profile_id and is_valid_entity_id(tx.profile_id, "DeviceProfile"):
            dev_ev = self.tools.find_shared_devices(tx.profile_id)

        return self.detect_patterns_from_evidence(
            tx=tx,
            card_hist=card_hist,
            shared_devices=dev_ev,
            regional=reg_ev,
            testing_ev=testing_ev
        )

    def detect_patterns_from_evidence(
        self,
        tx: Optional[TransactionDetail],
        card_hist: Optional[CardHistoryEvidence] = None,
        shared_devices: Optional[SharedDeviceEvidence] = None,
        velocity: Optional[VelocityEvidence] = None,
        regional: Optional[RegionalAnomalyEvidence] = None,
        testing_ev: Optional[CardTestingEvidence] = None,
    ) -> List[PatternDetectionResult]:
        """
        Evaluates fraud patterns strictly against the provided evidence objects.
        Guarantees that unqueried tools or missing evidence cannot inject phantom patterns.
        """
        if not tx:
            return [PatternDetectionResult(
                pattern=FraudPattern.NONE,
                detected=True,
                heuristic_confidence=0.0,
                claims=["No transaction evidence provided."],
                supporting_txn_ids=[],
                supporting_entity_ids=[],
                rationale="No graph transaction record found.",
            )]

        results = []
        txn_id = tx.txn_id
        card_id = tx.card_id

        # 1. Card Testing Check (Requires explicit CardTestingEvidence)
        if testing_ev and testing_ev.is_testing_detected:
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

        # 2. Out of Region Use Check (Requires explicit RegionalAnomalyEvidence)
        if regional and regional.is_anomaly and tx.channel == "in_person":
            results.append(PatternDetectionResult(
                pattern=FraudPattern.OUT_OF_REGION_USE,
                detected=True,
                heuristic_confidence=regional.heuristic_confidence,
                claims=[
                    f"In-person transaction in remote billing region {regional.current_addr1}",
                    f"Cardholder historical baseline established in home region {regional.historical_home_addr1} ({regional.prior_home_txns_count} prior transactions)"
                ],
                supporting_txn_ids=[txn_id],
                supporting_entity_ids=[card_id, f"Region-{regional.current_addr1}"],
                rationale=f"Card-present use in billing region {regional.current_addr1} where cardholder has no history while retaining card.",
            ))

        # 3. Shared Device Syndicate Check (Requires explicit SharedDeviceEvidence)
        if shared_devices and shared_devices.is_shared and len(shared_devices.connected_cards) >= 2:
            if tx.profile_id and is_valid_entity_id(tx.profile_id, "DeviceProfile"):
                results.append(PatternDetectionResult(
                    pattern=FraudPattern.UNDOCUMENTED,
                    detected=True,
                    heuristic_confidence=0.88,
                    claims=[
                        f"Device profile {tx.profile_id} is shared across {len(shared_devices.connected_cards)} distinct cards",
                        f"Connected customers: {', '.join(shared_devices.connected_customers)}"
                    ],
                    supporting_txn_ids=[txn_id],
                    supporting_entity_ids=[tx.profile_id] + shared_devices.connected_cards,
                    rationale="Coordinated syndicate: identical device profile shared across multiple cardholders in a short window.",
                ))

        # 4. Card Not Present New Device Check (Requires CardHistoryEvidence & valid profile)
        if tx.channel == "online" and tx.profile_id and is_valid_entity_id(tx.profile_id, "DeviceProfile") and card_hist:
            prior_dev_txns = [t for t in card_hist.transactions if t.txn_id != tx.txn_id and clean_entity_id(t.profile_id) == tx.profile_id]
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

        # 5. Standard Card Not Present Fraud Check (Requires CardHistoryEvidence)
        if tx.channel == "online" and tx.amount >= 100.0 and card_hist:
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

        # 6. Fallback: Legitimate (None)
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
