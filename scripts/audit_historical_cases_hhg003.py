import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tigergraph.client import TigerGraphClient
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.mcp.server import TigerGraphMCPServer
from src.rag.synthesis import InvestigationContextSynthesizer
from src.models.context import InvestigationContext
from src.models.agent import InvestigationTrigger, TriggerType

client = TigerGraphClient()
conn = client.get_connection()
tools = TigerGraphInvestigationTools(tg_client=client)

print("=" * 70)
print("AUDIT: LIVE HISTORICAL CASES & HHG-003 CONTEXT SYNTHESIS")
print("=" * 70)

# 1. Raw GSQL Query with Customer ID
print("\n[1] Raw GSQL get_historical_cases(cust='C08623'):")
raw_gsql_res = conn.runInstalledQuery("get_historical_cases", {"cust": ("C08623", "Customer"), "top_k": 20})
for d in raw_gsql_res:
    for k, v in d.items():
        print(f"  {k} ({len(v)} vertices):")
        for item in v:
            attrs = item.get("attributes", {})
            print(f"    - ID: {item.get('v_id')}, outcome={attrs.get('outcome')}, pattern={attrs.get('pattern')}, exposure=${attrs.get('exposure_usd')}, card={attrs.get('card_id')}, n_txns={attrs.get('n_txns')}")

# 2. Tools get_historical_cases(customer_id="C08623")
print("\n[2] Tools get_historical_cases(customer_id='C08623'):")
cases_cust = tools.get_historical_cases(customer_id="C08623", top_k=20)
print(f"  Total returned: {len(cases_cust)}")
for c in cases_cust:
    print(f"    - Case {c.case_id}: outcome={c.outcome}, pattern={c.pattern}, exposure=${c.exposure_usd}, card={c.card_id}, reason={c.similarity_reason}")

# 3. Tools get_historical_cases(card_id="C08623-K2")
print("\n[3] Tools get_historical_cases(card_id='C08623-K2'):")
cases_card = tools.get_historical_cases(card_id="C08623-K2", top_k=20)
print(f"  Total returned: {len(cases_card)}")
for c in cases_card:
    print(f"    - Case {c.case_id}: outcome={c.outcome}, pattern={c.pattern}, exposure=${c.exposure_usd}, card={c.card_id}")

# 4. MCP Server call_tool("get_historical_cases", {"card_id": "C08623-K2"})
print("\n[4] MCP Server call_tool('get_historical_cases', {'card_id': 'C08623-K2'}):")
mcp = TigerGraphMCPServer(investigation_tools=tools)
mcp_res = mcp.call_tool("get_historical_cases", {"card_id": "C08623-K2"})
print(f"  MCP Tool Status: {mcp_res.get('status')}")
print(f"  MCP Evidence:    {mcp_res.get('evidence')}")
print(f"  MCP Metrics:     {mcp_res.get('metrics')}")

# 5. Synthesizer Context Check for HHG-003
print("\n[5] Synthesizer Context for HHG-003:")
synth = InvestigationContextSynthesizer()
ctx = synth.synthesize_context(
    trigger=InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=3530164,
        customer_id="C08623",
        card_id="C08623-K2",
        model_risk_score=0.40,
        trigger_details="Customer C08623 message: 'I never made this $49.00 purchase. Please check my card.' Refers to 3530164."
    )
)
print(f"  Synthesizer retrieved {len(ctx.historical_case_matches)} historical cases:")
for hm in ctx.historical_case_matches:
    print(f"    - Case {hm.case_id}: outcome={hm.outcome}, pattern={hm.pattern}, exposure=${hm.exposure_usd}, card={hm.card_id}, note={hm.notes[:60]}...")

# 6. Live HHG-003 Vertex attributes in Graph
print("\n[6] Live InvestigationCase HHG-003 in FraudGraph:")
live_hhg003 = conn.getVerticesById("InvestigationCase", "HHG-003")
print(json.dumps(live_hhg003, indent=2))
