"""
Agent Tools Module

Provides agents for the exploit agent's reasoning capabilities with structured Pydantic output.
"""
from services.snipers.agent.agent_tools.pattern_analysis_tool import (
    create_pattern_analysis_agent,
    analyze_pattern_with_context,
)
from services.snipers.agent.agent_tools.converter_selection_tool import (
    create_converter_selection_agent,
    select_converters_with_context,
)
from services.snipers.agent.agent_tools.payload_generation_tool import (
    create_payload_generation_agent,
    generate_payloads_with_context,
)
from services.snipers.agent.agent_tools.scoring_tool import (
    create_scoring_agent,
    score_attack_result,
)

__all__ = [
    "create_pattern_analysis_agent",
    "analyze_pattern_with_context",
    "create_converter_selection_agent",
    "select_converters_with_context",
    "create_payload_generation_agent",
    "generate_payloads_with_context",
    "create_scoring_agent",
    "score_attack_result",
]
