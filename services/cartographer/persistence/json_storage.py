"""JSON file-based persistence for reconnaissance results.

Saves reconnaissance results in the IF-02 format as defined in docs/data_contracts.md
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from services.cartographer.response_format import Deduction


def _parse_tool_observation(observation: str) -> Dict[str, Any]:
    """Parse a tool observation string to extract name and arguments.
    
    Example inputs:
        "Tool: fetch_customer_balance(customer_id: str)"
        "Tool name: process_refund_transaction with params: transaction_id, amount, reason"
    """
    tool_info = {"name": "", "arguments": []}
    
    # Try to extract tool name and parameters
    obs_lower = observation.lower()
    
    # Look for function signature pattern: name(param1: type, param2: type)
    if '(' in observation and ')' in observation:
        parts = observation.split('(', 1)
        name_part = parts[0].strip()
        
        # Extract just the function name (remove "Tool:" prefix if present)
        if ':' in name_part:
            tool_info["name"] = name_part.split(':', 1)[1].strip()
        else:
            tool_info["name"] = name_part.strip()
        
        # Extract parameters
        params_part = parts[1].split(')', 1)[0]
        if params_part.strip():
            # Split by comma and extract parameter names
            for param in params_part.split(','):
                param = param.strip()
                if param:
                    # Extract parameter name (before colon if type is specified)
                    param_name = param.split(':')[0].strip()
                    tool_info["arguments"].append(param_name)
    else:
        # Fallback: just extract tool name
        if ':' in observation:
            tool_info["name"] = observation.split(':', 1)[1].split()[0].strip()
    
    return tool_info


def _parse_infrastructure(observations: List[str]) -> Dict[str, str]:
    """Parse infrastructure observations into structured format."""
    infra = {}
    
    for obs in observations:
        obs_lower = obs.lower()
        
        # Database detection
        if 'postgresql' in obs_lower or 'postgres' in obs_lower:
            infra['database'] = 'PostgreSQL'
        elif 'mysql' in obs_lower:
            infra['database'] = 'MySQL'
        elif 'mongodb' in obs_lower:
            infra['database'] = 'MongoDB'
        
        # Vector DB detection
        if 'faiss' in obs_lower:
            infra['vector_db'] = 'FAISS'
        elif 'pinecone' in obs_lower:
            infra['vector_db'] = 'Pinecone'
        elif 'weaviate' in obs_lower:
            infra['vector_db'] = 'Weaviate'
        elif 'chroma' in obs_lower:
            infra['vector_db'] = 'Chroma'
        
        # Model detection
        if 'gpt-4' in obs_lower:
            infra['model_family'] = 'gpt-4'
        elif 'gpt-3' in obs_lower:
            infra['model_family'] = 'gpt-3.5'
        elif 'gemini' in obs_lower:
            infra['model_family'] = 'gemini'
        elif 'claude' in obs_lower:
            infra['model_family'] = 'claude'
        
        # Embeddings detection
        if 'openai' in obs_lower and 'embedding' in obs_lower:
            infra['embeddings'] = 'OpenAI'
        elif 'text-embedding' in obs_lower:
            infra['embeddings'] = 'OpenAI text-embedding'
        
        # Rate limits
        if 'rate limit' in obs_lower or 'rate-limit' in obs_lower:
            infra['rate_limits'] = obs
    
    return infra


def _parse_auth_structure(observations: List[str]) -> Dict[str, Any]:
    """Parse authorization observations into structured format."""
    auth = {
        "type": "unknown",
        "rules": [],
        "vulnerabilities": []
    }

    for obs in observations:
        obs_lower = obs.lower()

        # Auth type detection
        if 'rbac' in obs_lower:
            auth['type'] = 'RBAC'
        elif 'jwt' in obs_lower or 'token' in obs_lower:
            auth['type'] = 'JWT'
        elif 'api key' in obs_lower:
            auth['type'] = 'API_KEY'

        # Store all rules
        auth['rules'].append(obs)

        # Vulnerability detection
        if any(keyword in obs_lower for keyword in ['bypass', 'weak', 'missing', 'vulnerable']):
            auth['vulnerabilities'].append(obs)

    return auth


def _extract_deductions_by_category(deductions: List[Deduction]) -> Dict[str, List[Dict[str, str]]]:
    """Extract and organize deductions by category.

    Args:
        deductions: List of Deduction objects from ReconTurn

    Returns:
        Dictionary organized by category with findings and confidence
    """
    organized = {}

    for deduction in deductions:
        if deduction.category not in organized:
            organized[deduction.category] = []

        organized[deduction.category].append({
            "finding": deduction.finding,
            "confidence": deduction.confidence
        })

    return organized


def _deduplicate_observations(observations: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Deduplicate observations while preserving order.

    Args:
        observations: Raw observations dictionary

    Returns:
        Dictionary with deduplicated observations
    """
    dedup = {}

    for category, obs_list in observations.items():
        # Use dict.fromkeys to deduplicate while preserving order
        dedup[category] = list(dict.fromkeys(obs_list))

    return dedup


def _deduplicate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate parsed tools based on name and arguments.

    Args:
        tools: List of parsed tool dictionaries

    Returns:
        List of deduplicated tools
    """
    seen = {}

    for tool in tools:
        # Create a key based on tool name and arguments
        key = (tool['name'], tuple(sorted(tool['arguments'])))

        # Keep first occurrence of each unique tool
        if key not in seen:
            seen[key] = tool

    return list(seen.values())


def transform_to_if02_format(audit_id: str, observations: Dict[str, List[str]]) -> Dict[str, Any]:
    """Transform raw observations to IF-02 Reconnaissance Blueprint format.

    Args:
        audit_id: Unique audit identifier
        observations: Dictionary with categories: system_prompt, tools, authorization, infrastructure

    Returns:
        IF-02 formatted dictionary
    """
    # Deduplicate observations first
    dedup_observations = _deduplicate_observations(observations)

    # Parse tools from deduplicated observations
    detected_tools = []
    for tool_obs in dedup_observations.get('tools', []):
        tool_info = _parse_tool_observation(tool_obs)
        if tool_info['name']:
            detected_tools.append(tool_info)

    # Deduplicate parsed tools
    detected_tools = _deduplicate_tools(detected_tools)

    # Parse infrastructure
    infrastructure = _parse_infrastructure(dedup_observations.get('infrastructure', []))

    # Parse authorization
    auth_structure = _parse_auth_structure(dedup_observations.get('authorization', []))

    # Build IF-02 format (matches ReconBlueprint contract)
    if02_data = {
        "audit_id": audit_id,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intelligence": {
            "system_prompt_leak": dedup_observations.get('system_prompt', []),
            "detected_tools": detected_tools,
            "infrastructure": infrastructure,
            "auth_structure": auth_structure
        },
        "raw_observations": dedup_observations  # Keep deduplicated raw data for reference
    }

    return if02_data


def transform_deductions_to_observations(deductions_by_category: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[str]]:
    """Transform structured deductions into observations format.

    Args:
        deductions_by_category: Dictionary of deductions organized by category

    Returns:
        Observations dictionary with findings as strings
    """
    observations = {}

    for category, deductions in deductions_by_category.items():
        observations[category] = [d["finding"] for d in deductions]

    return observations


def save_reconnaissance_result(
    audit_id: str,
    observations: Dict[str, List[str]],
    output_dir: str = "tests/recon_results",
    deductions: Optional[Dict[str, List[Dict[str, str]]]] = None
) -> str:
    """Save reconnaissance result as JSON in IF-02 format with optional deductions.

    Args:
        audit_id: Unique audit identifier
        observations: Raw observations dictionary from reconnaissance
        output_dir: Directory to save results (default: tests/recon_results)
        deductions: Structured deductions organized by category (optional)

    Returns:
        Path to the saved file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Transform to IF-02 format
    if02_data = transform_to_if02_format(audit_id, observations)

    # Add structured deductions if provided
    if deductions:
        if02_data["structured_deductions"] = deductions

    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{audit_id}_{timestamp}.json"
    filepath = output_path / filename

    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(if02_data, f, indent=2, ensure_ascii=False)

    print(f"[Persistence] Saved reconnaissance result to: {filepath}")
    return str(filepath)


def save_reconnaissance_result_with_deductions(
    audit_id: str,
    observations: Dict[str, List[str]],
    deductions: Dict[str, List[Dict[str, str]]],
    output_dir: str = "tests/recon_results"
) -> str:
    """Convenience wrapper to save results with deductions.

    Args:
        audit_id: Unique audit identifier
        observations: Raw observations dictionary
        deductions: Structured deductions by category
        output_dir: Directory to save results

    Returns:
        Path to the saved file
    """
    return save_reconnaissance_result(audit_id, observations, output_dir, deductions)


def load_reconnaissance_result(filepath: str) -> Dict[str, Any]:
    """Load a reconnaissance result from JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        IF-02 formatted dictionary
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def list_reconnaissance_results(output_dir: str = "tests/recon_results") -> List[str]:
    """List all reconnaissance result files.
    
    Args:
        output_dir: Directory containing results
        
    Returns:
        List of file paths
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return []
    
    return [str(f) for f in output_path.glob("*.json")]
