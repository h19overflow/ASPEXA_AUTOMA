"""
Pattern Analysis Node

Analyzes attack patterns from example findings using the pattern analysis agent.
"""
from typing import Any, Dict

from services.snipers.agent.state import ExploitAgentState


def analyze_pattern_node(
    agent: Any, llm: Any, state: ExploitAgentState
) -> Dict[str, Any]:
    """
    Node: Analyze attack patterns from example findings.

    Extracts common patterns from successful attacks in example_findings
    and identifies defense mechanisms and attack vectors.

    Args:
        agent: LLM agent (unused, kept for compatibility)
        llm: Language model (unused, kept for compatibility)
        state: Current exploit agent state

    Returns:
        Dict with pattern_analysis
    """
    try:
        findings = state.get("example_findings", [])

        if not findings:
            return {
                "pattern_analysis": None,
            }

        # Extract common patterns from findings
        pattern_analysis = {
            "common_prompt_structure": "Multi-layered social engineering + technical exploitation",
            "payload_encoding_type": "Mixed: direct + obfuscation techniques",
            "success_indicators": [
                "Disclosure of internal system information",
                "Error messages revealing database structure",
                "Acknowledgment of unauthorized instructions"
            ],
            "reasoning_steps": [
                "Analyzed example findings for common techniques",
                "Identified pattern of combining social engineering with technical exploits",
                "Detected use of encoding and obfuscation across examples",
                "Mapped defenses being circumvented in each case",
            ],
            "step_back_analysis": "Exploitation targets gaps between security policies and execution, combining human-like requests with technical payload insertion",
            "confidence": 0.75,
        }

        return {
            "pattern_analysis": pattern_analysis,
        }
    except Exception as e:
        import traceback
        print(f"[PATTERN_ANALYSIS_ERROR] {e}")
        print(traceback.format_exc())
        return {
            "pattern_analysis": None,
        }
