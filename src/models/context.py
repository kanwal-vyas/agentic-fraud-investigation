from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class SourceProvenance(BaseModel):
    """Explicit provenance metadata for any piece of retrieved context."""
    source_type: Literal["closed_case", "policy", "regulation", "graph"]
    source_id: str
    relevance_score: float
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class HistoricalCaseMatch(BaseModel):
    """A retrieved historical case from the 5,565 closed bank investigations repository."""
    case_id: str
    customer_id: str
    card_id: str
    outcome: Literal["confirmed_fraud", "cleared"]
    pattern: str
    exposure_usd: float
    relevance_score: float
    similarity_reasons: List[str] = Field(default_factory=list)
    actions_taken: str
    analyst_notes: str

class PolicyRuleMatch(BaseModel):
    """An applicable bank fraud policy rule grounded in official rules R1-R10."""
    rule_id: str
    name: str
    description: str
    triggering_evidence: List[str]
    applicable_condition: str
    recommended_actions: List[str]
    approval_level: str = "auto"
    source_ref: str = "Bank Fraud Policy Manual (Rules R1-R10)"

class RegulatoryReferenceMatch(BaseModel):
    """Applicable regulatory compliance mandate or industry standard."""
    regulation_id: str
    title: str
    section: str
    excerpt: str
    applicability: str
    mandate_summary: str

class EvidenceItem(BaseModel):
    """A granular piece of investigative evidence supporting hypothesis formation."""
    source_id: str
    statement: str
    confidence: float
    category: Literal["graph_fact", "historical_precedent", "policy_directive", "regulatory_mandate"]

class ContradictoryEvidenceItem(BaseModel):
    """Evidence pointing towards a benign or legitimate explanation rather than fraud."""
    evidence: str
    benign_explanation: str
    source_id: str
    weight: float = 0.5

class EvidenceGapItem(BaseModel):
    """Unresolved information required to complete a definitive investigation."""
    missing_information: str
    recommended_verification: str
    urgency: Literal["low", "medium", "high"] = "medium"

class InvestigationContext(BaseModel):
    """
    Comprehensive synthesized investigation context grounding the future AI agent.
    Combines TigerGraph structured evidence, historical precedent, bank policy rules,
    regulatory standards, supporting & contradictory evidence, and explicit provenance.
    """
    case_id: str
    opened_at: str
    trigger_type: str
    trigger_text: str
    flagged_txn_id: int
    card_id: str
    customer_id: str
    model_risk_score: float
    graph_evidence_summary: List[str] = Field(default_factory=list)
    detected_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    historical_cases_confirmed_fraud: List[HistoricalCaseMatch] = Field(default_factory=list)
    historical_cases_cleared: List[HistoricalCaseMatch] = Field(default_factory=list)
    applicable_policies: List[PolicyRuleMatch] = Field(default_factory=list)
    regulatory_references: List[RegulatoryReferenceMatch] = Field(default_factory=list)
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    contradictory_evidence: List[ContradictoryEvidenceItem] = Field(default_factory=list)
    evidence_gaps: List[EvidenceGapItem] = Field(default_factory=list)
    source_attributions: List[SourceProvenance] = Field(default_factory=list)
