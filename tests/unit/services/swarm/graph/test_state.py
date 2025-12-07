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

    def test_cancelled_field_default_false(self):
        """Test that cancelled field defaults to False."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
        )

        assert state.cancelled is False

    def test_cancelled_field_can_be_set(self):
        """Test that cancelled field can be set to True."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            cancelled=True,
        )

        assert state.cancelled is True

    def test_progress_field_default_zero(self):
        """Test that progress field defaults to 0.0."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
        )

        assert state.progress == 0.0

    def test_progress_field_can_be_set(self):
        """Test that progress field can be set to valid values."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            progress=0.5,
        )

        assert state.progress == 0.5

    def test_progress_field_validates_min_boundary(self):
        """Test that progress cannot be less than 0.0."""
        with pytest.raises(ValueError):
            SwarmState(
                audit_id="test-001",
                target_url="https://api.test.local/chat",
                agent_types=["sql"],
                progress=-0.1,
            )

    def test_progress_field_validates_max_boundary(self):
        """Test that progress cannot be greater than 1.0."""
        with pytest.raises(ValueError):
            SwarmState(
                audit_id="test-001",
                target_url="https://api.test.local/chat",
                agent_types=["sql"],
                progress=1.1,
            )

    def test_progress_field_accepts_boundary_values(self):
        """Test that progress accepts 0.0 and 1.0."""
        state_start = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            progress=0.0,
        )
        assert state_start.progress == 0.0

        state_end = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            progress=1.0,
        )
        assert state_end.progress == 1.0

    def test_state_with_cancelled_and_progress(self):
        """Test state with both cancelled and progress fields."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth"],
            cancelled=True,
            progress=0.75,
        )

        assert state.cancelled is True
        assert state.progress == 0.75

    def test_progress_various_valid_values(self):
        """Test that progress accepts various valid decimal values."""
        valid_values = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]

        for value in valid_values:
            state = SwarmState(
                audit_id="test-001",
                target_url="https://api.test.local/chat",
                agent_types=["sql"],
                progress=value,
            )
            assert state.progress == value
