"""
SQL Agent for data surface vulnerability scanning.

Purpose: Plan and execute SQL/XSS/data extraction scans
Dependencies: langchain>=1.0, langchain-google-genai
Used by: services.swarm.agents registry
"""
import json
import logging
from typing import Any, Dict, List

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from services.swarm.agents.base_agent import BaseAgent, ProbePlan

from .sql_probes import SQL_PROBES, get_available_probes, get_probe_categories
from .sql_prompt import SQL_SYSTEM_PROMPT
from .sql_tools import SQL_TOOLS
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)


class SQLAgent(BaseAgent):
    """Agent specializing in SQL injection and data surface attacks.

    Uses LangChain v1 create_agent with Gemini 2.5 Pro for intelligent
    probe selection based on recon intelligence.
    """

    def __init__(self, model_name: str = "google_genai:gemini-2.5-pro"):
        """Initialize SQL agent.

        Args:
            model_name: LangChain model identifier
        """
        self._model_name = model_name
        self._agent = None

    @property
    def agent_type(self) -> str:
        return "sql"

    @property
    def system_prompt(self) -> str:
        return SQL_SYSTEM_PROMPT.format(
            probe_categories=get_probe_categories(),
            available_probes=get_available_probes(),
        )

    @property
    def available_probes(self) -> List[str]:
        return SQL_PROBES

    def _get_or_create_agent(self):
        """Lazy initialization of LangChain agent."""
        if self._agent is None:
            self._agent = create_agent(
                model=self._model_name,
                tools=SQL_TOOLS,
                system_prompt=self.system_prompt,
                response_format=ToolStrategy(ProbePlan),
            )
        return self._agent

    async def plan(self, recon_context: Dict[str, Any]) -> ProbePlan:
        """Use LLM to analyze recon and intelligently select probes.

        Args:
            recon_context: Intelligence from recon phase

        Returns:
            ProbePlan with selected probes and reasoning
        """
        agent = self._get_or_create_agent()

        infrastructure = recon_context.get("infrastructure", {})
        detected_tools = recon_context.get("detected_tools", [])
        approach = recon_context.get("approach", "standard")

        user_message = f"""
        Analyze this target and select SQL/data surface probes:

        Infrastructure: {json.dumps(infrastructure)}
        Detected Tools: {len(detected_tools)} tools found
        Approach: {approach}

        Steps:
        1. Use analyze_sql_infrastructure to assess SQL-specific risks
        2. Use get_sql_probe_list to see available probes for the approach
        3. Select the most relevant probes with reasoning for each

        Focus on probes that test for:
        - SQL/NoSQL injection vulnerabilities
        - Data extraction via error messages
        - Parameter tampering attacks
        """

        logger.info(f"SQLAgent planning with approach: {approach}")

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]}
        )

        return result["structured_response"]
