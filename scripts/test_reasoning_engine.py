import os
import sys
from pathlib import Path
import pandas as pd

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.data.loader import load_case_pack
from src.rag.corpus import GraphRAGCorpus
from src.rag.retriever import GraphRAGRetriever
from src.rag.synthesis import InvestigationContextSynthesizer
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.reasoning.engine import DeterministicReasoningEngine

def run_reasoning_benchmark():
    print("==================================================")
    print("[*] REASONING, UNCERTAINTY & ACTION POLICY ENGINE BENCHMARK")
    print("==================================================")

    corpus = GraphRAGCorpus()
    retriever = GraphRAGRetriever(corpus)
    tools = TigerGraphInvestigationTools()
    synthesizer = InvestigationContextSynthesizer(retriever=retriever, tools=tools)
    reasoning_engine = DeterministicReasoningEngine()

    cp_df = load_case_pack()

    # 6 diverse benchmark cases
    benchmark_case_ids = [
        "HHG-001",  # Customer report (Out-of-region)
        "HHG-004",  # Low risk score (0.34) + cleared precedent (travel)
        "HHG-010",  # High risk score (0.90) + high exposure + shared device
        "HHG-008",  # Customer report + shared syndicate + prior fraud
        "HHG-003",  # Customer report
        "HHG-005",  # Analyst request + out-of-region
    ]

    for cid in benchmark_case_ids:
        row = cp_df[cp_df["case_id"] == cid].iloc[0]
        
        # 1. Synthesize Context
        ctx = synthesizer.build_context_for_case(
            case_id=row["case_id"],
            opened_at=row["opened_at"],
            trigger_type=row["trigger_type"],
            trigger_text=row["trigger_text"],
            flagged_txn_id=int(row["flagged_txn_id"]),
            card_id=str(row["card_id"]),
            customer_id=str(row["customer_id"]),
            risk_score=float(row["risk_score"]) if pd.notna(row["risk_score"]) else 0.0
        )

        # 2. Run Assessment
        assessment = reasoning_engine.assess(ctx)

        print("==================================================")
        print(f"CASE: {assessment.case_id} ({ctx.customer_id} | {ctx.card_id} | Txn {ctx.flagged_txn_id})")
        print("==================================================")
        print(f"TRIGGER: [{ctx.trigger_type.upper()}] {ctx.trigger_text}")
        print(f"INITIAL ASSESSMENT: {assessment.fraud_assessment.value.upper()}")
        print(f"CONFIDENCE: {assessment.confidence:.2f}")
        print(f"UNCERTAINTY: {assessment.uncertainty.level.value.upper()} ({len(assessment.uncertainty.reasons)} reasons)")
        for r in assessment.uncertainty.reasons:
            print(f"  - {r}")

        print("\nSUPPORTING EVIDENCE:")
        for se in assessment.supporting_evidence[:3]:
            print(f"  + {se}")

        print("\nCONTRADICTORY EVIDENCE (BENIGN SIGNALS):")
        if assessment.contradictory_evidence:
            for ce in assessment.contradictory_evidence:
                print(f"  - {ce}")
        else:
            print("  (None)")

        print("\nEVIDENCE GAPS:")
        for eg in assessment.evidence_gaps:
            print(f"  ? {eg}")

        print("\nADDITIONAL EVIDENCE REQUESTS:")
        if assessment.evidence_requests:
            for req in assessment.evidence_requests[:2]:
                print(f"  -> [{req.request_type.upper()}] {req.reason} (Info Gain: {req.expected_information_gain:.2f})")
        else:
            print("  (None required)")

        print("\nPOLICY DECISION:")
        for pol in assessment.policy_decisions:
            print(f"  Rules Evaluated: {', '.join(pol['governing_rules'])}")
            print(f"  Permitted: {pol['is_permitted']} | Approval Route: {pol['approval_route']}")
            if pol["prerequisites"]:
                print(f"  Prerequisites: {', '.join(pol['prerequisites'])}")

        nba = assessment.next_best_action
        print(f"\nNEXT BEST ACTION: {nba.action.value}")
        print(f"  Execution Status: {nba.execution_status.upper()} (NOT auto-executed)")
        print(f"  Rationale: {nba.rationale}")
        print(f"  Alternatives Considered: {', '.join(nba.alternatives_considered)}")
        print(f"HUMAN APPROVAL REQUIRED: {assessment.requires_human_approval} (Route: Level {nba.approval_route.value})")

        stop = assessment.stop_decision
        print(f"\nSTOP DECISION: {'STOP' if stop.should_stop else 'CONTINUE'}")
        print(f"  Reason: {stop.reason}")
        print(f"  Next Step: {stop.next_step}")

        print("\nSTRUCTURED EXPLANATION:")
        print(f"  [Why Suspicious]: {assessment.explanation.why_suspicious[0] if assessment.explanation.why_suspicious else 'N/A'}")
        print(f"  [Why Not Certain]: {assessment.explanation.why_not_certain[0] if assessment.explanation.why_not_certain else 'N/A'}")
        print(f"  [Why Action]: {assessment.explanation.why_action[0] if assessment.explanation.why_action else 'N/A'}")

        print("\n")

    # Reassessment Demonstration
    print("==================================================")
    print("[*] REASSESSMENT DEMONSTRATION (SIMULATED CUSTOMER RESPONSE)")
    print("==================================================")
    case_row = cp_df[cp_df["case_id"] == "HHG-004"].iloc[0]
    ctx_demo = synthesizer.build_context_for_case(
        case_id=case_row["case_id"],
        opened_at=case_row["opened_at"],
        trigger_type=case_row["trigger_type"],
        trigger_text=case_row["trigger_text"],
        flagged_txn_id=int(case_row["flagged_txn_id"]),
        card_id=str(case_row["card_id"]),
        customer_id=str(case_row["customer_id"]),
        risk_score=float(case_row["risk_score"]) if pd.notna(case_row["risk_score"]) else 0.0
    )

    print(f"Initial State for {ctx_demo.case_id}: Trigger={ctx_demo.trigger_type}, Model Score={ctx_demo.model_risk_score}")
    init_assess = reasoning_engine.assess(ctx_demo)
    print(f"Initial NBA: {init_assess.next_best_action.action.value} (Sufficiency={init_assess.evidence_sufficiency.value})")

    # Simulate Customer Confirms Legitimate Travel
    reassess_result = reasoning_engine.reassess_with_additional_evidence(
        ctx_demo,
        additional_evidence={"customer_response": "confirmed"}
    )
    print(f"Re-assessment after Customer Response: {reassess_result.fraud_assessment.value.upper()}")
    print(f"Re-assessed NBA: {reassess_result.next_best_action.action.value}")
    print(f"Stop Decision: {reassess_result.stop_decision.reason}")
    print("\n[SUCCESS] Reasoning Engine benchmark completed successfully!")

if __name__ == "__main__":
    run_reasoning_benchmark()
