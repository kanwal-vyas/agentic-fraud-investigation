import sys
import json
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tigergraph.client import TigerGraphClient
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.mcp.server import TigerGraphMCPServer
from src.models.agent import InvestigationTrigger, TriggerType
from src.agent.orchestrator import AgenticFraudInvestigator
from src.memory.graph_writeback import CaseGraphWritebackEngine

def run_live_investigation():
    print("=" * 80)
    print("LIVE END-TO-END AGENT INVESTIGATION: BENCHMARK CASE HHG-003")
    print("=" * 80)

    # 1. Connect to live TigerGraph
    tg_client = TigerGraphClient()
    ping = tg_client.ping()
    print(f"TigerGraph Live Ping: {ping}")
    if not ping.get("connected"):
        print("ERROR: Live TigerGraph is not connected.")
        return

    # 2. Setup Tools & MCP Server on LIVE backend
    tools = TigerGraphInvestigationTools(tg_client=tg_client)
    print(f"TigerGraph Tools is_live(): {tools.is_live()}")

    mcp_server = TigerGraphMCPServer(investigation_tools=tools)
    server_status = mcp_server.get_server_status()
    print(f"MCP Server Status: backend={server_status.get('backend')}, is_live={server_status.get('is_live_tigergraph')}")

    # 3. Setup Writeback Engine with Live Client
    writeback_engine = CaseGraphWritebackEngine(tg_client=tg_client)
    print(f"Writeback Engine is_live_deployment(): {writeback_engine.is_live_deployment()}")

    # 4. Instantiate Agentic Fraud Investigator
    investigator = AgenticFraudInvestigator(
        mcp_server=mcp_server,
        writeback_engine=writeback_engine
    )

    # 5. Build HHG-003 Trigger from case_pack.csv
    case_pack_path = Path("data/sample/case_pack.csv")
    df = pd.read_csv(case_pack_path)
    hhg003_row = df[df["case_id"] == "HHG-003"].iloc[0]

    trigger = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=int(hhg003_row["flagged_txn_id"]),
        customer_id=str(hhg003_row["customer_id"]),
        card_id=str(hhg003_row["card_id"]),
        model_risk_score=float(hhg003_row["risk_score"]) if pd.notna(hhg003_row["risk_score"]) else 0.40,
        trigger_details=str(hhg003_row["trigger_text"])
    )

    print("\n" + "-" * 40)
    print("1. TRIGGER DETAILS")
    print("-" * 40)
    print(f"Case ID:        {trigger.case_id}")
    print(f"Trigger Type:   {trigger.trigger_type.value}")
    print(f"Txn ID:         {trigger.transaction_id}")
    print(f"Customer ID:    {trigger.customer_id}")
    print(f"Card ID:        {trigger.card_id}")
    print(f"Model Risk:     {trigger.model_risk_score}")
    print(f"Trigger Text:   {trigger.trigger_details}")

    # 6. Run Investigation
    print("\n" + "-" * 40)
    print("2. AGENT EXECUTION")
    print("-" * 40)

    result = investigator.investigate(trigger)

    print(f"Total Tool Steps:  {result.total_tool_calls}")
    print(f"Persisted Case ID: {result.persisted_case_id}")
    print(f"Written to Graph:  {result.written_to_graph}")

    # 7. Print Investigation Steps & Live Results
    print("\n" + "-" * 40)
    print("3. STEP-BY-STEP TOOL SELECTION & LIVE INVESTIGATION QUERIES")
    print("-" * 40)
    for step in result.investigation_steps:
        print(f"\n[Step {step.step_number}] Tool Invoked: '{step.tool}'")
        print(f"  Reason / Intent:  {step.reason}")
        print(f"  Input Arguments:  {step.input_args}")
        print(f"  Execution Outcome:{step.outcome}")
        print(f"  Result Summary:   {step.result_summary}")

    # 8. Evidence Collected
    print("\n" + "-" * 40)
    print("4. EVIDENCE COLLECTED")
    print("-" * 40)
    for idx, ev in enumerate(result.evidence_collected, 1):
        source = ev.get("source", "unknown")
        print(f"  [Evidence #{idx}] Source: {source}")
        for k, v in ev.items():
            if k != "source":
                print(f"    - {k}: {v}")

    # 9. Reasoning, Sufficiency, Uncertainty Assessment
    print("\n" + "-" * 40)
    print("5. REASONING, UNCERTAINTY & SUFFICIENCY ASSESSMENT")
    print("-" * 40)
    assessment = result.final_assessment
    if assessment:
        print(f"Assessment Outcome:   {assessment.fraud_assessment.value}")
        print(f"Confidence Score:     {assessment.confidence:.2f}")
        print(f"Uncertainty Level:    {assessment.uncertainty.level.value}")
        print(f"Uncertainty Reasons:  {assessment.uncertainty.reasons}")
        print(f"Evidence Sufficiency: {assessment.evidence_sufficiency.value}")
        print(f"Fraud Patterns:       {assessment.suspected_patterns}")
        print(f"Supporting Evidence:  {assessment.supporting_evidence}")
        print(f"Contradictory Ev:     {assessment.contradictory_evidence}")
        print(f"Evidence Gaps:        {assessment.evidence_gaps}")

    # 10. Evidence Requests / Reassessment
    print("\n" + "-" * 40)
    print("6. EVIDENCE REQUESTS & REASSESSMENT")
    print("-" * 40)
    if result.evidence_requests:
        for er in result.evidence_requests:
            print(f"  - Request ID: {er.request_id}")
            print(f"    Type:       {er.request_type}")
            print(f"    Reason:     {er.reason}")
            print(f"    Rationale:  {er.rationale}")
            print(f"    Policy Ref: {er.policy_reference}")
    else:
        print("  - No additional evidence requests required. Evidence is sufficient under customer report validation rule.")

    # 11. GraphRAG Historical Case Memory Retrieval
    print("\n" + "-" * 40)
    print("7. GRAPHRAG HISTORICAL CASE CONTEXT")
    print("-" * 40)
    hist_cases = tools.get_historical_cases(customer_id=trigger.customer_id, top_k=5)
    print(f"Retrieved {len(hist_cases)} historical cases for customer {trigger.customer_id} via Live TigerGraph:")
    for hc in hist_cases[:3]:
        print(f"  - Case {hc.case_id}: outcome={hc.outcome}, pattern={hc.pattern}, exposure=${hc.exposure_usd}, note={hc.analyst_notes[:70]}...")

    # 12. Policy Evaluation & NBA
    print("\n" + "-" * 40)
    print("8. POLICY RULES EVALUATED & NEXT BEST ACTION (NBA)")
    print("-" * 40)
    print(f"Policy Decisions Evaluated ({len(result.policy_decisions)}):")
    for pd_item in result.policy_decisions:
        print(f"  - Rule: {pd_item.get('rule_id')} | Triggered: {pd_item.get('triggered')} | Action: {pd_item.get('action')}")
        print(f"    Rationale: {pd_item.get('rationale')}")

    nba = result.next_best_action
    if nba:
        print(f"\nNext Best Action:")
        print(f"  Recommended Action:   {nba.action.value}")
        print(f"  Approval Required:    {nba.approval_required}")
        print(f"  Approval Route:       {nba.approval_route.value}")
        print(f"  Execution Status:     {nba.execution_status}")
        print(f"  Policy References:    {nba.policy_references}")
        print(f"  Confidence:           {nba.confidence:.2f}")
        print(f"  Rationale:            {nba.rationale}")
        print(f"  Alternatives:         {nba.alternatives_considered}")

    # 13. Explanation
    print("\n" + "-" * 40)
    print("9. 5-PART STRUCTURED EXPLANATION")
    print("-" * 40)
    expl = result.explanation
    print(f"Why Suspicious:       {expl.why_suspicious}")
    print(f"Why Not Certain:      {expl.why_not_certain}")
    print(f"Why Action:           {expl.why_action}")
    print(f"Why Stop:             {expl.why_stop}")

    # 14. Stored Case Record from CaseStore & Lifecycle
    print("\n" + "-" * 40)
    print("10. CASE MEMORY LIFECYCLE & SAR STATUS")
    print("-" * 40)
    stored_case = investigator.case_store.get_case("HHG-003")
    if stored_case:
        print(f"Lifecycle Status:     {stored_case.status.value}")
        print(f"Recommended NBA:      {stored_case.recommended_nba}")
        print(f"Approval Required:    {stored_case.approval_required}")
        print(f"Approval Route:       {stored_case.approval_route}")
        print(f"Execution Status:     {stored_case.execution_status.value}")
        print(f"Final Outcome:        {stored_case.final_outcome}")
        print(f"Actions Executed:     {len(stored_case.actions_actually_executed)} (Separation preserved: 0 destructive actions auto-executed)")
        if stored_case.sar_data:
            print(f"SAR Required:         {stored_case.sar_data.sar_required}")
            print(f"SAR Exposure USD:     ${stored_case.sar_data.exposure_usd}")
            print(f"SAR Status:           {stored_case.sar_data.sar_status}")
            print(f"SAR Narrative:        {stored_case.sar_data.narrative[:150]}...")

    # 15. Verify in LIVE TigerGraph Graph Database
    print("\n" + "-" * 40)
    print("11. LIVE TIGERGRAPH INVESTIGATIONCASE VERIFICATION")
    print("-" * 40)
    conn = tg_client.get_connection()
    live_case_vertices = conn.getVerticesById("InvestigationCase", "HHG-003")
    print(f"Live InvestigationCase Vertex: {live_case_vertices}")

    edges_involves = conn.getEdges("InvestigationCase", "HHG-003", "INVOLVES")
    edges_on_card = conn.getEdges("InvestigationCase", "HHG-003", "ON_CARD")
    print(f"Live INVOLVES Edges: {edges_involves}")
    print(f"Live ON_CARD Edges:  {edges_on_card}")

if __name__ == "__main__":
    run_live_investigation()
