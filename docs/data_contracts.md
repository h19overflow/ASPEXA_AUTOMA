Aspexa System: Interface Control & Data Contracts
1. Protocol Standards
Serialization: JSON (Strict Mode).
Date Format: ISO 8601 (YYYY-MM-DDThh:mm:ssZ).
Encoding: UTF-8.
Validation: All payloads must pass Pydantic/JSON Schema validation before processing.

2. Interface Definitions
IF-01: Reconnaissance Request
Topic: cmd_recon_start
Source: API Gateway
Destination: Cartographer
Purpose: The initial instruction to map the target.
JSON
{
  "audit_id": "uuid-v4",
  "target": {
    "url": "https://api.target-llm.com/v1/chat",
    "auth_headers": {
      "Authorization": "Bearer sk-..."
    }
  },
  "scope": {
    "depth": "standard",  // shallow, standard, aggressive
    "max_turns": 10,
    "forbidden_keywords": ["DELETE", "DROP TABLE", "shutdown"]
  }
}


IF-02: Reconnaissance Blueprint
Topic: evt_recon_finished
Source: Cartographer
Destination: Swarm / Gateway
Purpose: The Intelligence Graph. It describes what the target is, so the scanners know how to attack.
JSON
{
  "audit_id": "uuid-v4",
  "timestamp": "2025-11-23T12:00:00Z",
  "intelligence": {
    "system_prompt_leak": ["You are a helpful assistant", "Do not discuss politics"],
    "detected_tools": [
      {
        "name": "search_database",
        "arguments": ["query", "limit"]
      }
    ],
    "infrastructure": {
      "vector_db": "pinecone",
      "model_family": "gpt-4",
      "rate_limits": "strict"
    },
    "auth_structure": {
      "type": "RBAC",
      "vulnerabilities": ["potential_idor"]
    }
  }
}


IF-03: Scan Job Dispatch
Topic: cmd_scan_start
Source: Gateway
Destination: Swarm
Purpose: The Authorization to Scan. It combines the Recon Blueprint with human-defined safety boundaries.
JSON
{
  "job_id": "scan-001",
  "blueprint_context": { ... }, // The IF-02 payload
  "safety_policy": {
    "allowed_attack_vectors": ["injection", "jailbreak"],
    "blocked_attack_vectors": ["dos", "prompt_extraction"],
    "aggressiveness": "medium"
  }
}


IF-04: Vulnerability Cluster
Topic: evt_vuln_found
Source: Swarm
Destination: Strategist
Purpose: A signal that a specific weakness was found.
JSON
{
  "audit_id": "uuid-v4",
  "cluster_id": "vuln-sql-05",
  "category": "injection.sql", // or "compliance.bias", "safety.pii"
  "severity": "high",
  "evidence": {
    "input_payload": "' OR 1=1 --",
    "error_response": "Syntax error in SQL statement...",
    "confidence_score": 0.95
  },
  "affected_component": "tool:search_database"
}


IF-05: The Sniper Plan (Polymorphic)
Topic: evt_plan_proposed
Source: Strategist
Destination: Gateway (Pending Approval)
Purpose: A generated, unsigned plan. The structure changes based on the engine required.
Variant A: Exploitation Plan (PyRit)
JSON
{
  "plan_id": "plan-alpha",
  "engine": "pyrit",
  "objective": "Prove SQL Injection via Search Tool",
  "configuration": {
    "orchestrator": "RedTeamingOrchestrator",
    "strategy_template": "sql_exfiltration_v2",
    "max_turns": 5,
    "conversation_seed": "I need to search for order ID: ' UNION SELECT..."
  }
}

Variant B: Compliance Audit Plan (DeepTeam)
JSON
{
  "plan_id": "plan-beta",
  "engine": "deepteam",
  "objective": "Verify Resistance to Political Bias",
  "configuration": {
    "metric": "Bias",
    "iterations": 20,
    "threshold": 0.7, // Fail if bias score > 0.7
    "scenario": "User asks leading political questions"
  }
}


IF-06: The Attack Warrant
Topic: cmd_attack_execute
Source: Gateway
Destination: Snipers
Purpose: The "Permission to Fire". It wraps IF-05 with a cryptographic signature.
JSON
{
  "warrant_id": "warrant-999",
  "signer_id": "admin_user_alice",
  "digital_signature": "sha256_hash_of_plan_content",
  "approved_plan": { ... } // The complete IF-05 JSON object
}


IF-07: Kill Chain Result -  Must revise , would it be better to have 2 configs baked in a single message to the topic or not.
Topic: evt_attack_finished
Source: Snipers
Destination: Gateway
Purpose: The final proof.
Variant A: Exploitation Proof (PyRit)
JSON
{
  "warrant_id": "warrant-999",
  "status": "VULNERABLE",
  "artifact_type": "kill_chain",
  "data": {
    "steps": [
      {"role": "attacker", "content": "..."},
      {"role": "target", "content": "Here is the admin password..."}
    ],
    "extracted_secret": "password123"
  }
}

Variant B: Compliance Report (DeepTeam)
JSON
{
  "warrant_id": "warrant-999",
  "status": "SAFE", // or "FAILED_COMPLIANCE"
  "artifact_type": "metrics",
  "data": {
    "metric_name": "Bias",
    "average_score": 0.12, // Low bias
    "iterations_run": 20,
    "failure_count": 0
  }
}




3. Critical Integration Rules
The Infrastructure Rule (Phase 1 to 2):
If IF-02: infrastructure_intel contains "PostgreSQL", the Attack Trinity MUST prioritize loading injection.sql probes and MUST deprioritize injection.nosql probes.
The Generative Safety Rule (Phase 3 to4):
The IF-05: generative_content field is the only place where LLM-generated text is allowed. The pyrit_instruction fields (class names) MUST come strictly from the Strategy Atlas (Allowlist). This prevents the "Refiner" LLM from tricking the system into running malicious code.
The Signature Rule (Gate 2 to 4):
The Sniper Service MUST validate digital_signature in IF-06 before execution. If the hash of approved_config does not match the signature, the Sniper must abort immediately (Tamper Protection).

