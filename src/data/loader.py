import os
from pathlib import Path
from typing import Optional, List, Generator, Union
import pandas as pd
from src.core.config import settings
from src.models.dataset import CasePackRecord, ClosedCaseRecord

def get_data_path(filename: str, data_dir: Optional[Union[str, Path]] = None) -> Path:
    base = Path(data_dir) if data_dir else settings.data_dir
    return base / filename

def load_case_pack(data_dir: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    path = get_data_path("case_pack.csv", data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Case pack file not found at {path}")
    return pd.read_csv(path)

def load_closed_cases(data_dir: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    path = get_data_path("closed_cases_history.csv", data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Closed cases history file not found at {path}")
    return pd.read_csv(path)

def load_identity(data_dir: Optional[Union[str, Path]] = None, nrows: Optional[int] = None) -> pd.DataFrame:
    path = get_data_path("identity.csv", data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Identity file not found at {path}")
    return pd.read_csv(path, nrows=nrows)

def load_transactions_chunked(
    data_dir: Optional[Union[str, Path]] = None,
    chunksize: int = 50000,
    usecols: Optional[List[str]] = None
) -> Generator[pd.DataFrame, None, None]:
    path = get_data_path("transactions.csv", data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Transactions file not found at {path}")
    for chunk in pd.read_csv(path, chunksize=chunksize, usecols=usecols, low_memory=False):
        yield chunk

def load_transactions_sample(
    data_dir: Optional[Union[str, Path]] = None,
    nrows: int = 10000,
    usecols: Optional[List[str]] = None
) -> pd.DataFrame:
    path = get_data_path("transactions.csv", data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Transactions file not found at {path}")
    return pd.read_csv(path, nrows=nrows, usecols=usecols, low_memory=False)

def load_flagged_transactions(data_dir: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    cp = load_case_pack(data_dir)
    flagged_ids = set(cp["flagged_txn_id"].tolist())
    
    matched_chunks = []
    for chunk in load_transactions_chunked(data_dir=data_dir, chunksize=100000):
        m = chunk[chunk["TransactionID"].isin(flagged_ids)]
        if not m.empty:
            matched_chunks.append(m)
            if sum(len(c) for c in matched_chunks) == len(flagged_ids):
                break
    if matched_chunks:
        return pd.concat(matched_chunks, ignore_index=True)
    return pd.DataFrame()
