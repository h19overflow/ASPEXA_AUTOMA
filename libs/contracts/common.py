"""Common enums and base models for the Aspexa system."""
from enum import Enum
from pydantic import BaseModel, ConfigDict


class DepthLevel(str, Enum):
    """Reconnaissance depth levels."""
    SHALLOW = "shallow"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


class AttackEngine(str, Enum):
    """Attack execution engines."""
    PYRIT = "pyrit"
    DEEPTEAM = "deepteam"


class VulnerabilityCategory(str, Enum):
    """Vulnerability classification categories."""
    INJECTION_SQL = "injection.sql"
    INJECTION_NOSQL = "injection.nosql"
    COMPLIANCE_BIAS = "compliance.bias"
    SAFETY_PII = "safety.pii"
    JAILBREAK = "jailbreak"
    AUTH_BYPASS = "auth.bypass"


class SeverityLevel(str, Enum):
    """Finding severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResultStatus(str, Enum):
    """Execution result status."""
    VULNERABLE = "VULNERABLE"
    SAFE = "SAFE"
    FAILED_COMPLIANCE = "FAILED_COMPLIANCE"
    ERROR = "ERROR"


class ArtifactType(str, Enum):
    """Result artifact types."""
    KILL_CHAIN = "kill_chain"
    METRICS = "metrics"


class StrictBaseModel(BaseModel):
    """Base model with strict validation enabled."""
    model_config = ConfigDict(extra="forbid", validate_default=True, validate_assignment=True)
