"""
Output formatting utilities.

Purpose: Category mapping and severity calculation
Dependencies: libs.contracts.common
Used by: reporting/report_parser.py, utils.py
"""
from typing import Dict

from libs.contracts.common import VulnerabilityCategory, SeverityLevel


# Mapping from probe patterns to vulnerability categories
PROBE_TO_CONTRACT_CATEGORY: Dict[str, VulnerabilityCategory] = {
    "dan": VulnerabilityCategory.JAILBREAK,
    "promptinj": VulnerabilityCategory.JAILBREAK,
    "encoding": VulnerabilityCategory.JAILBREAK,
    "grandma": VulnerabilityCategory.JAILBREAK,
    "leak": VulnerabilityCategory.SAFETY_PII,
    "continuation": VulnerabilityCategory.SAFETY_PII,
    "goodside": VulnerabilityCategory.JAILBREAK,
    "glitch": VulnerabilityCategory.AUTH_BYPASS,
    "malware": VulnerabilityCategory.AUTH_BYPASS,
    "profanity": VulnerabilityCategory.COMPLIANCE_BIAS,
    "slur": VulnerabilityCategory.COMPLIANCE_BIAS,
    "sexual": VulnerabilityCategory.COMPLIANCE_BIAS,
    "donotanswer": VulnerabilityCategory.SAFETY_PII,
    "snowball": VulnerabilityCategory.SAFETY_PII,
    "pkg": VulnerabilityCategory.AUTH_BYPASS,
}


def get_category_for_probe(probe_name: str) -> VulnerabilityCategory:
    """Map probe name to vulnerability category.

    Args:
        probe_name: Name of the probe to categorize

    Returns:
        VulnerabilityCategory enum matching the probe type
    """
    probe_lower = probe_name.lower()
    for key, category in PROBE_TO_CONTRACT_CATEGORY.items():
        if key in probe_lower:
            return category
    return VulnerabilityCategory.SAFETY_PII


def get_severity(category: VulnerabilityCategory, failure_count: int) -> SeverityLevel:
    """Determine severity level based on category and failure count.

    Args:
        category: Vulnerability category
        failure_count: Number of failed tests

    Returns:
        SeverityLevel enum (CRITICAL, HIGH, MEDIUM, etc.)
    """
    if category in (VulnerabilityCategory.INJECTION_SQL, VulnerabilityCategory.INJECTION_NOSQL):
        return SeverityLevel.CRITICAL

    if category in (VulnerabilityCategory.JAILBREAK, VulnerabilityCategory.AUTH_BYPASS):
        return SeverityLevel.CRITICAL if failure_count > 5 else SeverityLevel.HIGH

    return SeverityLevel.HIGH if failure_count > 10 else SeverityLevel.MEDIUM
