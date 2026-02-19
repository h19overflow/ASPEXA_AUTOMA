"""Attack mode and category enums."""
from enum import Enum


class AttackMode(str, Enum):
    """Attack execution mode."""
    GUIDED = "guided"      # Uses Garak findings for pattern analysis
    MANUAL = "manual"      # Custom payload with optional converters
    SWEEP = "sweep"        # All probes in selected categories


class ProbeCategory(str, Enum):
    """Probe categories for sweep mode."""
    JAILBREAK = "jailbreak"              # DAN, roleplay bypass
    PROMPT_INJECTION = "prompt_injection"  # Ignore instructions
    ENCODING = "encoding"                # Base64, ROT13, Unicode bypass
    DATA_EXTRACTION = "data_extraction"   # System prompt leak
    TOOL_EXPLOITATION = "tool_exploitation"  # Function call abuse
