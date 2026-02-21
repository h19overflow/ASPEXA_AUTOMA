"""
Snipers models package.

Import from submodules for explicit usage:
  - models.enums: AttackMode, ProbeCategory
  - models.requests: ExploitStreamRequest, ExampleFinding, etc.
  - models.results: AttackResult, Phase1Result, Phase2Result, Phase3Result, etc.
"""

from services.snipers.models.enums import AttackMode, ProbeCategory
from services.snipers.models.requests import (
    ExampleFinding,
    ExploitAgentConfig,
    ExploitAgentInput,
    ExploitJobRequest,
    ExploitStreamRequest,
    GarakVulnerabilityFinding,
    VulnerableProbe,
)
from services.snipers.models.results import (
    AttackResponse,
    AttackResult,
    ConvertedPayload,
    ExploitJobResult,
    GarakReportSummary,
    ParsedGarakReport,
    Phase1Result,
    Phase2Result,
    Phase3Result,
)

__all__ = [
    # Enums
    "AttackMode",
    "ProbeCategory",
    # Requests
    "ExampleFinding",
    "ExploitAgentConfig",
    "ExploitAgentInput",
    "ExploitJobRequest",
    "ExploitStreamRequest",
    "GarakVulnerabilityFinding",
    "VulnerableProbe",
    # Results
    "AttackResponse",
    "AttackResult",
    "ConvertedPayload",
    "ExploitJobResult",
    "GarakReportSummary",
    "ParsedGarakReport",
    "Phase1Result",
    "Phase2Result",
    "Phase3Result",
]
