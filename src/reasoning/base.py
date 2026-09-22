from abc import ABC, abstractmethod
from typing import List
from src.models.context import InvestigationContext
from src.models.reasoning import (
    InvestigationAssessment,
    EvidenceRequest,
    NextBestAction
)

class ReasoningEngineInterface(ABC):
    """
    Abstract interface for Fraud Investigation Reasoning Engines.
    Enables pluggable swap between deterministic reference engines
    and future LLM-guided agent reasoners without refactoring other subsystems.
    """
    @abstractmethod
    def assess(self, ctx: InvestigationContext) -> InvestigationAssessment:
        """Executes full multi-dimensional assessment of the investigation context."""
        pass

    @abstractmethod
    def plan_evidence(self, ctx: InvestigationContext) -> List[EvidenceRequest]:
        """Plans prioritized requests for additional evidence to reduce uncertainty."""
        pass

    @abstractmethod
    def recommend_action(self, ctx: InvestigationContext) -> NextBestAction:
        """Determines the policy-compliant Next Best Action for the case."""
        pass
