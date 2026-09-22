import pytest
from pathlib import Path
import pandas as pd
from src.data.validator import validate_dataset_files, validate_schemas, validate_case_pack_integrity

def test_sample_files_exist(sample_data_dir):
    assert sample_data_dir.exists(), "Sample data directory does not exist"
    for fname in ["customers.csv", "cards.csv", "device_profiles.csv", "email_domains.csv", "billing_regions.csv", "transactions.csv", "case_pack.csv", "closed_cases_history.csv"]:
        fpath = sample_data_dir / fname
        assert fpath.exists(), f"Missing sample file {fname}"
        assert fpath.stat().st_size > 0, f"Sample file {fname} is empty"

def test_sample_case_pack_integrity(sample_data_dir):
    res = validate_case_pack_integrity(sample_data_dir)
    assert res["valid"] is True
    assert res["case_count"] == 20

def test_sample_entities_integrity(sample_data_dir):
    cust_df = pd.read_csv(sample_data_dir / "customers.csv")
    cards_df = pd.read_csv(sample_data_dir / "cards.csv")
    tx_df = pd.read_csv(sample_data_dir / "transactions.csv")
    
    assert len(cust_df) > 0
    assert len(cards_df) > 0
    assert len(tx_df) > 0
    
    # All card customers should exist in customers
    assert set(cards_df["customer_id"]).issubset(set(cust_df["customer_id"]))
    
    # All transaction cards should exist in cards
    assert set(tx_df["card_id"]).issubset(set(cards_df["card_id"]))
