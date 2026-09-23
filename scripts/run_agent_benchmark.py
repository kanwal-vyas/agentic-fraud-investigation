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
from src.models.case_memory import CaseLifecycleStatus, ActionExecutionStatus

def run_benchmark():
    case_pack_path = os.path.join("data", "sample", "case_pack.csv")
    if not os.path.exists(case_pack_path):
        case_pack_path = os.path.join("data", "raw", "case_pack.csv")

    df_cases = pd.read_csv(case_pack_path)
    
    # Run all 20 benchmark cases (HHG-001 through HHG-020)
    all_target_case_ids = [f"HHG-{i:03d}" for i in range(1, 21)]
    benchmark_df = df_cases[df_cases["case_id"].isin(all_target_case_ids)].copy()
    if benchmark_df.empty:
        benchmark_df = df_cases.copy()

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

    print("=" * 100)
    print("STAGE 8: AGENTIC FRAUD INVESTIGATION - CASE MEMORY, PERSISTENCE & GRAPH WRITEBACK BENCHMARK")
    print(f"Running full suite of {len(benchmark_df)} benchmark cases across all trigger modalities...")
    print("=" * 100)

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

        if not res.next_best_action.policy_references:
            unsupported_actions += 1

    # Stage 8 Detailed Case Memory & Writeback Audit for HHG-003 and HHG-010
    print("\n" + "=" * 100)
    print("STAGE 8 AUDIT: DETAILED CASE MEMORY, LIFECYCLE & WRITEBACK TRACE")
    print("=" * 100)

    for audit_case_id in ["HHG-003", "HHG-010"]:
        stored_case = investigator.case_store.get_case(audit_case_id)
        if not stored_case:
            continue

        print(f"\n" + "-" * 80)
        print(f"CASE MEMORY AUDIT: {audit_case_id} ({stored_case.customer_id} | {stored_case.card_id} | Txn {stored_case.triggering_txn_id})")
        print("-" * 80)
        print(f"1. TRIGGER [CURRENT]:")
        print(f"   - Type: {stored_case.trigger_type.upper()}")
        print(f"   - Created At: {stored_case.created_at}")
        print(f"   - Initial Status: OPEN")
        
        print(f"2. CASE CREATED & PERSISTENCE [CURRENT]:")
        print(f"   - Case Store Record: ID={stored_case.case_id}, Status={stored_case.status.value}")
        print(f"   - Primary Customer: {stored_case.customer_id}, Primary Card: {stored_case.card_id}")

        print(f"3. INVESTIGATION EVIDENCE [CURRENT]:")
        for idx, ev in enumerate(stored_case.evidence_items[:3], 1):
            print(f"   - Ev #{idx} [{ev.source_type.upper()} | {ev.source_id}]: {ev.statement}")

        print(f"4. FINDINGS & ASSESSMENT [CURRENT]:")
        print(f"   - Fraud Assessment: {stored_case.fraud_assessment.upper()} (Confidence: {stored_case.confidence:.2f})")
        print(f"   - Uncertainty Level: {stored_case.uncertainty_level.upper()}")
        print(f"   - Identified Patterns: {', '.join(stored_case.fraud_patterns_identified) if stored_case.fraud_patterns_identified else 'none'}")
        for sf in stored_case.supporting_findings[:2]:
            print(f"   + [Supporting Finding]: {sf}")
        for cf in stored_case.contradictory_findings[:2]:
            print(f"   - [Contradictory Finding]: {cf}")

        print(f"5. POLICY EVALUATION [CURRENT]:")
        print(f"   - Rules Evaluated: {', '.join(stored_case.policy_rules_evaluated)}")
        print(f"   - Permitted: {stored_case.policy_decision.permitted}")
        print(f"   - Approval Required: {stored_case.policy_decision.approval_required} (Route: {stored_case.policy_decision.approval_route})")

        print(f"6. NEXT BEST ACTION [RECOMMENDED]:")
        print(f"   - Action: {stored_case.recommended_nba}")
        print(f"   - Rationale: {stored_case.nba_rationale}")
        print(f"   - Execution Boundary: {stored_case.execution_status.value.upper()}")

        print(f"7. APPROVAL / AUTHORIZATION STATUS:")
        if stored_case.approval_required:
            print(f"   - Status: PENDING_APPROVAL (Action '{stored_case.recommended_nba}' held at authorization boundary)")
            print(f"   - Human Authorizer Required: Level {stored_case.approval_route}")
        else:
            print(f"   - Status: AUTO_APPROVED / RECOMMENDED")

        print(f"8. TIGERGRAPH GRAPH WRITEBACK:")
        mode_str = "LIVE" if investigator.writeback_engine.is_live_deployment() else "OFFLINE"
        print(f"   - Writeback Status: {'SUCCESS' if stored_case.written_to_graph else 'FAILED'} (Mode: {mode_str})")
        print(f"   - Vertices Linked: Case:{stored_case.case_id}, Transaction:{stored_case.triggering_txn_id}, Card:{stored_case.card_id}")

        print(f"9. HISTORICAL CASE MEMORY [HISTORICAL PRECEDENT]:")
        if stored_case.related_historical_case_ids:
            for hid in stored_case.related_historical_case_ids[:2]:
                print(f"   - Related Historical Case: {hid} [Source: closed_case:{hid}] (Separated from current evidence)")
        else:
            print(f"   - Related Historical Cases: None matching")

        print(f"10. FINCEN SAR COMPLIANCE [REGULATORY]:")
        print(f"   - SAR Required: {stored_case.sar_data.sar_required}")
        print(f"   - SAR Status: {stored_case.sar_data.sar_status} (Filing: {stored_case.sar_data.filing_status})")
        if stored_case.sar_data.sar_required:
            print(f"   - SAR Rationale: {stored_case.sar_data.sar_rationale}")
            print(f"   - Exposure USD: ${stored_case.sar_data.exposure_usd:.2f}")

        print(f"11. FINAL CASE OUTCOME & LIFECYCLE:")
        print(f"   - Final Outcome: {stored_case.final_outcome.upper()}")
        print(f"   - Final Lifecycle State: {stored_case.status.value}")

    # Aggregate Quality Metrics
    n_cases = len(results)
    avg_tools = total_tools_called / n_cases if n_cases else 0.0
    duplicate_rate = (duplicate_calls / n_cases) * 100 if n_cases else 0.0
    stop_rate = (stopped_within_limit / n_cases) * 100 if n_cases else 0.0
    ev_req_rate = (evidence_requested_count / n_cases) * 100 if n_cases else 0.0
    reassess_rate = (reassessment_count / n_cases) * 100 if n_cases else 0.0
    unsupported_rate = (unsupported_actions / n_cases) * 100 if n_cases else 0.0

    # Contamination Audit
    contaminated_cases = 0
    for res in results:
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

    # Invariant Verification across all 20 benchmark results
    policy_reference_mismatches = 0
    destructive_without_policy_ref = 0
    destructive_when_denied = 0
    persisted_cases_count = len(investigator.case_store.list_cases())
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

    print("\n" + "=" * 80)
    print("STAGE 8 BENCHMARK & CASE PERSISTENCE METRICS SUMMARY")
    print("=" * 80)
    print(f"Total Cases Evaluated:              {n_cases} (Target: 20)")
    print(f"Persisted Case Memory Records:      {persisted_cases_count} (Target: 20)")
    print(f"Average Tool Calls / Case:          {avg_tools:.2f}")
    print(f"Duplicate Tool Call Rate:           {duplicate_rate:.1f}%")
    print(f"Cases Stopping Within Limit:        {stop_rate:.1f}%")
    print(f"Missing-Entity Contamination:       {contaminated_cases} (Target: 0)")
    print(f"Policy Reference Mismatches:        {policy_reference_mismatches} (Target: 0)")
    print(f"Unreferenced Destructive Actions:   {destructive_without_policy_ref} (Target: 0)")
    print(f"Denied Destructive Actions Emitted: {destructive_when_denied} (Target: 0)")
    print("=" * 80)

    if (
        n_cases == 20 and
        persisted_cases_count == 20 and
        contaminated_cases == 0 and
        unsupported_rate == 0.0 and
        policy_reference_mismatches == 0 and
        destructive_without_policy_ref == 0 and
        destructive_when_denied == 0
    ):
        print("[SUCCESS] Stage 8 Case Memory, Persistence & Graph Writeback Benchmark passed with 0 invariant violations!")
    else:
        print("[WARNING] Invariant violation or incomplete benchmark run.")

if __name__ == "__main__":
    run_benchmark()
