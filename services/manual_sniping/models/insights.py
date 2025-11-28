"""Campaign insights models for intelligence display.

Provides aggregated intelligence from previous campaign phases.
Dependencies: pydantic
System role: Models for campaign intelligence aggregation
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VulnerabilityPattern(BaseModel):
    """Extracted vulnerability pattern from scans.

    Represents a discovered attack vector with confidence score.
    """

    pattern_id: str
    source: str  # "cartographer", "swarm", "snipers"
    vulnerability_type: str
    description: str
    successful_payloads: List[str] = Field(default_factory=list)
    confidence: float  # 0.0 - 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReconInsights(BaseModel):
    """Intelligence from Cartographer phase.

    Provides infrastructure and configuration details.
    """

    system_prompt_leak: Optional[str] = None
    detected_tools: List[Dict[str, Any]] = Field(default_factory=list)
    infrastructure: Dict[str, Any] = Field(default_factory=dict)
    auth_structure: Dict[str, Any] = Field(default_factory=dict)


class ScanInsights(BaseModel):
    """Intelligence from Swarm/Garak phase.

    Identifies vulnerable probes and successful payloads.
    """

    vulnerable_probes: List[str] = Field(default_factory=list)
    successful_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    detector_scores: Dict[str, float] = Field(default_factory=dict)


class ExploitInsights(BaseModel):
    """Intelligence from automated Snipers phase.

    Shows converter effectiveness and discovered patterns.
    """

    patterns_found: List[VulnerabilityPattern] = Field(default_factory=list)
    converter_effectiveness: Dict[str, float] = Field(default_factory=dict)


class CampaignInsights(BaseModel):
    """Aggregated campaign intelligence.

    Combines insights from all phases for informed manual attacks.
    """

    campaign_id: str
    campaign_name: Optional[str] = None
    recon: Optional[ReconInsights] = None
    scan: Optional[ScanInsights] = None
    exploit: Optional[ExploitInsights] = None
    patterns: List[VulnerabilityPattern] = Field(default_factory=list)
