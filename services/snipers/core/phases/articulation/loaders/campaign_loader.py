"""
Campaign Intelligence Loader.

Purpose: Load and parse campaign intelligence from S3
Role: Single source for loading recon + garak data
Dependencies: S3PersistenceAdapter
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from services.snipers.infrastructure.persistence.s3_adapter import load_campaign_intel
from services.snipers.core.phases.articulation.loaders.swarm_extractor import (
    extract_all_objectives,
    extract_probe_examples,
    extract_vulnerability_scores,
)

logger = logging.getLogger(__name__)


# Detector name to defense mechanism mapping
DETECTOR_TO_DEFENSE = {
    "dan.DAN": "jailbreak_filter",
    "dan": "jailbreak_filter",
    "promptinject": "prompt_injection_filter",
    "gcg": "adversarial_filter",
    "leakreplay": "prompt_leak_detection",
    "encoding": "encoding_filter",
    "goodside": "instruction_following",
    "knownbadsignatures": "keyword_filter",
}

# Detector to attack objective mapping
DETECTOR_TO_OBJECTIVE = {
    "dan.DAN": "Bypass instruction filters and enable unrestricted mode",
    "dan": "Bypass instruction filters and enable unrestricted mode",
    "promptinject": "Extract system prompt and internal instructions",
    "leakreplay": "Reveal training data or confidential information",
    "gcg": "Execute adversarial prompt to bypass safety filters",
    "encoding": "Bypass encoding-based content filters",
}

# Domain keywords mapping
DOMAIN_KEYWORDS = {
    "ecommerce": ["order", "refund", "transaction", "cart", "checkout", "product"],
    "healthcare": ["patient", "medical", "prescription", "diagnosis", "health"],
    "finance": ["account", "balance", "transfer", "payment", "banking"],
    "support": ["ticket", "support", "help", "issue", "complaint"],
}


@dataclass
class CampaignIntelligence:
    """Parsed campaign intelligence ready for payload generation."""

    campaign_id: str
    tools: list[str] = field(default_factory=list)
    domain: str = "general"
    defense_patterns: list[str] = field(default_factory=list)
    objective: str = ""
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)
    recon_raw: dict[str, Any] = field(default_factory=dict)
    probe_name: str = "unknown"
    # Enriched swarm context
    all_objectives: list[str] = field(default_factory=list)
    probe_examples: list[dict[str, Any]] = field(default_factory=list)
    vulnerability_scores: dict[str, float] = field(default_factory=dict)


class CampaignLoader:
    """Load campaign intelligence from S3."""

    def __init__(self):
        """Initialize campaign loader."""
        self.logger = logging.getLogger(__name__)

    async def load(self, campaign_id: str) -> CampaignIntelligence:
        """
        Load and parse campaign intelligence from S3.

        Args:
            campaign_id: Campaign identifier

        Returns:
            CampaignIntelligence with parsed data
        """
        self.logger.info(f"Loading intelligence for campaign: {campaign_id}")

        intel = await load_campaign_intel(campaign_id)

        recon_data = intel.get("recon") or {}
        garak_data = intel.get("garak") or {}

        tools = self._extract_tools(recon_data)
        vulnerabilities = garak_data.get("vulnerabilities", [])
        defense_patterns = self._infer_defense_patterns(vulnerabilities)
        domain = self._extract_domain(tools)
        objective = self._build_objective(vulnerabilities)
        probe_name = (
            vulnerabilities[0].get("detector", "unknown")
            if vulnerabilities
            else "unknown"
        )
        all_objectives = extract_all_objectives(vulnerabilities)
        probe_examples = extract_probe_examples(vulnerabilities)
        vulnerability_scores = extract_vulnerability_scores(vulnerabilities)

        self.logger.info(f"Loaded: {len(tools)} tools, {len(vulnerabilities)} vulns, {len(probe_examples)} examples")

        return CampaignIntelligence(
            campaign_id=campaign_id,
            tools=tools,
            domain=domain,
            defense_patterns=defense_patterns,
            objective=objective,
            vulnerabilities=vulnerabilities,
            recon_raw=recon_data,
            probe_name=probe_name,
            all_objectives=all_objectives,
            probe_examples=probe_examples,
            vulnerability_scores=vulnerability_scores,
        )

    def _extract_tools(self, recon_data: dict[str, Any]) -> list[str]:
        """Extract tool names from recon raw observations."""
        raw_observations = recon_data.get("raw_observations") or {}
        tools_raw = raw_observations.get("tools") or []

        tools = []
        for tool_str in tools_raw:
            if tool_str.startswith("Tool:"):
                parts = tool_str.split(" - ", 1)
                name = parts[0].replace("Tool:", "").strip()
                tools.append(name)
            else:
                tools.append(tool_str)

        return list(set(tools))

    def _infer_defense_patterns(self, vulnerabilities: list[dict]) -> list[str]:
        """Infer defense patterns from Garak detector names."""
        patterns = set()

        for vuln in vulnerabilities:
            detector = vuln.get("detector", "")

            if detector in DETECTOR_TO_DEFENSE:
                patterns.add(DETECTOR_TO_DEFENSE[detector])
                continue

            for detector_prefix, defense in DETECTOR_TO_DEFENSE.items():
                if detector.startswith(detector_prefix):
                    patterns.add(defense)
                    break

        if not patterns:
            patterns.add("content_analysis")

        return list(patterns)

    def _extract_domain(self, tools: list[str]) -> str:
        """Infer domain from tool names."""
        tools_lower = " ".join(tools).lower()

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in tools_lower:
                    return domain

        return "general"

    def _build_objective(self, vulnerabilities: list[dict]) -> str:
        """Build attack objective from first vulnerability."""
        if not vulnerabilities:
            return "Test target for security vulnerabilities"

        vuln = vulnerabilities[0]
        detector = vuln.get("detector", "")

        for detector_key, objective in DETECTOR_TO_OBJECTIVE.items():
            if detector.startswith(detector_key):
                return objective

        examples = vuln.get("examples", [])
        if examples:
            prompt = examples[0].get("prompt", "")
            if prompt:
                return prompt

        return f"Exploit {detector} vulnerability"
