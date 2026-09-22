from typing import Optional, List
from pydantic import BaseModel, Field

class CustomerVertex(BaseModel):
    customer_id: str

class CardVertex(BaseModel):
    card_id: str
    customer_id: str
    card1: int
    card4: Optional[str] = None  # network
    card6: Optional[str] = None  # type (credit/debit)

class DeviceProfileVertex(BaseModel):
    profile_id: str  # Composite: DeviceInfo | OS | Browser | Screen
    device_info: Optional[str] = ""
    os: Optional[str] = ""
    browser: Optional[str] = ""
    screen: Optional[str] = ""
    device_type: Optional[str] = ""

class EmailDomainVertex(BaseModel):
    domain: str

class BillingRegionVertex(BaseModel):
    region_code: str  # addr1 string
    country_code: Optional[str] = "87.0"  # addr2 string

class TransactionVertex(BaseModel):
    txn_id: str  # TransactionID as string
    amount: float
    ts: str  # YYYY-MM-DD HH:MM:SS
    channel: str  # in_person / online
    risk_score: float
    product_cd: str
    addr1: Optional[str] = None
    addr2: Optional[str] = None

class ClosedCaseVertex(BaseModel):
    case_id: str
    customer_id: str
    card_id: str
    opened_at: str
    closed_at: str
    outcome: str
    pattern: str
    exposure_usd: float
    n_txns: int
    analyst_notes: str

class CaseVertex(BaseModel):
    case_id: str
    status: str
    verdict: str
    fraud_probability: float
    pattern: str
    pattern_description: Optional[str] = ""
    exposure_usd: float
    summary: str
    created_at: str
