"""
Purpose: Enum definitions for Swarm scanner configuration
Role: Central enum types for agent types, scan approaches, and vulnerability categories
Dependencies: None
"""

from enum import Enum


class AgentType(str, Enum):
    """Supported agent types for Trinity scanning."""
    SQL = "agent_sql"
    AUTH = "agent_auth"
    JAILBREAK = "agent_jailbreak"


class ScanApproach(str, Enum):
    """Scan intensity levels - controls probe breadth and depth."""
    QUICK = "quick"          # Minimal probes, fast results
    STANDARD = "standard"    # Balanced coverage
    THOROUGH = "thorough"    # Maximum coverage, slower


class VulnCategory(str, Enum):
    """Vulnerability categories for classification."""
    JAILBREAK = "jailbreak"
    PROMPT_INJECTION = "prompt_injection"
    ENCODING_BYPASS = "encoding_bypass"
    DATA_LEAKAGE = "data_leakage"
    MALWARE_GEN = "malware_generation"
    TOXICITY = "toxicity"
    HALLUCINATION = "hallucination"
    HARMFUL_CONTENT = "harmful_content"
    PACKAGE_HALLUCINATION = "package_hallucination"
