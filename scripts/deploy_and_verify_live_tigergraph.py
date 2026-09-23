import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.core.config import settings
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.graph_loader import TigerGraphDataLoader
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.mcp.server import TigerGraphMCPServer
from src.memory.graph_writeback import CaseGraphWritebackEngine
from src.models.case_memory import CaseMemoryRecord, CaseLifecycleStatus
from src.agent.orchestrator import AgenticFraudInvestigator

def redact_secret(val: str) -> str:
    if not val:
        return "<NOT SET>"
    if len(val) <= 6:
        return "***"
    return val[:3] + "..." + val[-3:]

def run_live_tigergraph_pipeline() -> Dict[str, Any]:
    print("==================================================")
    print("STAGE 10: TIGERGRAPH SAVANNA LIVE DEPLOYMENT & VERIFICATION")
    print("==================================================")
    
    # Check credentials
    print(f"Host: {settings.tg_host}")
    print(f"Graph: {settings.tg_graph}")
    print(f"Username: {settings.tg_username}")
    print(f"Secret: {redact_secret(settings.tg_secret)}")
    print(f"Token: {redact_secret(settings.tg_api_token)}")
    
    client = TigerGraphClient()
    loader = TigerGraphDataLoader(tg_client=client)
    
    # 1. Test Connectivity
    print("\n[Step 1] Testing connectivity to TigerGraph...")
    ping_res = client.ping()
    print(f"Ping result: {ping_res}")
    
    if not ping_res.get("connected", False):
        print("\n[!] Live TigerGraph connection failed or credentials not configured.")
        print(f"    Error: {ping_res.get('error')}")
        return {
            "success": False,
            "stage": "connectivity",
            "ping": ping_res,
        }
        
    print(" -> Connection successful!")
    
    # 2. Deploy Schema
    print("\n[Step 2] Deploying GSQL Schema...")
    schema_file = settings.base_dir / "tigergraph" / "schema.gsql"
    schema_res = loader.load_schema(schema_file)
    print(f"Schema deployment result: {schema_res}")
    
    # 3. Install Queries
    print("\n[Step 3] Installing GSQL Investigation Queries...")
    queries_file = settings.base_dir / "tigergraph" / "queries" / "investigation_queries.gsql"
    queries_res = loader.install_queries(queries_file)
    print(f"Query installation result: {queries_res}")
    
    # 4. Load Data
    print("\n[Step 4] Loading Graph Data (Sample / Benchmark dataset)...")
    sample_dir = settings.sample_data_dir
    load_res = loader.batch_upsert_csv(sample_dir)
    print(f"Data loading result: {load_res}")
    
    # 5. Schema & Counts Verification
    print("\n[Step 5] Verifying Vertex and Edge counts...")
    vertex_types = ["Customer", "Card", "Transaction", "DeviceProfile", "EmailDomain", "BillingRegion", "ClosedCase", "Case"]
    counts = {}
    for vt in vertex_types:
        try:
            cnt = client.get_vertex_count(vt)
            counts[vt] = cnt
            print(f"  - Vertex '{vt}': {cnt}")
        except Exception as e:
            counts[vt] = f"Error: {e}"
            print(f"  - Vertex '{vt}': Error ({e})")
            
    # 6. Real Investigation Query Probes
    print("\n[Step 6] Running Live Investigation Queries...")
    tools = TigerGraphInvestigationTools(tg_client=client)
    print(f"Tools is_live(): {tools.is_live()}")
    
    # Benchmark Txn 3530164 (HHG-003)
    tx_3530164 = tools.get_transaction("3530164")
    print(f"  get_transaction('3530164'): {tx_3530164}")
    
    card_hist = tools.get_card_history("C12382-K1", limit=10)
    print(f"  get_card_history('C12382-K1'): {card_hist.total_txns} txns, ${card_hist.total_amount_usd}")
    
    cases = tools.get_historical_cases(customer_id="C12382", top_k=3)
    print(f"  get_historical_cases('C12382'): {len(cases)} cases found")
    
    # 7. MCP Layer Live Verification
    print("\n[Step 7] Verifying TigerGraph MCP Server routing...")
    mcp_server = TigerGraphMCPServer(investigation_tools=tools)
    status = mcp_server.get_server_status()
    print(f"  MCP Server Status: {status}")
    
    mcp_tx_res = mcp_server.call_tool("get_transaction", {"txn_id": "3530164"})
    print(f"  MCP get_transaction backend: {mcp_tx_res.get('backend')}, status: {mcp_tx_res.get('status')}")
    
    # 8. Case Writeback Live Verification
    print("\n[Step 8] Verifying Case Writeback against Live Graph...")
    writeback = CaseGraphWritebackEngine(tg_client=client)
    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
    test_case = CaseMemoryRecord(
        case_id="CASE-LIVE-TEST-001",
        status=CaseLifecycleStatus.INVESTIGATING,
        fraud_assessment="UNDER_REVIEW",
        confidence=0.50,
        triggering_txn_id=3530164,
        trigger_type="test_trigger",
        created_at=now_str,
        updated_at=now_str,
        card_id="C12382-K1",
        customer_id="C12382",
        summary="Live TigerGraph Savanna Writeback Test Verification",
        fraud_patterns_identified=["TEST_PATTERN"],
    )
    wb_res = writeback.write_case(test_case)
    print(f"  Writeback result: {wb_res}")
    
    # 9. Live Benchmark Smoke Test (HHG-003 and HHG-010)
    print("\n[Step 9] Running Live Benchmark Smoke Test for HHG-003 and HHG-010...")
    investigator = AgenticFraudInvestigator(investigation_tools=tools, writeback_engine=writeback)
    
    print("  -> Investigating HHG-003 (Txn 3530164)...")
    res_003 = investigator.investigate(
        txn_id="3530164",
        trigger="Online electronics order $1200 with elevated risk score",
        case_number="HHG-003"
    )
    print(f"     HHG-003 NBA: {res_003.nba.action.value}, Policy: {res_003.policy_decision.decision.value}")
    
    print("  -> Investigating HHG-010 (Txn 3506725)...")
    res_010 = investigator.investigate(
        txn_id="3506725",
        trigger="Repeated micro authorizations followed by large charge",
        case_number="HHG-010"
    )
    print(f"     HHG-010 NBA: {res_010.nba.action.value}, Policy: {res_010.policy_decision.decision.value}")
    
    return {
        "success": True,
        "counts": counts,
        "hhg_003": res_003.model_dump(),
        "hhg_010": res_010.model_dump(),
    }

if __name__ == "__main__":
    run_live_tigergraph_pipeline()
