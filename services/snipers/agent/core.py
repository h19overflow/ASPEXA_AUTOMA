"""
Phase 4: Exploit Agent Core Implementation

Core exploit agent using langchain.agents.create_agent with LangGraph workflows.
Implements Human-in-the-Loop (HITL) using LangGraph interrupts.

All agent reasoning steps use create_agent with Pydantic response_format for
structured output validation.

The core handles:
- Agent creation for pattern analysis, converter selection, payload generation, and scoring
- Workflow graph construction with HITL interrupts
- Routing logic between nodes

Actual node implementations are in the nodes/ directory.
Agent tools are in the agent_tools/ directory.
Routing logic is in routing.py.
"""
from functools import partial
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from services.snipers.agent.state import ExploitAgentState
from services.snipers.agent.routing import (
    route_after_human_review,
    route_after_result_review,
    route_after_retry,
)
from services.snipers.agent.agent_tools import (
    create_pattern_analysis_agent,
    create_converter_selection_agent,
    create_payload_generation_agent,
    create_scoring_agent,
)

# Import all node implementations
from services.snipers.agent.nodes import (
    analyze_pattern_node,
    select_converters_node,
    generate_payloads_node,
    create_attack_plan_node,
    human_review_plan_node,
    human_review_result_node,
    execute_attack_node,
    score_result_node,
    handle_retry_node,
)


class ExploitAgent:
    """
    Main exploit agent using langchain.agents.create_agent and LangGraph.

    Creates individual agents for each reasoning step with Pydantic-validated
    structured output, and uses LangGraph for workflow orchestration with HITL:
    1. Pattern Analysis Agent (structured PatternAnalysis output)
    2. Converter Selection Agent (structured ConverterSelection output)
    3. Payload Generation Agent (structured PayloadGeneration output)
    4. Human Review (INTERRUPT)
    5. Attack Execution (INTERRUPT - Human Approval Gate)
    6. Scoring Agent (structured ScoringResult output)
    7. Human Result Review (INTERRUPT)
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        checkpointer: Optional[MemorySaver] = None,
    ):
        """
        Initialize exploit agent.

        Args:
            llm: Language model for agent reasoning (default: Gemini 2.5 Flash)
            checkpointer: LangGraph checkpointer for state persistence (default: MemorySaver)
        """
        self.llm = llm or self._create_default_llm()
        self.checkpointer = checkpointer or MemorySaver()

        # Create specialized agents for each reasoning step
        self.pattern_analysis_agent = create_pattern_analysis_agent(self.llm)
        self.converter_selection_agent = create_converter_selection_agent(self.llm)
        self.payload_generation_agent = create_payload_generation_agent(self.llm)
        self.scoring_agent = create_scoring_agent(self.llm)

        # Create LangGraph workflow for orchestration
        self.workflow = self._create_workflow()

    def _create_default_llm(self) -> BaseChatModel:
        """Create default LLM (Google Gemini 2.5 Flash)."""
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.7, max_output_tokens=8192
        )

    def _create_workflow(self) -> StateGraph:
        """
        Create LangGraph workflow with all nodes and edges.

        The workflow orchestrates the complete exploitation process
        with Human-in-the-Loop interrupts at critical decision points.
        """
        workflow = StateGraph(ExploitAgentState)

        # Create partial functions that include the specialized agents
        analyze_node = partial(
            analyze_pattern_node,
            self.pattern_analysis_agent,
            self.llm,
        )
        select_node = partial(
            select_converters_node,
            self.converter_selection_agent,
            self.llm,
        )
        generate_node = partial(
            generate_payloads_node,
            self.payload_generation_agent,
            self.llm,
        )
        score_node = partial(
            score_result_node,
            self.scoring_agent,
            self.llm,
        )

        # Add nodes
        workflow.add_node("analyze_pattern", analyze_node)
        workflow.add_node("select_converters", select_node)
        workflow.add_node("generate_payloads", generate_node)
        workflow.add_node("create_attack_plan", create_attack_plan_node)
        workflow.add_node("human_review_plan", human_review_plan_node)
        workflow.add_node("execute_attack", execute_attack_node)
        workflow.add_node("score_result", score_node)
        workflow.add_node("human_review_result", human_review_result_node)
        workflow.add_node("handle_retry", handle_retry_node)

        # Set entry point
        workflow.set_entry_point("analyze_pattern")

        # Add edges
        workflow.add_edge("analyze_pattern", "select_converters")
        workflow.add_edge("select_converters", "generate_payloads")
        workflow.add_edge("generate_payloads", "create_attack_plan")
        workflow.add_edge("create_attack_plan", "human_review_plan")

        # Conditional edge after human review (uses routing.py)
        workflow.add_conditional_edges(
            "human_review_plan",
            route_after_human_review,
            {"approved": "execute_attack", "rejected": END, "modify": "generate_payloads"},
        )

        workflow.add_edge("execute_attack", "score_result")
        workflow.add_edge("score_result", "human_review_result")

        # Conditional edge after result review (uses routing.py)
        workflow.add_conditional_edges(
            "human_review_result",
            route_after_result_review,
            {"retry": "handle_retry", "complete": END},
        )

        # Conditional edge after retry handling (uses routing.py)
        workflow.add_conditional_edges(
            "handle_retry",
            route_after_retry,
            {"retry": "generate_payloads", "give_up": END},
        )

        return workflow.compile(checkpointer=self.checkpointer)

    def execute(
        self, initial_state: ExploitAgentState, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute exploit agent workflow.

        Args:
            initial_state: Initial state for the workflow
            config: Optional configuration (including thread_id for checkpointing)

        Returns:
            Final state after execution
        """
        if config is None:
            config = {
                "configurable": {
                    "thread_id": initial_state.get("thread_id", "default")
                }
            }

        result = self.workflow.invoke(initial_state, config)
        return result
