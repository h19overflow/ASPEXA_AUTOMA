"""Unit tests for Swarm service schema intelligence integration.

Tests verify that:
1. AuthIntelligence model validation works correctly
2. ScanInput accepts all new intelligence fields
3. ScanContext.from_scan_job() extracts full intelligence from ReconBlueprint
4. ScanContext.to_scan_input() preserves all fields
5. _build_planning_input() includes all intelligence sections in output
"""

import json
import pytest
from typing import Dict, List, Any

from libs.contracts.recon import (
    ReconBlueprint,
    Intelligence,
    InfrastructureIntel,
    AuthStructure,
    DetectedTool,
)
from libs.contracts.scanning import (
    ScanJobDispatch,
    SafetyPolicy,
    ScanConfigContract,
)
from services.swarm.core.schema import (
    AuthIntelligence,
    ScanInput,
    ScanContext,
    ScanConfig,
)
from services.swarm.agents.base import _build_planning_input


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def infrastructure_intel() -> InfrastructureIntel:
    """Create sample infrastructure intelligence."""
    return InfrastructureIntel(
        vector_db="pinecone",
        model_family="gpt-4",
        rate_limits="500 req/min"
    )


@pytest.fixture
def auth_structure() -> AuthStructure:
    """Create sample auth structure."""
    return AuthStructure(
        type="RBAC",
        rules=[
            "admin_role: full_access",
            "user_role: read_only",
            "guest_role: limited_read"
        ],
        vulnerabilities=[
            "missing_permission_check_on_delete",
            "privilege_escalation_via_role_assignment"
        ]
    )


@pytest.fixture
def detected_tools() -> List[DetectedTool]:
    """Create sample detected tools."""
    return [
        DetectedTool(name="search_database", arguments=["query", "limit"]),
        DetectedTool(name="get_user_info", arguments=["user_id"]),
        DetectedTool(name="execute_sql", arguments=["sql_query"]),
    ]


@pytest.fixture
def raw_observations() -> Dict[str, List[str]]:
    """Create sample raw observations."""
    return {
        "error_messages": [
            "ERROR: Invalid permission for operation",
            "ERROR: Database connection refused",
            "ERROR: User not authenticated"
        ],
        "response_headers": [
            "X-RateLimit-Limit: 500",
            "X-RateLimit-Remaining: 450",
            "X-Admin-Header: true"
        ],
        "behavior_patterns": [
            "Fast response on admin operations",
            "Slow response on data retrieval",
            "No error details in responses"
        ]
    }


@pytest.fixture
def structured_deductions() -> Dict[str, List[Dict[str, str]]]:
    """Create sample structured deductions."""
    return {
        "infrastructure": [
            {
                "deduction": "Uses PostgreSQL database based on error patterns",
                "confidence": "high",
                "evidence": "Error format matches PostgreSQL"
            },
            {
                "deduction": "Vector DB likely Pinecone for embeddings",
                "confidence": "medium",
                "evidence": "Response latency pattern suggests vector search"
            }
        ],
        "security": [
            {
                "finding": "RBAC implementation detected",
                "confidence": "high",
                "evidence": "Role headers present in responses"
            },
            {
                "finding": "Possible privilege escalation vulnerability",
                "confidence": "medium",
                "evidence": "Admin header modifiable in requests"
            }
        ],
        "auth": [
            {
                "finding": "Session-based authentication",
                "confidence": "high",
                "evidence": "Session cookie present"
            }
        ]
    }


@pytest.fixture
def intelligence(
    infrastructure_intel,
    auth_structure,
    detected_tools
) -> Intelligence:
    """Create sample Intelligence object."""
    return Intelligence(
        system_prompt_leak=[
            "You are a helpful AI assistant",
            "You have access to the following tools:",
            "Always verify user permissions"
        ],
        detected_tools=detected_tools,
        infrastructure=infrastructure_intel,
        auth_structure=auth_structure
    )


@pytest.fixture
def recon_blueprint(
    intelligence,
    raw_observations,
    structured_deductions
) -> ReconBlueprint:
    """Create sample ReconBlueprint with full intelligence."""
    return ReconBlueprint(
        audit_id="test-audit-123",
        timestamp="2025-11-23T12:00:00Z",
        intelligence=intelligence,
        raw_observations=raw_observations,
        structured_deductions=structured_deductions
    )


@pytest.fixture
def scan_config_contract() -> ScanConfigContract:
    """Create sample ScanConfigContract."""
    return ScanConfigContract(
        approach="standard",
        generations=5,
        custom_probes=["dan", "promptinj"],
        allow_agent_override=True,
        max_probes=10,
        max_generations=15,
        enable_parallel_execution=True,
        max_concurrent_probes=3,
        max_concurrent_generations=3,
        requests_per_second=10.0,
        max_concurrent_connections=15,
        request_timeout=30,
        max_retries=3,
        retry_backoff=1.0,
        connection_type="http"
    )


@pytest.fixture
def safety_policy() -> SafetyPolicy:
    """Create sample SafetyPolicy."""
    return SafetyPolicy(
        allowed_attack_vectors=["sql", "auth", "jailbreak"],
        blocked_attack_vectors=["destructive"],
        aggressiveness="standard"
    )


@pytest.fixture
def scan_job_dispatch(
    recon_blueprint,
    safety_policy,
    scan_config_contract
) -> ScanJobDispatch:
    """Create sample ScanJobDispatch."""
    return ScanJobDispatch(
        job_id="scan-job-001",
        blueprint_context=recon_blueprint.model_dump(),
        safety_policy=safety_policy,
        scan_config=scan_config_contract,
        target_url="https://api.target.local/v1/chat"
    )


# ============================================================================
# Tests for AuthIntelligence
# ============================================================================

class TestAuthIntelligence:
    """Tests for AuthIntelligence model validation."""

    def test_auth_intelligence_creation_with_all_fields(self):
        """Should create AuthIntelligence with all fields."""
        auth = AuthIntelligence(
            type="OAuth2",
            rules=["scope:user_read", "scope:user_write"],
            vulnerabilities=["missing_state_validation"]
        )

        assert auth.type == "OAuth2"
        assert auth.rules == ["scope:user_read", "scope:user_write"]
        assert auth.vulnerabilities == ["missing_state_validation"]

    def test_auth_intelligence_with_defaults(self):
        """Should create AuthIntelligence with default values."""
        auth = AuthIntelligence()

        assert auth.type == "unknown"
        assert auth.rules == []
        assert auth.vulnerabilities == []

    def test_auth_intelligence_partial_fields(self):
        """Should create AuthIntelligence with partial fields."""
        auth = AuthIntelligence(
            type="RBAC",
            rules=["admin", "user"]
        )

        assert auth.type == "RBAC"
        assert auth.rules == ["admin", "user"]
        assert auth.vulnerabilities == []

    def test_auth_intelligence_serialization(self):
        """Should serialize AuthIntelligence to dict."""
        auth = AuthIntelligence(
            type="LDAP",
            rules=["cn=admins", "cn=users"],
            vulnerabilities=["ldap_injection"]
        )

        data = auth.model_dump()

        assert data["type"] == "LDAP"
        assert data["rules"] == ["cn=admins", "cn=users"]
        assert data["vulnerabilities"] == ["ldap_injection"]

    def test_auth_intelligence_validation_from_dict(self):
        """Should validate AuthIntelligence from dict."""
        data = {
            "type": "Kerberos",
            "rules": ["spn:service/host"],
            "vulnerabilities": ["overpass_the_hash"]
        }

        auth = AuthIntelligence(**data)

        assert auth.type == "Kerberos"
        assert auth.rules == ["spn:service/host"]
        assert auth.vulnerabilities == ["overpass_the_hash"]


# ============================================================================
# Tests for ScanInput Intelligence Fields
# ============================================================================

class TestScanInput:
    """Tests for ScanInput with intelligence fields."""

    def test_scan_input_creation_with_all_intelligence_fields(self, auth_structure):
        """Should create ScanInput with all intelligence fields."""
        auth_intel = AuthIntelligence(
            type=auth_structure.type,
            rules=auth_structure.rules,
            vulnerabilities=auth_structure.vulnerabilities
        )

        scan_input = ScanInput(
            audit_id="test-audit",
            agent_type="agent_sql",
            target_url="https://api.local/v1",
            infrastructure={"model_family": "gpt-4"},
            detected_tools=[{"name": "search", "arguments": ["query"]}],
            system_prompt_leaks=["You are helpful"],
            auth_intelligence=auth_intel,
            raw_observations={"errors": ["error1"]},
            structured_deductions={"findings": [{"finding": "test"}]}
        )

        assert scan_input.audit_id == "test-audit"
        assert scan_input.agent_type == "agent_sql"
        assert scan_input.system_prompt_leaks == ["You are helpful"]
        assert scan_input.auth_intelligence == auth_intel
        assert scan_input.raw_observations == {"errors": ["error1"]}
        assert scan_input.structured_deductions == {"findings": [{"finding": "test"}]}

    def test_scan_input_with_defaults(self):
        """Should create ScanInput with default values for intelligence fields."""
        scan_input = ScanInput(
            audit_id="test-audit",
            agent_type="agent_auth",
            target_url="https://api.local/v1"
        )

        assert scan_input.system_prompt_leaks == []
        assert scan_input.auth_intelligence is None
        assert scan_input.raw_observations == {}
        assert scan_input.structured_deductions == {}

    def test_scan_input_serialization(self, auth_structure):
        """Should serialize ScanInput with all intelligence fields."""
        auth_intel = AuthIntelligence(
            type=auth_structure.type,
            rules=auth_structure.rules,
            vulnerabilities=auth_structure.vulnerabilities
        )

        scan_input = ScanInput(
            audit_id="test-audit",
            agent_type="agent_auth",
            target_url="https://api.local/v1",
            system_prompt_leaks=["You are helpful"],
            auth_intelligence=auth_intel,
            raw_observations={"errors": ["error1"]},
            structured_deductions={"findings": [{"finding": "test"}]}
        )

        data = scan_input.model_dump()

        assert data["system_prompt_leaks"] == ["You are helpful"]
        assert data["auth_intelligence"]["type"] == auth_structure.type
        assert data["raw_observations"]["errors"] == ["error1"]
        assert data["structured_deductions"]["findings"][0]["finding"] == "test"

    def test_scan_input_validation_from_dict(self):
        """Should validate ScanInput from dict with intelligence fields."""
        data = {
            "audit_id": "test-audit",
            "agent_type": "agent_jailbreak",
            "target_url": "https://api.local/v1",
            "system_prompt_leaks": ["You are helpful", "Always respect user intent"],
            "auth_intelligence": {
                "type": "JWT",
                "rules": ["iss: trusted", "exp: valid"],
                "vulnerabilities": ["none_algorithm"]
            },
            "raw_observations": {
                "headers": ["Authorization: Bearer token"]
            },
            "structured_deductions": {
                "auth": [{"finding": "JWT used", "confidence": "high"}]
            }
        }

        scan_input = ScanInput(**data)

        assert scan_input.system_prompt_leaks == ["You are helpful", "Always respect user intent"]
        assert scan_input.auth_intelligence.type == "JWT"
        assert scan_input.auth_intelligence.vulnerabilities == ["none_algorithm"]
        assert scan_input.raw_observations == {"headers": ["Authorization: Bearer token"]}
        assert len(scan_input.structured_deductions["auth"]) == 1


# ============================================================================
# Tests for ScanContext Intelligence Extraction
# ============================================================================

class TestScanContextFromScanJob:
    """Tests for ScanContext.from_scan_job() intelligence extraction."""

    def test_from_scan_job_extracts_all_intelligence(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should extract all intelligence from ReconBlueprint."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        # Verify all intelligence fields are extracted
        assert context.audit_id == recon_blueprint.audit_id
        assert context.system_prompt_leaks == recon_blueprint.intelligence.system_prompt_leak
        assert context.auth_intelligence is not None
        assert context.auth_intelligence.type == "RBAC"
        assert len(context.auth_intelligence.rules) == 3
        assert len(context.auth_intelligence.vulnerabilities) == 2
        assert context.raw_observations == recon_blueprint.raw_observations
        assert context.structured_deductions == recon_blueprint.structured_deductions

    def test_from_scan_job_infrastructure_extraction(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should extract infrastructure details."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        assert context.infrastructure["model_family"] == "gpt-4"
        assert context.infrastructure["vector_db"] == "pinecone"
        assert context.infrastructure["rate_limits"] == "500 req/min"

    def test_from_scan_job_detected_tools_extraction(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should extract detected tools."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        assert len(context.detected_tools) == 3
        tool_names = [t["name"] for t in context.detected_tools]
        assert "search_database" in tool_names
        assert "get_user_info" in tool_names
        assert "execute_sql" in tool_names

    def test_from_scan_job_scan_config_conversion(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should convert ScanConfigContract to ScanConfig."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        assert isinstance(context.config, ScanConfig)
        assert context.config.approach == "standard"
        assert context.config.generations == 5
        assert context.config.custom_probes == ["dan", "promptinj"]
        assert context.config.allow_agent_override is True
        assert context.config.max_probes == 10
        assert context.config.enable_parallel_execution is True

    def test_from_scan_job_target_url_override(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should use request target_url when provided."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        assert context.target_url == "https://api.target.local/v1/chat"

    def test_from_scan_job_target_url_default(
        self,
        recon_blueprint,
        safety_policy,
        scan_config_contract
    ):
        """Should use default target_url when request has None."""
        job = ScanJobDispatch(
            job_id="scan-job-001",
            blueprint_context=recon_blueprint.model_dump(),
            safety_policy=safety_policy,
            scan_config=scan_config_contract,
            target_url=None
        )

        context = ScanContext.from_scan_job(
            request=job,
            blueprint=recon_blueprint,
            agent_type="agent_sql",
            default_target_url="https://default.local/v1/chat"
        )

        assert context.target_url == "https://default.local/v1/chat"

    def test_from_scan_job_with_partial_intelligence(
        self,
        safety_policy,
        scan_config_contract
    ):
        """Should handle ReconBlueprint with minimal intelligence."""
        minimal_blueprint = ReconBlueprint(
            audit_id="test-audit",
            timestamp="2025-11-23T12:00:00Z",
            intelligence=Intelligence(
                system_prompt_leak=[],
                detected_tools=[],
                infrastructure=InfrastructureIntel(
                    vector_db=None,
                    model_family=None,
                    rate_limits=None
                ),
                auth_structure=AuthStructure(type="unknown")
            )
        )

        job = ScanJobDispatch(
            job_id="scan-job-001",
            blueprint_context=minimal_blueprint.model_dump(),
            safety_policy=safety_policy,
            scan_config=scan_config_contract,
            target_url="https://api.local/v1"
        )

        context = ScanContext.from_scan_job(
            request=job,
            blueprint=minimal_blueprint,
            agent_type="agent_auth"
        )

        assert context.audit_id == "test-audit"
        assert context.system_prompt_leaks == []
        assert context.detected_tools == []
        assert context.auth_intelligence is not None
        assert context.auth_intelligence.type == "unknown"

    def test_from_scan_job_agent_type_preserved(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should preserve agent_type in context."""
        for agent_type in ["agent_sql", "agent_auth", "agent_jailbreak"]:
            context = ScanContext.from_scan_job(
                request=scan_job_dispatch,
                blueprint=recon_blueprint,
                agent_type=agent_type
            )

            assert context.agent_type == agent_type


# ============================================================================
# Tests for ScanContext to ScanInput Conversion
# ============================================================================

class TestScanContextToScanInput:
    """Tests for ScanContext.to_scan_input() field preservation."""

    def test_to_scan_input_preserves_all_fields(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should preserve all fields in conversion to ScanInput."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()

        assert scan_input.audit_id == context.audit_id
        assert scan_input.agent_type == context.agent_type
        assert scan_input.target_url == context.target_url
        assert scan_input.infrastructure == context.infrastructure
        assert scan_input.detected_tools == context.detected_tools
        assert scan_input.system_prompt_leaks == context.system_prompt_leaks
        assert scan_input.auth_intelligence == context.auth_intelligence
        assert scan_input.raw_observations == context.raw_observations
        assert scan_input.structured_deductions == context.structured_deductions
        assert scan_input.config == context.config

    def test_to_scan_input_creates_valid_model(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should create a valid ScanInput model."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_auth"
        )

        scan_input = context.to_scan_input()

        # Verify it's a valid ScanInput instance
        assert isinstance(scan_input, ScanInput)
        # Verify it can be serialized
        data = scan_input.model_dump()
        assert data["audit_id"] == context.audit_id
        assert data["agent_type"] == context.agent_type

    def test_to_scan_input_serialization_roundtrip(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should support serialization and deserialization roundtrip."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_jailbreak"
        )

        scan_input = context.to_scan_input()
        data = scan_input.model_dump()
        reconstructed = ScanInput(**data)

        assert reconstructed.audit_id == scan_input.audit_id
        assert reconstructed.agent_type == scan_input.agent_type
        assert reconstructed.system_prompt_leaks == scan_input.system_prompt_leaks
        assert reconstructed.auth_intelligence == scan_input.auth_intelligence


# ============================================================================
# Tests for _build_planning_input Intelligence Sections
# ============================================================================

class TestBuildPlanningInput:
    """Tests for _build_planning_input intelligence formatting."""

    def test_build_planning_input_includes_system_prompt_leaks(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include system prompt leaks section."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "System Prompt Leaks Found" in content
        assert "You are a helpful AI assistant" in content

    def test_build_planning_input_includes_auth_intelligence(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include authentication intelligence section."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_auth"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "Authentication Intelligence:" in content
        assert "Type: RBAC" in content
        assert "Rules:" in content
        assert "admin_role: full_access" in content
        assert "Known Vulnerabilities:" in content
        assert "privilege_escalation_via_role_assignment" in content

    def test_build_planning_input_includes_raw_observations(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include raw observations section."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "Raw Observations by Category:" in content
        assert "[error_messages]:" in content
        assert "ERROR: Invalid permission for operation" in content

    def test_build_planning_input_includes_structured_deductions(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include structured deductions section."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "Structured Deductions (Analyzed Findings):" in content
        assert "[infrastructure]:" in content
        assert "Uses PostgreSQL database" in content
        assert "confidence:" in content

    def test_build_planning_input_includes_infrastructure(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include infrastructure details."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "Infrastructure:" in content
        assert "gpt-4" in content
        assert "pinecone" in content

    def test_build_planning_input_includes_detected_tools(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include detected tools section."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "Detected Tools" in content
        assert "search_database" in content
        assert "execute_sql" in content

    def test_build_planning_input_includes_user_configuration(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should include user configuration section."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        content = message.content
        assert "User Configuration:" in content
        assert "Approach: standard" in content
        assert "Max Probes: 10" in content
        assert "Max Generations: 15" in content
        assert "Agent Override Allowed: True" in content

    def test_build_planning_input_handles_missing_auth_intelligence(
        self,
        safety_policy,
        scan_config_contract
    ):
        """Should handle ScanInput without auth_intelligence."""
        minimal_blueprint = ReconBlueprint(
            audit_id="test-audit",
            timestamp="2025-11-23T12:00:00Z",
            intelligence=Intelligence(
                system_prompt_leak=[],
                detected_tools=[],
                infrastructure=InfrastructureIntel(
                    vector_db=None,
                    model_family=None,
                    rate_limits=None
                ),
                auth_structure=AuthStructure(type="unknown")
            )
        )

        job = ScanJobDispatch(
            job_id="scan-job-001",
            blueprint_context=minimal_blueprint.model_dump(),
            safety_policy=safety_policy,
            scan_config=scan_config_contract,
            target_url="https://api.local/v1"
        )

        context = ScanContext.from_scan_job(
            request=job,
            blueprint=minimal_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        # Should not crash and should produce valid content
        assert isinstance(message.content, str)
        assert len(message.content) > 0
        # Auth section should be omitted since auth_intelligence is None
        # (unless auth_structure defaults to unknown type)

    def test_build_planning_input_message_format(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should produce properly formatted HumanMessage."""
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        scan_input = context.to_scan_input()
        message = _build_planning_input(scan_input)

        # Verify message structure
        assert hasattr(message, 'content')
        assert isinstance(message.content, str)
        assert len(message.content) > 100  # Substantial content
        assert "RECONNAISSANCE INTELLIGENCE" in message.content
        assert "INSTRUCTIONS" in message.content

    def test_build_planning_input_includes_allow_agent_override_instruction(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should vary instruction based on allow_agent_override flag."""
        # Test with allow_agent_override=True
        job_allow = ScanJobDispatch(
            job_id="scan-job-001",
            blueprint_context=recon_blueprint.model_dump(),
            safety_policy=SafetyPolicy(
                allowed_attack_vectors=["sql"],
                blocked_attack_vectors=[],
                aggressiveness="standard"
            ),
            scan_config=ScanConfigContract(allow_agent_override=True),
            target_url="https://api.local/v1"
        )

        context_allow = ScanContext.from_scan_job(
            request=job_allow,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )
        scan_input_allow = context_allow.to_scan_input()
        message_allow = _build_planning_input(scan_input_allow)

        assert "may adjust" in message_allow.content.lower()

        # Test with allow_agent_override=False
        job_fixed = ScanJobDispatch(
            job_id="scan-job-001",
            blueprint_context=recon_blueprint.model_dump(),
            safety_policy=SafetyPolicy(
                allowed_attack_vectors=["sql"],
                blocked_attack_vectors=[],
                aggressiveness="standard"
            ),
            scan_config=ScanConfigContract(allow_agent_override=False),
            target_url="https://api.local/v1"
        )

        context_fixed = ScanContext.from_scan_job(
            request=job_fixed,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )
        scan_input_fixed = context_fixed.to_scan_input()
        message_fixed = _build_planning_input(scan_input_fixed)

        assert "exact configuration" in message_fixed.content.lower()


# ============================================================================
# Integration Tests
# ============================================================================

class TestSchemaintelligenceIntegration:
    """Integration tests for full schema intelligence flow."""

    def test_full_flow_from_scan_job_to_planning_input(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should flow from ScanJobDispatch to planning input without loss."""
        # Step 1: Create ScanContext from ScanJobDispatch and ReconBlueprint
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_sql"
        )

        # Step 2: Convert to ScanInput
        scan_input = context.to_scan_input()

        # Step 3: Build planning input
        message = _build_planning_input(scan_input)

        # Verify full intelligence is present in planning input
        content = message.content
        assert scan_input.audit_id in content
        assert "System Prompt Leaks Found" in content
        assert "Authentication Intelligence" in content
        assert "Raw Observations" in content
        assert "Structured Deductions" in content
        assert scan_input.agent_type in content

    def test_multiple_agents_same_blueprint(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should create different contexts for different agent types."""
        agent_types = ["agent_sql", "agent_auth", "agent_jailbreak"]
        contexts = []

        for agent_type in agent_types:
            context = ScanContext.from_scan_job(
                request=scan_job_dispatch,
                blueprint=recon_blueprint,
                agent_type=agent_type
            )
            contexts.append(context)

        # All should have same intelligence but different agent_type
        for i, context in enumerate(contexts):
            assert context.agent_type == agent_types[i]
            assert context.audit_id == recon_blueprint.audit_id
            assert context.system_prompt_leaks == recon_blueprint.intelligence.system_prompt_leak

    def test_auth_intelligence_flow_through_layers(
        self,
        scan_job_dispatch,
        recon_blueprint
    ):
        """Should preserve auth intelligence through all layers."""
        original_auth = recon_blueprint.intelligence.auth_structure

        # Through ScanContext
        context = ScanContext.from_scan_job(
            request=scan_job_dispatch,
            blueprint=recon_blueprint,
            agent_type="agent_auth"
        )

        assert context.auth_intelligence.type == original_auth.type
        assert set(context.auth_intelligence.rules) == set(original_auth.rules)
        assert set(context.auth_intelligence.vulnerabilities) == set(original_auth.vulnerabilities)

        # Through ScanInput
        scan_input = context.to_scan_input()
        assert scan_input.auth_intelligence == context.auth_intelligence

        # Through planning input message
        message = _build_planning_input(scan_input)
        assert original_auth.type in message.content
