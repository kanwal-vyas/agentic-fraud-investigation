import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tigergraph.client import TigerGraphClient
from src.tigergraph.tools import TigerGraphInvestigationTools

def verify_live_graph():
    print("=" * 60)
    print("LIVE TIGERGRAPH DATA & BENCHMARK VERIFICATION")
    print("=" * 60)
    
    client = TigerGraphClient()
    print("Ping:", client.ping())
    
    counts = client.get_vertex_count('*')
    print("\n[1] Final Live Vertex Counts:")
    for vt, cnt in counts.items():
        print(f"  - {vt}: {cnt}")
        
    tools = TigerGraphInvestigationTools(tg_client=client)
    print(f"\nTools is_live(): {tools.is_live()}")
    
    # Verify all 20 benchmark transactions from case_pack.csv
    case_pack_path = Path("data/sample/case_pack.csv")
    df = pd.read_csv(case_pack_path)
    
    print(f"\n[2] Verifying All {len(df)} Benchmark Flagged Transactions from case_pack.csv:")
    all_found = True
    for idx, r in df.iterrows():
        case_id = r["case_id"]
        txn_id = str(r["flagged_txn_id"])
        expected_card = str(r["card_id"])
        expected_cust = str(r["customer_id"])
        
        tx = tools.get_transaction(txn_id)
        if tx is not None:
            print(f"  [{idx+1:02d}/20] {case_id} (Txn {txn_id}): FOUND | Amount=${tx.amount:.2f} | Card={tx.card_id} | Cust={tx.customer_id} | Channel={tx.channel} | Risk={tx.risk_score}")
        else:
            print(f"  [{idx+1:02d}/20] {case_id} (Txn {txn_id}): NOT FOUND [!]")
            all_found = False
            
    print(f"\n>> All 20/20 Benchmark Transactions Verified Live: {all_found}")
    
    # 3. Query representative HHG-003 and HHG-010
    print("\n[3] Querying Representative HHG-003 (Txn 3530164)...")
    hhg003_tx = tools.get_transaction("3530164")
    print(f"  - Transaction Detail: {hhg003_tx}")
    if hhg003_tx:
        hhg003_card_hist = tools.get_card_history(hhg003_tx.card_id, limit=5)
        print(f"  - Card History for {hhg003_tx.card_id}: {hhg003_card_hist.total_txns} total txns, ${hhg003_card_hist.total_amount_usd} spend")
        hhg003_cases = tools.get_historical_cases(customer_id=hhg003_tx.customer_id, top_k=3)
        print(f"  - Historical Cases for {hhg003_tx.customer_id}: {len(hhg003_cases)} case(s)")
        
    print("\n[4] Querying Representative HHG-010 (Txn 3506725)...")
    hhg010_tx = tools.get_transaction("3506725")
    print(f"  - Transaction Detail: {hhg010_tx}")
    if hhg010_tx:
        hhg010_testing = tools.detect_card_testing(hhg010_tx.card_id)
        print(f"  - Card Testing Evidence: detected={hhg010_testing.is_testing_detected}, micro_auth_count={hhg010_testing.micro_auth_count}, confidence={hhg010_testing.heuristic_confidence}")
        hhg010_velocity = tools.detect_velocity(hhg010_tx.card_id)
        print(f"  - Velocity Evidence: txns={hhg010_velocity.txn_count}, total=${hhg010_velocity.total_amount_usd}, is_spike={hhg010_velocity.is_velocity_spike}")
        
    return {
        "counts": counts,
        "all_20_found": all_found,
        "hhg003_tx": hhg003_tx,
        "hhg010_tx": hhg010_tx
    }

if __name__ == "__main__":
    verify_live_graph()
