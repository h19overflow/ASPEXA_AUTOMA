"""Campaigns (Audits) database model."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from libs.database.session import Base


class Campaign(Base):
    """Campaign/Audit session tracking."""
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    target_url = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # JSONB for evolving recon blueprint schema
    recon_blueprint = Column(JSONB, nullable=True, comment="IF-02 ReconBlueprint payload")
    
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Campaign(id={self.id}, target={self.target_url}, status={self.status})>"
