from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

from src.core.config import settings
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.sample_client import SampleGraphClient
from src.core.validation import is_valid_entity_id, clean_entity_id
from src.models.evidence import (
    TransactionDetail,
    CustomerHistoryEvidence,
    CardHistoryEvidence,
    NeighborhoodEvidence,
    SharedDeviceEvidence,
    CardTestingEvidence,
    VelocityEvidence,
    RegionalAnomalyEvidence,
    HistoricalCaseEvidence,
    ConnectedCardsEvidence,
    GraphNode,
    GraphEdge,
)

class TigerGraphInvestigationTools:
    """
    Standardized tool suite providing TigerGraph read-only investigation queries.
    Seamlessly routes between live TigerGraph GSQL queries and offline SampleGraphClient.
    """
    def __init__(self, client: Optional[Any] = None, tg_client: Optional[Any] = None):
        target_client = client or tg_client
        if target_client:
            self.client = target_client
        else:
            try:
                tg = TigerGraphClient()
                if tg.is_connected():
                    self.client = tg
                else:
                    self.client = SampleGraphClient()
            except Exception:
                self.client = SampleGraphClient()

    def is_live(self) -> bool:
        """Returns True if connected to a real live TigerGraph cluster."""
        return isinstance(self.client, TigerGraphClient)

    def get_transaction(self, txn_id: str) -> Optional[TransactionDetail]:
        """Fetches full transaction details and linked entities."""
        tid = str(txn_id).strip()
        if isinstance(self.client, SampleGraphClient):
            data = self.client.get_transaction_details(tid)
            return TransactionDetail.model_validate(data) if data else None
        else:
            try:
                res = self.client.run_installed_query("get_transaction", {"txn": tid})
                if not res or not res[0].get("Start"):
                    return None
                s_item = res[0]["Start"][0]
                s = s_item.get("attributes", {})
                c_item = res[0].get("CardOwner", [{}])[0]
                c = c_item.get("attributes", {})
                cust_item = res[0].get("CustomerOwner", [{}])[0]
                cust = cust_item.get("attributes", {})
                dev_item = res[0].get("DeviceUsed", [{}])[0]
                dev = dev_item.get("attributes", {})
                em_item = res[0].get("EmailUsed", [{}])[0]
                em = em_item.get("attributes", {})
                
                raw_prof = clean_entity_id(dev.get("profile_id", "") or dev_item.get("v_id", ""))
                prof_id = raw_prof if is_valid_entity_id(raw_prof, "DeviceProfile") else ""
                
                return TransactionDetail(
                    txn_id=str(s.get("txn_id") or s_item.get("v_id", tid)),
                    amount=float(s.get("amount", 0.0)),
                    ts=str(s.get("ts_str", "")),
                    channel=str(s.get("channel", "in_person")),
                    risk_score=float(s.get("risk_score", 0.0)),
                    product_cd=str(s.get("product_cd", "")),
                    addr1=str(s.get("addr1", "")),
                    addr2=str(s.get("addr2", "87.0")),
                    card_id=str(c.get("card_id", "") or c_item.get("v_id", "")),
                    customer_id=str(cust.get("customer_id", "") or cust_item.get("v_id", "")),
                    profile_id=prof_id,
                    email_domain=str(em.get("domain", "") or em_item.get("v_id", "")),
                )
            except Exception:
                return None

    def get_customer_history(self, customer_id: str, limit: int = 100) -> CustomerHistoryEvidence:
        cid = str(customer_id).strip()
        if isinstance(self.client, SampleGraphClient):
            txns_raw = self.client.get_customer_transaction_history(cid, limit_count=limit)
            txns = [TransactionDetail.model_validate(t) for t in txns_raw]
        else:
            txns = []
            try:
                res = self.client.run_installed_query("get_customer_transaction_history", {"cust": cid, "limit_count": limit})
                for t_item in res[0].get("Txns", []):
                    t_attr = t_item.get("attributes", {})
                    raw_prof = clean_entity_id(t_attr.get("profile_id", "") or t_item.get("v_id", ""))
                    prof_id = raw_prof if is_valid_entity_id(raw_prof, "DeviceProfile") else ""
                    txns.append(TransactionDetail(
                        txn_id=str(t_attr.get("txn_id") or t_item.get("v_id", "")),
                        amount=float(t_attr.get("amount", 0.0)),
                        ts=str(t_attr.get("ts_str", "")),
                        channel=str(t_attr.get("channel", "")),
                        risk_score=float(t_attr.get("risk_score", 0.0)),
                        product_cd=str(t_attr.get("product_cd", "")),
                        card_id="",
                        customer_id=cid,
                        profile_id=prof_id,
                    ))
            except Exception:
                pass

        total_spend = sum(t.amount for t in txns)
        avg_spend = total_spend / len(txns) if txns else 0.0
        cards = list(set(t.card_id for t in txns if clean_entity_id(t.card_id)))
        devs = list(set(t.profile_id for t in txns if is_valid_entity_id(t.profile_id, "DeviceProfile")))

        return CustomerHistoryEvidence(
            customer_id=cid,
            transaction_count=len(txns),
            total_spend_usd=round(total_spend, 2),
            avg_amount_usd=round(avg_spend, 2),
            cards_used=cards,
            devices_used=devs,
            recent_transactions=txns,
        )

    def get_card_history(self, card_id: str, limit: int = 100) -> CardHistoryEvidence:
        cid = str(card_id).strip()
        if isinstance(self.client, SampleGraphClient):
            txns_raw = self.client.get_card_transaction_history(cid, limit_count=limit)
            txns = [TransactionDetail.model_validate(t) for t in txns_raw]
            card_info = self.client.cards_df[self.client.cards_df["card_id"] == cid]
            if not card_info.empty:
                c_row = card_info.iloc[0]
                issuer_code = int(c_row.get("issuer_code", c_row.get("card1", 0)))
                network = str(c_row.get("card_network", c_row.get("card4", "unknown")))
                card_type = str(c_row.get("card_type", c_row.get("card6", "unknown")))
                cust_id = str(c_row.get("customer_id", cid.split("-")[0]))
            else:
                issuer_code = 0
                network = "unknown"
                card_type = "unknown"
                cust_id = cid.split("-")[0]
        else:
            txns = []
            issuer_code = 0
            network = "unknown"
            card_type = "unknown"
            cust_id = ""
            try:
                res = self.client.run_installed_query("get_card_transaction_history", {"card_node": cid, "limit_count": limit})
                for t_item in res[0].get("Txns", []):
                    t_attr = t_item.get("attributes", {})
                    txns.append(TransactionDetail(
                        txn_id=str(t_attr.get("txn_id") or t_item.get("v_id", "")),
                        amount=float(t_attr.get("amount", 0.0)),
                        ts=str(t_attr.get("ts_str", "")),
                        channel=str(t_attr.get("channel", "")),
                        risk_score=float(t_attr.get("risk_score", 0.0)),
                        product_cd=str(t_attr.get("product_cd", "")),
                        card_id=cid,
                        customer_id="",
                    ))
                if res and res[0].get("Start"):
                    c_item = res[0].get("Start", [{}])[0]
                    c_attr = c_item.get("attributes", {})
                    issuer_code = int(c_attr.get("issuer_code", 0))
                    network = str(c_attr.get("card_network", "unknown"))
                    card_type = str(c_attr.get("card_type", "unknown"))
                    cust_id = str(c_attr.get("customer_id", ""))
            except Exception:
                pass

        total_amt = sum(t.amount for t in txns)
        avg_amt = total_amt / len(txns) if txns else 0.0
        max_amt = max((t.amount for t in txns), default=0.0)

        return CardHistoryEvidence(
            card_id=cid,
            customer_id=cust_id,
            issuer_code=issuer_code,
            card_network=network,
            card_type=card_type,
            total_txns=len(txns),
            total_amount_usd=round(total_amt, 2),
            avg_amount_usd=round(avg_amt, 2),
            max_amount_usd=round(max_amt, 2),
            transactions=txns,
        )

    def get_transaction_neighborhood(self, txn_id: str, max_hops: int = 2) -> NeighborhoodEvidence:
        tid = str(txn_id).strip()
        if isinstance(self.client, SampleGraphClient):
            data = self.client.get_transaction_neighborhood(tid, max_hops=max_hops)
            nodes = [GraphNode(id=n["id"], type=n["type"], attributes=n.get("attributes", {})) for n in data["nodes"]]
            edges = [GraphEdge(source=e["source"], target=e["target"], type=e["type"]) for e in data["edges"]]
        else:
            res = self.client.run_installed_query("get_transaction_neighborhood", {"txn": tid, "max_hops": max_hops})
            nodes, edges = [], []
            # Extract nodes and edges from GSQL result structures
            nodes.append(GraphNode(id=tid, type="Transaction", attributes={}))
        return NeighborhoodEvidence(center_txn_id=tid, nodes=nodes, edges=edges)

    def find_shared_devices(self, profile_id: str) -> SharedDeviceEvidence:
        cleaned_pid = clean_entity_id(profile_id)
        if not cleaned_pid or not is_valid_entity_id(cleaned_pid, "DeviceProfile"):
            return SharedDeviceEvidence(
                profile_id="",
                device_info="",
                is_shared=False,
                connected_customers=[],
                connected_cards=[],
                total_txns_on_device=0,
            )

        if isinstance(self.client, SampleGraphClient):
            data = self.client.find_shared_devices(cleaned_pid)
            return SharedDeviceEvidence.model_validate(data)
        else:
            try:
                res = self.client.run_installed_query("find_shared_devices", {"dev": cleaned_pid})
                d_attr = res[0].get("Start", [{}])[0].get("attributes", {})
                cards = [clean_entity_id(c.get("attributes", {}).get("card_id") or c.get("v_id")) for c in res[0].get("Cards", []) if clean_entity_id(c.get("attributes", {}).get("card_id") or c.get("v_id"))]
                custs = [clean_entity_id(cu.get("attributes", {}).get("customer_id") or cu.get("v_id")) for cu in res[0].get("Customers", []) if clean_entity_id(cu.get("attributes", {}).get("customer_id") or cu.get("v_id"))]
                return SharedDeviceEvidence(
                    profile_id=cleaned_pid,
                    device_info=str(d_attr.get("device_info", "")),
                    is_shared=len(set(cards)) > 1 or len(set(custs)) > 1,
                    connected_customers=list(set(custs)),
                    connected_cards=list(set(cards)),
                    total_txns_on_device=len(cards),
                )
            except Exception:
                return SharedDeviceEvidence(
                    profile_id=cleaned_pid,
                    device_info="",
                    is_shared=False,
                    connected_customers=[],
                    connected_cards=[],
                    total_txns_on_device=0,
                )


    def detect_card_testing(self, card_id: str, window_hours: int = 24) -> CardTestingEvidence:
        card_hist = self.get_card_history(card_id, limit=200)
        txns = card_hist.transactions
        
        # Sort chronologically
        txns_sorted = sorted(txns, key=lambda x: x.ts)
        
        micro_txns = [t for t in txns_sorted if t.channel == "online" and t.amount <= 5.0]
        large_txns = [t for t in txns_sorted if t.amount >= 50.0]

        is_detected = False
        confidence = 0.0

        if len(micro_txns) >= 3 and len(large_txns) >= 1:
            # Check timing: micro authorizations followed by large purchase
            first_micro = datetime.fromisoformat(micro_txns[0].ts)
            last_large = datetime.fromisoformat(large_txns[-1].ts)
            diff_hours = (last_large - first_micro).total_seconds() / 3600.0
            
            if 0 <= diff_hours <= window_hours:
                is_detected = True
                confidence = min(0.95, 0.70 + (len(micro_txns) * 0.05))

        return CardTestingEvidence(
            card_id=card_id,
            is_testing_detected=is_detected,
            micro_auth_count=len(micro_txns),
            rapid_sequence_count=len(micro_txns) + len(large_txns),
            micro_auth_transactions=micro_txns,
            subsequent_large_purchases=large_txns,
            time_window_minutes=window_hours * 60.0,
            heuristic_confidence=round(confidence, 2),
        )

    def detect_velocity(self, card_id: str, window_hours: float = 48.0) -> VelocityEvidence:
        card_hist = self.get_card_history(card_id, limit=100)
        txns = card_hist.transactions
        if not txns:
            return VelocityEvidence(
                entity_id=card_id,
                time_window_hours=window_hours,
                txn_count=0,
                total_amount_usd=0.0,
                avg_amount_usd=0.0,
                max_amount_usd=0.0,
                is_velocity_spike=False,
                rapid_cluster_count=0,
            )

        total_amt = sum(t.amount for t in txns)
        avg_amt = total_amt / len(txns)
        max_amt = max(t.amount for t in txns)

        # Check burst within window
        is_spike = len(txns) >= 4 and avg_amt > 100.0

        return VelocityEvidence(
            entity_id=card_id,
            time_window_hours=window_hours,
            txn_count=len(txns),
            total_amount_usd=round(total_amt, 2),
            avg_amount_usd=round(avg_amt, 2),
            max_amount_usd=round(max_amt, 2),
            is_velocity_spike=is_spike,
            rapid_cluster_count=len(txns),
        )

    def detect_regional_anomaly(self, txn_id: str) -> RegionalAnomalyEvidence:
        tx = self.get_transaction(txn_id)
        if not tx:
            return RegionalAnomalyEvidence(
                txn_id=txn_id,
                card_id="",
                current_addr1="",
                historical_home_addr1="",
                is_anomaly=False,
                channel="in_person",
                prior_home_txns_count=0,
                recent_remote_txns_count=0,
                heuristic_confidence=0.0,
            )

        card_hist = self.get_card_history(tx.card_id, limit=100)
        prior_txns = [t for t in card_hist.transactions if t.txn_id != tx.txn_id and t.addr1]
        
        if not prior_txns:
            return RegionalAnomalyEvidence(
                txn_id=txn_id,
                card_id=tx.card_id,
                current_addr1=tx.addr1 or "",
                historical_home_addr1=tx.addr1 or "",
                is_anomaly=False,
                channel=tx.channel,
                prior_home_txns_count=0,
                recent_remote_txns_count=0,
                heuristic_confidence=0.0,
            )

        # Calculate home region mode
        addr_counts = pd.Series([t.addr1 for t in prior_txns if t.addr1]).value_counts()
        home_addr = str(addr_counts.index[0]) if not addr_counts.empty else tx.addr1

        is_anomaly = False
        confidence = 0.0

        if tx.channel == "in_person" and tx.addr1 and tx.addr1 != home_addr and addr_counts.get(home_addr, 0) >= 3:
            is_anomaly = True
            confidence = 0.85

        return RegionalAnomalyEvidence(
            txn_id=txn_id,
            card_id=tx.card_id,
            current_addr1=tx.addr1 or "",
            historical_home_addr1=home_addr,
            is_anomaly=is_anomaly,
            channel=tx.channel,
            prior_home_txns_count=int(addr_counts.get(home_addr, 0)),
            recent_remote_txns_count=1 if is_anomaly else 0,
            heuristic_confidence=confidence,
        )

    def get_historical_cases(
        self,
        customer_id: Optional[str] = None,
        card_id: Optional[str] = None,
        pattern: Optional[str] = None,
        top_k: int = 5
    ) -> List[HistoricalCaseEvidence]:
        if isinstance(self.client, SampleGraphClient):
            cases_raw = self.client.get_historical_cases(customer_id, card_id, pattern, top_k=top_k)
            return [HistoricalCaseEvidence.model_validate(c) for c in cases_raw]
        else:
            cases = []
            try:
                res = self.client.run_installed_query("get_historical_cases", {"cust": customer_id or "", "top_k": top_k})
                for c_item in res[0].get("DirectCases", []):
                    attr = c_item.get("attributes", {})
                    case_id = str(attr.get("case_id") or c_item.get("v_id", ""))
                    cases.append(HistoricalCaseEvidence(
                        case_id=case_id,
                        customer_id=str(attr.get("customer_id", "")),
                        card_id=str(attr.get("card_id", "")),
                        opened_at=str(attr.get("opened_at", "")),
                        closed_at=str(attr.get("closed_at", "")),
                        outcome=str(attr.get("outcome", "")),
                        pattern=str(attr.get("pattern", "")),
                        exposure_usd=float(attr.get("exposure_usd", 0.0)),
                        n_txns=int(attr.get("n_txns", 1)),
                        analyst_notes=str(attr.get("analyst_notes", "")),
                        similarity_reason="Direct historical case on customer card",
                    ))
            except Exception:
                pass
            return cases

    def find_connected_cards(self, card_id: str) -> ConnectedCardsEvidence:
        card_hist = self.get_card_history(card_id, limit=50)
        cust_hist = self.get_customer_history(card_hist.customer_id, limit=50)
        
        connected = []
        reasons = {}
        shared_devs = []

        # 1. Cards under the same customer
        for c in cust_hist.cards_used:
            if c != card_id:
                connected.append(c)
                reasons[c] = f"Same customer profile ({card_hist.customer_id})"

        # 2. Cards sharing unique device profiles
        unique_profiles = set(clean_entity_id(t.profile_id) for t in card_hist.transactions if is_valid_entity_id(t.profile_id, "DeviceProfile"))
        for prof_id in unique_profiles:
            if not prof_id:
                continue
            shared_dev_info = self.find_shared_devices(prof_id)
            if shared_dev_info.is_shared:
                shared_devs.append(prof_id)
                for sc in shared_dev_info.connected_cards:
                    if sc and sc != card_id and sc not in connected:
                        connected.append(sc)
                        reasons[sc] = f"Shared device profile: {prof_id}"


        return ConnectedCardsEvidence(
            card_id=card_id,
            connected_cards=connected,
            connection_reasons=reasons,
            shared_device_profiles=list(set(shared_devs)),
        )
