import os
import sys
import pandas as pd
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.agent import InvestigationTrigger, TriggerType, InvestigationResult
from src.agent.orchestrator import AgenticFraudInvestigator
from src.mcp.server import TigerGraphMCPServer
from src.rag.synthesis import InvestigationContextSynthesizer
from src.reasoning.engine import DeterministicReasoningEngine

def run_benchmark():
    case_pack_path = os.path.join("data", "sample", "case_pack.csv")
    if not os.path.exists(case_pack_path):
        case_pack_path = os.path.join("data", "raw", "case_pack.csv")

    df_cases = pd.read_csv(case_pack_path)
    
    # Select 12 representative benchmark cases covering all modalities
    target_case_ids = [
        "HHG-001", "HHG-002", "HHG-003", "HHG-004", "HHG-005",
        "HHG-006", "HHG-007", "HHG-010", "HHG-014", "HHG-015",
        "HHG-017", "HHG-018"
    ]
    benchmark_df = df_cases[df_cases["case_id"].isin(target_case_ids)].copy()

    # Initialize Orchestrator components
    mcp_server = TigerGraphMCPServer()
    synthesizer = InvestigationContextSynthesizer()
    reasoning_engine = DeterministicReasoningEngine()
    investigator = AgenticFraudInvestigator(
        mcp_server=mcp_server,
        synthesizer=synthesizer,
        reasoning_engine=reasoning_engine,
        max_steps=8
    )

    results: List[InvestigationResult] = []
    total_tools_called = 0
    duplicate_calls = 0
    stopped_within_limit = 0
    evidence_requested_count = 0
    reassessment_count = 0
    policy_conflicts = 0
    unsupported_actions = 0

    print("=" * 80)
    print("STAGE 7: AGENTIC FRAUD INVESTIGATION ORCHESTRATOR BENCHMARK EVALUATION")
    print(f"Running {len(benchmark_df)} benchmark cases across multiple trigger modalities...")
    print("=" * 80)

    for _, row in benchmark_df.iterrows():
        case_id = str(row["case_id"])
        trigger_type_str = str(row["trigger_type"])
        trigger_text = str(row["trigger_text"])
        txn_id = int(row["flagged_txn_id"])
        card_id = str(row["card_id"])
        customer_id = str(row["customer_id"])
        risk_score = float(row["risk_score"]) if pd.notna(row["risk_score"]) and str(row["risk_score"]).strip() != "" else 0.0
        opened_at = str(row["opened_at"]) if "opened_at" in row and pd.notna(row["opened_at"]) else ""

        # Map trigger string to enum
        if trigger_type_str == "customer_report":
            trig_type = TriggerType.CUSTOMER_REPORT
        elif trigger_type_str == "analyst_request":
            trig_type = TriggerType.ANALYST_REQUEST
        else:
            trig_type = TriggerType.RISK_SCORE

        trigger = InvestigationTrigger(
            case_id=case_id,
            trigger_type=trig_type,
            transaction_id=txn_id,
            customer_id=customer_id,
            card_id=card_id,
            model_risk_score=risk_score,
            trigger_details=trigger_text,
            opened_at=opened_at
        )

        # Include simulated customer response for reassessment scenario on HHG-005
        sim_response = None
        if case_id == "HHG-005":
            sim_response = {"customer_response": "confirmed"}
            reassessment_count += 1

        res = investigator.investigate(trigger, simulated_evidence_response=sim_response)
        results.append(res)

        # Orchestration Metrics Computation
        total_tools_called += res.total_tool_calls
        tool_names = [step.tool for step in res.investigation_steps]
        if len(tool_names) != len(set(tool_names)):
            duplicate_calls += 1

        if res.total_steps <= 8:
            stopped_within_limit += 1

        if res.evidence_requests:
            evidence_requested_count += 1

        # Check for policy compliance or unsupported actions
        if not res.next_best_action.policy_references:
            unsupported_actions += 1

        # Print structured case breakdown
        print(f"\n==================================================")
        print(f"CASE ID: {res.case_id} ({customer_id} | {card_id} | Txn {txn_id})")
        print(f"==================================================")
        print(f"TRIGGER: [{res.trigger.trigger_type.value.upper()}] {res.trigger.trigger_details}")
        print(f"TOOLS CALLED ({len(res.investigation_steps)} steps):")
        for step in res.investigation_steps:
            print(f"  Step {step.step_number} [{step.tool}]: {step.reason}")
            print(f"    -> Summary: {step.result_summary}")

        print(f"EVIDENCE FOUND:")
        for ev in res.final_assessment.supporting_evidence[:2]:
            print(f"  + [Supporting]: {ev}")
        for ev in res.final_assessment.contradictory_evidence[:2]:
            print(f"  - [Benign Signal]: {ev}")

        print(f"ASSESSMENT CHECKPOINTS: {len(res.assessment_history)} evaluated")
        for idx, chk in enumerate(res.assessment_history, 1):
            print(f"  Checkpoint {idx}: Verdict={chk.fraud_assessment.value} | Confidence={chk.confidence:.2f} | Uncertainty={chk.uncertainty.level.value}")

        print(f"UNCERTAINTY: {res.final_assessment.uncertainty.level.value.upper()}")
        for r in res.final_assessment.uncertainty.reasons[:2]:
            print(f"  - Reason: {r}")

        print(f"EVIDENCE GAPS: {', '.join(res.final_assessment.evidence_gaps) if res.final_assessment.evidence_gaps else 'None'}")
        
        if res.evidence_requests:
            print(f"EVIDENCE REQUESTS:")
            for req in res.evidence_requests:
                print(f"  -> [{req.request_type.upper()}] {req.reason} (Info Gain: {req.expected_information_gain:.2f})")

        print(f"POLICY DECISION:")
        for pol in res.policy_decisions:
            print(f"  Rules Evaluated: {', '.join(pol.get('rules_evaluated', []))} | Permitted: {pol.get('permitted')} | Route: {pol.get('approval_route')}")

        print(f"NEXT BEST ACTION: {res.next_best_action.action.value.upper()}")
        print(f"  Rationale: {res.next_best_action.rationale}")
        print(f"  Execution Status: {res.execution_status.upper()} (Approval Required: {res.approval_required}, Route: Level {res.approval_route.value})")

        print(f"STOP REASON: [{res.stop_decision.should_stop}] {res.stop_decision.reason}")

    # Aggregate Quality Metrics & Evidence Request Audit
    n_cases = len(results)
    avg_tools = total_tools_called / n_cases if n_cases else 0.0
    duplicate_rate = (duplicate_calls / n_cases) * 100 if n_cases else 0.0
    stop_rate = (stopped_within_limit / n_cases) * 100 if n_cases else 0.0
    ev_req_rate = (evidence_requested_count / n_cases) * 100 if n_cases else 0.0
    reassess_rate = (reassessment_count / n_cases) * 100 if n_cases else 0.0
    unsupported_rate = (unsupported_actions / n_cases) * 100 if n_cases else 0.0

    # Contamination Audit
    contaminated_cases = 0
    audit_table_rows = []
    justified_requests_count = 0

    for res in results:
        # Check for invalid entity strings in tool arguments, steps, or evidence summaries
        has_contamination = False
        for step in res.investigation_steps:
            for k, v in step.input_args.items():
                if str(v).lower() in ["nan", "none", "null", "unknown", "unknowndevice"]:
                    has_contamination = True
            if "device nan" in step.reason.lower() or "device nan" in step.result_summary.lower():
                has_contamination = True
        for ev in res.final_assessment.supporting_evidence:
            if "'nan'" in ev.lower() or "device nan" in ev.lower():
                has_contamination = True

        if has_contamination:
            contaminated_cases += 1

        # Classify Evidence Request Decision
        if res.evidence_requests:
            req = res.evidence_requests[0]
            req_type = req.request_type
            pol_ref = req.policy_reference
            gap = req.evidence_gap_addressed
            
            # Classification
            if req_type == "customer_validation" and res.trigger.trigger_type == TriggerType.CUSTOMER_REPORT:
                classification = "unnecessary (customer already reported denial)"
            elif res.trigger.model_risk_score < 0.20 and res.final_assessment.fraud_assessment.value == "likely_benign":
                classification = "unnecessary (low risk benign baseline)"
            elif "R1" in pol_ref or "R5" in pol_ref or "R6" in pol_ref or "R8" in pol_ref:
                classification = "justified (policy-mandated verification)"
                justified_requests_count += 1
            else:
                classification = "justified (unresolved information gap)"
                justified_requests_count += 1

            audit_table_rows.append({
                "case_id": res.case_id,
                "requested": "YES",
                "reason": classification,
                "policy_required": "YES" if ("R1" in pol_ref or "R5" in pol_ref or "R6" in pol_ref or "R8" in pol_ref) else "NO",
                "gap": gap[:45] + "..." if len(gap) > 45 else gap
            })
        else:
            audit_table_rows.append({
                "case_id": res.case_id,
                "requested": "NO",
                "reason": "sufficient evidence / benign baseline / customer report authoritative",
                "policy_required": "NO",
                "gap": "None (evidence sufficient for NBA)"
            })

    justified_rate = (justified_requests_count / evidence_requested_count * 100) if evidence_requested_count > 0 else 100.0

    print("\n" + "=" * 100)
    print("STAGE 7 EVIDENCE REQUEST AUDIT TABLE")
    print("=" * 100)
    print(f"{'CASE':<10} | {'REQUESTED?':<10} | {'REASON / CLASSIFICATION':<42} | {'POLICY REQ?':<11} | {'INFORMATION GAP'}")
    print("-" * 100)
    for row in audit_table_rows:
        print(f"{row['case_id']:<10} | {row['requested']:<10} | {row['reason']:<42} | {row['policy_required']:<11} | {row['gap']}")
    print("=" * 100)

    print("\n" + "=" * 80)
    print("ORCHESTRATION QUALITY METRICS SUMMARY")
    print("=" * 80)
    print(f"Total Cases Evaluated:              {n_cases}")
    print(f"Average Tool Calls / Case:          {avg_tools:.2f}")
    print(f"Duplicate Tool Call Rate:           {duplicate_rate:.1f}%")
    print(f"Max Allowed Steps:                  8")
    print(f"Cases Stopping Within Limit:        {stop_rate:.1f}%")
    print(f"Evidence Request Rate:              {ev_req_rate:.1f}%")
    print(f"Justified Evidence Request Rate:    {justified_rate:.1f}%")
    print(f"Reassessment Rate:                  {reassess_rate:.1f}%")
    # Invariant Verification across all benchmark results
    policy_reference_mismatches = 0
    destructive_without_policy_ref = 0
    destructive_when_denied = 0

    destructive_action_set = {"block_card", "block_all_cards", "freeze_account", "decline_transaction"}

    for res in results:
        pol_dict = res.policy_decisions[0] if res.policy_decisions else {}
        evaluated_rules = set(pol_dict.get("rules_evaluated", []))
        is_permitted = pol_dict.get("permitted", pol_dict.get("is_permitted", False))
        nba_action = res.next_best_action.action.value
        nba_refs = set(res.next_best_action.policy_references)

        if nba_action in destructive_action_set:
            if not is_permitted:
                destructive_when_denied += 1
            if not nba_refs:
                destructive_without_policy_ref += 1
            if not nba_refs.issubset(evaluated_rules):
                policy_reference_mismatches += 1

    print(f"Policy Reference Mismatches:        {policy_reference_mismatches} (Target: 0)")
    print(f"Unreferenced Destructive Actions:   {destructive_without_policy_ref} (Target: 0)")
    print(f"Denied Destructive Actions Emitted: {destructive_when_denied} (Target: 0)")
    print("=" * 80)
    if (
        contaminated_cases == 0 and
        unsupported_rate == 0.0 and
        policy_reference_mismatches == 0 and
        destructive_without_policy_ref == 0 and
        destructive_when_denied == 0
    ):
        print("[SUCCESS] Stage 7 Agentic Investigation Orchestrator audit & policy invariant criteria passed!")
    else:
        print("[WARNING] Audit criteria violation detected.")

if __name__ == "__main__":
    run_benchmark()
