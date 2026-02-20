"""Swarm scanning service — LLM vulnerability scanner.

Purpose: Executes targeted security scans against LLM agents using Garak probes
Role: Three agents (SQL, AUTH, JAILBREAK) select probes and run them against the target
Dependencies: garak, libs.contracts.scanning

Architecture:
    - phases/: Sequential scan phases (load_recon, run_deterministic_planning, run_probe_execution, persist_results)
    - core/: Configuration, schemas, utilities
    - garak_scanner/: Garak probe integration and result parsing
    - persistence/: S3 storage for scan results

Public API:
    - execute_scan_streaming: Async generator yielding SSE events
"""

from .entrypoint import execute_scan_streaming

__all__ = [
    "execute_scan_streaming",
]

