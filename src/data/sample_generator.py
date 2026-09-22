import os
from pathlib import Path
from typing import Optional, Union
import pandas as pd
from src.core.config import settings
from src.data.loader import (
    load_case_pack,
    load_closed_cases,
    load_identity,
    load_transactions_chunked,
    get_data_path,
)
from src.data.preprocessor import preprocess_subdataset

def generate_sample_dataset(
    output_dir: Optional[Union[str, Path]] = None,
    raw_dir: Optional[Union[str, Path]] = None,
    sample_closed_cases_count: int = 50,
) -> Path:
    """
    Creates a small, fully self-contained representative dataset in output_dir.
    Includes:
    - All 20 benchmark case customers & flagged transactions
    - All transactions for those 20 customers
    - A sample of closed cases spanning all fraud patterns
    - All transactions associated with those sample closed cases
    - Matching identity records
    """
    out_path = Path(output_dir) if output_dir else settings.sample_data_dir
    out_path.mkdir(parents=True, exist_ok=True)
    
    cp = load_case_pack(raw_dir)
    cc = load_closed_cases(raw_dir)
    
    # 1. Select representative closed cases (at least 2 of each pattern)
    sampled_cc_list = []
    for pattern, group in cc.groupby("pattern"):
        sampled_cc_list.append(group.head(5))
    sampled_cc = pd.concat(sampled_cc_list, ignore_index=True)
    
    # Add any closed cases that involve the benchmark case customers
    cp_custs = set(cp["customer_id"].tolist())
    related_cc = cc[cc["customer_id"].isin(cp_custs)]
    sample_cc_final = pd.concat([sampled_cc, related_cc]).drop_duplicates(subset=["case_id"])
    
    # Collect all customer IDs and transaction IDs needed
    target_custs = set(cp["customer_id"].tolist()) | set(sample_cc_final["customer_id"].tolist())
    
    target_txns = set(cp["flagged_txn_id"].tolist())
    for _, r in sample_cc_final.iterrows():
        tx_str = str(r.get("txn_ids", ""))
        if tx_str and pd.notna(tx_str):
            for t in tx_str.split("|"):
                if t.strip():
                    try:
                        target_txns.add(int(float(t.strip())))
                    except ValueError:
                        pass
        first_t = r.get("first_fraud_txn_id")
        if pd.notna(first_t):
            try:
                target_txns.add(int(float(first_t)))
            except ValueError:
                pass
                
    print(f"[Sample Generator] Target customers: {len(target_custs)}, Target explicit txns: {len(target_txns)}")
    
    # 2. Extract transactions for target customers
    collected_txns = []
    for chunk in load_transactions_chunked(data_dir=raw_dir, chunksize=100000):
        m = chunk[chunk["customer_id"].isin(target_custs) | chunk["TransactionID"].isin(target_txns)]
        if not m.empty:
            collected_txns.append(m)
            
    sample_tx_df = pd.concat(collected_txns, ignore_index=True).drop_duplicates(subset=["TransactionID"])
    print(f"[Sample Generator] Collected {len(sample_tx_df)} sample transactions.")
    
    # 3. Extract matching identity records
    sample_txn_ids = set(sample_tx_df["TransactionID"].tolist())
    raw_id = load_identity(raw_dir)
    sample_id_df = raw_id[raw_id["TransactionID"].isin(sample_txn_ids)].copy()
    print(f"[Sample Generator] Collected {len(sample_id_df)} sample identity records.")
    
    # 4. Save raw sample CSVs
    cp.to_csv(out_path / "case_pack.csv", index=False)
    sample_cc_final.to_csv(out_path / "closed_cases_history.csv", index=False)
    sample_tx_df.to_csv(out_path / "transactions.csv", index=False)
    sample_id_df.to_csv(out_path / "identity.csv", index=False)
    
    # 5. Generate and save preprocessed normalized entity tables
    entities = preprocess_subdataset(
        tx_df=sample_tx_df,
        id_df=sample_id_df,
        cc_df=sample_cc_final,
        cp_df=cp
    )
    
    for name, df in entities.items():
        df.to_csv(out_path / f"{name}.csv", index=False)
        print(f"[Sample Generator] Saved preprocessed entity {name}.csv ({len(df)} rows)")
        
    return out_path

if __name__ == "__main__":
    generate_sample_dataset()
