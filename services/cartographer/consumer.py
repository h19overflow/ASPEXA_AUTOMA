"""Cartographer service consumer - Integrates recon agent with event bus."""
import logging
import re
from datetime import datetime
from libs.events.publisher import broker, publish_recon_finished, CMD_RECON_START
from libs.contracts.recon import (
    ReconRequest,
    ReconBlueprint,
    Intelligence,
    InfrastructureIntel,
    AuthStructure,
    DetectedTool
)
from services.cartographer.agent.graph import run_reconnaissance
from services.cartographer.persistence.s3_adapter import persist_recon_result

logger = logging.getLogger(__name__)


def extract_infrastructure_intel(observations: list) -> InfrastructureIntel:
    """Extract structured infrastructure intelligence from text observations."""
    vector_db = None
    model_family = None
    rate_limits = None

    # Combine all observations into one text for pattern matching
    combined = " ".join(observations).lower()

    # Extract vector database - expanded patterns
    vector_patterns = [
        ("faiss", "FAISS"),
        ("pinecone", "Pinecone"),
        ("chroma", "Chroma"),
        ("weaviate", "Weaviate"),
        ("qdrant", "Qdrant"),
        ("milvus", "Milvus"),
        ("pgvector", "PGVector"),
        ("elasticsearch", "Elasticsearch"),
        ("opensearch", "OpenSearch"),
        ("vector store", None),  # Generic marker
        ("vector database", None),
    ]
    for pattern, name in vector_patterns:
        if pattern in combined:
            if name:
                vector_db = name
                break
            # For generic patterns, try to extract the actual name
            elif not vector_db:
                vector_db = "Vector DB (type unspecified)"

    # Extract model family - expanded patterns
    model_patterns = [
        ("gpt-4", "GPT-4"),
        ("gpt-3.5", "GPT-3.5"),
        ("gpt-3", "GPT-3"),
        ("claude", "Claude"),
        ("gemini", "Gemini"),
        ("llama", "LLaMA"),
        ("mistral", "Mistral"),
        ("cohere", "Cohere"),
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("google", "Google AI"),
        ("text-embedding", "OpenAI Embeddings"),
        ("embedding-001", "Google Embeddings"),
        ("sentence-transformer", "SentenceTransformers"),
    ]
    for pattern, name in model_patterns:
        if pattern in combined:
            model_family = name
            break

    # Extract rate limits
    if "rate limit" in combined or "strict" in combined:
        rate_limits = "strict"
    elif "moderate" in combined:
        rate_limits = "moderate"
    elif "relaxed" in combined:
        rate_limits = "relaxed"

    return InfrastructureIntel(
        vector_db=vector_db,
        model_family=model_family,
        rate_limits=rate_limits
    )


def extract_auth_structure(observations: list) -> AuthStructure:
    """Extract authentication structure from observations."""
    auth_type = "Unknown"
    vulnerabilities = []
    rules = []

    combined = " ".join(observations).lower()

    # Detect auth type - expanded patterns
    auth_patterns = [
        ("oauth 2.0", "OAuth 2.0"),
        ("oauth2", "OAuth 2.0"),
        ("oauth", "OAuth"),
        ("jwt", "JWT"),
        ("json web token", "JWT"),
        ("bearer token", "Bearer Token"),
        ("rbac", "RBAC"),
        ("role-based", "RBAC"),
        ("api key", "API Key"),
        ("api-key", "API Key"),
        ("session", "Session-based"),
        ("cookie", "Cookie-based"),
        ("basic auth", "Basic Auth"),
        ("token", "Token-based"),
    ]
    for pattern, name in auth_patterns:
        if pattern in combined:
            auth_type = name
            break

    # Detect vulnerabilities
    vuln_patterns = [
        "idor", "injection", "bypass", "weak", "insecure",
        "missing", "broken", "exposed", "vulnerability", "exploit"
    ]
    for pattern in vuln_patterns:
        if pattern in combined:
            vulnerabilities.append(pattern)

    # Extract rules - be more lenient with pattern matching
    rule_prefixes = ["authorization:", "validation:", "rule:", "limit:", "threshold:", "require"]
    for obs in observations:
        obs_lower = obs.lower()
        # Check if observation contains rule-like content
        if any(prefix in obs_lower for prefix in rule_prefixes):
            rules.append(obs.strip())
        # Also capture observations mentioning approvals, limits, thresholds
        elif any(keyword in obs_lower for keyword in ["approval", "manager", "limit", "maximum", "minimum", "threshold", "$"]):
            rules.append(obs.strip())

    return AuthStructure(
        type=auth_type,
        rules=list(dict.fromkeys(rules)),  # Deduplicate preserving order
        vulnerabilities=list(set(vulnerabilities))
    )


def extract_detected_tools(observations: list) -> list:
    """Extract tool information from observations."""
    tools = []

    for obs in observations:
        # Pattern 1: "Tool: tool_name(param1: type1, param2: type2)"
        match = re.search(r"Tool[:\s]+[`'\"]?(\w+)[`'\"]?\s*\(([^)]*)\)", obs, re.IGNORECASE)
        if match:
            tool_name = match.group(1)
            params_str = match.group(2)

            # Extract parameter names
            params = []
            if params_str:
                for param in params_str.split(","):
                    param_name = param.split(":")[0].strip()
                    if param_name:
                        params.append(param_name)

            tools.append(DetectedTool(
                name=tool_name,
                arguments=params
            ))
            continue

        # Pattern 2: "tool_name - description" or "`tool_name` - description"
        match = re.search(r"[`'\"]?(\w+)[`'\"]?\s*[-–:]\s*(?:Tool|capable|can|will)", obs, re.IGNORECASE)
        if match:
            tool_name = match.group(1)
            if tool_name.lower() not in ["the", "a", "an", "i", "it", "this", "that"]:
                tools.append(DetectedTool(name=tool_name, arguments=[]))
                continue

        # Pattern 3: Look for function-like mentions "function_name()" or "function_name"
        matches = re.findall(r"[`'\"](\w+)[`'\"]?\s*(?:\([^)]*\))?", obs)
        for fn_name in matches:
            # Filter out common non-tool words
            if fn_name.lower() not in ["tool", "the", "a", "an", "i", "it", "this", "that", "is", "are", "was", "were", "be"]:
                if len(fn_name) > 2 and "_" in fn_name:  # Likely a function name
                    tools.append(DetectedTool(name=fn_name, arguments=[]))

        # Pattern 4: "requires" followed by parameters
        if "require" in obs.lower():
            # Look for parameters mentioned after requires
            param_match = re.findall(r"(?:requires?|needs?|takes?)\s+(?:the\s+)?(\w+(?:_\w+)*)", obs, re.IGNORECASE)
            # These are parameters, not tools - store them for existing tools
            pass

    # Remove duplicates
    seen = set()
    unique_tools = []
    for tool in tools:
        key = (tool.name, tuple(tool.arguments))
        if key not in seen:
            seen.add(key)
            unique_tools.append(tool)

    return unique_tools


@broker.subscriber(CMD_RECON_START)
async def handle_recon_request(message: dict):
    """Handle reconnaissance request from event bus."""
    try:
        # Validate and parse IF-01 request
        request = ReconRequest(**message)

        print(f"[Cartographer] Starting reconnaissance for audit: {request.audit_id}")

        # Run reconnaissance
        observations = await run_reconnaissance(
            audit_id=request.audit_id,
            target_url=request.target.url,
            auth_headers=request.target.auth_headers,
            scope={
                "depth": request.scope.depth.value,
                "max_turns": request.scope.max_turns,
                "forbidden_keywords": request.scope.forbidden_keywords
            }
        )

        print(f"[Cartographer] Reconnaissance complete. Observations collected:")
        print(f"  - System Prompt: {len(observations.get('system_prompt', []))}")
        print(f"  - Tools: {len(observations.get('tools', []))}")
        print(f"  - Authorization: {len(observations.get('authorization', []))}")
        print(f"  - Infrastructure: {len(observations.get('infrastructure', []))}")

        # Deduplicate system prompts
        system_prompts = list(dict.fromkeys(observations.get("system_prompt", [])))

        # Map observations to IF-02 blueprint
        blueprint = ReconBlueprint(
            audit_id=request.audit_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            intelligence=Intelligence(
                system_prompt_leak=system_prompts,
                detected_tools=extract_detected_tools(observations.get("tools", [])),
                infrastructure=extract_infrastructure_intel(
                    observations.get("infrastructure", []) + observations.get("tools", [])
                ),
                auth_structure=extract_auth_structure(observations.get("authorization", []))
            )
        )

        # Persist to S3 and update campaign stage
        scan_id = f"recon-{request.audit_id}"
        try:
            await persist_recon_result(
                campaign_id=request.audit_id,
                scan_id=scan_id,
                blueprint=blueprint.model_dump(),
                target_url=request.target.url,
            )
            print(f"[Cartographer] Persisted recon to S3: {scan_id}")
        except Exception as e:
            logger.warning(f"Persistence failed (continuing): {e}")

        # Publish IF-02 blueprint with scan_id reference
        payload = blueprint.model_dump()
        payload["recon_scan_id"] = scan_id
        await publish_recon_finished(payload)

        print(f"[Cartographer] Published reconnaissance blueprint for audit: {request.audit_id}")

    except Exception as e:
        print(f"[Cartographer] Error processing reconnaissance request: {e}")
        import traceback
        traceback.print_exc()
