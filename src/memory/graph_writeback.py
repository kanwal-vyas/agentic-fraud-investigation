import datetime
from typing import Dict, Any, List, Optional
from src.models.case_memory import CaseMemoryRecord
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.sample_client import SampleGraphClient

class CaseGraphWritebackEngine:
    """
    Performs idempotent writeback of investigation cases into the TigerGraph graph layer.
    Connects Case entities to Transactions (INVOLVES), Cards (ON_CARD), and connected cards (CONNECTED_TO).
    Operates seamlessly in both LIVE and OFFLINE modes, reporting operational status clearly.
    """
    def __init__(
        self,
        tg_client: Optional[TigerGraphClient] = None,
        sample_client: Optional[SampleGraphClient] = None
    ):
        self.tg_client = tg_client
        self.sample_client = sample_client or SampleGraphClient()

    def is_live_deployment(self) -> bool:
        if self.tg_client is not None:
            try:
                ping_res = self.tg_client.ping()
                return bool(ping_res.get("connected", False))
            except Exception:
                return False
        return False

    def write_case(self, case: CaseMemoryRecord) -> Dict[str, Any]:
        """
        Idempotently writes the case record and its topological edges to the graph.
        Does not duplicate Case vertices if updated multiple times.
        """
        mode = "LIVE" if self.is_live_deployment() else "OFFLINE"
        now = datetime.datetime.now().isoformat()
        entities_linked: List[str] = []

        exposure_val = case.sar_data.exposure_usd if case.sar_data else 0.0
        pattern_str = ", ".join(case.fraud_patterns_identified) if case.fraud_patterns_identified else "none"

        case_attributes = {
            "status": case.status.value,
            "verdict": case.fraud_assessment,
            "fraud_probability": float(case.confidence),
            "pattern": pattern_str,
            "pattern_description": case.nba_rationale or case.summary,
            "exposure_usd": float(exposure_val),
            "summary": case.summary,
            "created_at": case.created_at or now,
        }

        if mode == "LIVE" and self.tg_client is not None:
            # 1. Upsert InvestigationCase Vertex
            self.tg_client.upsert_vertex("InvestigationCase", case.case_id, case_attributes)
            entities_linked.append(f"InvestigationCase:{case.case_id}")

            # 2. Link InvestigationCase -> Transaction (INVOLVES)
            if case.triggering_txn_id:
                txn_str = str(case.triggering_txn_id)
                self.tg_client.upsert_edge("InvestigationCase", case.case_id, "INVOLVES", "Transaction", txn_str)
                entities_linked.append(f"Transaction:{txn_str}")

            # 3. Link InvestigationCase -> Card (ON_CARD)
            if case.card_id:
                self.tg_client.upsert_edge("InvestigationCase", case.case_id, "ON_CARD", "Card", case.card_id)
                entities_linked.append(f"Card:{case.card_id}")

            # 4. Link InvestigationCase -> Connected Cards (CONNECTED_TO)
            connected_cards = case.related_entities.get("cards", [])
            for cc in connected_cards:
                if cc != case.card_id:
                    self.tg_client.upsert_edge("InvestigationCase", case.case_id, "CONNECTED_TO", "Card", cc)
                    entities_linked.append(f"ConnectedCard:{cc}")

        else:
            # Offline In-Memory Graph Index Upsert
            if hasattr(self.sample_client, "upsert_case"):
                self.sample_client.upsert_case(
                    case_id=case.case_id,
                    status=case.status.value,
                    verdict=case.fraud_assessment,
                    fraud_probability=float(case.confidence),
                    pattern=pattern_str,
                    pattern_description=case.nba_rationale or case.summary,
                    exposure_usd=float(exposure_val),
                    summary=case.summary,
                    created_at=case.created_at or now
                )
            entities_linked.append(f"Case:{case.case_id}")

            if case.triggering_txn_id:
                txn_str = str(case.triggering_txn_id)
                if hasattr(self.sample_client, "upsert_edge"):
                    self.sample_client.upsert_edge("Case", case.case_id, "INVOLVES", "Transaction", txn_str)
                entities_linked.append(f"Transaction:{txn_str}")

            if case.card_id:
                if hasattr(self.sample_client, "upsert_edge"):
                    self.sample_client.upsert_edge("Case", case.case_id, "ON_CARD", "Card", case.card_id)
                entities_linked.append(f"Card:{case.card_id}")

            connected_cards = case.related_entities.get("cards", [])
            for cc in connected_cards:
                if cc != case.card_id:
                    if hasattr(self.sample_client, "upsert_edge"):
                        self.sample_client.upsert_edge("Case", case.case_id, "CONNECTED_TO", "Card", cc)
                    entities_linked.append(f"ConnectedCard:{cc}")

        case.written_to_graph = True
        case.graph_case_id = case.case_id

        return {
            "status": "success",
            "mode": mode,
            "case_id": case.case_id,
            "entities_linked": entities_linked,
            "timestamp": now,
        }
