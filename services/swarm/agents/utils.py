"""
Utility functions for agent operations.
"""
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def build_scan_message(
    scan_input,
    agent_type: str,
) -> str:
    """
    Build input message for agent with all context.
    
    Args:
        scan_input: ScanInput object with all scan configuration
        agent_type: Type of agent
        
    Returns:
        Formatted input message string
    """
    config = scan_input.config
    
    message = f"""
Scan Target: {scan_input.target_url}
Audit ID: {scan_input.audit_id}
Agent Type: {agent_type}

User Configuration:
- Approach: {config.approach}
- Max Probes: {config.max_probes}
- Max Generations: {config.max_generations}
- Agent Override Allowed: {config.allow_agent_override}
"""
    
    if config.custom_probes:
        message += f"- Custom Probes: {config.custom_probes}\n"
    
    if config.generations:
        message += f"- Fixed Generations: {config.generations}\n"
    
    message += f"""
Infrastructure Intelligence:
{json.dumps(scan_input.infrastructure, indent=2)}

Detected Tools:
{json.dumps(scan_input.detected_tools, indent=2)}

Instructions:
1. First use `analyze_target` to assess the intelligence and decide optimal scan parameters
2. Then use `execute_scan` to run the actual security scan
3. Report all findings accurately

"""
    
    if config.allow_agent_override:
        message += "You may adjust probe count and generations based on the intelligence.\n"
    else:
        message += "Use the exact configuration provided by the user.\n"
    
    return message


def validate_agent_type(agent_type: str) -> bool:
    """Validate that agent_type is recognized."""
    from services.swarm.core.config import AgentType
    return agent_type in [e.value for e in AgentType]


def parse_scan_result(result_json: str) -> Dict[str, Any]:
    """Parse scan result JSON string into dictionary."""
    try:
        return json.loads(result_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse scan result: {e}")
        return {"success": False, "error": "Invalid JSON result"}


def format_vulnerability_summary(clusters: List[Dict]) -> str:
    """Format vulnerability clusters into a readable summary."""
    if not clusters:
        return "No vulnerabilities detected."
    
    lines = [f"\nFound {len(clusters)} vulnerability cluster(s):\n"]
    
    for i, cluster in enumerate(clusters, 1):
        lines.append(f"{i}. Category: {cluster.get('category', 'unknown')}")
        lines.append(f"   Severity: {cluster.get('severity', 'unknown')}")
        lines.append(f"   Cluster ID: {cluster.get('cluster_id', 'unknown')}")
        
        evidence = cluster.get('evidence', {})
        if evidence:
            confidence = evidence.get('confidence_score', 0)
            lines.append(f"   Confidence: {confidence:.2%}")
        
        lines.append("")
    
    return "\n".join(lines)
