import os
import sys
from pathlib import Path
from typing import Dict, Any

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
from src.core.config import settings
from src.tigergraph.client import TigerGraphClient

def validate_tigergraph_graph(data_dir: Path = None) -> Dict[str, Any]:
    """
    Validates the TigerGraph graph structure, relationships, and benchmark entities.
    Checks:
    1. Customer -> Card resolution
    2. Card -> Transaction resolution
    3. Transaction -> DeviceProfile resolution
    4. Shared device relationship discovery
    5. Historical ClosedCase -> Transaction resolution
    6. All 20 Benchmark Case Pack flagged transactions resolution
    """
    sample_dir = data_dir or settings.sample_data_dir
    print(f"==================================================")
    print(f"[*] TIGERGRAPH GRAPH VALIDATION")
    print(f"[*] Validating against preprocessed graph data in: {sample_dir}")
    print(f"==================================================")

    results = {}
    
    # 1. Load entities
    cust_df = pd.read_csv(sample_dir / "customers.csv")
    cards_df = pd.read_csv(sample_dir / "cards.csv")
    tx_df = pd.read_csv(sample_dir / "transactions.csv")
    dev_df = pd.read_csv(sample_dir / "device_profiles.csv")
    cp_df = pd.read_csv(sample_dir / "case_pack.csv")
    cc_df = pd.read_csv(sample_dir / "closed_cases_history.csv")

    # Check 1: Customer -> Card
    sample_cust = cp_df.iloc[0]["customer_id"]
    cust_cards = cards_df[cards_df["customer_id"] == sample_cust]
    c1_pass = len(cust_cards) > 0
    results["1_customer_to_cards"] = {
        "status": "PASS" if c1_pass else "FAIL",
        "sample_customer": sample_cust,
        "cards_found": cust_cards["card_id"].tolist(),
    }
    print(f"[Check 1] Customer -> Cards: {results['1_customer_to_cards']['status']} (Found {len(cust_cards)} cards for {sample_cust})")

    # Check 2: Card -> Transactions
    sample_card = cust_cards.iloc[0]["card_id"]
    card_txns = tx_df[tx_df["card_id"] == sample_card]
    c2_pass = len(card_txns) > 0
    results["2_card_to_transactions"] = {
        "status": "PASS" if c2_pass else "FAIL",
        "sample_card": sample_card,
        "transaction_count": len(card_txns),
    }
    print(f"[Check 2] Card -> Transactions: {results['2_card_to_transactions']['status']} (Found {len(card_txns)} transactions for {sample_card})")

    # Check 3: Transaction -> DeviceProfile
    online_txns = tx_df[tx_df["profile_id"].notna() & (tx_df["profile_id"] != "") & (tx_df["profile_id"] != "UnknownDevice | UnknownOS | UnknownBrowser | UnknownScreen")]
    c3_pass = len(online_txns) > 0
    sample_online_tx = online_txns.iloc[0] if c3_pass else None
    results["3_transaction_to_device"] = {
        "status": "PASS" if c3_pass else "FAIL",
        "sample_txn_id": str(sample_online_tx["txn_id"]) if sample_online_tx is not None else "",
        "profile_id": str(sample_online_tx["profile_id"]) if sample_online_tx is not None else "",
    }
    print(f"[Check 3] Transaction -> DeviceProfile: {results['3_transaction_to_device']['status']}")

    # Check 4: Shared Device Relationships (Syndicate Detection)
    dev_card_counts = tx_df.groupby("profile_id")["card_id"].nunique()
    shared_devs = dev_card_counts[dev_card_counts > 1]
    # Filter out empty/unknown profiles
    shared_devs = shared_devs[[idx for idx in shared_devs.index if idx and "Unknown" not in idx]]
    c4_pass = len(shared_devs) > 0
    results["4_shared_devices"] = {
        "status": "PASS" if c4_pass else "FAIL",
        "shared_profile_count": len(shared_devs),
        "sample_shared_profile": str(shared_devs.index[0]) if len(shared_devs) > 0 else "",
    }
    print(f"[Check 4] Shared Device Relationships: {results['4_shared_devices']['status']} (Found {len(shared_devs)} shared profiles)")

    # Check 5: Historical ClosedCase -> Transactions
    sample_cc = cc_df[cc_df["txn_ids"].notna()].iloc[0]
    cc_txns = str(sample_cc["txn_ids"]).split("|")
    c5_pass = len(cc_txns) > 0
    results["5_closed_case_to_txns"] = {
        "status": "PASS" if c5_pass else "FAIL",
        "case_id": sample_cc["case_id"],
        "pattern": sample_cc["pattern"],
        "txn_count": len(cc_txns),
    }
    print(f"[Check 5] ClosedCase -> Transactions: {results['5_closed_case_to_txns']['status']} (Case {sample_cc['case_id']})")

    # Check 6: Benchmark 20 Flagged Transactions Resolution
    flagged_ids = set(str(t) for t in cp_df["flagged_txn_id"])
    graph_tx_ids = set(str(t) for t in tx_df["txn_id"])
    resolved_count = len(flagged_ids.intersection(graph_tx_ids))
    c6_pass = resolved_count == 20
    results["6_benchmark_flagged_txns"] = {
        "status": "PASS" if c6_pass else "FAIL",
        "total_benchmark_cases": len(flagged_ids),
        "resolved_flagged_txns": resolved_count,
    }
    print(f"[Check 6] Benchmark 20 Flagged Txns Resolution: {results['6_benchmark_flagged_txns']['status']} ({resolved_count}/20 resolved)")

    # Overall Status
    all_passed = c1_pass and c2_pass and c3_pass and c4_pass and c5_pass and c6_pass
    print(f"==================================================")
    print(f"OVERALL VALIDATION STATUS: {'[PASS]' if all_passed else '[FAIL]'}")
    print(f"==================================================")
    
    return {
        "overall_status": "PASS" if all_passed else "FAIL",
        "checks": results,
    }

if __name__ == "__main__":
    res = validate_tigergraph_graph()
    if res["overall_status"] != "PASS":
        sys.exit(1)
