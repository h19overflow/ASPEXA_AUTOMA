"""
Attack Plan Creation Node

Creates a complete attack plan for human review.
"""
from typing import Any, Dict

from services.snipers.models import AttackPlan
from services.snipers.agent.state import ExploitAgentState


def assess_risk(state: ExploitAgentState) -> str:
    """
    Assess risk level of the attack plan.

    Args:
        state: Current exploit agent state

    Returns:
        Risk assessment string
    """
    probe_name = state["probe_name"]
    pattern = state["pattern_analysis"]

    risk_level = "MEDIUM"

    if pattern.confidence > 0.9:
        risk_level = "LOW"
    elif pattern.confidence < 0.5:
        risk_level = "HIGH"

    return f"""
Risk Level: {risk_level}
Confidence: {pattern.confidence}
Attack Type: {pattern.payload_encoding_type}
Target: {state['target_url']}

Assessment: Based on pattern analysis confidence of {pattern.confidence},
the attack has a {risk_level.lower()} risk profile. The exploit targets
the {probe_name} vulnerability using {pattern.payload_encoding_type}.
"""


def create_attack_plan_node(state: ExploitAgentState) -> Dict[str, Any]:
    """
    Node: Create complete attack plan for human review.

    Assembles all analysis outputs into a comprehensive attack plan
    that will be presented to human reviewers for approval.

    Args:
        state: Current exploit agent state

    Returns:
        Dict with attack_plan, next_action, and awaiting_human_review flag
    """
    if not all([
        state.get("pattern_analysis"),
        state.get("converter_selection"),
        state.get("payload_generation")
    ]):
        return {"error": "Incomplete analysis", "next_action": "error"}

    reasoning_summary = f"""
Pattern Analysis Summary:
- Attack Type: {state['pattern_analysis'].payload_encoding_type}
- Confidence: {state['pattern_analysis'].confidence}

Converter Selection:
- Selected: {', '.join(state['converter_selection'].selected_converters)}

Payload Generation:
- Generated {len(state['payload_generation'].generated_payloads)} payload variants
- Template: {state['payload_generation'].template_used}
"""

    risk_assessment = assess_risk(state)

    attack_plan = AttackPlan(
        probe_name=state["probe_name"],
        pattern_analysis=state["pattern_analysis"],
        converter_selection=state["converter_selection"],
        payload_generation=state["payload_generation"],
        reasoning_summary=reasoning_summary,
        risk_assessment=risk_assessment
    )

    return {
        "attack_plan": attack_plan,
        "next_action": "human_review_plan",
        "awaiting_human_review": True
    }
