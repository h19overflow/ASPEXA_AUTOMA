"""
Phase 1: Payload Articulation.

Purpose: Generate articulated attack payloads from campaign intelligence
Role: First phase of attack flow - produces payloads ready for conversion

Sequential execution of 3 nodes:
1. InputProcessingNode - Load and parse S3 campaign intelligence
2. ConverterSelectionNodePhase3 - Select converter chain
3. PayloadArticulationNodePhase3 - Generate attack payloads

Usage:
    from services.snipers.attack_phases import PayloadArticulation

    phase1 = PayloadArticulation()
    result = await phase1.execute(
        campaign_id="fresh1",
        payload_count=3,
        framing_types=["qa_testing", "debugging"],
    )

    # Result contains articulated_payloads and selected_chain
    # Ready for handoff to Phase 2 (Conversion)
"""

import logging

from libs.persistence import S3PersistenceAdapter
from libs.config.settings import get_settings

from services.snipers.utils.nodes.input_processing_node import InputProcessingNode
from services.snipers.utils.nodes.converter_selection_node import ConverterSelectionNodePhase3
from services.snipers.utils.nodes.payload_articulation_node import PayloadArticulationNodePhase3
from services.snipers.models import Phase1Result
from services.snipers.utils.persistence.s3_adapter import S3InterfaceAdapter
from services.snipers.utils.llm_provider import get_default_agent

logger = logging.getLogger(__name__)


class PayloadArticulation:
    """
    Phase 1: Payload Articulation.

    Executes: Input Processing → Chain Selection → Payload Articulation

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

        # Create interface adapter for chain discovery
        self._s3_interface = S3InterfaceAdapter(self._s3_persistence)

        # Get LLM agent
        self._llm_agent = get_default_agent()

        # Initialize nodes
        self.input_processor = InputProcessingNode()
        self.converter_selector = ConverterSelectionNodePhase3(self._s3_interface)
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
    ) -> Phase1Result:
        """
        Execute Phase 1: Input → Chain Selection → Payload Articulation.

        Args:
            campaign_id: Campaign ID to load intelligence from S3
            payload_count: Number of payloads to generate (1-6)
            framing_types: Specific framing types to use (None = auto)
                Options: qa_testing, compliance_audit, documentation, debugging, educational, research
            custom_framing: Custom framing strategy (overrides framing_types)
                Example: {"name": "IT Support", "system_context": "...", "user_prefix": "...", "user_suffix": "..."}

        Returns:
            Phase1Result with selected chain and articulated payloads
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Phase 1: Payload Articulation - Campaign {campaign_id}")
        self.logger.info(f"{'='*60}\n")

        # Step 1: Input Processing
        self.logger.info("[Step 1/3] Input Processing")
        self.logger.info("-" * 40)
        state = await self.input_processor.process_input(campaign_id)

        # Add payload configuration to state
        state["payload_config"] = {
            "payload_count": min(max(1, payload_count), 6),
            "framing_types": framing_types,
            "exclude_high_risk": True,
            "custom_framing": custom_framing,
        }

        # Log extracted info
        tools = state["recon_intelligence"].get("tools", [])
        defenses = state["pattern_analysis"].get("defense_mechanisms", [])
        objective = state["attack_plan"].get("objective", "")
        vulnerabilities = state.get("garak_vulnerabilities", [])

        self.logger.info(f"  Tools detected: {len(tools)}")
        for tool in tools:
            self.logger.info(f"    - {tool}")

        self.logger.info(f"  Defense patterns: {defenses}")
        self.logger.info(f"  Attack objective: {objective[:80]}...")

        if vulnerabilities:
            vuln = vulnerabilities[0]
            self.logger.info(f"  Garak finding: {vuln.get('detector', 'unknown')} (severity: {vuln.get('severity', 'unknown')})")

        # Step 2: Chain Selection
        self.logger.info(f"\n[Step 2/3] Converter Chain Selection")
        self.logger.info("-" * 40)

        chain_result = await self.converter_selector.select_converters(state)
        selected_chain = chain_result.get("selected_converters")

        if selected_chain:
            self.logger.info(f"  Chain ID: {selected_chain.chain_id}")
            self.logger.info(f"  Converters: {selected_chain.converter_names}")
            self.logger.info(f"  Defense patterns: {selected_chain.defense_patterns}")

            # Update state with selected chain
            state["converter_selection"] = selected_chain
            state["selected_converters"] = selected_chain
        else:
            self.logger.warning("  No chain selected!")

        # Step 3: Payload Articulation
        self.logger.info(f"\n[Step 3/3] Payload Articulation")
        self.logger.info("-" * 40)

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
        result = Phase1Result(
            campaign_id=campaign_id,
            selected_chain=selected_chain,
            articulated_payloads=articulated_payloads,
            framing_type=framing_str,
            framing_types_used=framing_types_used,
            context_summary=context_summary,
            garak_objective=objective,
            defense_patterns=defenses,
            tools_detected=tools,
        )

        self.logger.info(f"\n{'='*60}")
        self.logger.info("Phase 1 Complete - Ready for Phase 2 (Conversion)")
        self.logger.info(f"{'='*60}\n")

        return result


async def main():
    """Test Phase 1 with campaign fresh1."""
    import sys
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Phase 1: Payload Articulation")
    parser.add_argument("--campaign", "-c", default="fresh1", help="Campaign ID")
    parser.add_argument("--payloads", "-p", type=int, default=1, help="Number of payloads (1-6)")
    parser.add_argument("--framing", "-f", nargs="*", help="Framing types to use")
    parser.add_argument("--custom-name", help="Custom framing name")
    parser.add_argument("--custom-context", help="Custom framing system context")
    parser.add_argument("--custom-prefix", help="Custom framing user prefix")
    parser.add_argument("--custom-suffix", default="", help="Custom framing user suffix")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        stream=sys.stdout,
    )

    # Suppress noisy loggers
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)

    print("\n" + "="*70)
    print("PHASE 1: PAYLOAD ARTICULATION")
    print("="*70 + "\n")

    # Build custom framing if provided
    custom_framing = None
    if args.custom_name and args.custom_context:
        custom_framing = {
            "name": args.custom_name,
            "system_context": args.custom_context,
            "user_prefix": args.custom_prefix or "",
            "user_suffix": args.custom_suffix or "",
        }
        print(f"Using custom framing: {args.custom_name}")

    # Initialize and execute
    phase1 = PayloadArticulation()
    result = await phase1.execute(
        campaign_id=args.campaign,
        payload_count=args.payloads,
        framing_types=args.framing,
        custom_framing=custom_framing,
    )

    # Print detailed results
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)

    print(f"\nCampaign ID: {result.campaign_id}")
    print(f"Tools Detected: {result.tools_detected}")
    print(f"Defense Patterns: {result.defense_patterns}")
    print(f"Attack Objective: {result.garak_objective}")

    print(f"\n--- Selected Chain ---")
    if result.selected_chain:
        print(f"Chain ID: {result.selected_chain.chain_id}")
        print(f"Converters: {result.selected_chain.converter_names}")
    else:
        print("No chain selected")

    print(f"\n--- Articulated Payloads ---")
    print(f"Framing Type: {result.framing_type}")
    print(f"Payload Count: {len(result.articulated_payloads)}")

    for i, payload in enumerate(result.articulated_payloads):
        print(f"\n[Payload {i+1}] ({len(payload)} chars):")
        print("-" * 50)
        print(payload)
        print("-" * 50)

    print("\n" + "="*70)
    print("PHASE 1 COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
