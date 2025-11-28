"""
Phase 4: Exploit Agent LangGraph State

State management for the exploit agent workflow using LangGraph v1.
Supports Human-in-the-Loop interrupts at critical decision points.
"""
from typing import Any, Dict, List, Optional, TypedDict

from services.snipers.models import (
    AttackPlan,
    AttackResult,
    ConverterSelection,
    ExampleFinding,
    HumanFeedback,
    PatternAnalysis,
    PayloadGeneration,
)


class ExploitAgentState(TypedDict, total=False):
    """
    LangGraph state for exploit agent workflow.

    Maintains all context, reasoning outputs, and human feedback
    throughout the multi-step exploitation process.
    """

    # Core input context
    probe_name: str
    example_findings: List[ExampleFinding]
    target_url: str
    recon_intelligence: Optional[Dict[str, Any]]
    vulnerability_cluster: Optional[Dict[str, Any]]

    # Campaign tracking (for persistence)
    campaign_id: Optional[str]

    # Agent reasoning outputs
    pattern_analysis: Optional[PatternAnalysis]
    converter_selection: Optional[ConverterSelection]
    payload_generation: Optional[PayloadGeneration]
    attack_plan: Optional[AttackPlan]

    # Execution results
    attack_results: List[AttackResult]
    current_payload_index: int

    # Human-in-the-Loop state
    human_approved: Optional[bool]
    human_feedback: Optional[HumanFeedback]
    awaiting_human_review: bool

    # Retry and adaptation state
    retry_count: int
    max_retries: int
    failed_payloads: List[str]

    # Enhanced tracking fields
    failure_analysis: Optional[Dict[str, Any]]  # Failure pattern analysis
    current_payload: Optional[str]               # Currently executing payload
    current_response: Optional[str]              # Current target response
    converter_execution_errors: List[str]        # Track converter failures

    # Workflow control
    next_action: Optional[str]
    error: Optional[str]
    completed: bool

    # Thread ID for checkpointing
    thread_id: str


def create_initial_state(
    probe_name: str,
    example_findings: List[ExampleFinding],
    target_url: str,
    recon_intelligence: Optional[Dict[str, Any]] = None,
    vulnerability_cluster: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    thread_id: str = "default",
    campaign_id: Optional[str] = None,
) -> ExploitAgentState:
    """
    Create initial state for exploit agent workflow.

    Args:
        probe_name: Name of the vulnerable probe
        example_findings: Example findings for pattern learning
        target_url: Target endpoint URL
        recon_intelligence: Optional recon intelligence data
        vulnerability_cluster: Optional vulnerability cluster data
        max_retries: Maximum retry attempts
        thread_id: Thread ID for LangGraph checkpointing
        campaign_id: Optional campaign ID for persistence tracking

    Returns:
        Initialized ExploitAgentState
    """
    return ExploitAgentState(
        probe_name=probe_name,
        example_findings=example_findings,
        target_url=target_url,
        recon_intelligence=recon_intelligence,
        vulnerability_cluster=vulnerability_cluster,
        campaign_id=campaign_id,
        pattern_analysis=None,
        converter_selection=None,
        payload_generation=None,
        attack_plan=None,
        attack_results=[],
        current_payload_index=0,
        human_approved=None,
        human_feedback=None,
        awaiting_human_review=False,
        retry_count=0,
        max_retries=max_retries,
        failed_payloads=[],
        failure_analysis=None,
        current_payload=None,
        current_response=None,
        converter_execution_errors=[],
        next_action="analyze_pattern",
        error=None,
        completed=False,
        thread_id=thread_id
    )
