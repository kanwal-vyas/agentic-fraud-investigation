import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from src.core.config import settings

class SampleGraphClient:
    """
    Offline repository-backed graph query client for development and local testing.
    Executes graph traversals against preprocessed normalized CSV files in data/sample/.
    Implements the same query contracts as the live TigerGraph GSQL queries.
    """
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else settings.sample_data_dir
        self._load_data()

    def _load_data(self):
        self.cust_df = pd.read_csv(self.data_dir / "customers.csv")
        self.cards_df = pd.read_csv(self.data_dir / "cards.csv")
        self.tx_df = pd.read_csv(self.data_dir / "transactions.csv")
        self.dev_df = pd.read_csv(self.data_dir / "device_profiles.csv")
        
        cc_file = self.data_dir / "closed_cases.csv"
        if not cc_file.exists():
            cc_file = self.data_dir / "closed_cases_history.csv"
        self.cc_df = pd.read_csv(cc_file) if cc_file.exists() else pd.DataFrame()

        # Build fast in-memory indices
        self._tx_by_id = {str(r["txn_id"]): r for _, r in self.tx_df.iterrows()}
        self._cards_by_id = {str(r["card_id"]): r for _, r in self.cards_df.iterrows()}
        self._dev_by_id = {str(r["profile_id"]): r for _, r in self.dev_df.iterrows()}
        
        self._tx_by_card = {}
        self._tx_by_cust = {}
        self._tx_by_profile = {}
        for _, r in self.tx_df.iterrows():
            cid = str(r["card_id"])
            cust = str(r["customer_id"])
            pid = str(r.get("profile_id", "") or "")
            self._tx_by_card.setdefault(cid, []).append(r)
            self._tx_by_cust.setdefault(cust, []).append(r)
            if pid and pid != "UnknownDevice | UnknownOS | UnknownBrowser | UnknownScreen":
                self._tx_by_profile.setdefault(pid, []).append(r)

    def is_live_deployment(self) -> bool:
        return False

    def get_transaction_details(self, txn_id: str) -> Dict[str, Any]:
        tid = str(txn_id).strip()
        row = self._tx_by_id.get(tid)
        if row is None:
            return {}
        card_id = str(row["card_id"])
        card_row = self._cards_by_id.get(card_id, {})
        issuer_code = int(card_row.get("issuer_code", card_row.get("card1", 0))) if isinstance(card_row, pd.Series) or isinstance(card_row, dict) else 0
        card_network = str(card_row.get("card_network", card_row.get("card4", "unknown"))) if isinstance(card_row, pd.Series) or isinstance(card_row, dict) else "unknown"
        card_type = str(card_row.get("card_type", card_row.get("card6", "unknown"))) if isinstance(card_row, pd.Series) or isinstance(card_row, dict) else "unknown"
        
        prof_id = str(row.get("profile_id", "") or "")
        dev_row = self._dev_by_id.get(prof_id, {})
        device_info = str(dev_row.get("device_info", "")) if isinstance(dev_row, pd.Series) or isinstance(dev_row, dict) else ""
        os_val = str(dev_row.get("os", "")) if isinstance(dev_row, pd.Series) or isinstance(dev_row, dict) else ""
        browser_val = str(dev_row.get("browser", "")) if isinstance(dev_row, pd.Series) or isinstance(dev_row, dict) else ""
        screen_val = str(dev_row.get("screen", "")) if isinstance(dev_row, pd.Series) or isinstance(dev_row, dict) else ""

        return {
            "txn_id": tid,
            "amount": float(row["amount"]),
            "ts": str(row["ts"]),
            "ts_str": str(row["ts"]),
            "channel": str(row["channel"]),
            "risk_score": float(row["risk_score"]),
            "product_cd": str(row["product_cd"]),
            "addr1": str(row["addr1"]) if pd.notna(row["addr1"]) else "",
            "addr2": str(row["addr2"]) if pd.notna(row["addr2"]) else "87.0",
            "card_id": card_id,
            "customer_id": str(row["customer_id"]),
            "issuer_code": issuer_code,
            "card_network": card_network,
            "card_type": card_type,
            "profile_id": prof_id,
            "device_info": device_info,
            "os": os_val,
            "browser": browser_val,
            "screen": screen_val,
            "email_domain": str(row.get("email_domain", "") or ""),
        }

    def get_customer_transaction_history(self, customer_id: str, limit_count: int = 100) -> List[Dict[str, Any]]:
        cid = str(customer_id).strip()
        txns = self._tx_by_cust.get(cid, [])
        txns_sorted = sorted(txns, key=lambda r: str(r["ts"]), reverse=True)[:limit_count]
        return [self.get_transaction_details(str(t["txn_id"])) for t in txns_sorted]

    def get_card_transaction_history(self, card_id: str, limit_count: int = 100) -> List[Dict[str, Any]]:
        cid = str(card_id).strip()
        txns = self._tx_by_card.get(cid, [])
        txns_sorted = sorted(txns, key=lambda r: str(r["ts"]), reverse=True)[:limit_count]
        return [self.get_transaction_details(str(t["txn_id"])) for t in txns_sorted]

    def get_transaction_neighborhood(self, txn_id: str, max_hops: int = 2) -> Dict[str, Any]:
        tx_detail = self.get_transaction_details(txn_id)
        if not tx_detail:
            return {"nodes": [], "edges": []}
        
        nodes = [{"id": tx_detail["txn_id"], "type": "Transaction", "attributes": tx_detail}]
        edges = []

        # 1-Hop: Card, Device, Region, Email
        card_id = tx_detail["card_id"]
        nodes.append({"id": card_id, "type": "Card", "attributes": {"card_id": card_id, "customer_id": tx_detail["customer_id"]}})
        edges.append({"source": card_id, "target": tx_detail["txn_id"], "type": "PERFORMED_TXN"})

        cust_id = tx_detail["customer_id"]
        nodes.append({"id": cust_id, "type": "Customer", "attributes": {"customer_id": cust_id}})
        edges.append({"source": cust_id, "target": card_id, "type": "OWNS_CARD"})

        prof_id = tx_detail["profile_id"]
        if prof_id and "Unknown" not in prof_id:
            nodes.append({"id": prof_id, "type": "DeviceProfile", "attributes": {"profile_id": prof_id, "device_info": tx_detail["device_info"]}})
            edges.append({"source": tx_detail["txn_id"], "target": prof_id, "type": "USED_DEVICE"})

            # Connected siblings on same device
            sibling_txns = self._tx_by_profile.get(prof_id, [])[:10]
            for srow in sibling_txns:
                stid = str(srow["txn_id"])
                scard = str(srow["card_id"])
                if stid != tx_detail["txn_id"]:
                    nodes.append({"id": stid, "type": "Transaction", "attributes": {"txn_id": stid, "amount": float(srow["amount"])}})
                    edges.append({"source": stid, "target": prof_id, "type": "USED_DEVICE"})
                    if scard != card_id:
                        nodes.append({"id": scard, "type": "Card", "attributes": {"card_id": scard, "customer_id": str(srow["customer_id"])}})
                        edges.append({"source": scard, "target": stid, "type": "PERFORMED_TXN"})

        return {"nodes": nodes, "edges": edges}

    def find_shared_devices(self, profile_id: str) -> Dict[str, Any]:
        pid = str(profile_id).strip()
        txns = self._tx_by_profile.get(pid, [])
        connected_cards = list(set(str(r["card_id"]) for r in txns))
        connected_custs = list(set(str(r["customer_id"]) for r in txns))
        dev_row = self._dev_by_id.get(pid, {})
        dev_info = str(dev_row.get("device_info", "")) if isinstance(dev_row, pd.Series) or isinstance(dev_row, dict) else ""

        return {
            "profile_id": pid,
            "device_info": dev_info,
            "is_shared": len(connected_cards) > 1 or len(connected_custs) > 1,
            "connected_customers": connected_custs,
            "connected_cards": connected_cards,
            "total_txns_on_device": len(txns),
        }

    def get_historical_cases(self, customer_id: Optional[str] = None, card_id: Optional[str] = None, pattern: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.cc_df.empty:
            return []
        
        matches = self.cc_df.copy()
        if customer_id:
            cust_matches = matches[matches["customer_id"] == customer_id]
            if not cust_matches.empty:
                matches = cust_matches
        elif card_id:
            card_matches = matches[matches["card_id"] == card_id]
            if not card_matches.empty:
                matches = card_matches
        elif pattern and pattern != "none":
            pat_matches = matches[matches["pattern"] == pattern]
            if not pat_matches.empty:
                matches = pat_matches

        cases = []
        for _, r in matches.head(top_k).iterrows():
            cases.append({
                "case_id": str(r["case_id"]),
                "customer_id": str(r["customer_id"]),
                "card_id": str(r["card_id"]),
                "opened_at": str(r["opened_at"]),
                "closed_at": str(r["closed_at"]),
                "outcome": str(r["outcome"]),
                "pattern": str(r["pattern"]),
                "exposure_usd": float(r["exposure_usd"]) if pd.notna(r["exposure_usd"]) else 0.0,
                "n_txns": int(r["n_txns"]) if pd.notna(r["n_txns"]) else 1,
                "analyst_notes": str(r.get("analyst_notes", "") or ""),
                "similarity_reason": f"Matched historical case on {customer_id or card_id or pattern}",
            })
        return cases
