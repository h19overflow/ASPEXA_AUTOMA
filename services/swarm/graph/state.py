"""
Graph state definition for Swarm scanning.

Purpose: Define typed state passed between graph nodes
Dependencies: pydantic, typing
Used by: graph/nodes.py, graph/swarm_graph.py
"""
from typing import Any, Dict, List, Optional, Annotated
from operator import add

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Result from a single agent execution.

    Captures the outcome of planning and execution phases for one agent.
    """

    agent_type: str = Field(..., description="Agent identifier (sql, auth, jailbreak)")
    status: str = Field(
        ...,
        description="Execution status: success, failed, blocked, error"
    )
    scan_id: Optional[str] = Field(
        None,
        description="Unique scan identifier for persistence"
    )
    plan: Optional[Dict[str, Any]] = Field(
        None,
        description="The scan plan if planning succeeded"
    )
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Probe execution results"
    )
    vulnerabilities_found: int = Field(
        default=0,
        description="Count of detected vulnerabilities"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if status is failed/error"
    )
    phase: Optional[str] = Field(
        None,
        description="Phase where failure occurred: planning, execution, persistence"
    )
    duration_ms: int = Field(
        default=0,
        description="Total execution time in milliseconds"
    )
    persisted: bool = Field(
        default=False,
        description="Whether results were persisted to S3"
    )


class SwarmState(BaseModel):
    """State passed through the scanning graph.

    Accumulates results as graph executes. Uses LangGraph reducers
    for agent_results and events to support appending from nodes.
    """

    # Input - set at graph start
    audit_id: str = Field(..., description="Audit identifier for tracking")
    target_url: str = Field(..., description="Target endpoint URL")
    agent_types: List[str] = Field(
        ...,
        description="Agent types to run: sql, auth, jailbreak"
    )
    recon_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recon blueprint data from S3 or request"
    )
    scan_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scan configuration (approach, timeout, headers)"
    )
    safety_policy: Optional[Dict[str, Any]] = Field(
        None,
        description="Safety policy with blocked attack vectors"
    )

    # Progress tracking
    current_agent_index: int = Field(
        default=0,
        description="Index of currently processing agent"
    )

    # Observability fields (Phase 2)
    cancelled: bool = Field(
        default=False,
        description="Whether scan was cancelled by user"
    )
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall scan progress (0.0-1.0)"
    )

    # Accumulators (use operator.add reducer to append)
    agent_results: Annotated[List[AgentResult], add] = Field(
        default_factory=list,
        description="Results from completed agents"
    )
    events: Annotated[List[Dict[str, Any]], add] = Field(
        default_factory=list,
        description="SSE events for streaming"
    )

    # Transient state for inter-node communication
    current_plan: Optional[Dict[str, Any]] = Field(
        None,
        description="Plan from current agent's planning phase"
    )

    # Error tracking
    errors: List[str] = Field(
        default_factory=list,
        description="Fatal errors that stop execution"
    )

    @property
    def current_agent(self) -> Optional[str]:
        """Get current agent type being processed."""
        if self.current_agent_index < len(self.agent_types):
            return self.agent_types[self.current_agent_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all agents have been processed."""
        return self.current_agent_index >= len(self.agent_types)

    @property
    def has_fatal_error(self) -> bool:
        """Check if a fatal error occurred."""
        return len(self.errors) > 0

    @property
    def total_agents(self) -> int:
        """Total number of agents to process."""
        return len(self.agent_types)

    model_config = {"extra": "allow"}
