"""Operations (Attack Plans & Executions) database model."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy import ForeignKey
from libs.database.session import Base


class StrategyAtlas(Base):
    """Knowledge base of attack strategies."""
    __tablename__ = "strategy_atlas"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_name = Column(String(100), nullable=False, unique=True)
    
    # PyRit YAML template
    skeleton_yaml = Column(Text, nullable=False, comment="PyRit template YAML")
    
    # Strict allowlist for security
    pyrit_class_ref = Column(String(200), nullable=False, comment="e.g., pyrit.orchestrator.RedTeamingOrchestrator")
    
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<StrategyAtlas(name={self.strategy_name}, class={self.pyrit_class_ref})>"


class SniperPlan(Base):
    """Generated attack plans awaiting approval."""
    __tablename__ = "sniper_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    plan_id = Column(String(100), nullable=False, unique=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategy_atlas.id"), nullable=True)
    
    # IF-05 payload (fully hydrated with LLM-generated persona)
    generated_config = Column(JSONB, nullable=False, comment="IF-05 SniperPlan payload")
    
    status = Column(String(50), nullable=False, default="pending_approval", comment="State machine trigger")
    engine_type = Column(String(20), nullable=False, comment="pyrit or deepteam")
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<SniperPlan(id={self.plan_id}, engine={self.engine_type}, status={self.status})>"


class PlanSignature(Base):
    """Digital signatures for approved plans (Tamper Protection)."""
    __tablename__ = "plan_signatures"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("sniper_plans.id"), nullable=False, unique=True)
    
    signer_user_id = Column(String(100), nullable=False, comment="User who approved the plan")
    
    # SHA-256 hash of generated_config blob
    digital_signature = Column(String(64), nullable=False, comment="SHA-256 hash for tamper detection")
    
    signed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PlanSignature(plan_id={self.plan_id}, signer={self.signer_user_id})>"


class ExecutionResult(Base):
    """Attack execution results (from Snipers)."""
    __tablename__ = "execution_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    warrant_id = Column(String(100), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("sniper_plans.id"), nullable=False)
    
    status = Column(String(50), nullable=False, comment="VULNERABLE, SAFE, FAILED_COMPLIANCE, ERROR")
    artifact_type = Column(String(20), nullable=False, comment="kill_chain or metrics")
    
    # Stores mixed results (Text logs from PyRit, Metrics from DeepTeam)
    result_data = Column(JSONB, nullable=False, comment="IF-07 KillChainResult payload")
    
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ExecutionResult(warrant_id={self.warrant_id}, status={self.status})>"
