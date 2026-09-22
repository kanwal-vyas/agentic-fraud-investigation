from enum import Enum
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from src.core.constants import PolicyAction, ApprovalRoute

class FraudAssessmentOutcome(str, Enum):
    """Controlled fraud assessment vocabulary."""
    LIKELY_FRAUD = "likely_fraud"
    SUSPICIOUS_BUT_UNCERTAIN = "suspicious_but_uncertain"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    LIKELY_BENIGN = "likely_benign"

class EvidenceSufficiencyState(str, Enum):
    """Explicit evidence sufficiency status."""
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    CONFLICTING = "conflicting"

class UncertaintyLevel(str, Enum):
    """Uncertainty severity level."""
    LOW = "low"
    MODERATE = "moderate"
    MATERIAL = "material"
    HIGH = "high"

class ReasoningFactor(BaseModel):
    """An individual auditable reasoning factor influencing the assessment."""
    dimension: Literal["transaction", "behavioral", "network", "historical", "policy", "contradictory"]
    factor: str
    impact: Literal["increases_suspicion", "decreases_suspicion", "neutral"]
    weight: float = 1.0
    source_id: str

class UncertaintyAssessment(BaseModel):
    """Structured uncertainty model identifying reasons for doubt or ambiguity."""
    level: UncertaintyLevel
    reasons: List[str] = Field(default_factory=list)
    conflicting_factors: List[str] = Field(default_factory=list)

class EvidenceRequest(BaseModel):
    """A controlled, policy-compliant request for additional investigative evidence."""
    request_id: str
    request_type: Literal[
        "customer_validation",
        "step_up_auth",
        "analyst_info",
        "secondary_card_check",
        "additional_txn_history"
    ]
    reason: str
    evidence_gap_addressed: str
    expected_information_gain: float = Field(ge=0.0, le=1.0)
    rationale: str
    policy_reference: str
    approval_required: bool = False
    status: Literal["planned", "pending", "executed", "fulfilled"] = "planned"

class NextBestAction(BaseModel):
    """Next Best Action recommendation adhering to strict recommendation/execution separation."""
    action: PolicyAction
    rationale: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    policy_references: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    approval_required: bool
    approval_route: ApprovalRoute
    execution_status: Literal["recommended", "authorized", "executed", "pending_approval"] = "recommended"
    alternatives_considered: List[str] = Field(default_factory=list)

class StopDecision(BaseModel):
    """Formal investigation stop condition evaluation."""
    should_stop: bool
    reason: str
    remaining_uncertainty: UncertaintyLevel
    unresolved_gaps: List[str] = Field(default_factory=list)
    next_step: str

class StructuredExplanation(BaseModel):
    """Human-auditable structured 5-part investigation explanation."""
    why_suspicious: List[str] = Field(default_factory=list)
    why_not_certain: List[str] = Field(default_factory=list)
    why_request_more_evidence: List[str] = Field(default_factory=list)
    why_action: List[str] = Field(default_factory=list)
    why_stop: List[str] = Field(default_factory=list)

class InvestigationAssessment(BaseModel):
    """
    Comprehensive structured assessment combining fraud outcome, confidence,
    uncertainty, evidence sufficiency, NBA, policy decisions, and explanation.
    """
    case_id: str
    fraud_assessment: FraudAssessmentOutcome
    suspected_patterns: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: UncertaintyAssessment
    evidence_sufficiency: EvidenceSufficiencyState
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    reasoning_factors: List[ReasoningFactor] = Field(default_factory=list)
    evidence_requests: List[EvidenceRequest] = Field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    next_best_action: NextBestAction
    stop_decision: StopDecision
    explanation: StructuredExplanation
    requires_human_approval: bool
