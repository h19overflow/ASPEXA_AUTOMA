"""Tests for swarm_graph routing and graph building."""

import pytest
from services.swarm.graph.state import SwarmState, AgentResult
from services.swarm.graph.swarm_graph import (
    route_after_recon,
    route_after_safety,
    route_after_plan,
    route_after_execute,
    build_swarm_graph,
    get_swarm_graph,
)


class TestRouteAfterRecon:
    """Tests for route_after_recon function."""

    def test_routes_to_persist_on_fatal_error(self):
        """Test routing to persist when fatal error exists."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            errors=["Fatal error"],
        )

        assert route_after_recon(state) == "persist"

    def test_routes_to_persist_when_complete(self):
        """Test routing to persist when no agents to process."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=[],
        )

        assert route_after_recon(state) == "persist"

    def test_routes_to_check_safety_normally(self):
        """Test routing to check_safety when agents to process."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth"],
        )

        assert route_after_recon(state) == "check_safety"


class TestRouteAfterSafety:
    """Tests for route_after_safety function."""

    def test_routes_to_plan_normally(self):
        """Test routing to plan when not blocked."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
        )

        assert route_after_safety(state) == "plan"

    def test_routes_to_check_safety_when_blocked(self):
        """Test routing to next agent when current is blocked."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth"],
            agent_results=[AgentResult(agent_type="sql", status="blocked")],
        )

        assert route_after_safety(state) == "check_safety"

    def test_routes_to_persist_when_all_blocked(self):
        """Test routing to persist when all agents done."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            current_agent_index=1,  # Complete
            agent_results=[AgentResult(agent_type="sql", status="blocked")],
        )

        assert route_after_safety(state) == "persist"


class TestRouteAfterPlan:
    """Tests for route_after_plan function."""

    def test_routes_to_execute_with_plan(self):
        """Test routing to execute when plan exists."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            current_plan={"selected_probes": ["test"]},
        )

        assert route_after_plan(state) == "execute"

    def test_routes_to_check_safety_without_plan(self):
        """Test routing to next agent when planning failed."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth"],
            current_plan=None,
        )

        assert route_after_plan(state) == "check_safety"

    def test_routes_to_persist_when_complete(self):
        """Test routing to persist when all agents done."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            current_agent_index=1,
            current_plan=None,
        )

        assert route_after_plan(state) == "persist"


class TestRouteAfterExecute:
    """Tests for route_after_execute function."""

    def test_routes_to_check_safety_for_next_agent(self):
        """Test routing to check_safety for next agent."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql", "auth"],
            current_agent_index=1,  # Still have auth to process
        )

        assert route_after_execute(state) == "check_safety"

    def test_routes_to_persist_when_complete(self):
        """Test routing to persist when all agents done."""
        state = SwarmState(
            audit_id="test-001",
            target_url="https://api.test.local/chat",
            agent_types=["sql"],
            current_agent_index=1,
        )

        assert route_after_execute(state) == "persist"


class TestGraphBuilding:
    """Tests for graph building functions."""

    def test_build_swarm_graph_returns_compiled_graph(self):
        """Test that build_swarm_graph returns a compiled graph."""
        graph = build_swarm_graph()

        # Should have invoke method
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")

    def test_get_swarm_graph_returns_singleton(self):
        """Test that get_swarm_graph returns the same instance."""
        graph1 = get_swarm_graph()
        graph2 = get_swarm_graph()

        assert graph1 is graph2
