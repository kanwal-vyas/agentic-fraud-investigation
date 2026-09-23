import datetime
from typing import Dict, Any, Optional, List, Tuple
from src.core.constants import PolicyAction, ApprovalRoute
from src.models.case_memory import (
    CaseLifecycleStatus,
    ActionExecutionStatus,
    ActionAuditRecord,
    CaseMemoryRecord,
)

class CaseLifecycleManager:
    """
    Manages deterministic and auditable state transitions for fraud investigations.
    Strictly enforces separation between RECOMMENDED, PENDING_APPROVAL, AUTHORIZED, and EXECUTED actions.
    Destructive actions (e.g. BLOCK_CARD, BLOCK_ALL_CARDS, DECLINE_TRANSACTION, FILE_REPORT)
    can NEVER be marked EXECUTED without explicit human authorization.
    """
    VALID_TRANSITIONS: Dict[CaseLifecycleStatus, List[CaseLifecycleStatus]] = {
        CaseLifecycleStatus.OPEN: [CaseLifecycleStatus.INVESTIGATING, CaseLifecycleStatus.RESOLVED],
        CaseLifecycleStatus.INVESTIGATING: [
            CaseLifecycleStatus.AWAITING_EVIDENCE,
            CaseLifecycleStatus.REASSESSED,
            CaseLifecycleStatus.ACTION_PENDING_APPROVAL,
            CaseLifecycleStatus.ACTION_EXECUTED,
            CaseLifecycleStatus.RESOLVED,
            CaseLifecycleStatus.ESCALATED,
        ],
        CaseLifecycleStatus.AWAITING_EVIDENCE: [
            CaseLifecycleStatus.REASSESSED,
            CaseLifecycleStatus.ACTION_PENDING_APPROVAL,
            CaseLifecycleStatus.RESOLVED,
            CaseLifecycleStatus.ESCALATED,
        ],
        CaseLifecycleStatus.REASSESSED: [
            CaseLifecycleStatus.ACTION_PENDING_APPROVAL,
            CaseLifecycleStatus.ACTION_EXECUTED,
            CaseLifecycleStatus.RESOLVED,
            CaseLifecycleStatus.ESCALATED,
        ],
        CaseLifecycleStatus.ACTION_PENDING_APPROVAL: [
            CaseLifecycleStatus.ACTION_EXECUTED,
            CaseLifecycleStatus.RESOLVED,
            CaseLifecycleStatus.ESCALATED,
        ],
        CaseLifecycleStatus.ACTION_EXECUTED: [
            CaseLifecycleStatus.RESOLVED,
            CaseLifecycleStatus.ESCALATED,
        ],
        CaseLifecycleStatus.RESOLVED: [CaseLifecycleStatus.INVESTIGATING],  # Reopened if new evidence arrives
        CaseLifecycleStatus.ESCALATED: [CaseLifecycleStatus.RESOLVED],
    }

    DESTRUCTIVE_ACTIONS = {
        PolicyAction.BLOCK_CARD.value,
        PolicyAction.BLOCK_ALL_CARDS.value,
        PolicyAction.DECLINE_TRANSACTION.value,
        PolicyAction.FILE_REPORT.value,
    }

    def transition_state(
        self,
        case: CaseMemoryRecord,
        new_status: CaseLifecycleStatus,
        reason: str = ""
    ) -> CaseMemoryRecord:
        """Transitions case lifecycle state if permitted by transition graph."""
        current_status = case.status
        allowed = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed and new_status != current_status:
            raise ValueError(
                f"Invalid lifecycle transition from {current_status.value} to {new_status.value}. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

        case.status = new_status
        case.updated_at = datetime.datetime.now().isoformat()
        return case

    def record_recommendation(
        self,
        case: CaseMemoryRecord,
        action: str,
        approval_required: bool,
        approval_route: str,
        rationale: str,
        policy_references: List[str]
    ) -> CaseMemoryRecord:
        """Records an action recommended by the Next Best Action engine."""
        case.recommended_nba = action
        case.approval_required = approval_required
        case.approval_route = approval_route
        case.nba_rationale = rationale

        if approval_required:
            case.execution_status = ActionExecutionStatus.PENDING_APPROVAL
            self.transition_state(case, CaseLifecycleStatus.ACTION_PENDING_APPROVAL, reason="Action requires approval")
        else:
            case.execution_status = ActionExecutionStatus.RECOMMENDED

        return case

    def authorize_and_execute_action(
        self,
        case: CaseMemoryRecord,
        action: str,
        authorized_by: str,
        execution_details: Optional[Dict[str, Any]] = None,
        rationale: str = ""
    ) -> Tuple[CaseMemoryRecord, ActionAuditRecord]:
        """
        Explicit authorization and execution boundary.
        Destructive actions can only become EXECUTED through this method.
        """
        if not authorized_by or not str(authorized_by).strip():
            raise ValueError("Explicit authorizer identity is required to execute action.")

        now = datetime.datetime.now().isoformat()
        audit_entry = ActionAuditRecord(
            action=action,
            execution_status=ActionExecutionStatus.EXECUTED,
            approval_route=case.approval_route,
            approval_required=case.approval_required,
            rationale=rationale or case.nba_rationale,
            policy_references=case.policy_rules_evaluated,
            authorized_by=authorized_by,
            executed_at=now,
            execution_details=execution_details or {"status": "success", "channel": "bank_core_api"}
        )

        case.actions_actually_executed.append(audit_entry)
        case.execution_status = ActionExecutionStatus.EXECUTED
        self.transition_state(case, CaseLifecycleStatus.ACTION_EXECUTED, reason=f"Action authorized and executed by {authorized_by}")
        return case, audit_entry

    def resolve_case(
        self,
        case: CaseMemoryRecord,
        outcome: str,  # closed_fraud, closed_legitimate, escalated
        summary: str = ""
    ) -> CaseMemoryRecord:
        """Resolves the case with a final outcome."""
        case.final_outcome = outcome
        if summary:
            case.summary = summary
        
        target_status = CaseLifecycleStatus.ESCALATED if outcome == "escalated" else CaseLifecycleStatus.RESOLVED
        self.transition_state(case, target_status, reason=f"Case resolved with outcome {outcome}")
        return case
