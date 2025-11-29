"""
Phase 3 & 4: Exploit Agent Core Implementation

Core exploit agent using langchain.agents.create_agent with LangGraph workflows.
Implements Human-in-the-Loop (HITL) using LangGraph interrupts.

7-Node workflow:
1. Pattern Analysis: Extract patterns from vulnerability cluster
2. Converter Selection: Multi-strategy chain discovery
3. Payload Articulation: Phase 2 integration with learning
4. Attack Execution: Execute converters against target
5. Composite Scoring: 5-scorer parallel evaluation
6. Learning & Adaptation: Update pattern database
7. Decision Routing: Retry/escalate/success logic

Node implementations are in the nodes/ directory.
Routing logic is in routing.py.
"""
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from services.snipers.agent.state import ExploitAgentState
from services.snipers.agent.nodes.decision_routing_node import route_from_decision
from services.snipers.tools.llm_provider import get_default_agent

# Phase 3 & 4 node implementations
from services.snipers.agent.nodes.pattern_analysis import analyze_pattern_node
from services.snipers.agent.nodes.converter_selection_phase3 import ConverterSelectionNodePhase3
from services.snipers.agent.nodes.payload_articulation_node import PayloadArticulationNodePhase3
from services.snipers.agent.nodes.attack_execution import execute_attack_node
from services.snipers.agent.nodes.composite_scoring_node import CompositeScoringNodePhase34
from services.snipers.agent.nodes.learning_adaptation_node import LearningAdaptationNode
from services.snipers.agent.nodes.decision_routing_node import DecisionRoutingNode

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class ExploitAgent:
    """
    Main exploit agent using langchain.agents.create_agent and LangGraph.

    Orchestrates 7-node workflow for intelligent red teaming:
    1. Pattern Analysis: Extract common patterns from vulnerability cluster
    2. Converter Selection: Multi-strategy chain discovery with learning
    3. Payload Articulation: Generate contextual payloads (Phase 2 integration)
    4. Attack Execution: Execute converters via PyRIT
    5. Composite Scoring: 5-scorer parallel evaluation (Phase 4A)
    6. Learning & Adaptation: Update pattern database for continuous improvement
    7. Decision Routing: Route success/retry/escalate with max retry limit

    Supports Human-in-the-Loop (HITL) via LangGraph interrupts at critical gates.
    """

    def __init__(
        self,
        s3_client: Optional[Any] = None,
        chat_target: Optional[Any] = None,
        checkpointer: Optional[MemorySaver] = None,
    ):
        """
        Initialize exploit agent with Phase 3 & 4 components.

        Args:
            s3_client: S3 interface for pattern database persistence
            chat_target: PyRIT PromptChatTarget for composite scoring
            checkpointer: LangGraph checkpointer for state persistence (default: MemorySaver)
        """
        self.s3_client = s3_client
        self.chat_target = chat_target
        self.checkpointer = checkpointer or MemorySaver()

        # Initialize Phase 3 & 4 node components
        self.converter_selector = ConverterSelectionNodePhase3(s3_client) if s3_client else None
        self.payload_articulator = PayloadArticulationNodePhase3(get_default_agent(), s3_client) if s3_client else None
        self.composite_scorer = CompositeScoringNodePhase34(chat_target) if chat_target else None
        self.learning_adapter = LearningAdaptationNode(s3_client) if s3_client else None
        self.decision_router = DecisionRoutingNode()

        # Create LangGraph workflow for orchestration
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """
        Create LangGraph workflow with all 7 Phase 3 & 4 nodes.

        Orchestrates the complete exploitation process:
        1. Pattern Analysis → Extract patterns from vulnerability cluster
        2. Converter Selection → Multi-strategy chain discovery
        3. Payload Articulation → Phase 2 integration with learning
        4. Attack Execution → Execute converters against target
        5. Composite Scoring → 5-scorer parallel evaluation
        6. Learning & Adaptation → Update pattern database
        7. Decision Routing → Route success/retry/escalate/fail
        """
        workflow = StateGraph(ExploitAgentState)

        # Create node callables that work with LangGraph's async execution
        # These will be called asynchronously by LangGraph's ainvoke
        async def pattern_analysis_node(state: ExploitAgentState) -> Dict[str, Any]:
            """Pattern analysis node."""
            try:
                print("[NODE] pattern_analysis - Starting")
                logger.info("NODE: pattern_analysis - Starting")
                result = await self._run_pattern_analysis(state)
                print(f"[NODE] pattern_analysis - Success: {list(result.keys())}")
                if "error" in result:
                    print(f"[NODE] pattern_analysis - ERROR RETURNED: {result.get('error')}")
                logger.info(f"NODE: pattern_analysis - Success: {list(result.keys())}")
                return result
            except Exception as e:
                print(f"[NODE] pattern_analysis - FAILED: {e}")
                import traceback
                print(traceback.format_exc())
                logger.error(f"NODE: pattern_analysis - FAILED: {e}", exc_info=True)
                return {"error": str(e)}

        async def converter_selection_node(state: ExploitAgentState) -> Dict[str, Any]:
            """Converter selection node."""
            try:
                print("[NODE] converter_selection - Starting")
                if not self.converter_selector:
                    print("[NODE] converter_selection - No converter_selector available")
                    return {"converter_selection": None}
                result = await self.converter_selector.select_converters(state)
                print(f"[NODE] converter_selection - Success: {list(result.keys())}")
                # Map node output to state keys
                if "selected_converters" in result:
                    return {"converter_selection": result["selected_converters"]}
                return result
            except Exception as e:
                print(f"[NODE] converter_selection - FAILED: {e}")
                import traceback
                print(traceback.format_exc())
                return {"converter_selection": None}

        async def payload_articulation_node(state: ExploitAgentState) -> Dict[str, Any]:
            """Payload articulation node."""
            try:
                print("[NODE] payload_articulation - Starting")
                if not self.payload_articulator:
                    print("[NODE] payload_articulation - No payload_articulator available")
                    return {"payload_generation": None}
                result = await self.payload_articulator.articulate_payloads(state)
                print(f"[NODE] payload_articulation - Success: {list(result.keys())}")
                # Map node output to state keys
                if "articulated_payloads" in result:
                    return {"payload_generation": {"generated_payloads": result["articulated_payloads"]}}
                return result
            except Exception as e:
                print(f"[NODE] payload_articulation - FAILED: {e}")
                return {"payload_generation": None}

        async def composite_scoring_node(state: ExploitAgentState) -> Dict[str, Any]:
            """Composite scoring node."""
            try:
                print("[NODE] composite_scoring - Starting")
                if not self.composite_scorer:
                    print("[NODE] composite_scoring - No composite_scorer available")
                    return {"composite_score": None}
                result = await self.composite_scorer.score_responses(state)
                print(f"[NODE] composite_scoring - Success: {list(result.keys())}")
                return result
            except Exception as e:
                print(f"[NODE] composite_scoring - FAILED: {e}")
                return {"error": str(e)}

        async def learning_adaptation_node(state: ExploitAgentState) -> Dict[str, Any]:
            """Learning adaptation node."""
            try:
                print("[NODE] learning_adaptation - Starting")
                if not self.learning_adapter:
                    print("[NODE] learning_adaptation - No learning_adapter available")
                    return {}
                result = await self.learning_adapter.update_patterns(state)
                print(f"[NODE] learning_adaptation - Success: {list(result.keys())}")
                return result
            except Exception as e:
                print(f"[NODE] learning_adaptation - FAILED: {e}")
                return {"error": str(e)}

        async def decision_routing_node(state: ExploitAgentState) -> Dict[str, Any]:
            """Decision routing node."""
            try:
                print("[NODE] decision_routing - Starting")
                result = self.decision_router.route_decision(state)
                print(f"[NODE] decision_routing - Success: decision={result.get('decision')}")
                return result
            except Exception as e:
                print(f"[NODE] decision_routing - FAILED: {e}")
                return {"error": str(e)}

        # Add all 7 nodes
        workflow.add_node("pattern_analysis", pattern_analysis_node)
        workflow.add_node("converter_selection", converter_selection_node)
        workflow.add_node("payload_articulation", payload_articulation_node)
        workflow.add_node("attack_execution", execute_attack_node)
        workflow.add_node("composite_scoring", composite_scoring_node)
        workflow.add_node("learning_adaptation", learning_adaptation_node)
        workflow.add_node("decision_routing", decision_routing_node)

        # Set entry point
        workflow.set_entry_point("pattern_analysis")

        # Linear edges through main nodes
        workflow.add_edge("pattern_analysis", "converter_selection")
        workflow.add_edge("converter_selection", "payload_articulation")
        workflow.add_edge("payload_articulation", "attack_execution")
        workflow.add_edge("attack_execution", "composite_scoring")
        workflow.add_edge("composite_scoring", "learning_adaptation")
        workflow.add_edge("learning_adaptation", "decision_routing")

        # Conditional routing from decision node
        workflow.add_conditional_edges(
            "decision_routing",
            route_from_decision,
            {
                "success": END,
                "retry": "converter_selection",  # Loop back to retry
                "escalate": END,
                "fail": END,
            },
        )

        logger.info("Created Phase 3 & 4 exploit workflow with 7 nodes")

        # Compile with async support
        compiled = workflow.compile(checkpointer=self.checkpointer)
        return compiled

    async def _run_pattern_analysis(self, state: ExploitAgentState) -> Dict[str, Any]:
        """
        Execute pattern analysis node.

        Args:
            state: Current exploit agent state

        Returns:
            State updates with pattern_analysis
        """
        # Use analyze_pattern_node function with default agent
        default_agent = get_default_agent()
        return analyze_pattern_node(default_agent, default_agent, state)

    async def execute_async(
        self, initial_state: ExploitAgentState, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute exploit agent workflow (async).

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

        result = await self.workflow.ainvoke(initial_state, config)
        return result

    def execute(
        self, initial_state: ExploitAgentState, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute exploit agent workflow (sync wrapper).

        Wraps async execution for synchronous API.

        Args:
            initial_state: Initial state for the workflow
            config: Optional configuration (including thread_id for checkpointing)

        Returns:
            Final state after execution
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # Already in async context, create task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.execute_async(initial_state, config))
                return future.result()
        else:
            # Not in async context, run directly
            return asyncio.run(self.execute_async(initial_state, config))
