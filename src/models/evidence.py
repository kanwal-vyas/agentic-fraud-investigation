from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.core.constants import FraudPattern

class TransactionDetail(BaseModel):
    txn_id: str
    amount: float
    ts: str
    channel: str
    risk_score: float  # Model input score (NOT ground-truth verdict)
    product_cd: str
    addr1: Optional[str] = ""
    addr2: Optional[str] = "87.0"
    card_id: str
    customer_id: str
    card_network: Optional[str] = "unknown"
    card_type: Optional[str] = "unknown"
    profile_id: Optional[str] = ""
    email_domain: Optional[str] = ""

class CustomerHistoryEvidence(BaseModel):
    customer_id: str
    transaction_count: int
    total_spend_usd: float
    avg_amount_usd: float
    cards_used: List[str]
    devices_used: List[str]
    recent_transactions: List[TransactionDetail]

class CardHistoryEvidence(BaseModel):
    card_id: str
    customer_id: str
    issuer_code: int
    card_network: str
    card_type: str
    total_txns: int
    total_amount_usd: float
    avg_amount_usd: float
    max_amount_usd: float
    transactions: List[TransactionDetail]

class GraphNode(BaseModel):
    id: str
    type: str  # Customer, Card, Transaction, DeviceProfile, BillingRegion, EmailDomain, ClosedCase
    attributes: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # OWNS_CARD, PERFORMED_TXN, USED_DEVICE, BILLED_IN, PURCHASER_EMAIL, ON_CARD, INVOLVES
    attributes: Dict[str, Any] = Field(default_factory=dict)

class NeighborhoodEvidence(BaseModel):
    center_txn_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class SharedDeviceEvidence(BaseModel):
    profile_id: str
    device_info: str
    is_shared: bool
    connected_customers: List[str]
    connected_cards: List[str]
    total_txns_on_device: int

class CardTestingEvidence(BaseModel):
    card_id: str
    is_testing_detected: bool
    micro_auth_count: int
    rapid_sequence_count: int
    micro_auth_transactions: List[TransactionDetail]
    subsequent_large_purchases: List[TransactionDetail]
    time_window_minutes: float
    heuristic_confidence: float = 0.0

class VelocityEvidence(BaseModel):
    entity_id: str  # card_id or customer_id
    time_window_hours: float
    txn_count: int
    total_amount_usd: float
    avg_amount_usd: float
    max_amount_usd: float
    is_velocity_spike: bool
    rapid_cluster_count: int

class RegionalAnomalyEvidence(BaseModel):
    txn_id: str
    card_id: str
    current_addr1: str
    historical_home_addr1: str
    is_anomaly: bool
    channel: str
    prior_home_txns_count: int
    recent_remote_txns_count: int
    heuristic_confidence: float = 0.0

class HistoricalCaseEvidence(BaseModel):
    case_id: str
    customer_id: str
    card_id: str
    opened_at: str
    closed_at: str
    outcome: str  # confirmed_fraud / cleared
    pattern: str
    exposure_usd: float
    n_txns: int
    analyst_notes: str
    similarity_reason: str

class ConnectedCardsEvidence(BaseModel):
    card_id: str
    connected_cards: List[str]
    connection_reasons: Dict[str, str]  # card_id -> reason (e.g. "shared_device: SM-G892A", "same_customer")
    shared_device_profiles: List[str]

class PatternDetectionResult(BaseModel):
    pattern: FraudPattern
    detected: bool
    heuristic_confidence: float = Field(ge=0.0, le=1.0)
    claims: List[str]
    supporting_txn_ids: List[str]
    supporting_entity_ids: List[str]
    rationale: str
