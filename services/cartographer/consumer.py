"""Cartographer service consumer - Integrates recon agent with event bus."""
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


def extract_infrastructure_intel(observations: list) -> InfrastructureIntel:
    """Extract structured infrastructure intelligence from text observations."""
    vector_db = None
    model_family = None
    rate_limits = None

    # Combine all observations into one text for pattern matching
    combined = " ".join(observations).lower()

    # Extract vector database
    vector_patterns = ["faiss", "pinecone", "chroma", "weaviate", "qdrant"]
    for pattern in vector_patterns:
        if pattern in combined:
            vector_db = pattern.upper() if pattern == "faiss" else pattern.capitalize()
            break

    # Extract model family
    model_patterns = [
        ("gpt-4", "gpt-4"),
        ("gpt-3", "gpt-3.5"),
        ("claude", "Claude"),
        ("gemini", "Gemini"),
        ("llama", "LLaMA")
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

    # Detect auth type
    if "oauth" in combined:
        auth_type = "OAuth"
    elif "jwt" in combined:
        auth_type = "JWT"
    elif "rbac" in combined or "role-based" in combined:
        auth_type = "RBAC"
    elif "api key" in combined:
        auth_type = "API Key"

    # Detect vulnerabilities
    vuln_patterns = [
        "idor", "injection", "bypass", "weak", "insecure",
        "missing", "broken", "exposed"
    ]
    for pattern in vuln_patterns:
        if pattern in combined:
            vulnerabilities.append(pattern)
            
    # Extract rules
    for obs in observations:
        if obs.startswith("Authorization:") or obs.startswith("Validation:"):
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
        # Look for tool signatures
        # Pattern: "Tool: tool_name(param1: type1, param2: type2)"
        match = re.search(r"Tool:\s*(\w+)\s*\(([^)]*)\)", obs, re.IGNORECASE)
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

        # Publish IF-02 blueprint
        await publish_recon_finished(blueprint.model_dump())

        print(f"[Cartographer] Published reconnaissance blueprint for audit: {request.audit_id}")

    except Exception as e:
        print(f"[Cartographer] Error processing reconnaissance request: {e}")
        import traceback
        traceback.print_exc()
