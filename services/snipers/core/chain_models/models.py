"""
Data models for converter chains and pattern discovery.

ConverterChain represents a sequence of PyRIT converters with metadata.
Used by pattern database and chain discovery strategies.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any
import hashlib


class ConverterChain(BaseModel):
    """
    Sequence of PyRIT converters with execution metadata.

    Attributes:
        chain_id: Unique deterministic identifier (hash of converter names)
        converter_names: Ordered list of converter class names
        converter_params: Parameters for each converter
        success_count: Number of successful attacks using this chain
        defense_patterns: Defense mechanisms this chain bypassed
        created_at: Timestamp of first use
        last_used_at: Timestamp of last successful use
        avg_score: Average composite score achieved
    """
    model_config = ConfigDict(frozen=True)

    chain_id: str
    converter_names: list[str]
    converter_params: dict[str, dict[str, Any]] = Field(default_factory=dict)
    success_count: int = 0
    defense_patterns: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    avg_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for S3 storage."""
        return {
            "chain_id": self.chain_id,
            "converter_names": self.converter_names,
            "converter_params": self.converter_params,
            "success_count": self.success_count,
            "defense_patterns": self.defense_patterns,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat(),
            "avg_score": self.avg_score
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConverterChain":
        """Deserialize from S3 dict."""
        return cls(
            chain_id=data["chain_id"],
            converter_names=data["converter_names"],
            converter_params=data.get("converter_params", {}),
            success_count=data.get("success_count", 0),
            defense_patterns=data.get("defense_patterns", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used_at=datetime.fromisoformat(data["last_used_at"]),
            avg_score=data.get("avg_score", 0.0)
        )

    @classmethod
    def from_converter_names(
        cls,
        converter_names: list[str],
        params: dict[str, dict[str, Any]] | None = None,
        defense_patterns: list[str] | None = None
    ) -> "ConverterChain":
        """Create chain with auto-generated chain_id."""
        chain_id = _generate_chain_id(converter_names)
        return cls(
            chain_id=chain_id,
            converter_names=converter_names,
            converter_params=params or {},
            defense_patterns=defense_patterns or []
        )


class ChainMetadata(BaseModel):
    """
    Metadata for pattern database entries.

    Attributes:
        campaign_id: Campaign that discovered this chain
        target_type: Type of target (http, websocket, grpc)
        vulnerability_type: Vulnerability exploited
        composite_score: Score achieved with this chain
    """
    model_config = ConfigDict(frozen=True)

    campaign_id: str
    target_type: str
    vulnerability_type: str
    composite_score: float


def _generate_chain_id(converter_names: list[str]) -> str:
    """Generate deterministic chain ID from converter names."""
    chain_str = "|".join(converter_names)
    return hashlib.sha256(chain_str.encode()).hexdigest()[:16]
