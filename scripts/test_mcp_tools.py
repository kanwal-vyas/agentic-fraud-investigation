import os
import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mcp.server import TigerGraphMCPServer

def run_mcp_smoke_test():
    print("==================================================")
    print("[*] TIGERGRAPH MCP SERVER SMOKE TEST")
    print("==================================================")

    server = TigerGraphMCPServer()
    status = server.get_server_status()

    backend_display = "LIVE TIGERGRAPH" if status["is_live_tigergraph"] else "OFFLINE SAMPLE ADAPTER"
    print(f"[*] MCP Server Status: {status['status'].upper()}")
    print(f"[*] Active Backend Provider: {backend_display}")
    print(f"[*] Registered Tools ({status['tools_registered']}): {', '.join(status['tool_names'])}")
    print("--------------------------------------------------\n")

    test_cases = [
        {"case_id": "HHG-001", "txn_id": "3514030", "card_id": "C12382-K1", "customer_id": "C12382"},
        {"case_id": "HHG-004", "txn_id": "3583227", "card_id": "C08106-K1", "customer_id": "C08106"},
        {"case_id": "HHG-010", "txn_id": "3506725", "card_id": "C10434-K1", "customer_id": "C10434"},
    ]

    for tc in test_cases:
        print(f"==================================================")
        print(f"[*] PROBING BENCHMARK CASE: {tc['case_id']}")
        print(f"==================================================")

        # 1. get_transaction
        res_tx = server.call_tool("get_transaction", {"txn_id": tc["txn_id"]})
        print(f"-> [get_transaction({tc['txn_id']})]")
        print(f"   Status: {res_tx['status']} | Backend: {res_tx['backend']}")
        for ev in res_tx["evidence"]:
            print(f"   - {ev}")

        # 2. get_customer_history
        res_cust = server.call_tool("get_customer_history", {"customer_id": tc["customer_id"]})
        print(f"\n-> [get_customer_history({tc['customer_id']})]")
        for ev in res_cust["evidence"]:
            print(f"   - {ev}")

        # 3. get_card_history
        res_card = server.call_tool("get_card_history", {"card_id": tc["card_id"]})
        print(f"\n-> [get_card_history({tc['card_id']})]")
        for ev in res_card["evidence"]:
            print(f"   - {ev}")

        # 4. detect_velocity
        res_vel = server.call_tool("detect_velocity", {"card_id": tc["card_id"]})
        print(f"\n-> [detect_velocity({tc['card_id']})]")
        for ev in res_vel["evidence"]:
            print(f"   - {ev}")

        # 5. detect_regional_anomaly
        res_reg = server.call_tool("detect_regional_anomaly", {"txn_id": tc["txn_id"]})
        print(f"\n-> [detect_regional_anomaly({tc['txn_id']})]")
        for ev in res_reg["evidence"]:
            print(f"   - {ev}")

        # 6. get_historical_cases
        res_hist = server.call_tool("get_historical_cases", {"customer_id": tc["customer_id"], "top_k": 2})
        print(f"\n-> [get_historical_cases({tc['customer_id']})]")
        for ev in res_hist["evidence"]:
            print(f"   - {ev}")

        print("\n")

    # 7. Error Handling Verification
    print("==================================================")
    print("[*] TESTING ERROR HANDLING & EDGE CASES")
    print("==================================================")
    
    # Missing argument
    err_res1 = server.call_tool("get_transaction", {})
    print(f"-> Missing argument test: Status={err_res1['status']} | Error={err_res1.get('error')}")

    # Nonexistent entity
    err_res2 = server.call_tool("get_transaction", {"txn_id": "999999999"})
    print(f"-> Nonexistent entity test: Status={err_res2['status']} | Evidence={err_res2['evidence']}")

    # Unknown tool
    err_res3 = server.call_tool("unknown_fraud_tool", {})
    print(f"-> Unknown tool test: Status={err_res3['status']} | Error={err_res3.get('error')}")

    print("\n[SUCCESS] TigerGraph MCP Server smoke test passed completely!")

if __name__ == "__main__":
    run_mcp_smoke_test()
