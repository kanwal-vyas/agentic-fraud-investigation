# Hackathon Demo Script: Autonomous Agentic Fraud Investigator

**Presenter:** Kanwal Vyas  
**Duration:** 3–5 Minutes  
**Target Audience:** Hackathon Judges, Fraud Operations Managers, and Graph Architects  
**Grounded System Evidence:** Exact outputs from `scripts/run_agent_benchmark.py` and `src/ui/app.py`

---

## 1. Problem Statement (30 Seconds)

> *"Hello everyone. In modern banking, isolated machine learning models flag thousands of high-risk transactions every day. But a risk score of 0.88 is not a verdict—it's just a signal.*
>
> *Human fraud analysts waste hours manually pulling card histories, querying database silos, checking travel logs, and trying to spot coordinated syndicates. This creates huge analyst backlogs and costly false-positive card declines.*
>
> *Today, I present the **TigerGraph Autonomous Fraud Investigator**—an end-to-end agentic system that transforms raw fraud alerts into complete, policy-grounded case files, executes deep graph traversals via TigerGraph MCP, evaluates regulatory SAR mandates, and maintains bi-directional case memory in TigerGraph."*

---

## 2. Trigger Ingestion & Graph Investigation Flow (1 Minute)

> *"Let's look at **Case HHG-003** in our interactive investigation console.*
>
> *The investigation triggers from a customer message: 'I never made this $49.00 purchase. Please check my card.'*
>
> *Notice that the raw machine learning risk score was only 0.40—traditional thresholding would have missed this! But our agent takes over autonomously with an 8-step investigation budget:*
> 1. *It calls `get_transaction` via the **TigerGraph MCP Server**, extracting billing regions, merchant domains, and channel data.*
> 2. *It calls `get_card_history`, establishing customer C08623's spending baseline.*
> 3. *It queries `get_historical_cases` via **GraphRAG**, discovering confirmed prior fraud case CC-2935 on this card, while also separating historical cleared travel false alarms.*
>
> *All evidence items retain strict source provenance tags: `[GRAPH | get_transaction:3530164]` versus `[HISTORICAL CLOSED CASE | CC-2935]`."*

---

## 3. Reasoning, Uncertainty & Policy Guardrails (1 Minute)

> *"Next, the agent synthesizes the evidence in our **Reasoning & Uncertainty Engine**.*
>
> *Unlike naive LLM wrappers that make binary decisions, our agent evaluates contradictory evidence. Here, it identifies that while the customer reported fraud, device fingerprints were missing and the cardholder had cleared prior false alarms. It quantifies uncertainty as `HIGH` with a calibrated confidence of `0.70`.*
>
> *Crucially, the agent does NOT have permission to bypass bank policy. It checks our deterministic **Policy Engine** against Rules R1 through R8.*
>
> *Rule R2 mandates a card block, but enforces our core safety invariant: **`RECOMMENDED != AUTHORIZED != EXECUTED`**.*
>
> *The Next Best Action `BLOCK_CARD` is routed to human supervisor Level L1. The case status is held safely in `ACTION_PENDING_APPROVAL`, preventing unauthorized automated account disruption."*

---

## 4. Controlled Evidence Loop: Before vs After (1 Minute)

> *"Now let's look at **Case HHG-005** to see how our agent handles ambiguity.*
>
> *Initially, HHG-005 had conflicting indicators: an anomalous transaction amount versus a history of legitimate overseas travel. Instead of making an ungrounded guess or abruptly blocking the card, the agent paused in `AWAITING_CUSTOMER_EVIDENCE` and requested 2FA customer travel confirmation.*
>
> *When the simulated customer confirmation arrives confirming legitimate travel, the agent triggers an automated **Reassessment**:*
> - *Assessment shifts from `SUSPICIOUS_BUT_UNCERTAIN` to `LIKELY_BENIGN`.*
> - *Confidence increases to `0.90` with `LOW` uncertainty.*
> - *Next Best Action automatically updates to `MONITOR_CARD`.*
> - *Case lifecycle resolves cleanly as `RESOLVED_BENIGN`, eliminating a false positive!"*

---

## 5. FinCEN SAR Preparation & Case Graph Writeback (45 Seconds)

> *"In high-exposure cases like **HHG-010**, where a shared device profile reveals a multi-card syndicate with $1,000+ exposure, the agent automatically activates our **SAR Preparation Engine** under FinCEN 31 CFR § 1020.320.*
>
> *It generates a complete compliance narrative for FinCEN Form 111 with exact timeline, subject IDs, and regulatory citations.*
>
> *Finally, through **TigerGraph Graph Writeback**, the agent writes the new `Case` vertex back into the graph, linking it to the transaction, card, and connected syndicate entities with zero duplication. Future investigations immediately benefit from this newly created case memory!"*

---

## 6. Conclusion & Evaluation Metrics (15 Seconds)

> *"In our rigorous 20-case benchmark:*
> - *20 out of 20 cases evaluated deterministically*
> - *0 policy violations, 0 unreferenced actions, 0 missing-entity contaminations*
> - *100% test pass rate across all 100 test suites.*
>
> *Thank you, and I invite you to explore the live repository, run the benchmark, and test the console!"*
