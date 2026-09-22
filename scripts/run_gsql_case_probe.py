import os
import sys
import json
from pathlib import Path
import pandas as pd

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.core.config import settings
from src.data.loader import load_case_pack
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.analysis.pattern_detector import FraudPatternDetector

def run_case_probe(output_dir: Path = None):
    out_path = output_dir or (settings.base_dir / "docs" / "examples")
    out_path.mkdir(parents=True, exist_ok=True)
    
    cp = load_case_pack()
    tools = TigerGraphInvestigationTools()
    detector = FraudPatternDetector(tools)
    
    print(f"[*] Running GSQL Investigation Case Probe across {len(cp)} benchmark cases...")
    print(f"[*] Backend Provider: {'Live TigerGraph' if tools.is_live() else 'SampleGraphClient (Offline Adapter)'}")
    
    probe_results = []
    
    for _, row in cp.iterrows():
        case_id = str(row["case_id"])
        flagged_tid = str(row["flagged_txn_id"])
        cust_id = str(row["customer_id"])
        card_id = str(row["card_id"])
        trigger_type = str(row["trigger_type"])
        
        # 1. Transaction Detail
        tx = tools.get_transaction(flagged_tid)
        
        # 2. Historical Cases
        hist_cases = tools.get_historical_cases(customer_id=cust_id, card_id=card_id, top_k=3)
        
        # 3. Shared Devices
        shared_dev = tools.find_shared_devices(tx.profile_id) if tx and tx.profile_id else None
        
        # 4. Velocity
        vel = tools.detect_velocity(card_id)
        
        # 5. Regional Anomaly
        reg = tools.detect_regional_anomaly(flagged_tid)
        
        # 6. Card Testing
        testing = tools.detect_card_testing(card_id)
        
        # 7. Connected Cards
        connected = tools.find_connected_cards(card_id)
        
        # 8. Pattern Detection
        patterns = detector.detect_patterns(flagged_tid)
        top_pattern = patterns[0] if patterns else None
        
        res = {
            "case_id": case_id,
            "trigger_type": trigger_type,
            "flagged_transaction_id": flagged_tid,
            "customer_id": cust_id,
            "card_id": card_id,
            "transaction_amount_usd": tx.amount if tx else 0.0,
            "channel": tx.channel if tx else "",
            "model_risk_score": tx.risk_score if tx else 0.0,
            "historical_cases_count": len(hist_cases),
            "historical_case_ids": [c.case_id for c in hist_cases],
            "is_shared_device": shared_dev.is_shared if shared_dev else False,
            "shared_device_profile": tx.profile_id if shared_dev and shared_dev.is_shared else "",
            "connected_cards_count": len(connected.connected_cards),
            "connected_cards": connected.connected_cards,
            "is_velocity_spike": vel.is_velocity_spike,
            "is_regional_anomaly": reg.is_anomaly,
            "is_card_testing": testing.is_testing_detected,
            "top_detected_pattern": top_pattern.pattern.value if top_pattern else "none",
            "pattern_heuristic_confidence": top_pattern.heuristic_confidence if top_pattern else 0.0,
            "pattern_claims": top_pattern.claims if top_pattern else [],
        }
        probe_results.append(res)
        print(f"  [+] Probed {case_id}: Txn {flagged_tid} | Amt ${res['transaction_amount_usd']:.2f} | Pattern: {res['top_detected_pattern']} ({res['pattern_heuristic_confidence']:.2f})")

    # Save JSON report
    json_path = out_path / "benchmark_probe_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(probe_results, f, indent=2)
        
    # Save Markdown report
    md_path = out_path / "benchmark_probe_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Benchmark 20-Case GSQL Investigation Probe Report\n\n")
        f.write(f"**Execution Mode:** `{'Live TigerGraph' if tools.is_live() else 'SampleGraphClient (Offline Adapter)'}`  \n")
        f.write(f"**Total Cases Probed:** {len(probe_results)}  \n\n")
        f.write("| Case | Flagged Txn | Customer | Card | Amount | Channel | Model Risk Score | Detected Pattern | Conf | Shared Device | Hist Cases |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in probe_results:
            f.write(f"| `{r['case_id']}` | `{r['flagged_transaction_id']}` | `{r['customer_id']}` | `{r['card_id']}` | ${r['transaction_amount_usd']:.2f} | `{r['channel']}` | {r['model_risk_score']:.2f} | `{r['top_detected_pattern']}` | {r['pattern_heuristic_confidence']:.2f} | {'Yes' if r['is_shared_device'] else 'No'} | {r['historical_cases_count']} |\n")
        
        f.write("\n## Detailed Case Breakdown\n\n")
        for r in probe_results:
            f.write(f"### {r['case_id']} ({r['trigger_type']})\n")
            f.write(f"- **Flagged Txn:** `{r['flagged_transaction_id']}` (${r['transaction_amount_usd']:.2f}, `{r['channel']}`)\n")
            f.write(f"- **Customer & Card:** `{r['customer_id']}` / `{r['card_id']}`\n")
            f.write(f"- **Model Risk Score (Input):** `{r['model_risk_score']:.2f}`\n")
            f.write(f"- **Top Pattern:** `{r['top_detected_pattern']}` (Heuristic Confidence: `{r['pattern_heuristic_confidence']:.2f}`)\n")
            if r['pattern_claims']:
                f.write(f"- **Graph Claims:**\n")
                for c in r['pattern_claims']:
                    f.write(f"  - {c}\n")
            if r['historical_case_ids']:
                f.write(f"- **Historical Case Memory References:** `{', '.join(r['historical_case_ids'])}`\n")
            if r['connected_cards']:
                f.write(f"- **Connected Cards Found:** `{', '.join(r['connected_cards'])}`\n")
            f.write("\n")

    print(f"[SUCCESS] Probe reports generated at:")
    print(f"  - {json_path}")
    print(f"  - {md_path}")
    return probe_results

if __name__ == "__main__":
    run_case_probe()
