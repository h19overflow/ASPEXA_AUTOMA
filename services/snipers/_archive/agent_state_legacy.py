"""
Phase 4: Exploit Agent LangGraph State

State management for the exploit agent workflow using LangGraph v1.
Supports Human-in-the-Loop interrupts at critical decision points.
"""
from typing import Any, Dict, List, Literal, Optional, TypedDict

from services.snipers.models import (
    AttackPlan,
    AttackResult,
    ConverterSelection,
    ExampleFinding,
    HumanFeedback,
    PatternAnalysis,
    PayloadGeneration,
)


# Available framing types for payload articulation
FramingTypeLiteral = Literal[
    "qa_testing",
    "compliance_audit",
    "documentation",
    "debugging",
    "educational",
    "research",
]


class CustomFraming(TypedDict, total=False):
    """
    Custom framing strategy definition.

    Use this to define your own persona/context for payload generation
    instead of using the built-in framing types.

    Example:
        custom_framing = {
            "name": "IT Helpdesk",
            "system_context": "You are an IT helpdesk technician troubleshooting a system issue.",
            "user_prefix": "Hi, I'm from IT support. We're investigating a critical system error.",
            "user_suffix": "Please provide detailed diagnostic information."
        }
    """

    # Human-readable name for the framing
    name: str

    # System context to set the persona (e.g., "You are a QA tester...")
    system_context: str

    # Prefix text to prepend to payload
    user_prefix: str

    # Suffix text to append to payload (optional)
    user_suffix: str


class PayloadConfig(TypedDict, total=False):
    """
    Configuration for payload articulation.

    Options:
    1. Auto-select: Set payload_count, system picks best framing types
    2. Specific types: Set framing_types to use specific built-in framings
    3. Custom: Set custom_framing to define your own persona

    Built-in framing types:
    - qa_testing: QA tester running security tests
    - compliance_audit: Compliance auditor checking policies
    - documentation: Technical writer documenting features
    - debugging: Developer debugging an issue
    - educational: Instructor teaching about the system
    - research: Security researcher analyzing behavior
    """

    # Number of payloads to generate (1-6)
    payload_count: int

    # Specific framing types to use (if None, auto-select based on domain)
    # Options: qa_testing, compliance_audit, documentation, debugging, educational, research
    framing_types: Optional[List[FramingTypeLiteral]]

    # Exclude high-risk framing strategies (default: True)
    exclude_high_risk: bool

    # Custom framing strategy (overrides framing_types if provided)
    # Use this to define your own persona/context for payload generation
    custom_framing: Optional[CustomFraming]


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

    # Payload articulation configuration
    payload_config: Optional[PayloadConfig]

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
    payload_count: int = 1,
    framing_types: Optional[List[FramingTypeLiteral]] = None,
    exclude_high_risk: bool = True,
    custom_framing: Optional[CustomFraming] = None,
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
        payload_count: Number of payloads to generate (1-6)
        framing_types: Specific framing types to use (None = auto-select)
            Options: qa_testing, compliance_audit, documentation, debugging, educational, research
        exclude_high_risk: Whether to exclude high-risk framing strategies
        custom_framing: Custom framing strategy (overrides framing_types)
            Example: {"name": "IT Support", "system_context": "You are IT support...",
                      "user_prefix": "Hi, I'm from IT.", "user_suffix": "Thanks!"}

    Returns:
        Initialized ExploitAgentState
    """
    payload_config: PayloadConfig = {
        "payload_count": min(max(1, payload_count), 6),
        "framing_types": framing_types,
        "exclude_high_risk": exclude_high_risk,
        "custom_framing": custom_framing,
    }

    return ExploitAgentState(
        probe_name=probe_name,
        example_findings=example_findings,
        target_url=target_url,
        recon_intelligence=recon_intelligence,
        vulnerability_cluster=vulnerability_cluster,
        campaign_id=campaign_id,
        payload_config=payload_config,
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
