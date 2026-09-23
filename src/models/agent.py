from enum import Enum
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from src.core.constants import PolicyAction, ApprovalRoute
from src.models.context import InvestigationContext, HistoricalCaseMatch, PolicyRuleMatch
from src.models.reasoning import (
    InvestigationAssessment,
    EvidenceRequest,
    NextBestAction,
    StopDecision,
    StructuredExplanation,
    FraudAssessmentOutcome
)

class TriggerType(str, Enum):
    """Supported trigger types for starting an investigation."""
    RISK_SCORE = "risk_score"
    CUSTOMER_REPORT = "customer_report"
    ANALYST_REQUEST = "analyst_request"
    CUSTOMER_CONFIRMED = "customer_confirmed"

class InvestigationTrigger(BaseModel):
    """Initial trigger payload initiating a fraud case investigation."""
    case_id: str
    trigger_type: TriggerType
    transaction_id: int
    customer_id: str
    card_id: str
    model_risk_score: float = 0.0
    trigger_details: str = ""
    opened_at: str = ""

class AgentActionType(str, Enum):
    """Allowed structured decision types for the agent planner."""
    CALL_TOOL = "CALL_TOOL"
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    ASSESS = "ASSESS"
    STOP = "STOP"

class AgentToolCallDecision(BaseModel):
    """Structured schema for LLM / Planner tool invocation decisions."""
    action: AgentActionType
    tool: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str
    confidence: float = 1.0

class InvestigationStep(BaseModel):
    """Auditable trace entry representing an individual investigation action."""
    step_number: int
    reason: str
    tool: str
    input_args: Dict[str, Any] = Field(default_factory=dict)
    result_summary: str
    evidence_ids: List[str] = Field(default_factory=list)
    timestamp: str = ""
    outcome: Literal["success", "error", "no_data", "unsupported"] = "success"

class WorkingInvestigationState(BaseModel):
    """
    In-case working memory maintained dynamically across the investigation lifecycle.
    Updated incrementally after each tool execution.
    """
    trigger: InvestigationTrigger
    step_count: int = 0
    tools_called: List[str] = Field(default_factory=list)
    collected_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    retrieved_cases: List[HistoricalCaseMatch] = Field(default_factory=list)
    applicable_policies: List[PolicyRuleMatch] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    assessment_checkpoints: List[InvestigationAssessment] = Field(default_factory=list)
    requested_evidence: List[EvidenceRequest] = Field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    actions_considered: List[str] = Field(default_factory=list)
    is_stopped: bool = False

class InvestigationResult(BaseModel):
    """
    Comprehensive machine-readable output produced at the conclusion of an investigation.
    Maintains strict separation between recommended actions and actual execution.
    """
    case_id: str
    trigger: InvestigationTrigger
    investigation_steps: List[InvestigationStep] = Field(default_factory=list)
    evidence_collected: List[Dict[str, Any]] = Field(default_factory=list)
    assessment_history: List[InvestigationAssessment] = Field(default_factory=list)
    final_assessment: InvestigationAssessment
    evidence_requests: List[EvidenceRequest] = Field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    next_best_action: NextBestAction
    approval_required: bool
    approval_route: ApprovalRoute
    execution_status: Literal["recommended", "authorized", "executed", "pending_approval"] = "recommended"
    stop_decision: StopDecision
    explanation: StructuredExplanation
    total_tool_calls: int = 0
    total_steps: int = 0
    persisted_case_id: Optional[str] = None
    written_to_graph: bool = False
    sar_record: Optional[Any] = None

