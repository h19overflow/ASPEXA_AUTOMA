"""
Purpose: FastStream entry point for Swarm scanning service
Role: Service initialization and event loop
Dependencies: faststream, libs.events, services.swarm.consumer
"""

import logging
from typing import Dict, Any

from libs.events.publisher import app
from services.swarm.core.utils import StructuredFormatter

# Import consumers to register FastStream subscribers
from services.swarm.core import consumer  # noqa: F401

# Configure structured JSON logging
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
handler.setLevel(logging.INFO)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

# Remove default handlers to avoid duplicate logs
for h in root_logger.handlers[:]:
    if not isinstance(h.formatter, StructuredFormatter):
        root_logger.removeHandler(h)

logger = logging.getLogger(__name__)

# Track service metrics
_service_metrics: Dict[str, Any] = {
    "scans_started": 0,
    "scans_completed": 0,
    "scans_failed": 0,
    "last_scan_time": None,
}


@app.lifespan
async def lifespan():
    """Service lifecycle management."""
    logger.info("Swarm service starting...", extra={"extra_fields": {"event": "service_start"}})
    yield
    logger.info("Swarm service shutting down...", extra={"extra_fields": {"event": "service_shutdown"}})


async def main():
    """Main entry point for the Swarm service."""
    logger.info("Initializing Swarm scanning service", extra={"extra_fields": {"event": "init"}})
    logger.info("Connected to Redis broker", extra={"extra_fields": {"event": "broker_connected"}})
    logger.info("Registered Trinity agents", extra={
        "extra_fields": {
            "event": "agents_registered",
            "agents": ["agent_sql", "agent_auth", "agent_jailbreak"]
        }
    })

    await app.run()


# Health check endpoint (if FastStream supports HTTP endpoints)
# This would typically be added via FastStream's HTTP router if available
# For now, we'll add it as a utility function that can be called
def get_health_status() -> Dict[str, Any]:
    """Get service health status."""
    from services.swarm.garak_scanner.scanner import get_scanner
    
    scanner_status = "available"
    try:
        scanner = get_scanner()
        if scanner is None:
            scanner_status = "unavailable"
    except Exception:
        scanner_status = "error"
    
    return {
        "status": "healthy",
        "service": "swarm",
        "scanner": scanner_status,
        "metrics": _service_metrics,
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
