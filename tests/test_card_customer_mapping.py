import pytest
import pandas as pd
from src.data.loader import load_case_pack, load_flagged_transactions

def test_flagged_transactions_lookup(raw_data_dir):
    cp = load_case_pack(raw_data_dir)
    flagged_txns = load_flagged_transactions(raw_data_dir)
    
    assert len(flagged_txns) == 20, f"Expected 20 flagged transactions, found {len(flagged_txns)}"
    
    merged = pd.merge(cp, flagged_txns, left_on="flagged_txn_id", right_on="TransactionID", suffixes=("_cp", "_tx"))
    assert len(merged) == 20
    
    # Verify customer ID equality
    assert (merged["customer_id_cp"] == merged["customer_id_tx"]).all()
    
    # Verify card_id structure
    for card_id in merged["card_id"]:
        assert "-" in card_id
        prefix, suffix = card_id.split("-")
        assert prefix.startswith("C")
        assert suffix in ["K1", "K2", "K3"]
