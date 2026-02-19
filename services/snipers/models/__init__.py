"""
Snipers models package.

Re-exports all models for backward compatibility.
Import from submodules for explicit usage:
  - models.enums: AttackMode, ProbeCategory
  - models.events: AttackEvent
  - models.requests: ExploitStreamRequest, ExampleFinding, etc.
  - models.reasoning: PatternAnalysis, ScoringResult, AttackPlan, etc.
  - models.results: AttackResult, Phase1Result, Phase2Result, Phase3Result, etc.
  - models.state: ExploitAgentState
"""

from services.snipers.models.enums import AttackMode, ProbeCategory
from services.snipers.models.events import AttackEvent
from services.snipers.models.reasoning import (
    AttackPlan,
    ConverterSelection,
    HumanFeedback,
    PatternAnalysis,
    PayloadGeneration,
    ScoringResult,
)
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
from services.snipers.models.state import ExploitAgentState

__all__ = [
    # Enums
    "AttackMode",
    "ProbeCategory",
    # Events
    "AttackEvent",
    # Reasoning
    "AttackPlan",
    "ConverterSelection",
    "HumanFeedback",
    "PatternAnalysis",
    "PayloadGeneration",
    "ScoringResult",
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
    # State
    "ExploitAgentState",
]
