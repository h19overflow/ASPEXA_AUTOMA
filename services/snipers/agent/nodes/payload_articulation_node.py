"""
Phase 3: Payload Articulation Node (Phase 2 Integration).

Generates contextually-framed attack payloads using Phase 2 components:
- FramingLibrary for strategy selection
- PayloadGenerator for LLM-based generation
- EffectivenessTracker for learning and adaptation
"""

import logging
from typing import Any
from services.snipers.agent.state import ExploitAgentState
from services.snipers.tools.prompt_articulation import (
    PayloadContext,
    TargetInfo,
    AttackHistory,
    FramingLibrary,
    PayloadGenerator,
    EffectivenessTracker,
)

logger = logging.getLogger(__name__)


class PayloadArticulationNodePhase3:
    """
    Generate intelligent attack payloads using Phase 2 components.

    Integrates:
    - Recon intelligence as target context
    - Attack history and failed patterns
    - Observable defenses
    - Learned framing strategies with effectiveness tracking
    """

    def __init__(self, llm: Any, s3_client: Any):
        """
        Initialize payload articulation node.

        Args:
            llm: LLM for payload generation (LangChain BaseChatModel)
            s3_client: S3 interface for effectiveness persistence
        """
        self.llm = llm
        self.s3_client = s3_client
        self.logger = logging.getLogger(__name__)

    async def articulate_payloads(self, state: ExploitAgentState) -> dict[str, Any]:
        """
        Generate contextual attack payloads.

        Args:
            state: Current exploit agent state

        Returns:
            State updates with articulated_payloads
        """
        try:
            campaign_id = state.get("campaign_id", "unknown")
            target_url = state.get("target_url", "")
            recon_blueprint = state.get("recon_intelligence", {})
            vulnerability_cluster = state.get("vulnerability_cluster", {})
            pattern_analysis = state.get("pattern_analysis", {})
            # Read from converter_selection (state key set by core.py wrapper)
            selected_converters = state.get("converter_selection")

            self.logger.info(
                "Generating attack payloads (Phase 2 integration)",
                extra={"campaign_id": campaign_id}
            )

            # Build context from available intelligence
            target_domain = self._extract_domain(recon_blueprint)
            discovered_tools = self._extract_tools(recon_blueprint)
            infrastructure = recon_blueprint.get("infrastructure", {}) if recon_blueprint else {}

            # Build attack history
            failed_approaches = state.get("failed_payloads", [])
            successful_patterns = pattern_analysis.get("successful_payloads", []) if pattern_analysis else []

            context = PayloadContext(
                target=TargetInfo(
                    domain=target_domain or "general",
                    tools=discovered_tools,
                    infrastructure=infrastructure,
                ),
                history=AttackHistory(
                    failed_approaches=failed_approaches,
                    successful_patterns=successful_patterns,
                    blocked_keywords=pattern_analysis.get("blocked_keywords", []) if pattern_analysis else []
                ),
                observed_defenses=pattern_analysis.get("defense_mechanisms", []) if pattern_analysis else [],
                objective=state.get("attack_plan", {}).get("objective", "") if state.get("attack_plan") else "",
            )

            # Initialize effectiveness tracker
            tracker = EffectivenessTracker(campaign_id=campaign_id)
            try:
                await tracker.load_history()  # Load previous campaign data
            except Exception as e:
                self.logger.debug(f"Could not load effectiveness history: {e}")

            # Initialize payload generator
            library = FramingLibrary(effectiveness_provider=tracker)
            generator = PayloadGenerator(agent=self.llm, framing_library=library)

            # Generate payloads using selected converter chain
            converter_names = []
            if selected_converters:
                converter_names = selected_converters.converter_names

            payloads = []
            framing_type = None

            # Generate payload(s)
            try:
                payload = await generator.generate(context)
                payloads.append(payload.content)
                framing_type = payload.framing_type

                self.logger.info(
                    "Generated attack payload",
                    extra={
                        "campaign_id": campaign_id,
                        "framing_type": framing_type.value if framing_type else "unknown",
                        "payload_length": len(payload.content)
                    }
                )

            except Exception as e:
                self.logger.error(
                    f"Payload generation failed: {e}",
                    extra={"campaign_id": campaign_id}
                )
                # Fallback: use converters to transform objective
                if state.get("attack_plan"):
                    objective = state["attack_plan"].get("objective", "")
                    payloads = [objective]

            return {
                "articulated_payloads": payloads,
                "selected_framing": framing_type,
                "payload_context": context.to_dict(),
                "attack_objective": state.get("attack_plan", {}).get("objective", "") if state.get("attack_plan") else ""
            }

        except Exception as e:
            self.logger.error(
                "Payload articulation node failed",
                extra={"campaign_id": state.get("campaign_id"), "error": str(e)}
            )
            raise

    def _extract_domain(self, recon_blueprint: dict[str, Any]) -> str:
        """Extract target domain from recon blueprint."""
        if not recon_blueprint:
            return "general"

        # Check infrastructure for domain hints
        infrastructure = recon_blueprint.get("infrastructure", {})
        if infrastructure.get("domain_type"):
            return infrastructure["domain_type"].lower()

        # Check for service type
        if infrastructure.get("service_type"):
            service = infrastructure["service_type"].lower()
            if "healthcare" in service:
                return "healthcare"
            elif "financial" in service or "bank" in service:
                return "finance"
            elif "education" in service:
                return "education"

        return "general"

    def _extract_tools(self, recon_blueprint: dict[str, Any]) -> list[str]:
        """Extract tool names from recon blueprint."""
        if not recon_blueprint:
            return []

        tools = recon_blueprint.get("tools", [])
        if isinstance(tools, list):
            return tools

        return []


# Module-level async wrapper
async def articulate_payloads_node(state: ExploitAgentState) -> dict[str, Any]:
    """
    LangGraph-compatible node wrapper.

    Inject node instance via partial():
    from functools import partial
    graph.add_node(
        "payload_articulation",
        partial(articulate_payloads_node, node=node_instance)
    )
    """
    raise NotImplementedError(
        "Use functools.partial to inject PayloadArticulationNodePhase3 instance"
    )
