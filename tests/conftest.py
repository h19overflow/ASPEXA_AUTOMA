"""Global test fixtures and configuration."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_redis_broker():
    """Mock Redis broker for testing."""
    broker = MagicMock()
    broker.publish = AsyncMock()
    broker.subscriber = MagicMock(return_value=lambda f: f)
    return broker


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_recon_request():
    """Sample IF-01 ReconRequest payload."""
    return {
        "audit_id": "test-audit-123",
        "target": {
            "url": "https://api.example.com/v1/chat",
            "auth_headers": {"Authorization": "Bearer token123"}
        },
        "scope": {
            "depth": "standard",
            "max_turns": 10,
            "forbidden_keywords": ["DELETE", "DROP"]
        }
    }


@pytest.fixture
def sample_recon_blueprint():
    """Sample IF-02 ReconBlueprint payload."""
    return {
        "audit_id": "test-audit-123",
        "timestamp": "2025-11-23T12:00:00Z",
        "intelligence": {
            "system_prompt_leak": ["You are helpful"],
            "detected_tools": [{"name": "search_db", "arguments": ["query"]}],
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
    }


@pytest.fixture
def sample_vulnerability_cluster():
    """Sample IF-04 VulnerabilityCluster payload."""
    return {
        "audit_id": "test-audit-123",
        "cluster_id": "vuln-sql-01",
        "category": "injection.sql",
        "severity": "high",
        "evidence": {
            "input_payload": "' OR 1=1 --",
            "error_response": "SQL syntax error",
            "confidence_score": 0.95
        },
        "affected_component": "tool:search_database"
    }


@pytest.fixture
def sample_exploitation_plan():
    """Sample IF-05 ExploitationPlan payload."""
    return {
        "plan_id": "plan-alpha",
        "engine": "pyrit",
        "objective": "Test SQL injection",
        "configuration": {
            "orchestrator": "RedTeamingOrchestrator",
            "strategy_template": "sql_exfiltration_v2",
            "max_turns": 5,
            "conversation_seed": "Test seed"
        }
    }


@pytest.fixture
def sample_compliance_plan():
    """Sample IF-05 CompliancePlan payload."""
    return {
        "plan_id": "plan-beta",
        "engine": "deepteam",
        "objective": "Verify bias resistance",
        "configuration": {
            "metric": "Bias",
            "iterations": 20,
            "threshold": 0.7,
            "scenario": "Political questions"
        }
    }


@pytest.fixture
def sample_attack_warrant():
    """Sample IF-06 AttackWarrant payload."""
    return {
        "warrant_id": "warrant-001",
        "signer_id": "admin_alice",
        "digital_signature": "abc123def456",
        "approved_plan": {
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
    }
