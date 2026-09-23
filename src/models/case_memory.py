from enum import Enum
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from src.core.constants import PolicyAction, ApprovalRoute, FraudPattern, CaseVerdict

class CaseLifecycleStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    REASSESSED = "REASSESSED"
    ACTION_PENDING_APPROVAL = "ACTION_PENDING_APPROVAL"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"

class ActionExecutionStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"

class PersistedEvidenceItem(BaseModel):
    statement: str
    source_id: str
    source_type: str  # graph, closed_case, policy, customer, external
    category: str = "graph_fact"  # graph_fact, historical_precedent, contradictory, customer_statement
    weight: float = 1.0
    confidence: float = 1.0
    entity_ids: List[str] = Field(default_factory=list)
    timestamp: str = ""

class CaseDecisionRecord(BaseModel):
    rules_evaluated: List[str] = Field(default_factory=list)
    permitted: bool = True
    required_action: Optional[str] = None
    approval_route: str = "auto"
    approval_required: bool = False
    violations: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    timestamp: str = ""

class ActionAuditRecord(BaseModel):
    action: str
    execution_status: ActionExecutionStatus = ActionExecutionStatus.RECOMMENDED
    approval_route: str = "auto"
    approval_required: bool = False
    rationale: str = ""
    policy_references: List[str] = Field(default_factory=list)
    authorized_by: Optional[str] = None
    executed_at: Optional[str] = None
    execution_details: Dict[str, Any] = Field(default_factory=dict)

class SARCaseRecord(BaseModel):
    sar_required: bool = False
    sar_status: Literal["NOT_REQUIRED", "RECOMMENDED", "PENDING_REVIEW", "FILED"] = "NOT_REQUIRED"
    sar_rationale: str = ""
    exposure_usd: float = 0.0
    regulatory_references: List[str] = Field(default_factory=list)
    approval_route: str = "L2"
    filing_status: Literal["unfiled", "prepared", "submitted"] = "unfiled"
    narrative: str = ""

class ReassessmentRecord(BaseModel):
    timestamp: str
    prior_assessment: str
    new_assessment: str
    evidence_received: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""

class CaseMemoryRecord(BaseModel):
    case_id: str
    benchmark_case_id: Optional[str] = None
    customer_id: str
    card_id: str
    triggering_txn_id: int
    trigger_type: str
    created_at: str
    updated_at: str
    status: CaseLifecycleStatus = CaseLifecycleStatus.OPEN
    fraud_assessment: str = "insufficient_evidence"  # likely_fraud, suspicious_but_uncertain, likely_benign, insufficient_evidence
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty_level: str = "LOW"
    uncertainty_reasons: List[str] = Field(default_factory=list)
    evidence_items: List[PersistedEvidenceItem] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    fraud_patterns_identified: List[str] = Field(default_factory=list)
    supporting_findings: List[str] = Field(default_factory=list)
    contradictory_findings: List[str] = Field(default_factory=list)
    policy_rules_evaluated: List[str] = Field(default_factory=list)
    policy_decision: CaseDecisionRecord = Field(default_factory=CaseDecisionRecord)
    recommended_nba: str = "MONITOR_CARD"
    nba_rationale: str = ""
    approval_required: bool = False
    approval_route: str = "auto"
    execution_status: ActionExecutionStatus = ActionExecutionStatus.RECOMMENDED
    actions_actually_executed: List[ActionAuditRecord] = Field(default_factory=list)
    evidence_requests: List[Dict[str, Any]] = Field(default_factory=list)
    reassessments: List[ReassessmentRecord] = Field(default_factory=list)
    final_outcome: str = "pending"  # closed_fraud, closed_legitimate, escalated, pending
    sar_data: SARCaseRecord = Field(default_factory=SARCaseRecord)
    related_historical_case_ids: List[str] = Field(default_factory=list)
    related_entities: Dict[str, List[str]] = Field(default_factory=dict)
    summary: str = ""
    written_to_graph: bool = False
    graph_case_id: Optional[str] = None
