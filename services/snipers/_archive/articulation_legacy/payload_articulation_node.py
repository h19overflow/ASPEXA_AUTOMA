"""
Phase 3: Payload Articulation Node (Phase 2 Integration).

Generates contextually-framed attack payloads using Phase 2 components:
- FramingLibrary for strategy selection
- PayloadGenerator for LLM-based generation
- EffectivenessTracker for learning and adaptation

Configuration via state.payload_config:
- payload_count: Number of payloads to generate (1-6)
- framing_types: Specific framing types to use (None = auto-cycle)
- exclude_high_risk: Whether to exclude high-risk framing strategies
"""

import logging
from typing import Any

from services.snipers._archive.agent_state_legacy import ExploitAgentState, PayloadConfig, CustomFraming
from services.snipers.utils.prompt_articulation import (
    PayloadContext,
    TargetInfo,
    AttackHistory,
    FramingLibrary,
    PayloadGenerator,
    EffectivenessTracker,
)
from services.snipers.utils.prompt_articulation.models.framing_strategy import FramingType
from services.snipers.utils.prompt_articulation.extractors.recon_extractor import (
    ReconIntelligenceExtractor,
)

logger = logging.getLogger(__name__)

# Default payload configuration
DEFAULT_PAYLOAD_CONFIG: PayloadConfig = {
    "payload_count": 1,
    "framing_types": None,
    "exclude_high_risk": True,
}


class PayloadArticulationNodePhase3:
    """
    Generate intelligent attack payloads using Phase 2 components.

    Integrates:
    - Recon intelligence as target context
    - Attack history and failed patterns
    - Observable defenses
    - Learned framing strategies with effectiveness tracking

    Configuration is read from state.payload_config:
    - payload_count: Number of payloads (1-6), each uses different framing
    - framing_types: List of specific framing types to use
    - exclude_high_risk: Skip high-detection-risk strategies
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

        Reads configuration from state.payload_config:
        - payload_count: Number of payloads to generate (1-6)
        - framing_types: Specific framing types (None = auto-cycle)
        - exclude_high_risk: Skip high-risk strategies

        Args:
            state: Current exploit agent state

        Returns:
            State updates with articulated_payloads
        """
        try:
            campaign_id = state.get("campaign_id", "unknown")
            recon_blueprint = state.get("recon_intelligence") or {}
            pattern_analysis = state.get("pattern_analysis") or {}

            # Read payload configuration from state
            config = state.get("payload_config") or DEFAULT_PAYLOAD_CONFIG
            payload_count = min(max(1, config.get("payload_count", 1)), 6)
            requested_framing_types = config.get("framing_types")
            exclude_high_risk = config.get("exclude_high_risk", True)
            recon_custom_framing = config.get("recon_custom_framing")

            self.logger.info(
                f"Generating {payload_count} attack payload(s) (Phase 2 integration)",
                extra={
                    "campaign_id": campaign_id,
                    "payload_count": payload_count,
                    "requested_framings": requested_framing_types,
                    "exclude_high_risk": exclude_high_risk,
                    "has_recon_framing": recon_custom_framing is not None,
                }
            )

            if recon_custom_framing:
                self.logger.info(
                    f"Using recon-based custom framing: {recon_custom_framing.get('role')} - {recon_custom_framing.get('context')}"
                )

            # Extract structured recon intelligence
            extractor = ReconIntelligenceExtractor()
            recon_intelligence = extractor.extract(recon_blueprint)

            self.logger.info(
                f"Extracted {len(recon_intelligence.tools)} tools with full signatures",
                extra={
                    "campaign_id": campaign_id,
                    "tools": [t.tool_name for t in recon_intelligence.tools],
                    "has_business_rules": any(
                        t.business_rules for t in recon_intelligence.tools
                    ),
                },
            )

            # Build context from available intelligence
            target_domain = self._extract_domain(recon_blueprint)
            discovered_tools = self._extract_tools(recon_blueprint)
            infrastructure = recon_blueprint.get("infrastructure", {})

            # Build attack history
            failed_approaches = state.get("failed_payloads") or []
            successful_patterns = pattern_analysis.get("successful_payloads") or []

            # Extract objective from attack_plan dict
            attack_plan = state.get("attack_plan")
            objective = ""
            if isinstance(attack_plan, dict):
                objective = attack_plan.get("objective", "")

            context = PayloadContext(
                target=TargetInfo(
                    domain=target_domain or "general",
                    tools=discovered_tools,
                    infrastructure=infrastructure,
                ),
                history=AttackHistory(
                    failed_approaches=failed_approaches,
                    successful_patterns=successful_patterns,
                    blocked_keywords=pattern_analysis.get("blocked_keywords") or []
                ),
                observed_defenses=pattern_analysis.get("defense_mechanisms") or [],
                objective=objective,
                recon_intelligence=recon_intelligence,  # Full structured intelligence
                recon_custom_framing=recon_custom_framing,  # Recon-intelligence-based framing
            )

            # Check for custom framing in config
            custom_framing = config.get("custom_framing")

            # Initialize effectiveness tracker
            tracker = EffectivenessTracker(campaign_id=campaign_id)
            try:
                await tracker.load_history()
            except Exception as e:
                self.logger.debug(f"Could not load effectiveness history: {e}")

            # Initialize payload generator
            library = FramingLibrary(effectiveness_provider=tracker)
            generator = PayloadGenerator(agent=self.llm, framing_library=library)

            # Check if we have tool intelligence to exploit
            has_tool_intelligence = bool(
                recon_intelligence
                and recon_intelligence.tools
                and any(t.parameters or t.business_rules for t in recon_intelligence.tools)
            )

            if has_tool_intelligence:
                self.logger.info(
                    f"Using XML-tagged prompts for {len(recon_intelligence.tools)} tools",
                    extra={"campaign_id": campaign_id},
                )

            payloads = []
            framing_types_used: list[Any] = []

            # If custom framing provided, use it instead of built-in types
            if custom_framing:
                payloads, framing_types_used = await self._generate_with_custom_framing(
                    generator, context, custom_framing, payload_count, campaign_id or "unknown"
                )
            else:
                # Determine framing types to use
                framing_types_to_use = self._get_framing_types(
                    requested_framing_types,
                    payload_count,
                    exclude_high_risk,
                    library,
                )

                # Generate multiple payloads with different framing strategies
                # Use retry logic to mitigate transient LLM failures
                max_retries = 2
                generation_errors: list[str] = []

                for framing_type in framing_types_to_use:
                    payload_generated = False

                    for attempt in range(max_retries + 1):
                        try:
                            # NEW: Pass use_tagged_prompts flag when tool intelligence exists
                            payload = await generator.generate(
                                context,
                                framing_type=framing_type,
                                use_tagged_prompts=has_tool_intelligence,
                            )
                            payloads.append(payload.content)
                            framing_types_used.append(framing_type)
                            payload_generated = True

                            self.logger.info(
                                f"Generated payload with {framing_type.value} framing",
                                extra={
                                    "campaign_id": campaign_id,
                                    "framing_type": framing_type.value,
                                    "payload_length": len(payload.content),
                                    "attempt": attempt + 1,
                                }
                            )
                            break  # Success, move to next framing type

                        except Exception as e:
                            error_msg = f"{framing_type.value} attempt {attempt + 1}: {e}"
                            self.logger.warning(
                                f"Payload generation attempt failed: {error_msg}",
                                extra={"campaign_id": campaign_id, "attempt": attempt + 1}
                            )

                            if attempt == max_retries:
                                # Final attempt failed, record the error
                                generation_errors.append(error_msg)
                                self.logger.error(
                                    f"Payload generation failed after {max_retries + 1} attempts for {framing_type.value}",
                                    extra={"campaign_id": campaign_id, "error": str(e)}
                                )

                    if not payload_generated:
                        self.logger.warning(
                            f"Skipping framing type {framing_type.value} after all retries failed",
                            extra={"campaign_id": campaign_id}
                        )

                # Log summary of generation errors if any
                if generation_errors:
                    self.logger.warning(
                        f"Payload generation completed with {len(generation_errors)} failures out of {len(framing_types_to_use)} attempts",
                        extra={
                            "campaign_id": campaign_id,
                            "successful": len(payloads),
                            "failed": len(generation_errors),
                            "errors": generation_errors,
                        }
                    )

            # Fallback if no payloads generated
            if not payloads and objective:
                payloads = [objective]
                framing_types_used = [FramingType.QA_TESTING]

            # Format framing types for output
            framing_output = [
                ft.value if isinstance(ft, FramingType) else str(ft)
                for ft in framing_types_used
            ]

            return {
                "articulated_payloads": payloads,
                "selected_framing": framing_types_used[0] if framing_types_used else None,
                "framing_types_used": framing_output,
                "payload_context": context.to_dict(),
                "attack_objective": objective,
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

    async def _generate_with_custom_framing(
        self,
        generator: PayloadGenerator,
        context: PayloadContext,
        custom_framing: CustomFraming,
        payload_count: int,
        campaign_id: str,
    ) -> tuple[list[str], list[str]]:
        """
        Generate payloads using custom framing strategy.

        Args:
            generator: PayloadGenerator instance
            context: Payload context with target info
            custom_framing: Custom framing definition from config
            payload_count: Number of payloads to generate
            campaign_id: Campaign ID for logging

        Returns:
            Tuple of (payloads list, framing names list)
        """
        from services.snipers.utils.prompt_articulation.models.framing_strategy import (
            FramingStrategy,
        )

        framing_name = custom_framing.get("name", "custom")

        self.logger.info(
            f"Using custom framing: {framing_name}",
            extra={"campaign_id": campaign_id}
        )

        # Create custom FramingStrategy from config
        custom_strategy = FramingStrategy(
            type=FramingType.QA_TESTING,  # Use as base type
            name=framing_name,
            system_context=custom_framing.get("system_context", ""),
            user_prefix=custom_framing.get("user_prefix", ""),
            user_suffix=custom_framing.get("user_suffix", ""),
            domain_effectiveness={"general": 0.8},
            detection_risk="medium",
        )

        # Register custom strategy in library
        generator.framing_library.strategies[FramingType.QA_TESTING] = custom_strategy

        payloads = []
        framing_names = []
        max_retries = 2
        generation_errors: list[str] = []

        for i in range(payload_count):
            payload_generated = False

            for attempt in range(max_retries + 1):
                try:
                    # Generate using the custom strategy
                    payload = await generator.generate(context, framing_type=FramingType.QA_TESTING)
                    payloads.append(payload.content)
                    framing_names.append(f"{framing_name}_{i+1}" if payload_count > 1 else framing_name)
                    payload_generated = True

                    self.logger.info(
                        f"Generated payload with custom framing '{framing_name}'",
                        extra={
                            "campaign_id": campaign_id,
                            "framing_name": framing_name,
                            "payload_length": len(payload.content),
                            "payload_index": i + 1,
                            "attempt": attempt + 1,
                        }
                    )
                    break  # Success

                except Exception as e:
                    error_msg = f"Custom framing {i+1} attempt {attempt + 1}: {e}"
                    self.logger.warning(
                        f"Custom framing payload generation attempt failed: {error_msg}",
                        extra={"campaign_id": campaign_id, "attempt": attempt + 1}
                    )

                    if attempt == max_retries:
                        generation_errors.append(error_msg)
                        self.logger.error(
                            f"Custom framing payload generation failed after {max_retries + 1} attempts",
                            extra={"campaign_id": campaign_id, "framing_name": framing_name, "error": str(e)}
                        )

            if not payload_generated:
                self.logger.warning(
                    f"Skipping custom payload {i+1} after all retries failed",
                    extra={"campaign_id": campaign_id}
                )

        if generation_errors:
            self.logger.warning(
                f"Custom framing generation completed with {len(generation_errors)} failures",
                extra={
                    "campaign_id": campaign_id,
                    "successful": len(payloads),
                    "failed": len(generation_errors),
                }
            )

        return payloads, framing_names

    def _get_framing_types(
        self,
        requested_types: list[Any] | None,
        count: int,
        exclude_high_risk: bool,
        library: FramingLibrary,
    ) -> list[FramingType]:
        """
        Determine which framing types to use for payload generation.

        Args:
            requested_types: User-specified framing types (None = auto)
            count: Number of payloads to generate
            exclude_high_risk: Whether to skip high-risk strategies
            library: FramingLibrary for strategy lookup

        Returns:
            List of FramingType enums to use (cycles if count > available types)
        """
        # If user specified framing types, use those (cycle if needed)
        if requested_types:
            valid_types = []
            for ft_str in requested_types:
                try:
                    valid_types.append(FramingType(ft_str))
                except ValueError:
                    self.logger.warning(f"Unknown framing type: {ft_str}, skipping")

            if not valid_types:
                valid_types = [FramingType.QA_TESTING]

            # Cycle through valid types to reach requested count
            result = []
            for i in range(count):
                result.append(valid_types[i % len(valid_types)])
            return result

        # Auto-select: cycle through all available framing types
        all_types = list(FramingType)

        # Optionally filter high-risk strategies
        if exclude_high_risk:
            filtered = []
            for ft in all_types:
                try:
                    strategy = library.get_strategy(ft)
                    if strategy.detection_risk != "high":
                        filtered.append(ft)
                except ValueError:
                    filtered.append(ft)
            all_types = filtered if filtered else list(FramingType)

        # Cycle through available types to reach requested count
        result = []
        for i in range(count):
            result.append(all_types[i % len(all_types)])
        return result


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

