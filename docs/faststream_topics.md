Naming Convention
Format: snake_case (type_domain_action)
Prefixes:
cmd_: Imperative Command. (e.g., "Do this"). The producer expects an action.
evt_: Declarative Event. (e.g., "This happened"). The producer is just broadcasting a fact.

1. Stream Registry
Phase 1: Reconnaissance (The Cartographer)
Stream Name
Direction
Pattern
Logic & Definition
cmd_recon_start
Gateway → Cartographer
Direct
The Trigger. Initiates the mapping process. Payload includes target URL, auth headers, and scope constraints.

FastStream: Single Consumer Group (recon_workers).
evt_recon_finished
Cartographer → Swarm
Fan-Out
The Blueprint. Emitted when mapping is complete. Payload contains the "Intelligence Graph" (tools, auth, infrastructure).

FastStream: Multiple Consumer Groups (one for each Swarm Agent type) listen to this same stream to trigger parallel initialization.

Phase 2: Scanning (The Swarm)
Stream Name
Direction
Pattern
Logic & Definition
cmd_scan_start
Gateway → Swarm
Fan-Out
The Dispatch. Triggers the mass-scanning agents. It consumes the Blueprint from Phase 1.

FastStream: The "Trinity" (SQL Agent, Auth Agent, Jailbreak Agent) all subscribe to this stream using different group IDs so they all receive the copy.
evt_vuln_found
Swarm → Strategist
Load Balance
The Signal. High-volume stream of identified vulnerability clusters.

FastStream: A single Consumer Group (strategist_workers) with multiple active workers. Redis distributes messages via Round-Robin to handle the burst.

Phase 3: Planning (The Strategist)
Stream Name
Direction
Pattern
Logic & Definition
evt_plan_proposed
Strategist → Gateway
Direct
The Draft. The synthesized attack plan waiting for approval. Payload contains the generic Sniper Config.

FastStream: Consumed by the Dashboard/Gateway to notify the human user.

Phase 4: Execution (The Snipers)
Stream Name
Direction
Pattern
Logic & Definition
cmd_attack_execute
Gateway → Snipers
Strict Serial
The Warrant. Emitted only after human authorization. Payload contains Signed Sniper Config.

FastStream: strictly Concurrency = 1. Ensures we do not accidentally DDoS the target during the exploit phase.
evt_attack_finished
Snipers → Gateway
Direct
The Verdict. Final Kill Chain Result (logs/proof/score).


2. Configuration Requirements (Redis Specific)
A. Parallel Processing (The "Trinity" & "Strategist" Logic)
Target Stream: evt_vuln_found (and cmd_scan_start for the Trinity).
Redis Concept: Consumer Groups.
Configuration:
Logic: To scale processing speed, simply spin up more instances of the worker container.
FastStream Code:
Python
# Load Balancing (Strategist): 5 containers use SAME group
@broker.subscriber("evt_vuln_found", gr
oup="strategist_cluster")

# Fan-Out (Trinity): 3 agents use DIFFERENT groups
@broker.subscriber("cmd_scan_start", group="agent_sql")
@broker.subscriber("cmd_scan_start", group="agent_auth")




Reason: Redis Streams automatically handle "pending" messages. If a worker crashes, the message is not lost; it remains in the Pending Entries List (PEL) until another worker claims it.
B. Serial Execution (Safety Controls)
Target Stream: cmd_attack_execute
Redis Concept: Single Active Consumer.
Configuration:
Max Workers: Limit the deployment of the Sniper Service to 1 Replica, OR use a locking mechanism.
FastStream Code:
Python
# processing_key ensures strict ordering if needed
@broker.subscriber("cmd_attack_execute", group="sniper_elite")
async def execute_kill_chain(msg):
    # Code handles one target at a time




Reason: To prevent Race Conditions and bans. We must ensure that we never launch parallel exploit chains against the same target endpoint simultaneously.
C. State & Resource Management (The "OOM" Prevention)
Target Streams: All Streams.
Redis Concept: Stream Capping (maxlen).
Configuration:
Unlike Kafka (which uses disk), Redis uses RAM. We must limit stream size to prevent crashing the server.
FastStream Code:
Python
# When publishing, always define a safety cap
await broker.publish(
    payload, 
    stream="evt_vuln_found", 
    maxlen=10000  # Keep only last 10k messages
)




Reason: "Log Compaction" in Redis is manual. By setting maxlen, we ensure that old data (which should have been processed by now) is dropped to save memory, preventing the "RAM Trap."




