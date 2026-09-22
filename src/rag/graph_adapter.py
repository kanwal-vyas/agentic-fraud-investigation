from typing import Dict, Any, List, Optional
from src.models.evidence import (
    TransactionDetail,
    CustomerHistoryEvidence,
    CardHistoryEvidence,
    SharedDeviceEvidence,
    VelocityEvidence,
    RegionalAnomalyEvidence,
    ConnectedCardsEvidence,
    PatternDetectionResult
)

class GraphEvidenceAdapter:
    """
    Translates structured TigerGraph query outputs and MCP tool results into
    dense, graph-aware GraphRAG query payloads and feature descriptors.
    """
    def extract_retrieval_query(
        self,
        tx: Optional[TransactionDetail] = None,
        cust_hist: Optional[CustomerHistoryEvidence] = None,
        card_hist: Optional[CardHistoryEvidence] = None,
        shared_devices: Optional[SharedDeviceEvidence] = None,
        velocity: Optional[VelocityEvidence] = None,
        regional: Optional[RegionalAnomalyEvidence] = None,
        connected_cards: Optional[ConnectedCardsEvidence] = None,
        detected_patterns: Optional[List[PatternDetectionResult]] = None,
    ) -> Dict[str, Any]:
        """
        Converts multi-dimensional graph evidence into an enriched retrieval query payload.
        """
        tokens: List[str] = []
        graph_bullets: List[str] = []
        
        cust_id = tx.customer_id if tx else (cust_hist.customer_id if cust_hist else None)
        card_id = tx.card_id if tx else (card_hist.card_id if card_hist else None)
        amount_usd = tx.amount if tx else 0.0
        model_risk_score = tx.risk_score if tx else 0.0
        channel = tx.channel if tx else "online"

        if cust_id:
            tokens.append(f"customer {cust_id}")
        if card_id:
            tokens.append(f"card {card_id}")

        if tx:
            tokens.append(f"transaction {tx.txn_id} amount {tx.amount:.2f} channel {tx.channel}")
            graph_bullets.append(f"Transaction {tx.txn_id} (${tx.amount:.2f}, {tx.channel}) on {tx.card_id} for customer {tx.customer_id}")
            if tx.risk_score:
                tokens.append(f"model_risk_score {tx.risk_score:.2f}")

        # Patterns
        patterns_list = []
        if detected_patterns:
            for p in detected_patterns:
                patterns_list.append(p.pattern)
                tokens.append(f"pattern {p.pattern} confidence {p.heuristic_confidence:.2f}")
                graph_bullets.append(f"Detected graph pattern '{p.pattern}' (heuristic confidence: {p.heuristic_confidence:.2f})")

        # Shared Devices
        has_shared_dev = False
        shared_dev_count = 0
        if shared_devices:
            if shared_devices.is_shared:
                has_shared_dev = True
                shared_dev_count = len(shared_devices.connected_cards)
                tokens.append(f"shared_device syndicate multi_card count_{shared_dev_count}")
                graph_bullets.append(f"Device profile is shared across {shared_dev_count} cards and {len(shared_devices.connected_customers)} customers")
            else:
                tokens.append("unique_device single_card")
                graph_bullets.append("Device profile is unique to this cardholder account")

        # Velocity
        is_vel_spike = False
        if velocity:
            is_vel_spike = velocity.is_velocity_spike
            if velocity.is_velocity_spike:
                tokens.append(f"high_velocity velocity_spike txn_count_{velocity.txn_count}")
                graph_bullets.append(f"Velocity spike active: {velocity.txn_count} transactions totaling ${velocity.total_amount_usd:.2f}")
            else:
                tokens.append("normal_velocity baseline")
                graph_bullets.append(f"Normal spending velocity: {velocity.txn_count} transactions (${velocity.total_amount_usd:.2f})")

        # Regional Anomaly
        is_reg_anomaly = False
        if regional:
            is_reg_anomaly = regional.is_anomaly
            if regional.is_anomaly:
                tokens.append(f"out_of_region remote_region {regional.current_addr1} home_{regional.historical_home_addr1}")
                graph_bullets.append(f"Regional anomaly: billed in remote region {regional.current_addr1} vs home region {regional.historical_home_addr1}")
            else:
                tokens.append(f"home_region {regional.current_addr1} recurring_baseline")
                graph_bullets.append(f"Regional match: transaction region {regional.current_addr1} matches home baseline {regional.historical_home_addr1}")

        # Connected Cards
        if connected_cards and connected_cards.connected_cards:
            tokens.append(f"connected_cards count_{len(connected_cards.connected_cards)}")
            graph_bullets.append(f"Found {len(connected_cards.connected_cards)} secondary connected cards linked via customer/device")

        query_text = " ".join(tokens)

        return {
            "query_text": query_text,
            "customer_id": cust_id,
            "card_id": card_id,
            "amount_usd": amount_usd,
            "model_risk_score": model_risk_score,
            "channel": channel,
            "patterns": patterns_list,
            "has_shared_devices": has_shared_dev,
            "shared_device_count": shared_dev_count,
            "is_velocity_spike": is_vel_spike,
            "is_regional_anomaly": is_reg_anomaly,
            "graph_evidence_bullets": graph_bullets
        }
