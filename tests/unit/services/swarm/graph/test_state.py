"""Tests for graph state definitions."""

import pytest
from services.swarm.graph.state import SwarmState, AgentResult


class TestAgentResult:
    """Tests for AgentResult model."""

    def test_create_success_result(self):
        """Test creating a successful agent result."""
        result = AgentResult(
            agent_type="sql",
            status="success",
            scan_id="garak-test-001-sql",
            vulnerabilities_found=3,
        )

        assert result.agent_type == "sql"
        assert result.status == "success"
        assert result.scan_id == "garak-test-001-sql"
        assert result.vulnerabilities_found == 3
        assert result.error is None

    def test_create_failed_result(self):
        """Test creating a failed agent result."""
        result = AgentResult(
            agent_type="auth",
            status="failed",
            error="Planning failed",
            phase="planning",
        )

        assert result.status == "failed"
        assert result.error == "Planning failed"
        assert result.phase == "planning"

    def test_create_blocked_result(self):
        """Test creating a blocked agent result."""
        result = AgentResult(
            agent_type="jailbreak",
            status="blocked",
            error="Blocked by safety policy",
        )

        assert result.status == "blocked"


class TestSwarmState:
    """Tests for SwarmState model."""

    def test_create_initial_state(self):
        """Test creating initial swarm state."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth", "jailbreak"],
            recon_context={"audit_id": "test-001"},
        )

        assert state.audit_id == "test-001"
        assert state.target_url == "https://api.test.local/chat"
        assert len(state.agent_types) == 3
        assert state.current_agent_index == 0
        assert state.agent_results == []
        assert state.events == []

    def test_current_agent_property(self):
        """Test current_agent property returns correct agent."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth", "jailbreak"],
        )

        assert state.current_agent == "sql"

        # Simulate advancing
        state.current_agent_index = 1
        assert state.current_agent == "auth"

        state.current_agent_index = 2
        assert state.current_agent == "jailbreak"

    def test_current_agent_returns_none_when_complete(self):
        """Test current_agent returns None when all agents processed."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            current_agent_index=1,
        )

        assert state.current_agent is None

    def test_is_complete_property(self):
        """Test is_complete property."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth"],
        )

        assert state.is_complete is False

        state.current_agent_index = 2
        assert state.is_complete is True

    def test_has_fatal_error_property(self):
        """Test has_fatal_error property."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
        )

        assert state.has_fatal_error is False

        state.errors.append("Fatal error occurred")
        assert state.has_fatal_error is True

    def test_state_with_safety_policy(self):
        """Test state with safety policy."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            safety_policy={"blocked_attack_vectors": ["injection"]},
        )

        assert state.safety_policy is not None
        assert "injection" in state.safety_policy["blocked_attack_vectors"]
