from typing import List, Optional
from pydantic import BaseModel, Field
from src.core.constants import CaseStatus, CaseVerdict, FraudPattern, EvidenceSource, EvidenceRequestType, PolicyAction, ApprovalRoute

class EvidenceItem(BaseModel):
    claim: str
    source: EvidenceSource
    ref: str
    entity_ids: List[str] = Field(default_factory=list)

class CaseData(BaseModel):
    status: CaseStatus
    verdict: CaseVerdict
    fraud_probability: float = Field(ge=0.0, le=1.0)
    pattern: FraudPattern
    pattern_description: str = ""
    affected_txn_ids: List[str] = Field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: List[str] = Field(default_factory=list)
    connected_device_profiles: List[str] = Field(default_factory=list)
    exposure_usd: float = Field(default=0.0, ge=0.0)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    similar_prior_cases: List[str] = Field(default_factory=list)
    summary: str
    written_to_graph: bool = False
    graph_case_id: str = ""

class SARData(BaseModel):
    file: bool
    reason: str
    narrative: str = ""
    subjects: List[str] = Field(default_factory=list)
    total_amount_usd: float = 0.0
    activity_dates: List[str] = Field(default_factory=list)

class ActionItem(BaseModel):
    action: PolicyAction
    route: ApprovalRoute
    reason: str

class NextBestActions(BaseModel):
    initial: List[ActionItem] = Field(default_factory=list)
    final: List[ActionItem] = Field(default_factory=list)
    what_changed: str = "nothing"

class EvidenceRequest(BaseModel):
    type: EvidenceRequestType
    asked_after_step: int
    assumed_response: str

class CaseAnswerSubmission(BaseModel):
    case_id: str
    case: CaseData
    evidence_requests: List[EvidenceRequest] = Field(default_factory=list)
    next_best_actions: NextBestActions
    sar: SARData
    stop_reason: str
    tool_calls: int = 0
    tokens: int = 0
    latency_s: float = 0.0
