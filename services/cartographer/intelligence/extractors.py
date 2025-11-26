"""Intelligence extraction functions.

Purpose: Extract structured intelligence from raw text observations
Role: Pattern matching for infrastructure, auth, and tool detection
Dependencies: libs.contracts.recon (InfrastructureIntel, AuthStructure, DetectedTool)
"""

import re
from typing import List

from libs.contracts.recon import (
    InfrastructureIntel,
    AuthStructure,
    DetectedTool,
)


def extract_infrastructure_intel(observations: List[str]) -> InfrastructureIntel:
    """Extract structured infrastructure intelligence from text observations.

    Args:
        observations: List of raw observation strings

    Returns:
        InfrastructureIntel with vector_db, model_family, rate_limits
    """
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
        rate_limits=rate_limits,
    )


def extract_auth_structure(observations: List[str]) -> AuthStructure:
    """Extract authentication structure from observations.

    Args:
        observations: List of raw observation strings

    Returns:
        AuthStructure with type, rules, vulnerabilities
    """
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
        "idor",
        "injection",
        "bypass",
        "weak",
        "insecure",
        "missing",
        "broken",
        "exposed",
        "vulnerability",
        "exploit",
    ]
    for pattern in vuln_patterns:
        if pattern in combined:
            vulnerabilities.append(pattern)

    # Extract rules - be more lenient with pattern matching
    rule_prefixes = [
        "authorization:",
        "validation:",
        "rule:",
        "limit:",
        "threshold:",
        "require",
    ]
    for obs in observations:
        obs_lower = obs.lower()
        # Check if observation contains rule-like content
        if any(prefix in obs_lower for prefix in rule_prefixes):
            rules.append(obs.strip())
        # Also capture observations mentioning approvals, limits, thresholds
        elif any(
            keyword in obs_lower
            for keyword in [
                "approval",
                "manager",
                "limit",
                "maximum",
                "minimum",
                "threshold",
                "$",
            ]
        ):
            rules.append(obs.strip())

    return AuthStructure(
        type=auth_type,
        rules=list(dict.fromkeys(rules)),  # Deduplicate preserving order
        vulnerabilities=list(set(vulnerabilities)),
    )


def extract_detected_tools(observations: List[str]) -> List[DetectedTool]:
    """Extract tool information from observations.

    Args:
        observations: List of raw observation strings

    Returns:
        List of DetectedTool with name and arguments
    """
    tools = []

    for obs in observations:
        # Pattern 1: "Tool: tool_name(param1: type1, param2: type2)"
        match = re.search(
            r"Tool[:\s]+[`'\"]?(\w+)[`'\"]?\s*\(([^)]*)\)", obs, re.IGNORECASE
        )
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

            tools.append(DetectedTool(name=tool_name, arguments=params))
            continue

        # Pattern 2: "tool_name - description" or "`tool_name` - description"
        match = re.search(
            r"[`'\"]?(\w+)[`'\"]?\s*[-–:]\s*(?:Tool|capable|can|will)",
            obs,
            re.IGNORECASE,
        )
        if match:
            tool_name = match.group(1)
            if tool_name.lower() not in ["the", "a", "an", "i", "it", "this", "that"]:
                tools.append(DetectedTool(name=tool_name, arguments=[]))
                continue

        # Pattern 3: Look for function-like mentions "function_name()" or "function_name"
        matches = re.findall(r"[`'\"](\w+)[`'\"]?\s*(?:\([^)]*\))?", obs)
        for fn_name in matches:
            # Filter out common non-tool words
            if fn_name.lower() not in [
                "tool",
                "the",
                "a",
                "an",
                "i",
                "it",
                "this",
                "that",
                "is",
                "are",
                "was",
                "were",
                "be",
            ]:
                if len(fn_name) > 2 and "_" in fn_name:  # Likely a function name
                    tools.append(DetectedTool(name=fn_name, arguments=[]))

        # Pattern 4: "requires" followed by parameters
        # These are parameters, not tools - store them for existing tools
        # (currently a no-op placeholder for future enhancement)

    # Remove duplicates
    seen = set()
    unique_tools = []
    for tool in tools:
        key = (tool.name, tuple(tool.arguments))
        if key not in seen:
            seen.add(key)
            unique_tools.append(tool)

    return unique_tools
