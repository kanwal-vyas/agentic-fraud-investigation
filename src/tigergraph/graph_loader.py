import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from src.core.config import settings
from src.tigergraph.client import TigerGraphClient

class TigerGraphDataLoader:
    """
    Manages idempotent loading and resumption of preprocessed entity and edge CSV files
    into TigerGraph with robust transient error retry, reconnection, and progress tracking.
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
        batch_size: int = 2000,
        max_retries: int = 5
    ) -> Dict[str, Any]:
        """
        Upserts vertices and edges directly from preprocessed CSV files with batching,
        bulk edge upserting, exponential backoff, and transparent reconnection.
        """
        report: Dict[str, Any] = {}

        # 1. Customers
        cust_file = data_dir / "customers.csv"
        if cust_file.exists():
            df = pd.read_csv(cust_file)
            print(f"[*] Upserting {len(df)} Customer vertices...")
            cust_payload = [(str(r["customer_id"]), {}) for _, r in df.iterrows()]
            self.client.execute_with_retry(
                lambda c: c.upsertVertices("Customer", cust_payload),
                max_retries=max_retries
            )
            report["Customer"] = len(df)

        # 2. Cards & OWNS_CARD edges
        cards_file = data_dir / "cards.csv"
        if cards_file.exists():
            df = pd.read_csv(cards_file)
            print(f"[*] Upserting {len(df)} Card vertices & OWNS_CARD edges...")
            card_vertices: List[Tuple[str, Dict[str, Any]]] = []
            card_edges: List[Tuple[str, str, Dict[str, Any]]] = []
            for _, r in df.iterrows():
                cid = str(r["card_id"])
                cust_id = str(r["customer_id"])
                attrs = {
                    "customer_id": cust_id,
                    "issuer_code": int(r["issuer_code"]) if pd.notna(r["issuer_code"]) else 0,
                    "card_network": str(r["card_network"]),
                    "card_type": str(r["card_type"]),
                }
                card_vertices.append((cid, attrs))
                card_edges.append((cust_id, cid, {}))
            
            self.client.execute_with_retry(
                lambda c: c.upsertVertices("Card", card_vertices),
                max_retries=max_retries
            )
            self.client.execute_with_retry(
                lambda c: c.upsertEdges("Customer", "OWNS_CARD", "Card", card_edges),
                max_retries=max_retries
            )
            report["Card"] = len(df)
            report["OWNS_CARD"] = len(card_edges)

        # 3. DeviceProfiles
        dev_file = data_dir / "device_profiles.csv"
        if dev_file.exists():
            df = pd.read_csv(dev_file)
            print(f"[*] Upserting {len(df)} DeviceProfile vertices...")
            dev_payload: List[Tuple[str, Dict[str, Any]]] = []
            for _, r in df.iterrows():
                pid = str(r["profile_id"])
                attrs = {
                    "device_info": str(r.get("device_info", "") or ""),
                    "os": str(r.get("os", "") or ""),
                    "browser": str(r.get("browser", "") or ""),
                    "screen": str(r.get("screen", "") or ""),
                    "device_type": str(r.get("device_type", "") or ""),
                }
                dev_payload.append((pid, attrs))
            
            # Upsert in sub-batches if large
            for i in range(0, len(dev_payload), batch_size):
                chunk_dev = dev_payload[i:i + batch_size]
                self.client.execute_with_retry(
                    lambda c: c.upsertVertices("DeviceProfile", chunk_dev),
                    max_retries=max_retries
                )
            report["DeviceProfile"] = len(df)

        # 4. EmailDomains
        em_file = data_dir / "email_domains.csv"
        if em_file.exists():
            df = pd.read_csv(em_file)
            print(f"[*] Upserting {len(df)} EmailDomain vertices...")
            em_payload = [(str(r["domain"]), {}) for _, r in df.iterrows() if pd.notna(r["domain"])]
            self.client.execute_with_retry(
                lambda c: c.upsertVertices("EmailDomain", em_payload),
                max_retries=max_retries
            )
            report["EmailDomain"] = len(df)

        # 5. BillingRegions
        br_file = data_dir / "billing_regions.csv"
        if br_file.exists():
            df = pd.read_csv(br_file)
            print(f"[*] Upserting {len(df)} BillingRegion vertices...")
            br_payload = [(str(r["region_code"]), {"country_code": str(r.get("country_code", "87.0"))}) for _, r in df.iterrows()]
            self.client.execute_with_retry(
                lambda c: c.upsertVertices("BillingRegion", br_payload),
                max_retries=max_retries
            )
            report["BillingRegion"] = len(df)

        # 6. Transactions & connecting edges
        tx_file = data_dir / "transactions.csv"
        if tx_file.exists():
            total_tx_rows = sum(1 for _ in open(tx_file, "r", encoding="utf-8")) - 1
            total_chunks = (total_tx_rows + batch_size - 1) // batch_size
            print(f"[*] Upserting {total_tx_rows} Transactions & edges in {total_chunks} batches (size={batch_size})...")

            tx_count = 0
            edge_counts = {"PERFORMED_TXN": 0, "USED_DEVICE": 0, "PURCHASER_EMAIL": 0, "BILLED_IN": 0}

            for chunk_idx, chunk in enumerate(pd.read_csv(tx_file, chunksize=batch_size), start=1):
                tx_vertices: List[Tuple[str, Dict[str, Any]]] = []
                performed_edges: List[Tuple[str, str, Dict[str, Any]]] = []
                device_edges: List[Tuple[str, str, Dict[str, Any]]] = []
                email_edges: List[Tuple[str, str, Dict[str, Any]]] = []
                billing_edges: List[Tuple[str, str, Dict[str, Any]]] = []

                for _, r in chunk.iterrows():
                    tid = str(r["txn_id"])
                    card_id = str(r["card_id"])
                    attrs = {
                        "amount": float(r["amount"]),
                        "ts": str(r["ts"]),
                        "ts_str": str(r["ts"]),
                        "channel": str(r["channel"]),
                        "risk_score": float(r["risk_score"]),
                        "product_cd": str(r["product_cd"]),
                        "addr1": str(r["addr1"]) if pd.notna(r["addr1"]) else "",
                        "addr2": str(r["addr2"]) if pd.notna(r["addr2"]) else "",
                    }
                    tx_vertices.append((tid, attrs))

                    # Card -> Transaction
                    performed_edges.append((card_id, tid, {}))

                    # Transaction -> DeviceProfile
                    prof_id = str(r.get("profile_id", "") or "")
                    if prof_id and prof_id != "UnknownDevice | UnknownOS | UnknownBrowser | UnknownScreen" and pd.notna(r.get("profile_id")):
                        device_edges.append((tid, prof_id, {}))

                    # Transaction -> EmailDomain
                    email = str(r.get("email_domain", "") or "")
                    if email and pd.notna(r.get("email_domain")):
                        email_edges.append((tid, email, {}))

                    # Transaction -> BillingRegion
                    addr1 = str(r.get("addr1", "") or "")
                    if addr1 and pd.notna(r.get("addr1")):
                        billing_edges.append((tid, addr1, {}))

                # Upsert Transaction vertices for this batch
                self.client.execute_with_retry(
                    lambda c: c.upsertVertices("Transaction", tx_vertices),
                    max_retries=max_retries
                )

                # Upsert connecting edges in bulk for this batch
                if performed_edges:
                    self.client.execute_with_retry(
                        lambda c: c.upsertEdges("Card", "PERFORMED_TXN", "Transaction", performed_edges),
                        max_retries=max_retries
                    )
                    edge_counts["PERFORMED_TXN"] += len(performed_edges)

                if device_edges:
                    self.client.execute_with_retry(
                        lambda c: c.upsertEdges("Transaction", "USED_DEVICE", "DeviceProfile", device_edges),
                        max_retries=max_retries
                    )
                    edge_counts["USED_DEVICE"] += len(device_edges)

                if email_edges:
                    self.client.execute_with_retry(
                        lambda c: c.upsertEdges("Transaction", "PURCHASER_EMAIL", "EmailDomain", email_edges),
                        max_retries=max_retries
                    )
                    edge_counts["PURCHASER_EMAIL"] += len(email_edges)

                if billing_edges:
                    self.client.execute_with_retry(
                        lambda c: c.upsertEdges("Transaction", "BILLED_IN", "BillingRegion", billing_edges),
                        max_retries=max_retries
                    )
                    edge_counts["BILLED_IN"] += len(billing_edges)

                tx_count += len(chunk)
                pct = (tx_count / total_tx_rows) * 100.0 if total_tx_rows > 0 else 100.0
                print(f"    [Batch {chunk_idx}/{total_chunks}] Loaded {tx_count}/{total_tx_rows} transactions ({pct:.1f}% complete)...")

            report["Transaction"] = tx_count
            report["Edges"] = edge_counts

        # 7. Closed Cases
        cc_file = data_dir / "closed_cases.csv"
        if not cc_file.exists():
            cc_file = data_dir / "closed_cases_history.csv"
        if cc_file.exists():
            df = pd.read_csv(cc_file)
            print(f"[*] Upserting {len(df)} ClosedCase vertices & edges...")
            cc_payload: List[Tuple[str, Dict[str, Any]]] = []
            on_card_edges: List[Tuple[str, str, Dict[str, Any]]] = []
            involves_edges: List[Tuple[str, str, Dict[str, Any]]] = []

            for _, r in df.iterrows():
                cid = str(r["case_id"])
                card_id = str(r["card_id"])
                attrs = {
                    "customer_id": str(r["customer_id"]),
                    "card_id": card_id,
                    "opened_at": str(r["opened_at"]),
                    "closed_at": str(r["closed_at"]),
                    "outcome": str(r["outcome"]),
                    "pattern": str(r["pattern"]),
                    "exposure_usd": float(r["exposure_usd"]) if pd.notna(r["exposure_usd"]) else 0.0,
                    "n_txns": int(r["n_txns"]) if pd.notna(r["n_txns"]) else 1,
                    "analyst_notes": str(r.get("analyst_notes", "") or ""),
                }
                cc_payload.append((cid, attrs))
                on_card_edges.append((cid, card_id, {}))

                txn_str = str(r.get("txn_ids", "") or "")
                if txn_str and pd.notna(txn_str):
                    for t in txn_str.split("|"):
                        if t.strip():
                            involves_edges.append((cid, t.strip(), {}))

            self.client.execute_with_retry(
                lambda c: c.upsertVertices("ClosedCase", cc_payload),
                max_retries=max_retries
            )
            if on_card_edges:
                self.client.execute_with_retry(
                    lambda c: c.upsertEdges("ClosedCase", "ON_CARD", "Card", on_card_edges),
                    max_retries=max_retries
                )
            if involves_edges:
                self.client.execute_with_retry(
                    lambda c: c.upsertEdges("ClosedCase", "INVOLVES", "Transaction", involves_edges),
                    max_retries=max_retries
                )
            report["ClosedCase"] = len(df)
            report["ON_CARD"] = len(on_card_edges)
            report["INVOLVES"] = len(involves_edges)

        print("[+] Graph data loading completed successfully.")
        return {"success": True, "loaded_counts": report}
