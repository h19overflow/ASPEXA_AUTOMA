"""
Base agent class for all scanning agents.

Purpose: Define interface and shared response schema for scanning agents
Dependencies: pydantic, langchain>=1.0
Used by: sql/sql_agent.py, auth/auth_agent.py, jailbreak/jailbreak_agent.py
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ProbePlan(BaseModel):
    """Structured output schema for agent planning.

    Used with LangChain v1's ToolStrategy for guaranteed structured responses.
    All agents return this format via response_format=ToolStrategy(ProbePlan).
    """

    probes: List[str] = Field(
        description="List of probe names to execute (e.g., 'dan', 'promptinj')"
    )
    generations: int = Field(
        description="Number of generation attempts per probe",
        ge=1,
        le=20,
        default=5,
    )
    reasoning: Dict[str, str] = Field(
        description="Mapping of probe name to selection reasoning",
        default_factory=dict,
    )


class BaseAgent(ABC):
    """Abstract base for scanning agents.

    Each agent:
    1. Has a system prompt (XML-tagged for clarity)
    2. Has a probe collection specific to its attack surface
    3. Uses LangChain v1 create_agent with Gemini 2.5 Pro
    4. Returns structured ProbePlan via ToolStrategy
    """

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent identifier (e.g., 'sql', 'auth', 'jailbreak')."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent (with XML tags)."""
        pass

    @property
    @abstractmethod
    def available_probes(self) -> List[str]:
        """List of probe names this agent can use."""
        pass

    @abstractmethod
    async def plan(self, recon_context: Dict[str, Any]) -> ProbePlan:
        """Use LLM to analyze recon and select probes.

        Implementation should:
        1. Create LangChain agent with create_agent()
        2. Use ToolStrategy(ProbePlan) for structured output
        3. Invoke with recon context
        4. Return result["structured_response"]

        Args:
            recon_context: Intelligence from recon phase including:
                - infrastructure: Dict with database, model_family, etc.
                - detected_tools: List of tool definitions
                - approach: 'quick', 'standard', or 'thorough'

        Returns:
            ProbePlan with selected probes, generations, and reasoning
        """
        pass
