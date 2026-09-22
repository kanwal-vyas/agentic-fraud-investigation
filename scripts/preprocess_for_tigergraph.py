import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.core.config import settings
from src.data.loader import load_case_pack, load_closed_cases, load_identity, load_transactions_chunked
from src.data.preprocessor import build_device_profile_id, extract_device_profiles, build_card_lookup, assign_card_id

def preprocess_for_tigergraph(
    raw_dir: Path,
    out_dir: Path,
    chunksize: int = 100000,
    max_transactions: int = None
):
    """
    Deterministically processes raw dataset files into TigerGraph-ready CSV files.
    Streams large transactions file in chunks to ensure low memory footprint.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Preprocessing dataset from {raw_dir} -> {out_dir}")

    # 1. Load Case Pack & Closed Cases
    cp_df = load_case_pack(raw_dir)
    cc_df = load_closed_cases(raw_dir)
    print(f"[+] Loaded {len(cp_df)} case pack rows and {len(cc_df)} closed cases.")

    # 2. Build Card Lookup Mapping (from closed cases & case pack)
    txn_card_lookup = build_card_lookup(cc_df, cp_df)
    print(f"[+] Built card mapping lookup with {len(txn_card_lookup)} explicit transaction entries.")

    # 3. Load & Process Identity -> Device Profiles
    id_df = load_identity(raw_dir)
    id_map = {}
    for _, r in id_df.iterrows():
        prof_id = build_device_profile_id(r.get("DeviceInfo"), r.get("id_30"), r.get("id_31"), r.get("id_33"))
        id_map[int(r["TransactionID"])] = prof_id
        
    dev_profiles_df = extract_device_profiles(id_df)
    dev_profiles_df.to_csv(out_dir / "device_profiles.csv", index=False)
    print(f"[+] Extracted {len(dev_profiles_df)} unique device profiles -> device_profiles.csv")

    # 4. Stream Transactions Chunk by Chunk
    customers_set = set()
    cards_dict = {}
    email_domains_set = set()
    billing_regions_set = set()

    tx_out_path = out_dir / "transactions.csv"
    if tx_out_path.exists():
        tx_out_path.unlink()

    first_chunk = True
    total_processed = 0

    print("[*] Streaming transactions.csv...")
    for chunk in load_transactions_chunked(raw_dir, chunksize=chunksize):
        if max_transactions and total_processed >= max_transactions:
            break

        tx_rows = []
        for _, r in chunk.iterrows():
            tid = int(r["TransactionID"])
            cust_id = str(r["customer_id"]).strip()
            card_id = assign_card_id(r, txn_card_lookup)

            customers_set.add(cust_id)

            if card_id not in cards_dict:
                cards_dict[card_id] = {
                    "card_id": card_id,
                    "customer_id": cust_id,
                    "issuer_code": int(r["card1"]),
                    "card_network": str(r["card4"]) if pd.notna(r["card4"]) else "unknown",
                    "card_type": str(r["card6"]) if pd.notna(r["card6"]) else "unknown",
                }

            prof_id = id_map.get(tid, "")

            email_dom = str(r["P_emaildomain"]).strip() if pd.notna(r.get("P_emaildomain")) and str(r["P_emaildomain"]).strip() else ""
            if email_dom:
                email_domains_set.add(email_dom)

            addr1_val = str(r["addr1"]).strip() if pd.notna(r.get("addr1")) and str(r["addr1"]).strip() else ""
            addr2_val = str(r["addr2"]).strip() if pd.notna(r.get("addr2")) and str(r["addr2"]).strip() else "87.0"
            if addr1_val:
                billing_regions_set.add((addr1_val, addr2_val))

            tx_rows.append({
                "txn_id": str(tid),
                "amount": float(r["TransactionAmt"]),
                "ts": str(r["ts"]),
                "channel": str(r["channel"]),
                "risk_score": float(r["risk_score"]),
                "product_cd": str(r["ProductCD"]),
                "addr1": addr1_val,
                "addr2": addr2_val,
                "card_id": card_id,
                "customer_id": cust_id,
                "profile_id": prof_id,
                "email_domain": email_dom,
            })

        chunk_df = pd.DataFrame(tx_rows)
        chunk_df.to_csv(tx_out_path, mode="a", header=first_chunk, index=False)
        first_chunk = False
        total_processed += len(chunk)
        print(f"    ... processed {total_processed} transactions")

    # 5. Save Normalized Entity Files
    customers_df = pd.DataFrame([{"customer_id": c} for c in sorted(customers_set)])
    customers_df.to_csv(out_dir / "customers.csv", index=False)
    print(f"[+] Saved {len(customers_df)} customers -> customers.csv")

    cards_df = pd.DataFrame(list(cards_dict.values()))
    cards_df.to_csv(out_dir / "cards.csv", index=False)
    print(f"[+] Saved {len(cards_df)} cards -> cards.csv")

    email_domains_df = pd.DataFrame([{"domain": d} for d in sorted(email_domains_set)])
    email_domains_df.to_csv(out_dir / "email_domains.csv", index=False)
    print(f"[+] Saved {len(email_domains_df)} email domains -> email_domains.csv")

    billing_regions_df = pd.DataFrame([{"region_code": r[0], "country_code": r[1]} for r in sorted(billing_regions_set)])
    billing_regions_df.to_csv(out_dir / "billing_regions.csv", index=False)
    print(f"[+] Saved {len(billing_regions_df)} billing regions -> billing_regions.csv")

    # 6. Save Closed Cases
    cc_df.to_csv(out_dir / "closed_cases.csv", index=False)
    print(f"[+] Saved {len(cc_df)} closed cases -> closed_cases.csv")

    print("[SUCCESS] Preprocessing for TigerGraph complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic preprocessing for TigerGraph loading")
    parser.add_argument("--raw-dir", type=str, default="HHGOA_IEEE", help="Path to raw dataset directory")
    parser.add_argument("--out-dir", type=str, default="data/graph", help="Path to output directory")
    parser.add_argument("--max-txns", type=int, default=None, help="Optional max transaction limit for testing")
    args = parser.parse_args()

    preprocess_for_tigergraph(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        max_transactions=args.max_txns
    )
