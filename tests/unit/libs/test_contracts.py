"""Tests for data contracts (IF-01 through IF-07)."""
import pytest
from pydantic import ValidationError
from libs.contracts import (
    # Common
    DepthLevel,
    AttackEngine,
    VulnerabilityCategory,
    SeverityLevel,
    ResultStatus,
    ArtifactType,
    # Recon
    TargetConfig,
    ScopeConfig,
    ReconRequest,
    Intelligence,
    InfrastructureIntel,
    AuthStructure,
    ReconBlueprint,
    # Scanning
    SafetyPolicy,
    ScanJobDispatch,
    Evidence,
    VulnerabilityCluster,
    # Attack
    PyRitConfiguration,
    DeepTeamConfiguration,
    ExploitationPlan,
    CompliancePlan,
    AttackWarrant,
    ExploitationResult,
    ComplianceResult,
)


class TestCommonEnums:
    """Test common enums and base models."""
    
    def test_depth_level_values(self):
        """Test DepthLevel enum values."""
        assert DepthLevel.SHALLOW == "shallow"
        assert DepthLevel.STANDARD == "standard"
        assert DepthLevel.AGGRESSIVE == "aggressive"
    
    def test_attack_engine_values(self):
        """Test AttackEngine enum values."""
        assert AttackEngine.PYRIT == "pyrit"
        assert AttackEngine.DEEPTEAM == "deepteam"


class TestReconContracts:
    """Test IF-01 and IF-02: Reconnaissance contracts."""
    
    def test_recon_request_valid(self):
        """Test valid ReconRequest creation."""
        request = ReconRequest(
            audit_id="test-audit-123",
            target={
                "url": "https://api.example.com/v1/chat",
                "auth_headers": {"Authorization": "Bearer token123"}
            },
            scope={
                "depth": "standard",
                "max_turns": 10,
                "forbidden_keywords": ["DELETE", "DROP"]
            }
        )
        assert request.audit_id == "test-audit-123"
        assert request.target.url == "https://api.example.com/v1/chat"
        assert request.scope.depth == DepthLevel.STANDARD
    
    def test_scope_config_depth_validation(self):
        """Test ScopeConfig depth validation."""
        # Valid depths
        for depth in ["shallow", "standard", "aggressive"]:
            scope = ScopeConfig(depth=depth, max_turns=5)
            assert scope.depth in [DepthLevel.SHALLOW, DepthLevel.STANDARD, DepthLevel.AGGRESSIVE]
        
        # Invalid depth should raise error
        with pytest.raises(ValidationError):
            ScopeConfig(depth="invalid", max_turns=5)
    
    def test_recon_blueprint_valid(self):
        """Test valid ReconBlueprint creation."""
        blueprint = ReconBlueprint(
            audit_id="test-audit-123",
            timestamp="2025-11-23T12:00:00Z",
            intelligence={
                "system_prompt_leak": ["You are helpful"],
                "detected_tools": [
                    {"name": "search_db", "arguments": ["query"]}
                ],
                "infrastructure": {
                    "vector_db": "pinecone",
                    "model_family": "gpt-4",
                    "rate_limits": "strict"
                },
                "auth_structure": {
                    "type": "RBAC",
                    "vulnerabilities": ["idor"]
                }
            }
        )
        assert blueprint.audit_id == "test-audit-123"
        assert len(blueprint.intelligence.detected_tools) == 1
    
    def test_strict_validation_rejects_extra_fields(self):
        """Test that strict=True rejects extra fields."""
        with pytest.raises(ValidationError):
            ReconRequest(
                audit_id="test",
                target={"url": "http://test.com", "auth_headers": {}},
                scope={"depth": "standard", "max_turns": 5},
                extra_field="should_fail"
            )


class TestScanningContracts:
    """Test IF-03 and IF-04: Scanning contracts."""
    
    def test_scan_job_dispatch_valid(self):
        """Test valid ScanJobDispatch creation."""
        dispatch = ScanJobDispatch(
            job_id="scan-001",
            blueprint_context={"intelligence": {}},
            safety_policy={
                "allowed_attack_vectors": ["injection", "jailbreak"],
                "blocked_attack_vectors": ["dos"],
                "aggressiveness": "medium"
            }
        )
        assert dispatch.job_id == "scan-001"
        assert len(dispatch.safety_policy.allowed_attack_vectors) == 2
    
    def test_vulnerability_cluster_valid(self):
        """Test valid VulnerabilityCluster creation."""
        cluster = VulnerabilityCluster(
            audit_id="test-audit",
            cluster_id="vuln-sql-01",
            category="injection.sql",
            severity="high",
            evidence={
                "input_payload": "' OR 1=1 --",
                "error_response": "SQL syntax error",
                "confidence_score": 0.95
            },
            affected_component="tool:search_database"
        )
        assert cluster.category == VulnerabilityCategory.INJECTION_SQL
        assert cluster.severity == SeverityLevel.HIGH
        assert cluster.evidence.confidence_score == 0.95


class TestAttackContracts:
    """Test IF-05, IF-06, IF-07: Attack contracts (Polymorphic)."""
    
    def test_exploitation_plan_valid(self):
        """Test valid ExploitationPlan creation."""
        plan = ExploitationPlan(
            plan_id="plan-alpha",
            engine="pyrit",
            objective="Test SQL injection",
            configuration={
                "orchestrator": "RedTeamingOrchestrator",
                "strategy_template": "sql_exfiltration_v2",
                "max_turns": 5,
                "conversation_seed": "Test seed"
            }
        )
        assert plan.engine == AttackEngine.PYRIT
        assert plan.configuration.orchestrator == "RedTeamingOrchestrator"
    
    def test_exploitation_plan_requires_pyrit_engine(self):
        """Test ExploitationPlan rejects non-pyrit engine."""
        with pytest.raises(ValidationError):
            ExploitationPlan(
                plan_id="plan-alpha",
                engine="deepteam",  # Wrong engine
                objective="Test",
                configuration={
                    "orchestrator": "Test",
                    "strategy_template": "test",
                    "max_turns": 5,
                    "conversation_seed": "test"
                }
            )
    
    def test_compliance_plan_valid(self):
        """Test valid CompliancePlan creation."""
        plan = CompliancePlan(
            plan_id="plan-beta",
            engine="deepteam",
            objective="Verify bias resistance",
            configuration={
                "metric": "Bias",
                "iterations": 20,
                "threshold": 0.7,
                "scenario": "Political questions"
            }
        )
        assert plan.engine == AttackEngine.DEEPTEAM
        assert plan.configuration.metric == "Bias"
    
    def test_compliance_plan_requires_deepteam_engine(self):
        """Test CompliancePlan rejects non-deepteam engine."""
        with pytest.raises(ValidationError):
            CompliancePlan(
                plan_id="plan-beta",
                engine="pyrit",  # Wrong engine
                objective="Test",
                configuration={
                    "metric": "Bias",
                    "iterations": 20,
                    "threshold": 0.7,
                    "scenario": "test"
                }
            )
    
    def test_attack_warrant_with_exploitation_plan(self):
        """Test AttackWarrant with ExploitationPlan."""
        warrant = AttackWarrant(
            warrant_id="warrant-001",
            signer_id="admin_alice",
            digital_signature="abc123def456",
            approved_plan={
                "plan_id": "plan-alpha",
                "engine": "pyrit",
                "objective": "Test",
                "configuration": {
                    "orchestrator": "Test",
                    "strategy_template": "test",
                    "max_turns": 5,
                    "conversation_seed": "test"
                }
            }
        )
        assert warrant.warrant_id == "warrant-001"
        assert isinstance(warrant.approved_plan, ExploitationPlan)
    
    def test_attack_warrant_with_compliance_plan(self):
        """Test AttackWarrant with CompliancePlan."""
        warrant = AttackWarrant(
            warrant_id="warrant-002",
            signer_id="admin_bob",
            digital_signature="xyz789ghi012",
            approved_plan={
                "plan_id": "plan-beta",
                "engine": "deepteam",
                "objective": "Test",
                "configuration": {
                    "metric": "Bias",
                    "iterations": 20,
                    "threshold": 0.7,
                    "scenario": "test"
                }
            }
        )
        assert warrant.warrant_id == "warrant-002"
        assert isinstance(warrant.approved_plan, CompliancePlan)
    
    def test_exploitation_result_valid(self):
        """Test valid ExploitationResult creation."""
        result = ExploitationResult(
            warrant_id="warrant-001",
            status="VULNERABLE",
            artifact_type="kill_chain",
            data={
                "steps": [
                    {"role": "attacker", "content": "test payload"},
                    {"role": "target", "content": "leaked secret"}
                ],
                "extracted_secret": "password123"
            }
        )
        assert result.status == ResultStatus.VULNERABLE
        assert result.artifact_type == ArtifactType.KILL_CHAIN
        assert len(result.data.steps) == 2
    
    def test_compliance_result_valid(self):
        """Test valid ComplianceResult creation."""
        result = ComplianceResult(
            warrant_id="warrant-002",
            status="SAFE",
            artifact_type="metrics",
            data={
                "metric_name": "Bias",
                "average_score": 0.12,
                "iterations_run": 20,
                "failure_count": 0
            }
        )
        assert result.status == ResultStatus.SAFE
        assert result.artifact_type == ArtifactType.METRICS
        assert result.data.average_score == 0.12


class TestStrictValidation:
    """Test strict validation across all models."""
    
    def test_strict_validation_rejects_invalid_types(self):
        """Test that validation rejects truly invalid types."""
        with pytest.raises(ValidationError):
            Evidence(
                input_payload="test",
                error_response="test",
                confidence_score="invalid_string"  # Cannot be converted to float
            )
    
    def test_strict_validation_requires_all_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ReconRequest(
                audit_id="test"
                # Missing target and scope
            )
