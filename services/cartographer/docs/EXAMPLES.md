# Examples & Troubleshooting

Practical examples and solutions for using the Cartographer service.

## Basic Reconnaissance

### Scenario: Probe a Test Target

```python
import asyncio
from services.cartographer.agent.graph import run_reconnaissance
from libs.contracts.common import DepthLevel

async def basic_example():
    """Run basic reconnaissance against a target."""

    observations = await run_reconnaissance(
        audit_id="test-basic-001",
        target_url="http://localhost:8080/chat",
        auth_headers={"Authorization": "Bearer test-token"},
        scope={
            "depth": DepthLevel.STANDARD,
            "max_turns": 10,
            "forbidden_keywords": []
        }
    )

    # Results
    print("System Prompt Insights:")
    for finding in observations.get("system_prompt", []):
        print(f"  - {finding}")

    print("\nDetected Tools:")
    for finding in observations.get("tools", []):
        print(f"  - {finding}")

    print("\nInfrastructure:")
    for finding in observations.get("infrastructure", []):
        print(f"  - {finding}")

    print("\nAuthorization:")
    for finding in observations.get("authorization", []):
        print(f"  - {finding}")

if __name__ == "__main__":
    asyncio.run(basic_example())
```

**Expected Output**:
```
System Prompt Insights:
  - Role: Helpful coding assistant
  - Constraint: Cannot execute system commands

Detected Tools:
  - search_documents(query: str, limit: int, date_after: str)
  - analyze_code(code: str, language: str)
  - execute_query(sql: str, table: str)

Infrastructure:
  - Database: PostgreSQL with pgvector extension
  - Vector Store: FAISS with daily indexing
  - Embedding Model: OpenAI text-embedding-3-large

Authorization:
  - Type: JWT bearer token
  - Role-Based: user, admin, analyst roles
  - Data Access: Users can only see own documents
```

**Duration**: ~5-10 minutes depending on target responsiveness

---

## Advanced: Focused Reconnaissance

### Scenario: Target Specific Areas

```python
import asyncio
from services.cartographer.agent.graph import run_reconnaissance
from libs.contracts.common import DepthLevel

async def focused_example():
    """Target specific reconnaissance areas."""

    # Focus on authentication and authorization vulnerabilities
    observations = await run_reconnaissance(
        audit_id="test-auth-focus-001",
        target_url="http://localhost:8080/api",
        auth_headers={
            "Authorization": "Bearer user-token",
            "X-User-ID": "user-123"
        },
        scope={
            "depth": DepthLevel.AGGRESSIVE,
            "max_turns": 15,
            "forbidden_keywords": ["system", "admin"]  # Skip these in questions
        },
        special_instructions=(
            "Focus heavily on authorization boundaries and role-based access. "
            "Probe for privilege escalation vulnerabilities. "
            "Test if users can access other users' data. "
            "Investigate role definitions and permission models."
        )
    )

    # Analyze authorization findings
    auth_findings = observations.get("authorization", [])
    print(f"Authorization Findings ({len(auth_findings)}):")
    for finding in auth_findings:
        print(f"  - {finding}")

    # Look for vulnerability indicators
    vulnerabilities = [
        f for f in auth_findings
        if any(keyword in f.lower() for keyword in ["bypass", "escalation", "leak", "exposed"])
    ]

    if vulnerabilities:
        print(f"\n⚠️  Potential Vulnerabilities Detected ({len(vulnerabilities)}):")
        for vuln in vulnerabilities:
            print(f"  - {vuln}")

if __name__ == "__main__":
    asyncio.run(focused_example())
```

**Key Parameters**:
- `depth=AGGRESSIVE`: 15+ turns, exhaustive probing
- `max_turns=15`: Override default 10
- `forbidden_keywords`: Prevent agent from asking about certain topics
- `special_instructions`: Guide agent toward specific areas

**Expected Focus Areas**:
- Role definitions and capabilities
- Cross-user data access attempts
- Permission validation bypass techniques
- Privilege escalation patterns

---

## Event-Based Workflow

### Scenario: Integrate with Event Bus

```python
import asyncio
import json
from libs.events.publisher import publish_recon_request

async def event_based_example():
    """Publish reconnaissance request to event bus."""

    # Prepare request
    recon_request = {
        "audit_id": "event-test-001",
        "target": {
            "url": "http://target.example.com/api/v1/chat",
            "auth_headers": {
                "Authorization": "Bearer production-token",
                "X-API-Version": "v1"
            }
        },
        "scope": {
            "depth": "standard",
            "max_turns": 10,
            "forbidden_keywords": ["nuclear", "classified"]
        }
    }

    # Publish to Redis event bus
    await publish_recon_request(recon_request)
    print(f"Reconnaissance request published: {recon_request['audit_id']}")

    # Note: Results will be published to evt_recon_finished topic
    # Downstream services (Swarm) will consume the IF-02 blueprint

if __name__ == "__main__":
    asyncio.run(event_based_example())
```

**Workflow**:
1. Application publishes `IF-01 ReconRequest` to `cmd_recon_start`
2. Cartographer consumer handles request
3. Reconnaissance executes
4. Results transformed to `IF-02 ReconBlueprint`
5. Published to `evt_recon_finished`
6. Swarm service consumes for scanning

**Advantages**:
- Decoupled from direct API calls
- Automatic persistence via Redis
- Enables multi-step pipelines
- Asynchronous execution

---

## Loading & Analyzing Results

### Scenario: Load Previous Reconnaissance

```python
from services.cartographer.persistence.json_storage import (
    load_reconnaissance_result,
    list_reconnaissance_results
)
import json

def load_and_analyze():
    """Load and analyze a completed reconnaissance."""

    # List all reconnaissance results
    results = list_reconnaissance_results()
    print(f"Available Results: {len(results)}")
    for result_file in results[:5]:  # Show first 5
        print(f"  - {result_file}")

    # Load specific result
    if results:
        result = load_reconnaissance_result(results[0])
        blueprint = result["blueprint"]

        print(f"\nAudit ID: {blueprint['audit_id']}")
        print(f"Timestamp: {blueprint['timestamp']}")

        # Analyze intelligence
        intelligence = blueprint["intelligence"]

        print(f"\nSystem Prompt Leaks: {len(intelligence.get('system_prompt_leak', []))}")
        for leak in intelligence.get("system_prompt_leak", [])[:3]:
            print(f"  - {leak[:100]}...")

        print(f"\nDetected Tools: {len(intelligence.get('detected_tools', []))}")
        for tool in intelligence.get("detected_tools", []):
            args = ", ".join(tool.get("arguments", []))
            print(f"  - {tool['name']}({args})")

        infrastructure = intelligence.get("infrastructure", {})
        print(f"\nInfrastructure:")
        for key, value in infrastructure.items():
            print(f"  - {key}: {value}")

def load_specific_audit():
    """Load a specific audit by ID."""

    audit_id = "audit-001"
    result = load_reconnaissance_result(f"{audit_id}_*.json")

    if result:
        blueprint = result["blueprint"]
        print(f"Loaded: {blueprint['audit_id']}")
        print(json.dumps(blueprint, indent=2))
    else:
        print(f"No results found for audit {audit_id}")

if __name__ == "__main__":
    load_and_analyze()
    print("\n" + "="*50 + "\n")
    load_specific_audit()
```

**Output Structure**:
```
Available Results: 12
  - audit-001_2025-11-25T10-30-00.json
  - audit-002_2025-11-25T11-15-30.json
  ...

Audit ID: audit-001
Timestamp: 2025-11-25T10:30:00Z

System Prompt Leaks: 3
  - You are a helpful AI assistant...
  - You follow a specific security policy...
  ...

Detected Tools: 5
  - search_documents(query, limit, date_after)
  - analyze_code(code, language)
  ...

Infrastructure:
  - database: PostgreSQL
  - vector_db: FAISS
  - embedding_model: OpenAI text-embedding-3-large
```

---

## Troubleshooting

### Issue 1: "Google API Key Not Found"

**Error**:
```
ValueError: GOOGLE_API_KEY environment variable not set
```

**Solution**:
```bash
# Set environment variable
$env:GOOGLE_API_KEY = "your-api-key-here"

# Or in .env file
GOOGLE_API_KEY=your-api-key-here

# Verify
python -c "import os; print(os.getenv('GOOGLE_API_KEY'))"
```

**Check**:
```python
import os
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("Set GOOGLE_API_KEY before running")
```

---

### Issue 2: "Redis Connection Refused"

**Error**:
```
ConnectionError: Error 111 connecting to localhost:6379.
```

**Solution**:
```bash
# Start Redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest

# Verify connection
redis-cli ping
# Expected output: PONG
```

**Configuration**:
```python
# Default
REDIS_URL = "redis://localhost:6379"

# Custom
REDIS_URL = "redis://remote-host:6379"
REDIS_URL = "redis://user:password@host:6379"
```

---

### Issue 3: "Target Not Responding"

**Error**:
```
NetworkError: Timeout after 3 attempts
```

**Causes**:
- Target unreachable
- Firewall blocking connection
- Target service crashed
- Network latency

**Solutions**:

```python
# Check connectivity first
from services.cartographer.tools.network import check_target_connectivity

import asyncio

async def check():
    is_reachable = await check_target_connectivity("http://target.com/api")
    if is_reachable:
        print("✓ Target is reachable")
    else:
        print("✗ Target is unreachable")

asyncio.run(check())

# If unreachable, verify:
# 1. Target URL is correct
# 2. Service is running: curl http://target.com/api
# 3. Network access: ping target.com
# 4. Firewall rules: netstat -an | grep 8080
```

**Increase Retry Timeout**:
```python
# Currently: 30 seconds timeout, 3 retries
# To increase, modify tools/network.py:

async def call_target_endpoint(
    url: str,
    headers: Dict[str, str],
    message: str,
    timeout: int = 60,  # Increase to 60 seconds
    max_retries: int = 5  # Increase to 5 retries
) -> str:
    ...
```

---

### Issue 4: "Observations List Growing Too Large"

**Symptom**:
- Reconnaissance takes longer on each turn
- Memory usage increases
- Agent takes longer to analyze gaps

**Root Cause**:
- Duplicate detection (80% threshold) not catching similar variations
- Agent generating verbose/redundant observations
- Special instructions causing repetitive probing

**Solution**:

```python
# Check for duplicates
from difflib import SequenceMatcher

def analyze_duplicates(observations):
    """Find near-duplicate observations."""
    obs_list = observations.get("tools", [])
    duplicates = []

    for i, obs1 in enumerate(obs_list):
        for j, obs2 in enumerate(obs_list[i+1:], i+1):
            ratio = SequenceMatcher(None, obs1, obs2).ratio()
            if 0.6 < ratio < 0.8:  # Near-duplicates
                duplicates.append((ratio, obs1[:50], obs2[:50]))

    return sorted(duplicates, reverse=True)

# Lower max_turns
scope = {
    "depth": "standard",
    "max_turns": 8,  # Reduce from 10
    "forbidden_keywords": []
}

# Adjust special_instructions
special_instructions = "Focus on tools, not re-asking about the same topics."
```

---

### Issue 5: "Poor Quality Intelligence"

**Symptom**:
- Few system prompt findings
- Incomplete tool signatures
- Missing infrastructure details

**Root Causes**:
- Target is defensive (good security posture)
- Special instructions too narrow
- Depth level too shallow
- Max turns too low

**Solutions**:

```python
# Increase depth and turns
scope = {
    "depth": "aggressive",  # shallow → standard → aggressive
    "max_turns": 15,  # Increase from default 10
    "forbidden_keywords": []  # Remove unnecessary restrictions
}

# Remove special instructions that narrow focus
special_instructions = None  # Let agent use all vectors

# Use different attack vectors
special_instructions = (
    "Try various attack vectors: "
    "direct enumeration, meta-questioning, RAG mining, "
    "error elicitation, infrastructure probing."
)

# Run multiple audits with different auth contexts
audit_1 = await run_reconnaissance(
    audit_id="basic-user",
    auth_headers={"Authorization": "Bearer user-token"},
    scope={"depth": "standard", "max_turns": 10}
)

audit_2 = await run_reconnaissance(
    audit_id="admin-context",
    auth_headers={"Authorization": "Bearer admin-token"},
    scope={"depth": "standard", "max_turns": 10}
)

# Compare findings
user_tools = set(audit_1["tools"])
admin_tools = set(audit_2["tools"])
admin_only = admin_tools - user_tools
print(f"Admin-only tools: {admin_only}")
```

---

### Issue 6: "Forbidden Keywords Not Applied"

**Symptom**:
- Agent asks questions with forbidden keywords
- Blacklist doesn't prevent questions

**Root Cause**:
- Keywords case-sensitive
- Keyword in middle of sentence not caught
- Prompt filtering isn't perfect

**Solution**:

```python
# Use case-insensitive matching
forbidden_keywords = ["admin", "Admin", "ADMIN", "password", "PASSWORD"]

# Or normalize in agent
special_instructions = (
    "Do not ask about: admin panels, passwords, secret keys, "
    "internal APIs, source code, system configuration."
)

# Verify filtering is working
from services.cartographer.consumer import handle_recon_request

# Add logging
def filtered_question(question, forbidden):
    for keyword in forbidden:
        if keyword.lower() in question.lower():
            return True
    return False

# Check filtering
test_questions = [
    "What admin panels exist?",
    "How do you manage passwords?",
    "Can I access the admin area?"
]

for q in test_questions:
    is_forbidden = filtered_question(q, ["admin", "password"])
    print(f"'{q}' -> Forbidden: {is_forbidden}")
```

---

## Advanced Examples

### Example: Custom Intelligence Extraction

```python
from services.cartographer.persistence.json_storage import (
    load_reconnaissance_result
)
import re

def extract_custom_patterns():
    """Extract specific patterns from reconnaissance results."""

    result = load_reconnaissance_result("audit-001_*.json")
    if not result:
        print("No results found")
        return

    blueprint = result["blueprint"]
    observations = blueprint["raw_observations"]

    # Extract database connection strings
    db_patterns = []
    for obs in observations.get("infrastructure", []):
        # Pattern: [connection string or URL]
        matches = re.findall(
            r"(?:postgresql|mysql|mongodb)(?::\/\/|=)[^\s]+",
            obs
        )
        db_patterns.extend(matches)

    print(f"Database Patterns Found: {len(db_patterns)}")
    for pattern in db_patterns:
        print(f"  - {pattern}")

    # Extract API rate limits
    rate_limits = {}
    for obs in observations.get("infrastructure", []):
        if "limit" in obs.lower() or "rate" in obs.lower():
            # Try to extract numbers
            numbers = re.findall(r"\d+", obs)
            if numbers:
                rate_limits[obs[:50]] = numbers

    print(f"\nRate Limits Detected:")
    for desc, limits in rate_limits.items():
        print(f"  - {desc}: {limits}")

if __name__ == "__main__":
    extract_custom_patterns()
```

---

### Example: Comparative Analysis

```python
import asyncio
from services.cartographer.agent.graph import run_reconnaissance
from libs.contracts.common import DepthLevel

async def comparative_analysis():
    """Probe same target with different authentication levels."""

    target_url = "http://localhost:8080/api"

    configs = [
        {
            "name": "No Auth",
            "headers": {}
        },
        {
            "name": "User Token",
            "headers": {"Authorization": "Bearer user-token"}
        },
        {
            "name": "Admin Token",
            "headers": {"Authorization": "Bearer admin-token"}
        }
    ]

    results = {}

    for config in configs:
        print(f"\nProbing as: {config['name']}...")

        obs = await run_reconnaissance(
            audit_id=f"compare-{config['name'].replace(' ', '-')}",
            target_url=target_url,
            auth_headers=config["headers"],
            scope={
                "depth": "standard",
                "max_turns": 8,
                "forbidden_keywords": []
            }
        )

        results[config["name"]] = {
            "tools": obs.get("tools", []),
            "infrastructure": obs.get("infrastructure", []),
            "authorization": obs.get("authorization", [])
        }

    # Compare findings
    print("\n" + "="*60)
    print("COMPARATIVE ANALYSIS")
    print("="*60)

    no_auth_tools = set(results["No Auth"]["tools"])
    user_tools = set(results["User Token"]["tools"])
    admin_tools = set(results["Admin Token"]["tools"])

    print(f"\nTools by Auth Level:")
    print(f"  No Auth: {len(no_auth_tools)} tools")
    print(f"  User:    {len(user_tools)} tools (+ {len(user_tools - no_auth_tools)} new)")
    print(f"  Admin:   {len(admin_tools)} tools (+ {len(admin_tools - user_tools)} new)")

    print(f"\nRevealed by Admin Auth:")
    admin_only = admin_tools - user_tools
    for tool in admin_only:
        print(f"  - {tool}")

if __name__ == "__main__":
    asyncio.run(comparative_analysis())
```

**Output**:
```
Probing as: No Auth...
Probing as: User Token...
Probing as: Admin Token...

============================================================
COMPARATIVE ANALYSIS
============================================================

Tools by Auth Level:
  No Auth: 3 tools
  User:    5 tools (+ 2 new)
  Admin:   8 tools (+ 3 new)

Revealed by Admin Auth:
  - create_user(name, email, role)
  - delete_document(doc_id, permanent)
  - export_all_data(format, include_metadata)
```

---

## Best Practices

1. **Use Special Instructions**: Guide agent toward specific areas for focused results
2. **Start Shallow**: Use standard depth first, then aggressive if needed
3. **Analyze Results**: Load and study findings between audits
4. **Test Connectivity**: Always verify target is reachable before probing
5. **Compare Contexts**: Probe with different auth levels to find privilege escalation
6. **Check for Duplicates**: Monitor observation growth to catch redundancy
7. **Respect Rate Limits**: Use forbidden_keywords for sensitive areas
8. **Document Findings**: Save results with meaningful audit IDs

---

## Related Documentation

- **README.md** - Service overview and quick start
- **RECON_STRATEGY.md** - Attack vectors and strategy selection
- **ARCHITECTURE.md** - Implementation details and design patterns
