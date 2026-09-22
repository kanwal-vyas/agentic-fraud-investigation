from typing import Optional, List
from pydantic import BaseModel, Field

class CasePackRecord(BaseModel):
    case_id: str
    opened_at: str
    trigger_type: str
    trigger_text: str
    flagged_txn_id: int
    card_id: str
    customer_id: str
    risk_score: Optional[float] = None

class ClosedCaseRecord(BaseModel):
    case_id: str
    customer_id: str
    card_id: str
    opened_at: str
    closed_at: str
    outcome: str
    pattern: str
    first_fraud_txn_id: Optional[float] = None
    txn_ids: str
    n_txns: int
    exposure_usd: float
    connected_card_ids: Optional[str] = None
    actions_taken: str
    report_filed: Optional[str] = None
    analyst_notes: str

class IdentityRecord(BaseModel):
    TransactionID: int
    DeviceInfo: Optional[str] = None
    DeviceType: Optional[str] = None
    id_15: Optional[str] = None  # New / Found / Unknown
    id_23: Optional[str] = None  # IP_PROXY:*
    id_30: Optional[str] = None  # OS
    id_31: Optional[str] = None  # Browser
    id_33: Optional[str] = None  # Screen resolution
    id_34: Optional[str] = None

class TransactionRecord(BaseModel):
    TransactionID: int
    customer_id: str
    card1: int
    card2: Optional[float] = None
    card3: Optional[float] = None
    card4: Optional[str] = None  # visa, mastercard, etc.
    card5: Optional[float] = None
    card6: Optional[str] = None  # debit, credit
    TransactionAmt: float
    TransactionDT: int
    ts: str
    ProductCD: str
    channel: str  # in_person, online
    risk_score: float
    addr1: Optional[float] = None  # Billing region
    addr2: Optional[float] = None  # Country code
    P_emaildomain: Optional[str] = None
    R_emaildomain: Optional[str] = None
