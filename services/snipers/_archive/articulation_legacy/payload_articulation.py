"""
Phase 1: Payload Articulation.

Purpose: Generate articulated attack payloads from campaign intelligence
Role: First phase of attack flow - produces payloads ready for conversion

Sequential execution of 2 nodes:
1. InputProcessingNode - Load and parse S3 campaign intelligence
2. PayloadArticulationNodePhase3 - Generate attack payloads

NOTE: Chain selection is handled by adapt_node in the adaptive loop.
      PayloadArticulation does NOT select chains - this is intentional.

Usage:
    from services.snipers.attack_phases import PayloadArticulation

    phase1 = PayloadArticulation()
    result = await phase1.execute(
        campaign_id="fresh1",
        payload_count=3,
        framing_types=["qa_testing", "debugging"],
    )

    # Result contains articulated_payloads (NO selected_chain)
    # Ready for handoff to Phase 2 (Conversion)
"""

import logging

from libs.persistence import S3PersistenceAdapter
from libs.config.settings import get_settings

from services.snipers.utils.nodes.input_processing_node import InputProcessingNode
from services.snipers.utils.nodes.payload_articulation_node import PayloadArticulationNodePhase3
from services.snipers.models import Phase1Result
from services.snipers.utils.persistence.s3_adapter import S3InterfaceAdapter
from services.snipers.utils.llm_provider import get_default_agent
from services.snipers.utils.prompt_articulation.extractors.recon_extractor import (
    ReconIntelligenceExtractor,
)

logger = logging.getLogger(__name__)


class PayloadArticulation:
    """
    Phase 1: Payload Articulation.

    Executes: Input Processing → Payload Articulation

    NOTE: Chain selection is handled by adapt_node (single source of truth).
    Output can be inspected/modified before passing to Phase 2.
    """

    def __init__(self):
        """Initialize with real S3 client and LLM agent."""
        settings = get_settings()

        # Create S3 adapter
        self._s3_persistence = S3PersistenceAdapter(
            bucket_name=settings.s3_bucket_name,
            region=settings.aws_region,
        )

        # Create interface adapter for payload articulation
        self._s3_interface = S3InterfaceAdapter(self._s3_persistence)

        # Get LLM agent
        self._llm_agent = get_default_agent()

        # Initialize nodes (chain selection removed - handled by adapt_node)
        self.input_processor = InputProcessingNode()
        self.payload_articulator = PayloadArticulationNodePhase3(
            self._llm_agent,
            self._s3_interface
        )

        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        campaign_id: str,
        payload_count: int = 1,
        framing_types: list[str] | None = None,
        custom_framing: dict[str, str] | None = None,
        recon_custom_framing: dict[str, str] | None = None,
    ) -> Phase1Result:
        """
        Execute Phase 1: Input → Payload Articulation.

        NOTE: Chain selection is handled by adapt_node (single source of truth).

        Args:
            campaign_id: Campaign ID to load intelligence from S3
            payload_count: Number of payloads to generate (1-6)
            framing_types: Specific framing types to use (None = auto)
                Options: qa_testing, compliance_audit, documentation, debugging, educational, research
            custom_framing: Custom framing strategy (overrides framing_types)
                Example: {"name": "IT Support", "system_context": "...", "user_prefix": "...", "user_suffix": "..."}
            recon_custom_framing: Recon-intelligence-based custom framing (overrides custom_framing and framing_types)
                Example: {"role": "Tech shop customer", "context": "completing a purchase", "justification": "..."}

        Returns:
            Phase1Result with articulated payloads (no selected_chain)
        """
        state = await self.input_processor.process_input(campaign_id)

        # Extract structured recon intelligence immediately
        extractor = ReconIntelligenceExtractor()
        recon_blueprint = state.get("recon_intelligence") or {}
        recon_intelligence = extractor.extract(recon_blueprint)

        # Log extracted intelligence
        for tool in recon_intelligence.tools:
            self.logger.info(f"      • {tool.tool_name}")
            if tool.business_rules:
                self.logger.info(
                    f"        Business Rules: {len(tool.business_rules)} rules"
                )
            if tool.parameters:
                formats = [
                    p.format_constraint for p in tool.parameters if p.format_constraint
                ]
                if formats:
                    self.logger.info(f"        Format Constraints: {formats}")

        # Add payload configuration to state
        state["payload_config"] = {
            "payload_count": min(max(1, payload_count), 6),
            "framing_types": framing_types,
            "exclude_high_risk": True,
            "custom_framing": custom_framing,
            "recon_custom_framing": recon_custom_framing,
        }

        # Add structured recon intelligence to state
        state["recon_intelligence_structured"] = recon_intelligence

        # Log extracted info
        tools = state["recon_intelligence"].get("tools", [])
        defenses = state["pattern_analysis"].get("defense_mechanisms", [])
        objective = state["attack_plan"].get("objective", "")
        vulnerabilities = state.get("garak_vulnerabilities", [])

        for tool in tools:
            self.logger.info(f"    - {tool}")


        if vulnerabilities:
            vuln = vulnerabilities[0]
            self.logger.info(f"  Garak finding: {vuln.get('detector', 'unknown')} (severity: {vuln.get('severity', 'unknown')})")

        # NOTE: Chain selection removed - handled by adapt_node (single source of truth)

        # Log whether XML tags will be used
        has_tool_intel = (
            recon_intelligence
            and recon_intelligence.tools
            and any(t.parameters or t.business_rules for t in recon_intelligence.tools)
        )

        if has_tool_intel:
            self.logger.info(
                f"    Tools to exploit: {[t.tool_name for t in recon_intelligence.tools]}"
            )
        else:
            self.logger.info("  ⚠ Using generic prompts (no tool intelligence)")

        payload_result = await self.payload_articulator.articulate_payloads(state)
        articulated_payloads = payload_result.get("articulated_payloads", [])
        framing_type = payload_result.get("selected_framing")
        framing_types_used = payload_result.get("framing_types_used", [])
        context_summary = payload_result.get("payload_context", {})

        framing_str = framing_type.value if hasattr(framing_type, 'value') else str(framing_type) if framing_type else "unknown"
        self.logger.info(f"  Framing type: {framing_str}")
        self.logger.info(f"  Framing types used: {framing_types_used}")
        self.logger.info(f"  Payloads generated: {len(articulated_payloads)}")

        for i, payload in enumerate(articulated_payloads):
            self.logger.info(f"  Payload {i+1} length: {len(payload)} chars")

        # Build result - ready for handoff to Phase 2
        # NOTE: selected_chain removed - handled by adapt_node
        result = Phase1Result(
            campaign_id=campaign_id,
            articulated_payloads=articulated_payloads,
            framing_type=framing_str,
            framing_types_used=framing_types_used,
            context_summary=context_summary,
            garak_objective=objective,
            defense_patterns=defenses,
            tools_detected=tools,
        )

        return result

