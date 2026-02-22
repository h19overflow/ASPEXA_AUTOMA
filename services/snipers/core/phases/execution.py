"""
Phase 3: Attack Execution.

Purpose: Send attacks to target, evaluate responses
Role: Third phase of attack flow - executes attacks and scores results
Dependencies: PyRIT targets, composite scoring

Sequential execution of 2 stages:
1. Attack Execution - Send converted payloads via PyRIT target adapters
2. Composite Scoring - Evaluate responses with all Phase 3/4 scorers

Usage:
    from services.snipers.core.phases import AttackExecution

    phase3 = AttackExecution(target_url="http://localhost:8082/chat")
    result = await phase3.execute(
        campaign_id="fresh1",
        payloads=phase2_result.payloads,
        chain=phase1_result.selected_chain,
    )

    # Result contains attack_responses, composite_score, learning outcomes
"""

import asyncio
import logging
import time

import httpx


from services.snipers.core.phases.scoring.composite_scoring_node import CompositeScoringNodePhase34
from services.snipers.models.chain_models.models import ConverterChain
from services.snipers.models import (
    AttackResponse,
    ConvertedPayload,
    Phase3Result,
)
from services.snipers.core.phases.scoring.models import CompositeScore

logger = logging.getLogger(__name__)


class AttackExecution:
    """
    Phase 3: Attack Execution.

    Executes: Send Attacks → Score Responses

    Output contains scoring results.
    """

    def __init__(
        self,
        target_url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        success_scorers: list[str] | None = None,
    ):
        """
        Initialize with target configuration.

        Args:
            target_url: HTTP endpoint to attack
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
            success_scorers: Scorers that MUST succeed for is_successful=True.
                             If None, any scorer reaching MEDIUM+ counts as success.
                             Valid values: jailbreak, prompt_leak, data_leak, tool_abuse, pii_exposure
        """
        self._target_url = target_url
        self._headers = headers or {"Content-Type": "application/json"}
        self._timeout = timeout

        # Initialize nodes with required scorers filter
        self._scoring_node = CompositeScoringNodePhase34(required_scorers=success_scorers)

        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        campaign_id: str,
        payloads: list[ConvertedPayload],
        chain: ConverterChain | None = None,
        max_concurrent: int = 3,
    ) -> Phase3Result:
        """
        Execute Phase 3: Attack → Score → Learn.

        Args:
            campaign_id: Campaign ID for persistence
            payloads: Converted payloads from Phase 2
            chain: Converter chain used (for learning)
            max_concurrent: Max concurrent attack requests

        Returns:
            Phase3Result with responses, scores, and learnings
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Phase 3: Attack Execution - Campaign {campaign_id}")
        self.logger.info(f"{'='*60}\n")

        # Step 1: Send attacks
        self.logger.info("[Step 1/3] Sending Attacks")
        self.logger.info("-" * 40)
        self.logger.info(f"  Target: {self._target_url}")
        self.logger.info(f"  Payloads: {len(payloads)}")

        attack_responses = await self._send_attacks(payloads, max_concurrent)

        success_count = sum(1 for r in attack_responses if r.error is None)
        self.logger.info(f"  Completed: {success_count}/{len(payloads)} successful")

        # Step 2: Score responses
        self.logger.info("\n[Step 2/3] Scoring Responses")
        self.logger.info("-" * 40)

        # Build state for scoring node
        scoring_state = {
            "campaign_id": campaign_id,
            "attack_results": [
                {"content": r.response, "status_code": r.status_code}
                for r in attack_responses
                if r.error is None
            ],
            "articulated_payloads": [p.converted for p in payloads],
        }

        scoring_result = await self._scoring_node.score_responses(scoring_state)
        composite_score: CompositeScore = scoring_result.get("composite_score")

        self.logger.info(f"  Overall severity: {composite_score.overall_severity.value}")
        self.logger.info(f"  Total score: {composite_score.total_score:.1f}")
        self.logger.info(f"  Is successful: {composite_score.is_successful}")

        # Log individual scorer results
        for scorer_name, result in composite_score.scorer_results.items():
            self.logger.info(
                f"    {scorer_name}: {result.severity.value} "
                f"(confidence: {result.confidence:.2f})"
            )

        # Build result
        result = Phase3Result(
            campaign_id=campaign_id,
            target_url=self._target_url,
            attack_responses=attack_responses,
            composite_score=composite_score,
            is_successful=composite_score.is_successful,
            overall_severity=composite_score.overall_severity.value,
            total_score=composite_score.total_score,
            learned_chain=None,
            failure_analysis=None,
            adaptation_strategy=None,
        )

        self.logger.info(f"\n{'='*60}")
        self.logger.info("Phase 3 Complete - Attack Evaluation Done")
        self.logger.info(f"{'='*60}\n")

        return result

    async def _send_attacks(
        self,
        payloads: list[ConvertedPayload],
        max_concurrent: int,
    ) -> list[AttackResponse]:
        """
        Send attack payloads to target.

        Args:
            payloads: Converted payloads to send
            max_concurrent: Max concurrent requests

        Returns:
            List of attack responses
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def send_single(idx: int, payload: ConvertedPayload) -> AttackResponse:
            async with semaphore:
                return await self._send_payload(idx, payload)

        tasks = [send_single(i, p) for i, p in enumerate(payloads)]
        return await asyncio.gather(*tasks)

    async def _send_payload(
        self,
        idx: int,
        payload: ConvertedPayload,
    ) -> AttackResponse:
        """
        Send single payload to target.

        Args:
            idx: Payload index
            payload: Payload to send

        Returns:
            Attack response
        """
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._target_url,
                    headers=self._headers,
                    json={"prompt": payload.converted},
                )

                latency_ms = (time.perf_counter() - start_time) * 1000

                # Extract response content
                try:
                    resp_json = response.json()
                    content = resp_json.get("response", str(resp_json))
                except Exception:
                    content = response.text

                self.logger.debug(
                    f"  [{idx+1}] Status: {response.status_code}, "
                    f"Latency: {latency_ms:.0f}ms"
                )

                return AttackResponse(
                    payload_index=idx,
                    payload=payload.converted,
                    response=content,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000

            self.logger.warning(f"  [{idx+1}] Error: {e}")

            return AttackResponse(
                payload_index=idx,
                payload=payload.converted,
                response="",
                status_code=0,
                latency_ms=latency_ms,
                error=str(e),
            )

