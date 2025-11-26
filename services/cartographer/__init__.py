"""Cartographer service - Reconnaissance agent for LLM applications.

Purpose: Intelligent reconnaissance to extract system intelligence from target LLM agents
Role: Maps target capabilities, tools, authorization rules, and infrastructure
Dependencies: langchain, langchain_google_genai, libs.contracts.recon, libs.events

Public API:
- execute_recon: Synchronous recon execution
- execute_recon_streaming: Async streaming recon with real-time events
"""

from .entrypoint import execute_recon, execute_recon_streaming

__all__ = [
    "execute_recon",
    "execute_recon_streaming",
]
