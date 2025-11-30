"""
Attack Phases Module.

Provides the three-phase attack flow for payload generation, conversion, and execution.

Phase 1: Payload Articulation
    - Loads campaign intelligence from S3
    - Selects optimal converter chain
    - Generates articulated payloads with framing strategies

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

    # User can inspect/modify result1 here

    # Phase 2
    phase2 = Conversion()
    result2 = await phase2.execute(
        payloads=result1.articulated_payloads,
        chain=result1.selected_chain,
    )

    # Phase 3
    phase3 = AttackExecution(target_url="http://localhost:8082/chat")
    result3 = await phase3.execute(
        campaign_id="fresh1",
        payloads=result2.payloads,
        chain=result1.selected_chain,
    )

    # result3 contains attack responses, scores, and learnings
"""

from services.snipers.attack_phases.payload_articulation import PayloadArticulation
from services.snipers.attack_phases.conversion import Conversion
from services.snipers.attack_phases.attack_execution import AttackExecution

__all__ = [
    "PayloadArticulation",
    "Conversion",
    "AttackExecution",
]
