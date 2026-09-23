import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tigergraph.client import TigerGraphClient
from src.tigergraph.tools import TigerGraphInvestigationTools

TARGET_REMOVALS = {
    "Customer": ["C"],
    "Card": ["C", "C01128-K1", "card_102"],
    "Transaction": ["2987103", "3", "3048997"],
    "DeviceProfile": [
        "0", "2", "4", "5", "6", "7", "8", "9",
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
        "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "e", "g", "h", "i", "m", "nan", "o", "r", "v"
    ],
    "EmailDomain": [
        "a", "b", "c", "e", "f", "g", "h", "i", "j", "l", "m", "n",
        "nan", "o", "p", "q", "r", "s", "t", "v", "w", "y"
    ],
    "BillingRegion": ["1", "2", "3", "4", "5", "nan"],
    "ClosedCase": ["C"],
    "InvestigationCase": ["HHG-BENIGN"],
}

CSV_MAP = {
    "Customer": ("customers.csv", "customer_id"),
    "Card": ("cards.csv", "card_id"),
    "Transaction": ("transactions.csv", "txn_id"),
    "DeviceProfile": ("device_profiles.csv", "profile_id"),
    "EmailDomain": ("email_domains.csv", "domain"),
    "BillingRegion": ("billing_regions.csv", "region_code"),
    "ClosedCase": ("closed_cases_history.csv", "case_id"),
}

def perform_targeted_cleanup():
    print("=" * 70)
    print("STAGE: TARGETED CONTAMINATION CLEANUP & VERIFICATION")
    print("=" * 70)

    client = TigerGraphClient()
    conn = client.get_connection()
    sample_dir = Path("data/sample")

    # STEP 1: SAFETY AUDIT BEFORE DELETION
    print("\n[Step 1] Safety Verification Before Deletion...")
    
    # Load expected CSV sets
    csv_expected: Dict[str, Set[str]] = {}
    for vtype, (fname, colname) in CSV_MAP.items():
        df = pd.read_csv(sample_dir / fname)
        csv_expected[vtype] = set(df[colname].dropna().astype(str).str.strip())
    csv_expected["InvestigationCase"] = set(f"HHG-{i:03d}" for i in range(1, 21))

    # Verify every deletion target is NOT in expected CSV sets
    safety_passed = True
    for vtype, ids in TARGET_REMOVALS.items():
        for target_id in ids:
            if target_id in csv_expected[vtype]:
                print(f"  [CRITICAL SAFETY FAIL] Target {vtype}:{target_id} is in expected CSV data!")
                safety_passed = False

    if not safety_passed:
        print("[!] Aborting due to safety check failure.")
        return

    print(" -> PASS: None of the target deletion IDs belong to the expected benchmark dataset.")

    # Verify targets currently exist in graph
    print("\n[Step 2] Verifying Target IDs Exist in Live Graph...")
    pre_deletion_counts = {}
    for vtype, ids in TARGET_REMOVALS.items():
        cnt = client.get_vertex_count(vtype)
        pre_deletion_counts[vtype] = cnt
        live_raw = conn.getVertices(vtype, limit=max(cnt + 500, 100000))
        live_ids = set(str(v["v_id"]).strip() for v in live_raw)
        missing_targets = [tid for tid in ids if tid not in live_ids]
        present_targets = [tid for tid in ids if tid in live_ids]
        print(f"  {vtype} (Total Live: {cnt}): {len(present_targets)}/{len(ids)} target IDs found live")
        if missing_targets:
            print(f"    Notice: target IDs not in graph: {missing_targets}")

    # STEP 3: EXECUTE TARGETED EXACT-ID DELETION
    print("\n[Step 3] Executing Exact-ID Deletion...")
    total_deleted = 0
    for vtype, ids in TARGET_REMOVALS.items():
        print(f"  Deleting {len(ids)} vertices from '{vtype}'...")
        for vid in ids:
            try:
                res = conn.delVerticesById(vtype, vid)
                total_deleted += 1
            except Exception as e:
                print(f"    Failed deleting {vtype}:{vid} -> {e}")

    print(f" -> Deletion calls executed: {total_deleted}")

    # STEP 4: POST-DELETION EXACT SET COMPARISON & AUDIT
    print("\n[Step 4] Re-fetching exact live IDs & Strict Set Comparison...")
    post_counts = {}
    for vtype, (fname, colname) in CSV_MAP.items():
        cnt = client.get_vertex_count(vtype)
        post_counts[vtype] = cnt
        live_raw = conn.getVertices(vtype, limit=max(cnt + 500, 100000))
        live_ids = set(str(v["v_id"]).strip() for v in live_raw)
        expected = csv_expected[vtype]

        extra = live_ids - expected
        missing = expected - live_ids
        print(f"\n>>> {vtype.upper()} <<<")
        print(f"  Pre-Deletion Count:  {pre_deletion_counts[vtype]}")
        print(f"  Post-Deletion Count: {cnt} (Expected: {len(expected)})")
        print(f"  Extra (Live - CSV):  {len(extra)} -> {list(extra)}")
        print(f"  Missing (CSV - Live):{len(missing)} -> {list(missing)}")

    # InvestigationCase post-check
    vtype = "InvestigationCase"
    cnt = client.get_vertex_count(vtype)
    post_counts[vtype] = cnt
    live_raw = conn.getVertices(vtype, limit=100)
    live_ids = set(str(v["v_id"]).strip() for v in live_raw)
    extra_inv = live_ids - csv_expected[vtype]
    missing_inv = csv_expected[vtype] - live_ids
    print(f"\n>>> {vtype.upper()} <<<")
    print(f"  Pre-Deletion Count:  {pre_deletion_counts[vtype]}")
    print(f"  Post-Deletion Count: {cnt} (Expected: 20)")
    print(f"  Extra (Live - 20):   {len(extra_inv)} -> {list(extra_inv)}")
    print(f"  Missing (20 - Live): {len(missing_inv)} -> {list(missing_inv)}")

    # STEP 5: VERIFY 20 BENCHMARK FLAGGED TRANSACTIONS
    print("\n[Step 5] Verifying All 20 Benchmark Transactions from case_pack.csv...")
    tools = TigerGraphInvestigationTools(tg_client=client)
    case_pack_df = pd.read_csv(sample_dir / "case_pack.csv")
    all_20_tx_present = True
    for idx, r in case_pack_df.iterrows():
        case_id = r["case_id"]
        txn_id = str(r["flagged_txn_id"])
        tx = tools.get_transaction(txn_id)
        if tx:
            print(f"  [{idx+1:02d}/20] {case_id} (Txn {txn_id}): FOUND | Amount=${tx.amount:.2f} | Card={tx.card_id} | Cust={tx.customer_id}")
        else:
            print(f"  [{idx+1:02d}/20] {case_id} (Txn {txn_id}): MISSING [!]")
            all_20_tx_present = False

    print(f"\n>> All 20/20 Benchmark Flagged Transactions Intact: {all_20_tx_present}")

    # STEP 6: VERIFY HHG-003 & HHG-010 LIVE GSQL QUERIES
    print("\n[Step 6] Verifying Representative Queries (HHG-003 & HHG-010)...")
    hhg003 = tools.get_transaction("3530164")
    print(f"  HHG-003 Detail: {hhg003}")
    if hhg003:
        hhg003_hist = tools.get_card_history(hhg003.card_id, limit=5)
        print(f"  HHG-003 Card History: {hhg003_hist.total_txns} txns, ${hhg003_hist.total_amount_usd}")
        hhg003_cases = tools.get_historical_cases(customer_id=hhg003.customer_id, top_k=3)
        print(f"  HHG-003 Historical Cases: {len(hhg003_cases)} case(s)")

    hhg010 = tools.get_transaction("3506725")
    print(f"  HHG-010 Detail: {hhg010}")
    if hhg010:
        hhg010_testing = tools.detect_card_testing(hhg010.card_id)
        print(f"  HHG-010 Card Testing Evidence: detected={hhg010_testing.is_testing_detected}, micro_auth_count={hhg010_testing.micro_auth_count}")
        hhg010_vel = tools.detect_velocity(hhg010.card_id)
        print(f"  HHG-010 Velocity Evidence: txns={hhg010_vel.txn_count}, total=${hhg010_vel.total_amount_usd}, is_spike={hhg010_vel.is_velocity_spike}")

if __name__ == "__main__":
    perform_targeted_cleanup()
