"""LangGraph state model."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.snipers.models.reasoning import (
    AttackPlan,
    ConverterSelection,
    HumanFeedback,
    PatternAnalysis,
    PayloadGeneration,
)
from services.snipers.models.requests import ExampleFinding
from services.snipers.models.results import AttackResult


class ExploitAgentState(BaseModel):
    """LangGraph state for exploit agent workflow with HITL interrupts."""
    # Input context
    probe_name: str
    example_findings: List[ExampleFinding]
    target_url: str
    recon_intelligence: Optional[Dict[str, Any]] = None
    vulnerability_cluster: Optional[Dict[str, Any]] = None

    # Agent reasoning outputs
    pattern_analysis: Optional[PatternAnalysis] = None
    converter_selection: Optional[ConverterSelection] = None
    payload_generation: Optional[PayloadGeneration] = None
    attack_plan: Optional[AttackPlan] = None

    # Execution results
    attack_results: List[AttackResult] = Field(default_factory=list)

    # Human-in-the-Loop state
    human_approved: Optional[bool] = None
    human_feedback: Optional[HumanFeedback] = None
    awaiting_human_review: bool = False

    # Retry and adaptation
    retry_count: int = 0
    max_retries: int = 3

    # Workflow control
    next_action: Optional[str] = None
    error: Optional[str] = None
    completed: bool = False

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
