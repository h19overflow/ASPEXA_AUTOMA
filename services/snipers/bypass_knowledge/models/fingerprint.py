"""
Defense fingerprint model for semantic similarity matching.

Represents the structured input for embedding generation,
combining defense characteristics into a searchable representation.
"""

from pydantic import BaseModel, Field


class DefenseFingerprint(BaseModel):
    """
    Structured input for embedding generation.

    Combines defense response characteristics into a semantic
    representation suitable for vector similarity search.
    """

    defense_response: str = Field(description="Raw blocking message from the defense")
    failed_techniques: list[str] = Field(
        default_factory=list,
        description="Techniques that didn't work: encoding, direct_request, etc.",
    )
    domain: str = Field(default="", description="Target domain for semantic context")

    def to_embedding_text(self) -> str:
        """
        Convert fingerprint to text for embedding.

        Returns:
            Structured text representation combining all fingerprint components.
        """
        parts = [f"Defense Response: {self.defense_response}"]

        if self.failed_techniques:
            parts.append(f"Failed Techniques: {', '.join(self.failed_techniques)}")

        if self.domain:
            parts.append(f"Domain: {self.domain}")

        return "\n".join(parts)
