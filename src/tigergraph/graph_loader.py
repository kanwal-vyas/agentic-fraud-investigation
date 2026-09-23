import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from src.core.config import settings
from src.tigergraph.client import TigerGraphClient

class TigerGraphDataLoader:
    """
    Manages loading of preprocessed entity and edge CSV files into TigerGraph.
    """
    def __init__(self, tg_client: Optional[TigerGraphClient] = None):
        self.client = tg_client or TigerGraphClient()

    def load_schema(self, schema_file: Optional[Path] = None) -> Dict[str, Any]:
        """Executes the GSQL schema definition script."""
        file_path = schema_file or (settings.base_dir / "tigergraph" / "schema.gsql")
        if not file_path.exists():
            return {"success": False, "error": f"Schema file not found at {file_path}"}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                gsql_content = f.read()
            res = self.client.gsql(gsql_content)
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def deploy_schema(self, schema_file: Optional[Path] = None, graph_name: Optional[str] = None) -> Dict[str, Any]:
        """Deploys the schema to the configured graph database."""
        return self.load_schema(schema_file)

    def install_queries(self, queries_file: Optional[Path] = None) -> Dict[str, Any]:
        """Installs the GSQL investigation queries into TigerGraph."""
        file_path = queries_file or (settings.base_dir / "tigergraph" / "queries" / "investigation_queries.gsql")
        if not file_path.exists():
            return {"success": False, "error": f"Queries file not found at {file_path}"}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                gsql_content = f.read()
            res = self.client.gsql(gsql_content)
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_upsert_csv(
        self,
        data_dir: Path,
        batch_size: int = 2000
    ) -> Dict[str, Any]:
        """
        Upserts vertices and edges directly from preprocessed CSV files via REST API / pyTigerGraph upsert.
        Ideal for sample datasets and environments without GSQL server file access permissions.
        """
        conn = self.client.get_connection()
        report = {}

        # 1. Customers
        cust_file = data_dir / "customers.csv"
        if cust_file.exists():
            df = pd.read_csv(cust_file)
            print(f"[*] Upserting {len(df)} Customer vertices...")
            cust_payload = {str(r["customer_id"]): {} for _, r in df.iterrows()}
            conn.upsertVertices("Customer", cust_payload)
            report["Customer"] = len(df)

        # 2. Cards
        cards_file = data_dir / "cards.csv"
        if cards_file.exists():
            df = pd.read_csv(cards_file)
            print(f"[*] Upserting {len(df)} Card vertices & OWNS_CARD edges...")
            card_vertices = {}
            for _, r in df.iterrows():
                cid = str(r["card_id"])
                card_vertices[cid] = {
                    "customer_id": str(r["customer_id"]),
                    "issuer_code": int(r["issuer_code"]) if pd.notna(r["issuer_code"]) else 0,
                    "card_network": str(r["card_network"]),
                    "card_type": str(r["card_type"]),
                }
            conn.upsertVertices("Card", card_vertices)
            
            # Edges: Customer -> Card
            for _, r in df.iterrows():
                conn.upsertEdge("Customer", str(r["customer_id"]), "OWNS_CARD", "Card", str(r["card_id"]))
            report["Card"] = len(df)

        # 3. DeviceProfiles
        dev_file = data_dir / "device_profiles.csv"
        if dev_file.exists():
            df = pd.read_csv(dev_file)
            print(f"[*] Upserting {len(df)} DeviceProfile vertices...")
            dev_payload = {}
            for _, r in df.iterrows():
                pid = str(r["profile_id"])
                dev_payload[pid] = {
                    "device_info": str(r.get("device_info", "") or ""),
                    "os": str(r.get("os", "") or ""),
                    "browser": str(r.get("browser", "") or ""),
                    "screen": str(r.get("screen", "") or ""),
                    "device_type": str(r.get("device_type", "") or ""),
                }
            conn.upsertVertices("DeviceProfile", dev_payload)
            report["DeviceProfile"] = len(df)

        # 4. EmailDomains
        em_file = data_dir / "email_domains.csv"
        if em_file.exists():
            df = pd.read_csv(em_file)
            print(f"[*] Upserting {len(df)} EmailDomain vertices...")
            em_payload = {str(r["domain"]): {} for _, r in df.iterrows() if pd.notna(r["domain"])}
            conn.upsertVertices("EmailDomain", em_payload)
            report["EmailDomain"] = len(df)

        # 5. BillingRegions
        br_file = data_dir / "billing_regions.csv"
        if br_file.exists():
            df = pd.read_csv(br_file)
            print(f"[*] Upserting {len(df)} BillingRegion vertices...")
            br_payload = {}
            for _, r in df.iterrows():
                rcode = str(r["region_code"])
                br_payload[rcode] = {"country_code": str(r.get("country_code", "87.0"))}
            conn.upsertVertices("BillingRegion", br_payload)
            report["BillingRegion"] = len(df)

        # 6. Transactions & connecting edges
        tx_file = data_dir / "transactions.csv"
        if tx_file.exists():
            print(f"[*] Upserting Transaction vertices & edges from {tx_file}...")
            tx_count = 0
            for chunk in pd.read_csv(tx_file, chunksize=batch_size):
                tx_payload = {}
                for _, r in chunk.iterrows():
                    tid = str(r["txn_id"])
                    tx_payload[tid] = {
                        "amount": float(r["amount"]),
                        "ts": str(r["ts"]),
                        "ts_str": str(r["ts"]),
                        "channel": str(r["channel"]),
                        "risk_score": float(r["risk_score"]),
                        "product_cd": str(r["product_cd"]),
                        "addr1": str(r["addr1"]) if pd.notna(r["addr1"]) else "",
                        "addr2": str(r["addr2"]) if pd.notna(r["addr2"]) else "",
                    }
                conn.upsertVertices("Transaction", tx_payload)

                # Upsert edges for chunk
                for _, r in chunk.iterrows():
                    tid = str(r["txn_id"])
                    card_id = str(r["card_id"])
                    conn.upsertEdge("Card", card_id, "PERFORMED_TXN", "Transaction", tid)
                    
                    prof_id = str(r.get("profile_id", "") or "")
                    if prof_id and prof_id != "UnknownDevice | UnknownOS | UnknownBrowser | UnknownScreen":
                        conn.upsertEdge("Transaction", tid, "USED_DEVICE", "DeviceProfile", prof_id)
                        
                    email = str(r.get("email_domain", "") or "")
                    if email and pd.notna(email):
                        conn.upsertEdge("Transaction", tid, "PURCHASER_EMAIL", "EmailDomain", email)
                        
                    addr1 = str(r.get("addr1", "") or "")
                    if addr1 and pd.notna(addr1):
                        conn.upsertEdge("Transaction", tid, "BILLED_IN", "BillingRegion", addr1)

                tx_count += len(chunk)
                print(f"    ... loaded {tx_count} transactions")
            report["Transaction"] = tx_count

        # 7. Closed Cases
        cc_file = data_dir / "closed_cases.csv"
        if not cc_file.exists():
            cc_file = data_dir / "closed_cases_history.csv"
        if cc_file.exists():
            df = pd.read_csv(cc_file)
            print(f"[*] Upserting {len(df)} ClosedCase vertices & edges...")
            cc_payload = {}
            for _, r in df.iterrows():
                cid = str(r["case_id"])
                cc_payload[cid] = {
                    "customer_id": str(r["customer_id"]),
                    "card_id": str(r["card_id"]),
                    "opened_at": str(r["opened_at"]),
                    "closed_at": str(r["closed_at"]),
                    "outcome": str(r["outcome"]),
                    "pattern": str(r["pattern"]),
                    "exposure_usd": float(r["exposure_usd"]) if pd.notna(r["exposure_usd"]) else 0.0,
                    "n_txns": int(r["n_txns"]) if pd.notna(r["n_txns"]) else 1,
                    "analyst_notes": str(r.get("analyst_notes", "") or ""),
                }
            conn.upsertVertices("ClosedCase", cc_payload)
            for _, r in df.iterrows():
                cid = str(r["case_id"])
                card_id = str(r["card_id"])
                conn.upsertEdge("ClosedCase", cid, "ON_CARD", "Card", card_id)
                
                txn_str = str(r.get("txn_ids", "") or "")
                if txn_str and pd.notna(txn_str):
                    for t in txn_str.split("|"):
                        if t.strip():
                            conn.upsertEdge("ClosedCase", cid, "INVOLVES", "Transaction", t.strip())
            report["ClosedCase"] = len(df)

        return {"success": True, "loaded_counts": report}
