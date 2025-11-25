1. Conceptual Data Model
The schema follows a strict hierarchy:
Target: The asset being tested (e.g., "Customer Service Bot").
Campaign (Audit): A specific testing session (e.g., "Q3 Security Review").
Findings: The raw cracks found by the Swarm.
Operations: The specific attack plans and their execution results.
2. Entity Relationship Diagram (ERD)
Here is the visual map of how these tables connect. Notice the central role of the campaigns table.


3. Schema Specification (Data Definition)
Here are the specific details for the critical tables, specifically focusing on how we store the complex JSON outputs from our agents.
A. campaigns (The Session State)
This table tracks the entire lifecycle.
recon_blueprint (JSONB): Stores the entire output from Phase 1.
Why JSONB? The blueprint structure might change as we add new probes (e.g., adding a "Latency" field next month). We don't want to migrate the DB schema every time the Recon agent gets smarter.
Indexing: We can still query it: SELECT * FROM campaigns WHERE recon_blueprint->'auth_type' = 'oauth'.
B. scan_findings (The Garak Output)
This stores the "Clustered" vulnerabilities from Phase 2.
vuln_type: Indexed string (e.g., injection.sql) for fast lookup by the Strategist.
evidence_payload: The specific string that broke the target (e.g., ' OR 1=1).
raw_log: Stores the full context from Garak for debugging, but the Strategist mostly cares about the evidence_payload.
C. strategy_atlas (The Knowledge Base)
This is the persistence for Phase 3.
skeleton_yaml: Stores the PyRit YAML template text directly.
pyrit_class_ref: The strict allowlist. e.g., pyrit.orchestrator.RedTeamingOrchestrator.
D. sniper_plans (The Bridge)
The generated output from Phase 3 waiting for approval.
generated_config (JSONB): This is the IF-05 payload (The fully hydrated plan with the LLM-generated persona).
status: The State Machine trigger. When this switches from pending_approval to approved, the Event Bus fires the CMD_EXECUTE_ATTACK event.
E. plan_signatures (The Audit Trail)
Critical for Enterprise Security.
digital_signature: A SHA-256 hash of the generated_config blob at the moment of signing.
Security Logic: When Phase 4 (Sniper) starts, it re-hashes the plan. If the hash doesn't match this column, it means someone tampered with the plan in the DB after the human signed it. Execution aborts.
4. The PyRit Sync Strategy (Shadow Storage)
The Problem: PyRit has its own internal memory (usually DuckDB) to track conversation history during an attack. The Solution: Ephemeral vs. Persistent.
Ephemeral (During Phase 4): The Sniper Agent spins up a temporary DuckDB instance for the active attack. This allows PyRit to do its fast, complex queries on conversation history.
Persistent (End of Phase 4): Once the attack is finished (Success/Fail), the Sniper Agent extracts the relevant "Kill Chain" turns (e.g., the 3 turns that led to the leak) and saves them into the main PostgreSQL execution_results table.
Cleanup: The temporary DuckDB file is wiped.
5. Operational View (Traceability)
With this schema, you can answer the following questions effortlessly:
"What happened in the Audit last Tuesday?"
SELECT * FROM campaigns WHERE created_at = 'Tuesday...'
"Show me the proof that we are vulnerable to SQL Injection."
SELECT proof_artifact FROM execution_results JOIN sniper_plans ON ... WHERE strategy_id = 'sql_exfil'
"Who authorized this attack?"
SELECT signer_user_id FROM plan_signatures WHERE plan_id = '...'

