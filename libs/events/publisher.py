"""FastStream event publisher for Redis Streams."""
from typing import Any, Dict
from faststream import FastStream
from faststream.redis import RedisBroker

# Topic constants
CMD_RECON_START = "cmd_recon_start"
EVT_RECON_FINISHED = "evt_recon_finished"
CMD_SCAN_START = "cmd_scan_start"
EVT_VULN_FOUND = "evt_vuln_found"
CMD_ATTACK_EXECUTE = "cmd_attack_execute"
EVT_PLAN_PROPOSED = "evt_plan_proposed"
EVT_ATTACK_FINISHED = "evt_attack_finished"

# Stream capping to prevent OOM
MAX_STREAM_LENGTH = 10000

# Global broker instance
broker = RedisBroker()
app = FastStream(broker)


async def publish_message(
    stream: str,
    payload: Dict[str, Any],
    maxlen: int = MAX_STREAM_LENGTH
) -> None:
    """
    Publish a message to a Redis stream with automatic capping.
    
    Args:
        stream: Stream name to publish to
        payload: Message payload (will be JSON serialized)
        maxlen: Maximum stream length (default: 10000)
    """
    await broker.publish(
        payload,
        stream=stream,
        maxlen=maxlen
    )


async def publish_recon_request(payload: Dict[str, Any]) -> None:
    """Publish IF-01: Reconnaissance Request."""
    await publish_message(CMD_RECON_START, payload)


async def publish_recon_finished(payload: Dict[str, Any]) -> None:
    """Publish IF-02: Reconnaissance Blueprint."""
    await publish_message(EVT_RECON_FINISHED, payload)


async def publish_scan_dispatch(payload: Dict[str, Any]) -> None:
    """Publish IF-03: Scan Job Dispatch."""
    await publish_message(CMD_SCAN_START, payload)


async def publish_vuln_found(payload: Dict[str, Any]) -> None:
    """Publish IF-04: Vulnerability Cluster."""
    await publish_message(EVT_VULN_FOUND, payload)


async def publish_plan_proposed(payload: Dict[str, Any]) -> None:
    """Publish IF-05: The Sniper Plan."""
    await publish_message(EVT_PLAN_PROPOSED, payload)


async def publish_attack_warrant(payload: Dict[str, Any]) -> None:
    """Publish IF-06: The Attack Warrant."""
    await publish_message(CMD_ATTACK_EXECUTE, payload)


async def publish_attack_finished(payload: Dict[str, Any]) -> None:
    """Publish IF-07: Kill Chain Result."""
    await publish_message(EVT_ATTACK_FINISHED, payload)
