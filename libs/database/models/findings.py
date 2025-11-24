"""Scan findings database model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from libs.database.session import Base


class ScanFinding(Base):
    """Vulnerability findings from the Swarm service."""

    __tablename__ = "scan_findings"

    id = Column(UUID(as_uuid=True), primary_key=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    cluster_id = Column(String(100), nullable=False)

    # Indexed for Strategist lookup queries
    vuln_type = Column(
        String(100), nullable=False, index=True, comment="e.g., injection.sql"
    )

    severity = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)

    evidence_payload = Column(
        Text, nullable=False, comment="The specific attack string"
    )
    error_response = Column(Text, nullable=True)

    # Full context for debugging
    raw_log = Column(JSONB, nullable=True, comment="Full Garak output")

    affected_component = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<ScanFinding(id={self.id}, vuln_type={self.vuln_type}, severity={self.severity})>"


# GIN index on vuln_type for fast lookup
Index("idx_findings_vuln_type_gin", ScanFinding.vuln_type, postgresql_using="gin")
