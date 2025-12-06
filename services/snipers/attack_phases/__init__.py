"""
Attack Phases Module.

Provides the three-phase attack flow for payload generation, conversion, and execution.

Phase 1: Payload Articulation
    - Loads campaign intelligence from S3
    - Generates articulated payloads with framing strategies
    - Chain selection handled by adapt_node (single source of truth)

Phase 2: Conversion
    - Applies converter chain to payloads
    - Produces attack-ready converted payloads

Phase 3: Attack Execution
    - Sends attacks via PyRIT target adapters
    - Scores responses with composite scorers
    - Records learnings to pattern database

Usage:
    from services.snipers.attack_phases import PayloadArticulation, Conversion, AttackExecution

    # Phase 1
    phase1 = PayloadArticulation()
    result1 = await phase1.execute(campaign_id="fresh1", payload_count=3)

    # Phase 2
    phase2 = Conversion()
    result2 = await phase2.execute(
        payloads=result1.articulated_payloads,
        converter_names=["rot13"],  # Chain from adapt_node
    )

    # Phase 3
    phase3 = AttackExecution(target_url="http://localhost:8082/chat")
    result3 = await phase3.execute(
        campaign_id="fresh1",
        payloads=result2.payloads,
    )
"""

# Re-export ArticulationPhase as PayloadArticulation for backward compatibility
from services.snipers.utils.prompt_articulation import (
    ArticulationPhase as PayloadArticulation,
)
from services.snipers.attack_phases.conversion import Conversion
from services.snipers.attack_phases.attack_execution import AttackExecution

__all__ = [
    "PayloadArticulation",
    "Conversion",
    "AttackExecution",
]
