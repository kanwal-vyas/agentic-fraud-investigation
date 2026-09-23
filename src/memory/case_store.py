import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.models.case_memory import (
    CaseMemoryRecord,
    PersistedEvidenceItem,
    CaseDecisionRecord,
    ActionAuditRecord,
    CaseLifecycleStatus,
)
from src.models.context import HistoricalCaseMatch

class CaseStoreInterface(ABC):
    """Abstract interface defining the contract for Case Memory Persistence."""
    @abstractmethod
    def create_case(self, case: CaseMemoryRecord) -> CaseMemoryRecord:
        pass

    @abstractmethod
    def update_case(self, case_id: str, updates: Dict[str, Any]) -> CaseMemoryRecord:
        pass

    @abstractmethod
    def append_evidence(self, case_id: str, evidence: PersistedEvidenceItem):
        pass

    @abstractmethod
    def append_finding(self, case_id: str, finding: str, finding_type: str = "supporting"):
        pass

    @abstractmethod
    def append_decision(self, case_id: str, policy_decision: Dict[str, Any]):
        pass

    @abstractmethod
    def append_action(self, case_id: str, action: Dict[str, Any]):
        pass

    @abstractmethod
    def append_outcome(self, case_id: str, outcome: str, status: CaseLifecycleStatus):
        pass

    @abstractmethod
    def get_case(self, case_id: str) -> Optional[CaseMemoryRecord]:
        pass

    @abstractmethod
    def list_cases(self, filter_params: Optional[Dict[str, Any]] = None) -> List[CaseMemoryRecord]:
        pass

    @abstractmethod
    def search_similar_cases(self, query: Dict[str, Any], top_k: int = 5) -> List[HistoricalCaseMatch]:
        pass

class InMemoryCaseStore(CaseStoreInterface):
    """
    Thread-safe, deterministic in-memory case store for development, testing, and offline operations.
    Maintains fast indexes across customer_id, card_id, pattern, and status.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._cases: Dict[str, CaseMemoryRecord] = {}
        self._by_customer: Dict[str, List[str]] = {}
        self._by_card: Dict[str, List[str]] = {}
        self._by_pattern: Dict[str, List[str]] = {}

    def create_case(self, case: CaseMemoryRecord) -> CaseMemoryRecord:
        with self._lock:
            cid = case.case_id
            self._cases[cid] = case.model_copy(deep=True)
            self._index_case(case)
            return self._cases[cid]

    def _index_case(self, case: CaseMemoryRecord):
        cid = case.case_id
        if case.customer_id:
            self._by_customer.setdefault(case.customer_id, [])
            if cid not in self._by_customer[case.customer_id]:
                self._by_customer[case.customer_id].append(cid)

        if case.card_id:
            self._by_card.setdefault(case.card_id, [])
            if cid not in self._by_card[case.card_id]:
                self._by_card[case.card_id].append(cid)

        for pat in case.fraud_patterns_identified:
            self._by_pattern.setdefault(pat, [])
            if cid not in self._by_pattern[pat]:
                self._by_pattern[pat].append(cid)

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> CaseMemoryRecord:
        with self._lock:
            if case_id not in self._cases:
                raise KeyError(f"Case {case_id} not found in case store.")
            current = self._cases[case_id]
            data = current.model_dump()
            data.update(updates)
            updated = CaseMemoryRecord(**data)
            self._cases[case_id] = updated
            self._index_case(updated)
            return updated

    def append_evidence(self, case_id: str, evidence: PersistedEvidenceItem):
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found.")
            case.evidence_items.append(evidence)
            self._cases[case_id] = case

    def append_finding(self, case_id: str, finding: str, finding_type: str = "supporting"):
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found.")
            if finding_type == "supporting":
                if finding not in case.supporting_findings:
                    case.supporting_findings.append(finding)
            else:
                if finding not in case.contradictory_findings:
                    case.contradictory_findings.append(finding)
            self._cases[case_id] = case

    def append_decision(self, case_id: str, policy_decision: Dict[str, Any]):
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found.")
            case.policy_decision = CaseDecisionRecord(**policy_decision)
            case.policy_rules_evaluated = policy_decision.get("rules_evaluated", [])
            self._cases[case_id] = case

    def append_action(self, case_id: str, action: Dict[str, Any]):
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found.")
            entry = ActionAuditRecord(**action)
            case.actions_actually_executed.append(entry)
            self._cases[case_id] = case

    def append_outcome(self, case_id: str, outcome: str, status: CaseLifecycleStatus):
        with self._lock:
            case = self.get_case(case_id)
            if not case:
                raise KeyError(f"Case {case_id} not found.")
            case.final_outcome = outcome
            case.status = status
            self._cases[case_id] = case

    def get_case(self, case_id: str) -> Optional[CaseMemoryRecord]:
        with self._lock:
            case = self._cases.get(case_id)
            return case.model_copy(deep=True) if case else None

    def list_cases(self, filter_params: Optional[Dict[str, Any]] = None) -> List[CaseMemoryRecord]:
        with self._lock:
            if not filter_params:
                return [c.model_copy(deep=True) for c in self._cases.values()]
            
            results = []
            for c in self._cases.values():
                match = True
                for k, v in filter_params.items():
                    if getattr(c, k, None) != v:
                        match = False
                        break
                if match:
                    results.append(c.model_copy(deep=True))
            return results

    def search_similar_cases(self, query: Dict[str, Any], top_k: int = 5) -> List[HistoricalCaseMatch]:
        """
        Retrieves matching persisted cases preserving complete historical provenance.
        Differentiates persisted case records from static closed cases.
        """
        with self._lock:
            target_cust = query.get("customer_id")
            target_card = query.get("card_id")
            target_pattern = query.get("pattern")
            target_outcome = query.get("outcome")

            candidate_ids = set()
            if target_cust and target_cust in self._by_customer:
                candidate_ids.update(self._by_customer[target_cust])
            if target_card and target_card in self._by_card:
                candidate_ids.update(self._by_card[target_card])
            if target_pattern and target_pattern in self._by_pattern:
                candidate_ids.update(self._by_pattern[target_pattern])

            # If no index match, search all
            if not candidate_ids:
                candidate_ids = set(self._cases.keys())

            matches: List[HistoricalCaseMatch] = []
            for cid in candidate_ids:
                c = self._cases.get(cid)
                if not c:
                    continue
                if target_outcome and c.final_outcome != target_outcome:
                    continue

                relevance = 0.5
                if target_cust and c.customer_id == target_cust:
                    relevance += 0.3
                if target_card and c.card_id == target_card:
                    relevance += 0.2
                if target_pattern and target_pattern in c.fraud_patterns_identified:
                    relevance += 0.2

                relevance = min(1.0, relevance)

                outcome_mapped = "confirmed_fraud" if c.final_outcome.lower() in ["closed_fraud", "likely_fraud", "confirmed_fraud", "resolved_fraud"] or c.fraud_assessment.lower() in ["likely_fraud", "confirmed_fraud"] and c.final_outcome.lower() in ["action_pending_approval"] else "cleared"
                actions_str = ", ".join([a.action for a in c.actions_actually_executed]) if c.actions_actually_executed else c.recommended_nba
                sim_reasons = []
                if target_cust and c.customer_id == target_cust:
                    sim_reasons.append(f"Matching customer: {target_cust}")
                if target_card and c.card_id == target_card:
                    sim_reasons.append(f"Matching card: {target_card}")
                if target_pattern and target_pattern in c.fraud_patterns_identified:
                    sim_reasons.append(f"Matching pattern: {target_pattern}")

                matches.append(
                    HistoricalCaseMatch(
                        case_id=c.case_id,
                        customer_id=c.customer_id,
                        card_id=c.card_id,
                        outcome=outcome_mapped,
                        pattern=", ".join(c.fraud_patterns_identified) if c.fraud_patterns_identified else "none",
                        exposure_usd=c.sar_data.exposure_usd if c.sar_data else 0.0,
                        relevance_score=relevance,
                        similarity_reasons=sim_reasons,
                        actions_taken=actions_str,
                        analyst_notes=c.summary or c.nba_rationale
                    )
                )

            matches.sort(key=lambda x: x.relevance_score, reverse=True)
            return matches[:top_k]
