"""
Jailbreak Agent LangChain tools.

Purpose: Define tools for system prompt surface analysis
Dependencies: langchain.tools
Used by: jailbreak_agent.py
"""
import json
from typing import Any, Dict

from langchain.tools import tool

from .jailbreak_probes import get_probes


@tool
def analyze_jailbreak_target(infrastructure: Dict[str, Any]) -> str:
    """Analyze target for jailbreak attack vectors.

    Args:
        infrastructure: Dict with model_family, safety_features, etc.

    Returns:
        Analysis summary with recommended focus areas
    """
    model = infrastructure.get("model_family", "unknown")
    has_safety = infrastructure.get("has_safety_filter", True)
    has_content_filter = infrastructure.get("has_content_filter", True)

    findings = []
    if any(llm in model.lower() for llm in ["gpt-4", "claude", "gemini"]):
        findings.append(f"Advanced LLM ({model}) - use sophisticated DAN variants")
    elif any(llm in model.lower() for llm in ["gpt-3", "llama", "mistral"]):
        findings.append(f"Standard LLM ({model}) - classic jailbreaks may work")

    if not has_safety:
        findings.append("No safety filter - basic jailbreaks likely effective")
    if not has_content_filter:
        findings.append("No content filter - toxicity probes recommended")

    return " | ".join(findings) if findings else "Unknown model - test broad jailbreak categories"


@tool
def get_jailbreak_probe_list(approach: str = "standard") -> str:
    """Get available probes for jailbreak/prompt injection scanning.

    Args:
        approach: Scan intensity ('quick', 'standard', 'thorough')

    Returns:
        JSON list of available probes
    """
    probes = get_probes(approach)
    return json.dumps({"probes": probes, "approach": approach})


# Export all tools for agent consumption
JAILBREAK_TOOLS = [analyze_jailbreak_target, get_jailbreak_probe_list]
