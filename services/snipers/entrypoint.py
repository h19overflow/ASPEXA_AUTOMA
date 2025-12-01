"""
HTTP entrypoint for Snipers exploitation service.

Purpose: Chain the three-phase attack flow for automated exploitation
Role: Orchestrates Phase 1 → Phase 2 → Phase 3 execution
Dependencies: PayloadArticulation, Conversion, AttackExecution

Two execution modes:
1. Single-shot: execute_full_attack() - One iteration through all phases
2. Adaptive: execute_adaptive_attack() - LangGraph loop with auto-adaptation

Three-Phase Attack Flow:
1. Phase 1 (Payload Articulation) - Load intel, select chain, generate payloads
2. Phase 2 (Conversion) - Apply converter chain transformations
3. Phase 3 (Attack Execution) - Send attacks, score responses, record learnings

Usage:
    # Single-shot attack
    from services.snipers.entrypoint import execute_full_attack

    result = await execute_full_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        payload_count=3,
    )

    # Adaptive attack with auto-retry
    from services.snipers.entrypoint import execute_adaptive_attack

    result = await execute_adaptive_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=5,
    )

    # Adaptive attack with custom success criteria
    result = await execute_adaptive_attack(
        campaign_id="fresh1",
        target_url="http://localhost:8082/chat",
        max_iterations=10,
        success_scorers=["jailbreak"],  # Only succeed on jailbreak
        success_threshold=1.0,           # Require 100% confidence
    )
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from services.snipers.attack_phases import (
    PayloadArticulation,
    Conversion,
    AttackExecution,
)
from services.snipers.models import Phase1Result, Phase2Result, Phase3Result
from services.snipers.adaptive_attack import run_adaptive_attack, AdaptiveAttackState
from services.snipers.persistence.s3_adapter import (
    persist_exploit_result,
    format_exploit_result,
)

logger = logging.getLogger(__name__)


@dataclass
class FullAttackResult:
    """Complete result from all three phases."""

    campaign_id: str
    target_url: str
    phase1: Phase1Result
    phase2: Phase2Result
    phase3: Phase3Result

    # Summary fields
    is_successful: bool
    overall_severity: str
    total_score: float
    payloads_generated: int
    payloads_sent: int


async def execute_full_attack(
    campaign_id: str,
    target_url: str,
    payload_count: int = 3,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    max_concurrent: int = 3,
) -> FullAttackResult:
    """
    Execute complete three-phase attack flow.

    Args:
        campaign_id: Campaign ID to load intelligence from S3
        target_url: Target URL to attack
        payload_count: Number of payloads to generate (1-6)
        framing_types: Specific framing types (None = auto-select)
        converter_names: Override converter chain (None = use Phase 1 selection)
        max_concurrent: Max concurrent attack requests

    Returns:
        FullAttackResult with all phase results and summary
    """
    start_time = time.time()

    logger.info("\n" + "=" * 70)
    logger.info("SNIPERS: FULL ATTACK EXECUTION")
    logger.info("=" * 70)
    logger.info(f"Campaign: {campaign_id}")
    logger.info(f"Target: {target_url}")
    logger.info(f"Payloads: {payload_count}")
    logger.info("=" * 70 + "\n")

    # Phase 1: Payload Articulation
    phase1 = PayloadArticulation()
    result1 = await phase1.execute(
        campaign_id=campaign_id,
        payload_count=payload_count,
        framing_types=framing_types,
    )

    # Phase 2: Conversion
    phase2 = Conversion()
    result2 = await phase2.execute(
        payloads=result1.articulated_payloads,
        chain=result1.selected_chain if not converter_names else None,
        converter_names=converter_names,
    )

    # Phase 3: Attack Execution
    phase3 = AttackExecution(target_url=target_url)
    result3 = await phase3.execute(
        campaign_id=campaign_id,
        payloads=result2.payloads,
        chain=result1.selected_chain,
        max_concurrent=max_concurrent,
    )

    execution_time = time.time() - start_time

    # Build complete result
    full_result = FullAttackResult(
        campaign_id=campaign_id,
        target_url=target_url,
        phase1=result1,
        phase2=result2,
        phase3=result3,
        is_successful=result3.is_successful,
        overall_severity=result3.overall_severity,
        total_score=result3.total_score,
        payloads_generated=len(result1.articulated_payloads),
        payloads_sent=len(result3.attack_responses),
    )

    # Persist to S3 and update campaign stage
    scan_id = f"{campaign_id}-{uuid.uuid4().hex[:8]}"
    state_dict = _full_result_to_state_dict(full_result)
    exploit_result = format_exploit_result(
        state=state_dict,
        audit_id=campaign_id,
        target_url=target_url,
        execution_time=execution_time,
    )
    await persist_exploit_result(
        campaign_id=campaign_id,
        scan_id=scan_id,
        exploit_result=exploit_result,
        target_url=target_url,
    )
    logger.info(f"Persisted exploit result: {scan_id}")

    logger.info("\n" + "=" * 70)
    logger.info("ATTACK COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Success: {full_result.is_successful}")
    logger.info(f"Severity: {full_result.overall_severity}")
    logger.info(f"Score: {full_result.total_score:.2f}")
    logger.info(f"Scan ID: {scan_id}")
    logger.info("=" * 70 + "\n")

    return full_result


def _full_result_to_state_dict(result: FullAttackResult) -> dict:
    """Convert FullAttackResult to state dict for format_exploit_result."""
    return {
        "probe_name": result.phase1.framing_type,
        "pattern_analysis": result.phase1.context_summary,
        "converter_selection": {
            "selected_converters": result.phase2.converter_names,
        } if result.phase2 else None,
        "attack_results": [
            {
                "success": resp.error is None and result.is_successful,
                "payload": resp.payload,
                "response": resp.response,
            }
            for resp in result.phase3.attack_responses
        ],
        "recon_intelligence": result.phase1.context_summary.get("recon_used"),
    }


async def execute_adaptive_attack(
    campaign_id: str,
    target_url: str,
    max_iterations: int = 5,
    payload_count: int = 2,
    framing_types: list[str] | None = None,
    converter_names: list[str] | None = None,
    success_scorers: list[str] | None = None,
    success_threshold: float = 0.8,
) -> AdaptiveAttackState:
    """
    Execute adaptive attack with automatic parameter adjustment.

    Uses LangGraph state machine to iterate through attack phases,
    automatically adapting framing/converters based on failure analysis.

    Args:
        campaign_id: Campaign ID to load intelligence from S3
        target_url: Target URL to attack
        max_iterations: Maximum adaptation iterations (default 5)
        payload_count: Initial number of payloads (1-6)
        framing_types: Initial framing types (None = auto-select)
        converter_names: Initial converter chain (None = auto-select)
        success_scorers: Scorers that must succeed (e.g., ["jailbreak"])
            Options: jailbreak, prompt_leak, data_leak, tool_abuse, pii_exposure
        success_threshold: Minimum confidence for success (0.0-1.0)

    Returns:
        AdaptiveAttackState with final results and iteration history
    """
    start_time = time.time()

    result = await run_adaptive_attack(
        campaign_id=campaign_id,
        target_url=target_url,
        max_iterations=max_iterations,
        payload_count=payload_count,
        framing_types=framing_types,
        converter_names=converter_names,
        success_scorers=success_scorers,
        success_threshold=success_threshold,
    )

    execution_time = time.time() - start_time

    # Persist to S3 and update campaign stage
    scan_id = f"{campaign_id}-adaptive-{uuid.uuid4().hex[:8]}"
    state_dict = _adaptive_result_to_state_dict(result)
    exploit_result = format_exploit_result(
        state=state_dict,
        audit_id=campaign_id,
        target_url=target_url,
        execution_time=execution_time,
    )
    await persist_exploit_result(
        campaign_id=campaign_id,
        scan_id=scan_id,
        exploit_result=exploit_result,
        target_url=target_url,
    )
    logger.info(f"Persisted adaptive attack result: {scan_id}")

    return result


def _adaptive_result_to_state_dict(state: AdaptiveAttackState) -> dict:
    """Convert AdaptiveAttackState to state dict for format_exploit_result."""
    phase3 = state.get("phase3_result")
    phase1 = state.get("phase1_result")

    # Build attack results from phase3 if available
    attack_results = []
    if phase3:
        for resp in phase3.attack_responses:
            attack_results.append({
                "success": resp.error is None and state.get("is_successful", False),
                "payload": resp.payload,
                "response": resp.response,
            })

    # Get converter selection from chain selection result or phase1
    converter_selection = None
    chain_selection = state.get("chain_selection_result")
    if chain_selection:
        converter_selection = {
            "selected_converters": chain_selection.selected_chain or [],
        }
    elif phase1 and phase1.selected_chain:
        converter_selection = {
            "selected_converters": phase1.selected_chain.converter_names,
        }

    return {
        "probe_name": phase1.framing_type if phase1 else "adaptive",
        "pattern_analysis": phase1.context_summary if phase1 else {},
        "converter_selection": converter_selection,
        "attack_results": attack_results,
        "recon_intelligence": phase1.context_summary.get("recon_used") if phase1 else None,
        # Adaptive-specific fields for logging
        "iteration_count": state.get("iteration", 0) + 1,
        "best_score": state.get("best_score", 0.0),
        "best_iteration": state.get("best_iteration", 0),
        "adaptation_reasoning": state.get("adaptation_reasoning", ""),
    }


async def main():
    """Example: Run attack against test_target_agent."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Snipers: Attack Execution (single-shot or adaptive)"
    )
    parser.add_argument(
        "--campaign", "-c",
        default="fresh1",
        help="Campaign ID to load intelligence from S3"
    )
    parser.add_argument(
        "--target", "-t",
        default="http://localhost:8082/chat",
        help="Target URL to attack"
    )
    parser.add_argument(
        "--payloads", "-p",
        type=int,
        default=2,
        help="Number of payloads to generate (1-6)"
    )
    parser.add_argument(
        "--framing", "-f",
        nargs="*",
        help="Framing types (qa_testing, debugging, etc.)"
    )
    parser.add_argument(
        "--converters",
        nargs="*",
        help="Override converters (e.g., homoglyph xml_escape)"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="Max concurrent attack requests"
    )
    parser.add_argument(
        "--adaptive", "-a",
        action="store_true",
        help="Enable adaptive mode with auto-retry"
    )
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=5,
        help="Max iterations for adaptive mode"
    )
    parser.add_argument(
        "--success-scorers", "-s",
        nargs="*",
        help="Scorers that must succeed (jailbreak, prompt_leak, data_leak, tool_abuse, pii_exposure)"
    )
    parser.add_argument(
        "--success-threshold",
        type=float,
        default=0.8,
        help="Minimum confidence threshold for success (0.0-1.0)"
    )
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
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.adaptive:
        # Adaptive mode with LangGraph loop
        result = await execute_adaptive_attack(
            campaign_id=args.campaign,
            target_url=args.target,
            max_iterations=args.max_iterations,
            payload_count=args.payloads,
            framing_types=args.framing,
            converter_names=args.converters,
            success_scorers=args.success_scorers,
            success_threshold=args.success_threshold,
        )
        _print_adaptive_results(result)
    else:
        # Single-shot mode
        result = await execute_full_attack(
            campaign_id=args.campaign,
            target_url=args.target,
            payload_count=args.payloads,
            framing_types=args.framing,
            converter_names=args.converters,
            max_concurrent=args.concurrent,
        )
        _print_single_shot_results(result)


def _print_adaptive_results(result: AdaptiveAttackState) -> None:
    """Print adaptive attack results with chain discovery intelligence."""
    print("\n" + "=" * 70)
    print("ADAPTIVE ATTACK RESULTS")
    print("=" * 70)

    print(f"\n--- Summary ---")
    print(f"Campaign ID: {result.get('campaign_id')}")
    print(f"Target URL: {result.get('target_url')}")
    print(f"Success: {result.get('is_successful', False)}")
    print(f"Total Iterations: {result.get('iteration', 0) + 1}")
    print(f"Best Score: {result.get('best_score', 0.0):.2f}")
    print(f"Best Iteration: {result.get('best_iteration', 0)}")

    print(f"\n--- Iteration History ---")
    for entry in result.get("iteration_history", []):
        success = "SUCCESS" if entry.get("is_successful") else "FAIL"
        score = entry.get("score", 0.0)
        framing = entry.get("framing") or "auto"
        converters = entry.get("converters") or "auto"
        print(f"  [{entry['iteration']}] {success} - Score: {score:.2f}")
        print(f"      Framing: {framing}, Converters: {converters}")

    # Show chain discovery context if available
    chain_context = result.get("chain_discovery_context")
    if chain_context:
        print(f"\n--- Chain Discovery Intelligence ---")
        print(f"Defense Signals: {chain_context.defense_signals}")
        print(f"Root Cause: {chain_context.failure_root_cause}")
        print(f"Defense Evolution: {chain_context.defense_evolution}")
        print(f"Best Chain So Far: {chain_context.best_chain_so_far or 'None'}")
        if chain_context.unexplored_directions:
            print(f"Unexplored Directions:")
            for direction in chain_context.unexplored_directions[:3]:
                print(f"    - {direction}")
        if chain_context.required_properties:
            print(f"Required Properties:")
            for prop in chain_context.required_properties:
                print(f"    - {prop}")

    # Show chain discovery decision if available
    chain_decision = result.get("chain_discovery_decision")
    if chain_decision:
        print(f"\n--- Chain Discovery Decision ---")
        print(f"Primary Defense Target: {chain_decision.primary_defense_target}")
        print(f"Mode: {chain_decision.exploration_vs_exploitation}")
        print(f"Confidence: {chain_decision.confidence:.2f}")
        print(f"Generated Chains:")
        for i, chain in enumerate(chain_decision.chains[:3]):
            print(f"    {i+1}. {chain.converters} (expected: {chain.expected_effectiveness:.2f})")
            print(f"       Strategy: {chain.defense_bypass_strategy[:60]}...")

    # Show chain selection result with full observability
    chain_selection = result.get("chain_selection_result")
    if chain_selection:
        print(f"\n--- Chain Selection (Full Observability) ---")
        print(f"Selected Chain: {chain_selection.selected_chain}")
        print(f"Selection Method: {chain_selection.selection_method}")
        print(f"Selection Reasoning: {chain_selection.selection_reasoning[:150]}...")

        # Show all candidates with rankings
        if chain_selection.all_candidates:
            print(f"\nAll Candidates (ranked by effectiveness):")
            for candidate in chain_selection.all_candidates[:5]:
                print(f"    #{candidate['rank']}: {candidate['converters']} "
                      f"(eff: {candidate['expected_effectiveness']:.2f})")
                print(f"         Strategy: {candidate['defense_bypass_strategy'][:50]}...")

        # Show defense match details
        if chain_selection.defense_match_details.get("matches_found"):
            print(f"\nDefense Matches Found:")
            for match in chain_selection.defense_match_details["matches_found"]:
                print(f"    Chain: {match['chain']}")
                print(f"    Matched: {match['matched_defenses']}")

        # Show rejected chains
        if chain_selection.rejected_chains:
            print(f"\nRejected Chains ({len(chain_selection.rejected_chains)} total):")
            for rejected in chain_selection.rejected_chains[:3]:
                print(f"    {rejected['chain']}: {rejected['reason']}")

    # Show final phase 3 results if available
    phase3 = result.get("phase3_result")
    if phase3:
        print(f"\n--- Final Attack Results ---")
        print(f"Overall Severity: {phase3.overall_severity}")
        print(f"Total Score: {phase3.total_score:.2f}")

        print(f"\n--- Scorer Results ---")
        for scorer_name, score_result in phase3.composite_score.scorer_results.items():
            print(f"  {scorer_name}: {score_result.severity.value} ({score_result.confidence:.2f})")

    # Show adaptation reasoning if available
    adaptation_reasoning = result.get("adaptation_reasoning")
    if adaptation_reasoning:
        print(f"\n--- Adaptation Reasoning ---")
        reasoning_preview = adaptation_reasoning[:200]
        print(f"  {reasoning_preview}...")

    print("\n" + "=" * 70)
    print("ADAPTIVE ATTACK COMPLETE")
    print("=" * 70 + "\n")


def _print_single_shot_results(result: FullAttackResult) -> None:
    """Print single-shot attack results."""
    print("\n" + "=" * 70)
    print("FULL ATTACK RESULTS")
    print("=" * 70)

    print(f"\n--- Campaign Info ---")
    print(f"Campaign ID: {result.campaign_id}")
    print(f"Target URL: {result.target_url}")

    print(f"\n--- Phase 1: Payload Articulation ---")
    print(f"Framing Type: {result.phase1.framing_type}")
    print(f"Payloads Generated: {len(result.phase1.articulated_payloads)}")
    print(f"Attack Objective: {result.phase1.garak_objective[:80]}...")
    if result.phase1.selected_chain:
        print(f"Selected Chain: {result.phase1.selected_chain.converter_names}")

    print(f"\n--- Phase 2: Conversion ---")
    print(f"Chain ID: {result.phase2.chain_id}")
    print(f"Converters Applied: {result.phase2.converter_names}")
    print(f"Success: {result.phase2.success_count}, Errors: {result.phase2.error_count}")

    print(f"\n--- Phase 3: Attack Execution ---")
    print(f"Attacks Sent: {len(result.phase3.attack_responses)}")
    print(f"Overall Severity: {result.phase3.overall_severity}")
    print(f"Total Score: {result.phase3.total_score:.2f}")
    print(f"Is Successful: {result.phase3.is_successful}")

    print(f"\n--- Scorer Results ---")
    for scorer_name, score_result in result.phase3.composite_score.scorer_results.items():
        print(f"  {scorer_name}: {score_result.severity.value} ({score_result.confidence:.2f})")

    print(f"\n--- Attack Responses ---")
    for i, resp in enumerate(result.phase3.attack_responses):
        status = "OK" if resp.error is None else f"ERROR: {resp.error}"
        print(f"  [{i+1}] Status: {resp.status_code}, Latency: {resp.latency_ms:.0f}ms - {status}")
        if resp.error is None:
            preview = resp.response[:100].replace("\n", " ")
            print(f"      Response: {preview}...")

    if result.phase3.failure_analysis:
        print(f"\n--- Failure Analysis ---")
        print(f"Primary Cause: {result.phase3.failure_analysis.get('primary_cause')}")
        recs = result.phase3.failure_analysis.get('recommendations', [])
        for rec in recs:
            print(f"  - {rec}")

    if result.phase3.adaptation_strategy:
        print(f"\n--- Adaptation Strategy ---")
        print(f"Can Retry: {result.phase3.adaptation_strategy.get('can_retry')}")
        actions = result.phase3.adaptation_strategy.get('adaptation_actions', [])
        for action in actions:
            print(f"  - {action}")

    print("\n" + "=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
