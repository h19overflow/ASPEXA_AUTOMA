"""
Agent-level constants shared across the agents package.
"""

from services.snipers.core.phases.converters import SUFFIX_CONVERTER_NAMES

# Maximum converters per chain to prevent over-stacking and unrecognizable payloads
MAX_CHAIN_LENGTH = 3
# Length penalty: points deducted per converter over 2
LENGTH_PENALTY_FACTOR = 5
# Bonus for optimal length (2-3 converters)
OPTIMAL_LENGTH_BONUS = 10

# Base converters available in the system
_BASE_CONVERTERS = [
    "homoglyph",
    "unicode_substitution",
    "leetspeak",
    "base64",
    "rot13",
    "character_space",
    "morse_code",
    "html_entity",
    "xml_escape",
    "json_escape",
]

# All converters including suffix converters
AVAILABLE_CONVERTERS = _BASE_CONVERTERS + SUFFIX_CONVERTER_NAMES
