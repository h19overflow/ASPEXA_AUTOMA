"""IF-05, IF-06, IF-07: Attack Plan, Warrant, and Result contracts (Polymorphic)."""
from typing import Any, Dict, List, Literal, Union
from pydantic import Field, model_validator
from .common import StrictBaseModel, AttackEngine, ResultStatus, ArtifactType


class PyRitConfiguration(StrictBaseModel):
    """Configuration for PyRit exploitation engine."""
    orchestrator: str = Field(..., description="PyRit orchestrator class name")
    strategy_template: str = Field(..., description="Strategy template identifier")
    max_turns: int = Field(..., gt=0, description="Maximum conversation turns")
    conversation_seed: str = Field(..., description="Initial conversation seed")


class DeepTeamConfiguration(StrictBaseModel):
    """Configuration for DeepTeam compliance engine."""
    metric: str = Field(..., description="DeepEval metric name")
    iterations: int = Field(..., gt=0, description="Number of test iterations")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Pass/fail threshold")
    scenario: str = Field(..., description="Test scenario description")


class ExploitationPlan(StrictBaseModel):
    """Variant A: Exploitation Plan using PyRit."""
    plan_id: str = Field(..., description="Plan identifier")
    engine: Literal[AttackEngine.PYRIT] = Field(..., description="Must be 'pyrit'")
    objective: str = Field(..., description="Attack objective description")
    configuration: PyRitConfiguration
    
    @model_validator(mode="after")
    def validate_engine(self):
        """Ensure engine is pyrit for exploitation plans."""
        if self.engine != AttackEngine.PYRIT:
            raise ValueError("ExploitationPlan requires engine='pyrit'")
        return self


class CompliancePlan(StrictBaseModel):
    """Variant B: Compliance Audit Plan using DeepTeam."""
    plan_id: str = Field(..., description="Plan identifier")
    engine: Literal[AttackEngine.DEEPTEAM] = Field(..., description="Must be 'deepteam'")
    objective: str = Field(..., description="Compliance objective description")
    configuration: DeepTeamConfiguration
    
    @model_validator(mode="after")
    def validate_engine(self):
        """Ensure engine is deepteam for compliance plans."""
        if self.engine != AttackEngine.DEEPTEAM:
            raise ValueError("CompliancePlan requires engine='deepteam'")
        return self


SniperPlan = Union[ExploitationPlan, CompliancePlan]


class AttackWarrant(StrictBaseModel):
    """IF-06: The Attack Warrant (cmd_attack_execute)."""
    warrant_id: str = Field(..., description="Warrant identifier")
    signer_id: str = Field(..., description="User ID who signed the warrant")
    digital_signature: str = Field(..., description="SHA-256 hash of plan content")
    approved_plan: Union[ExploitationPlan, CompliancePlan] = Field(
        ...,
        discriminator="engine",
        description="The complete IF-05 plan object"
    )


class KillChainStep(StrictBaseModel):
    """A single step in an exploitation kill chain."""
    role: str = Field(..., description="Role (attacker/target)")
    content: str = Field(..., description="Message content")


class ExploitationProof(StrictBaseModel):
    """Exploitation proof data."""
    steps: List[KillChainStep] = Field(..., description="Kill chain conversation steps")
    extracted_secret: str = Field(..., description="Extracted sensitive data")


class ComplianceMetrics(StrictBaseModel):
    """Compliance test metrics."""
    metric_name: str = Field(..., description="Metric name")
    average_score: float = Field(..., ge=0.0, le=1.0, description="Average metric score")
    iterations_run: int = Field(..., gt=0, description="Number of iterations executed")
    failure_count: int = Field(..., ge=0, description="Number of failed tests")


class ExploitationResult(StrictBaseModel):
    """Variant A: Exploitation Result."""
    warrant_id: str = Field(..., description="Warrant identifier")
    status: ResultStatus = Field(..., description="Execution status")
    artifact_type: Literal[ArtifactType.KILL_CHAIN] = Field(
        ...,
        description="Must be 'kill_chain'"
    )
    data: ExploitationProof


class ComplianceResult(StrictBaseModel):
    """Variant B: Compliance Result."""
    warrant_id: str = Field(..., description="Warrant identifier")
    status: ResultStatus = Field(..., description="Execution status")
    artifact_type: Literal[ArtifactType.METRICS] = Field(
        ...,
        description="Must be 'metrics'"
    )
    data: ComplianceMetrics


KillChainResult = Union[ExploitationResult, ComplianceResult]
