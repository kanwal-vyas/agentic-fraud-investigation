import pytest
from pathlib import Path
from src.data.loader import (
    load_case_pack,
    load_closed_cases,
    load_identity,
    load_transactions_sample,
)
from src.data.validator import (
    validate_dataset_files,
    validate_schemas,
    validate_case_pack_integrity,
)

def test_dataset_files_exist(raw_data_dir):
    res = validate_dataset_files(raw_data_dir)
    assert res["valid"] is True, f"Missing required dataset files: {res}"

def test_dataset_schemas(raw_data_dir):
    res = validate_schemas(raw_data_dir)
    assert res["valid"] is True, f"Schema validation failed: {res['missing_columns']}"

def test_case_pack_integrity(raw_data_dir):
    res = validate_case_pack_integrity(raw_data_dir)
    assert res["valid"] is True
    assert res["case_count"] == 20
    assert res["case_ids_match"] is True
    assert res["no_null_keys"] is True

def test_closed_cases_counts(raw_data_dir):
    cc = load_closed_cases(raw_data_dir)
    assert len(cc) == 5565
    assert (cc["outcome"] == "confirmed_fraud").sum() == 4665
    assert (cc["outcome"] == "cleared").sum() == 900
    assert cc["first_fraud_txn_id"].notna().sum() == 4665
    assert cc["txn_ids"].notna().sum() == 5565

def test_identity_sample(raw_data_dir):
    id_df = load_identity(raw_data_dir, nrows=50)
    assert len(id_df) == 50
    assert "TransactionID" in id_df.columns
    assert "DeviceInfo" in id_df.columns
