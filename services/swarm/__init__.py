"""Swarm scanning service - Intelligent security scanning for LLM applications.

Purpose: Executes targeted security scans against LLM agents using Garak probes
Role: Trinity agents (SQL, AUTH, JAILBREAK) analyze recon and execute vulnerability scans
Dependencies: garak, langchain, libs.contracts.scanning, libs.events

Architecture:
    - agents/: LangChain-based intelligent agents for scan orchestration
    - core/: Configuration, schemas, utilities, and event consumers
    - garak_scanner/: Garak probe integration and result parsing
    - persistence/: S3 storage for scan results

Public API:
    - execute_scan_streaming: Async streaming scan with real-time events
"""

from .entrypoint import execute_scan_streaming

__all__ = [
    "execute_scan_streaming",
]

