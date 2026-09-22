import os
import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.data.loader import load_case_pack
from src.rag.corpus import GraphRAGCorpus
from src.rag.retriever import GraphRAGRetriever
from src.rag.synthesis import InvestigationContextSynthesizer
from src.tigergraph.tools import TigerGraphInvestigationTools

def run_graphrag_benchmark_probe():
    print("==================================================")
    print("[*] GRAPHRAG CONTEXT SYNTHESIS ENGINE BENCHMARK PROBE")
    print("==================================================")

    corpus = GraphRAGCorpus()
    inventory = corpus.get_inventory()
    print("[*] CORPUS INVENTORY:")
    print(f"    - Closed Cases: {inventory['closed_cases']['total_records']} ({inventory['closed_cases']['confirmed_fraud_records']} confirmed fraud, {inventory['closed_cases']['cleared_records']} cleared)")
    print(f"    - Policy Rules: {inventory['policy_rules']['total_records']} rules (R1 to R10)")
    print(f"    - Regulatory References: {inventory['regulatory_references']['total_records']} compliance standards")
    print("--------------------------------------------------\n")

    retriever = GraphRAGRetriever(corpus)
    tools = TigerGraphInvestigationTools()
    synthesizer = InvestigationContextSynthesizer(retriever=retriever, tools=tools)

    cp_df = load_case_pack()
    
    # Select targeted benchmark test cases covering diverse triggers & historical profiles
    selected_cases = [
        "HHG-001",  # Customer report trigger (C12382, Out of region / CNP new device)
        "HHG-004",  # Analyst request trigger (C08106, cleared historical cases present)
        "HHG-010",  # Risk-score trigger (C10434, score 0.90, cleared travel history present)
        "HHG-008",  # Analyst request trigger (C09933)
    ]

    for case_id in selected_cases:
        row = cp_df[cp_df["case_id"] == case_id].iloc[0]
        
        print("==================================================")
        print(f"[*] INVESTIGATION CONTEXT FOR BENCHMARK: {case_id}")
        print("==================================================")
        print(f"Trigger Type: {row['trigger_type'].upper()}")
        print(f"Trigger Text: {row['trigger_text']}")
        print(f"Target Transaction: {row['flagged_txn_id']} | Card: {row['card_id']} | Customer: {row['customer_id']}")
        print(f"Input Model Risk Score: {row['risk_score'] if pd.notna(row['risk_score']) else 'N/A'}")
        print("--------------------------------------------------")

        # Synthesize Context
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

        # 1. Authoritative Graph Evidence
        print("\n[1] AUTHORITATIVE GRAPH EVIDENCE:")
        for bullet in ctx.graph_evidence_summary:
            print(f"  • {bullet}")

        # 2. Historical Cases: Confirmed Fraud Precedent
        print("\n[2] HISTORICAL PRECEDENT (CONFIRMED FRAUD):")
        if ctx.historical_cases_confirmed_fraud:
            for hc in ctx.historical_cases_confirmed_fraud:
                print(f"  • [{hc.case_id}] ({hc.pattern}, Exposure: ${hc.exposure_usd:.2f}, Score: {hc.relevance_score}): {hc.analyst_notes[:100]}...")
                print(f"    Reasons: {', '.join(hc.similarity_reasons)}")
        else:
            print("  • No matching confirmed fraud cases found.")

        # 3. Historical Cases: Cleared Precedent
        print("\n[3] HISTORICAL PRECEDENT (CLEARED / BENIGN):")
        if ctx.historical_cases_cleared:
            for cl in ctx.historical_cases_cleared:
                print(f"  • [{cl.case_id}] (CLEARED, {cl.pattern}, Score: {cl.relevance_score}): {cl.analyst_notes[:100]}...")
                print(f"    Reasons: {', '.join(cl.similarity_reasons)}")
        else:
            print("  • No matching cleared cases found.")

        # 4. Applicable Bank Policy Rules
        print("\n[4] APPLICABLE BANK POLICY RULES:")
        for pol in ctx.applicable_policies:
            print(f"  • [{pol.rule_id}] {pol.name} (Approval: {pol.approval_level})")
            print(f"    Condition: {pol.applicable_condition}")
            print(f"    Recommended Actions: {', '.join(pol.recommended_actions)}")

        # 5. Regulatory Compliance References
        print("\n[5] REGULATORY REFERENCES:")
        for reg in ctx.regulatory_references:
            print(f"  • [{reg.regulation_id}] {reg.title} ({reg.section})")
            print(f"    Mandate: {reg.mandate_summary}")

        # 6. Contradictory Evidence (Benign Indicators)
        print("\n[6] CONTRADICTORY EVIDENCE (BENIGN INDICATORS):")
        if ctx.contradictory_evidence:
            for ce in ctx.contradictory_evidence:
                print(f"  • Evidence: {ce.evidence}")
                print(f"    Benign Rationale: {ce.benign_explanation} (Source: {ce.source_id}, Weight: {ce.weight})")
        else:
            print("  • No contradictory or benign indicators identified.")

        # 7. Evidence Gaps
        print("\n[7] EVIDENCE GAPS & NEXT STEPS:")
        for eg in ctx.evidence_gaps:
            print(f"  • [{eg.urgency.upper()}] {eg.missing_information}")
            print(f"    Verification: {eg.recommended_verification}")

        # 8. Provenance Attribution Sample
        print(f"\n[8] PROVENANCE ATTRIBUTIONS: {len(ctx.source_attributions)} total source links captured.")
        for src in ctx.source_attributions[:3]:
            print(f"  • Type: {src.source_type} | ID: {src.source_id} | Score: {src.relevance_score}")

        print("\n")

    print("[SUCCESS] GraphRAG context synthesis benchmark probe completed successfully!")

if __name__ == "__main__":
    import pandas as pd
    run_graphrag_benchmark_probe()
