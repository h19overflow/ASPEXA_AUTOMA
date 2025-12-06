"""
Input Processing Node for Phase 1 Attack Flow.

Loads campaign intelligence from S3 and prepares state for subsequent nodes.
Uses existing load_campaign_intel() from persistence layer.
"""

import logging
from typing import Any

from services.snipers.utils.persistence.s3_adapter import load_campaign_intel

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


class InputProcessingNode:
    """
    Load and process campaign intelligence from S3.

    Extracts:
    - Garak vulnerabilities
    - Recon tool information
    - Defense pattern inference
    - Domain hints
    - Attack objectives
    """

    def __init__(self):
        """Initialize input processor."""
        self.logger = logging.getLogger(__name__)

    async def process_input(self, campaign_id: str) -> dict[str, Any]:
        """
        Load campaign intelligence and prepare state for attack flow.

        Args:
            campaign_id: Campaign identifier to load from S3

        Returns:
            State dict with processed intelligence for subsequent nodes
        """
        self.logger.info(f"[InputProcessingNode] Loading intelligence for campaign: {campaign_id}")

        # Load intelligence from S3
        intel = await load_campaign_intel(campaign_id)

        recon_data = intel.get("recon", {})
        garak_data = intel.get("garak", {})

        self.logger.info(f"[InputProcessingNode] Loaded recon and garak data")

        # Extract tools from recon
        tools = self._extract_tools(recon_data)
        self.logger.info(f"[InputProcessingNode] Extracted {len(tools)} tools")

        # Extract vulnerabilities from garak
        vulnerabilities = garak_data.get("vulnerabilities", [])
        self.logger.info(f"[InputProcessingNode] Found {len(vulnerabilities)} vulnerabilities")

        # Infer defense patterns from detector names
        defense_patterns = self._infer_defense_patterns(vulnerabilities)
        self.logger.info(f"[InputProcessingNode] Inferred defense patterns: {defense_patterns}")

        # Extract domain hint
        domain = self._extract_domain(tools)
        self.logger.info(f"[InputProcessingNode] Domain hint: {domain}")

        # Build attack objective from first vulnerability
        objective = self._build_objective(vulnerabilities)
        self.logger.info(f"[InputProcessingNode] Attack objective: {objective[:100]}...")

        # Build state dict for subsequent nodes
        state = {
            "campaign_id": campaign_id,
            "recon_intelligence": {
                "tools": tools,
                "infrastructure": recon_data.get("intelligence", {}).get("infrastructure", {}),
                "auth_structure": recon_data.get("intelligence", {}).get("auth_structure", {}),
                "domain_type": domain,
            },
            "pattern_analysis": {
                "defense_mechanisms": defense_patterns,
            },
            "attack_plan": {
                "objective": objective,
            },
            "garak_vulnerabilities": vulnerabilities,
            "probe_name": vulnerabilities[0].get("detector", "unknown") if vulnerabilities else "unknown",
        }

        return state

    def _extract_tools(self, recon_data: dict[str, Any]) -> list[str]:
        """Extract tool names from recon raw observations."""
        raw_observations = recon_data.get("raw_observations", {})
        tools_raw = raw_observations.get("tools", [])

        tools = []
        for tool_str in tools_raw:
            # Parse "Tool: Name - Description" format
            if tool_str.startswith("Tool:"):
                parts = tool_str.split(" - ", 1)
                name = parts[0].replace("Tool:", "").strip()
                tools.append(name)
            else:
                tools.append(tool_str)

        # Deduplicate
        return list(set(tools))

    def _infer_defense_patterns(self, vulnerabilities: list[dict]) -> list[str]:
        """Infer defense patterns from Garak detector names."""
        patterns = set()

        for vuln in vulnerabilities:
            detector = vuln.get("detector", "")

            # Check exact match first
            if detector in DETECTOR_TO_DEFENSE:
                patterns.add(DETECTOR_TO_DEFENSE[detector])
                continue

            # Check prefix match
            for detector_prefix, defense in DETECTOR_TO_DEFENSE.items():
                if detector.startswith(detector_prefix):
                    patterns.add(defense)
                    break

        # Default if no patterns found
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

        # Check if we have a mapped objective
        for detector_key, objective in DETECTOR_TO_OBJECTIVE.items():
            if detector.startswith(detector_key):
                return objective

        # Fallback: use example prompt if available
        examples = vuln.get("examples", [])
        if examples:
            prompt = examples[0].get("prompt", "")
            if prompt:
                return prompt

        return f"Exploit {detector} vulnerability"
