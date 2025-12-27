"""Integration tests for the Swarm scanning service end-to-end flow."""

from unittest.mock import MagicMock, patch

import pytest

from services.swarm.agents import run_scanning_agent
from services.swarm.core import ScanInput, AgentType


@pytest.fixture
def sample_scan_input():
    """Sample scan input for agent."""
    return ScanInput(
        audit_id="test-audit-123",
        agent_type="agent_sql",
        target_url="https://api.target.local/chat",
        infrastructure={"database": "PostgreSQL", "model_family": "gpt-4"},
        detected_tools=[{"name": "search_database", "arguments": ["query", "limit"]}],
    )


class TestSwarmIntegration:
    """Integration tests for the full Swarm scanning flow.

    NOTE: The architecture has changed to use planning agents (run_planning_agent)
    instead of execution agents. These tests now verify the planning phase.
    """

    @pytest.mark.asyncio
    async def test_sql_agent_planning_flow(self, sample_scan_input):
        """Test SQL agent planning from scan input to plan."""
        import json
        from services.swarm.agents import run_planning_agent

        with patch("services.swarm.agents.base.create_planning_agent") as mock_create:
            from services.swarm.core.schema import ScanPlan, ScanConfig

            # Mock agent that returns a valid plan via plan_scan tool
            mock_agent = MagicMock()

            async def mock_ainvoke(input_dict):
                from langchain_core.messages import ToolMessage
                plan = ScanPlan(
                    audit_id="test-audit-123",
                    agent_type="agent_sql",
                    target_url="https://api.target.local/chat",
                    selected_probes=["promptinj", "sqli"],
                    probe_reasoning={"promptinj": "Test SQL injection", "sqli": "Direct SQL test"},
                    generations=5,
                    scan_config=ScanConfig(),
                )
                # Content must be JSON string for _extract_plan_from_result
                tool_msg = ToolMessage(
                    content=json.dumps({"status": "planned", "plan": plan.model_dump()}),
                    name="plan_scan",
                    tool_call_id="test",
                )
                return {"messages": [tool_msg]}

            mock_agent.ainvoke = mock_ainvoke
            mock_create.return_value = mock_agent

            result = await run_planning_agent("agent_sql", sample_scan_input)

            assert result.success is True
            assert result.plan is not None
            assert result.plan.agent_type == "agent_sql"

    @pytest.mark.asyncio
    async def test_jailbreak_agent_planning_flow(self):
        """Test jailbreak agent planning initialization."""
        import json
        from services.swarm.agents import run_planning_agent

        scan_input = ScanInput(
            audit_id="test-audit-456",
            agent_type="agent_jailbreak",
            target_url="https://api.target.local/chat",
            infrastructure={"model_family": "gpt-4"},
            detected_tools=[],
        )

        with patch("services.swarm.agents.base.create_planning_agent") as mock_create:
            from services.swarm.core.schema import ScanPlan, ScanConfig

            mock_agent = MagicMock()

            async def mock_ainvoke(input_dict):
                from langchain_core.messages import ToolMessage
                plan = ScanPlan(
                    audit_id="test-audit-456",
                    agent_type="agent_jailbreak",
                    target_url="https://api.target.local/chat",
                    selected_probes=["dan", "jailbreak"],
                    probe_reasoning={"dan": "DAN test", "jailbreak": "General jailbreak"},
                    generations=5,
                    scan_config=ScanConfig(),
                )
                tool_msg = ToolMessage(
                    content=json.dumps({"status": "planned", "plan": plan.model_dump()}),
                    name="plan_scan",
                    tool_call_id="test",
                )
                return {"messages": [tool_msg]}

            mock_agent.ainvoke = mock_ainvoke
            mock_create.return_value = mock_agent

            result = await run_planning_agent("agent_jailbreak", scan_input)

            assert result.success is True
            assert result.plan is not None
            assert result.plan.agent_type == "agent_jailbreak"

    @pytest.mark.asyncio
    async def test_auth_agent_planning_flow(self):
        """Test auth agent planning initialization."""
        import json
        from services.swarm.agents import run_planning_agent

        scan_input = ScanInput(
            audit_id="test-audit-789",
            agent_type="agent_auth",
            target_url="https://api.target.local/chat",
            infrastructure={"database": "PostgreSQL"},
            detected_tools=[{"name": "admin_panel", "arguments": ["action"]}],
        )

        with patch("services.swarm.agents.base.create_planning_agent") as mock_create:
            from services.swarm.core.schema import ScanPlan, ScanConfig

            mock_agent = MagicMock()

            async def mock_ainvoke(input_dict):
                from langchain_core.messages import ToolMessage
                plan = ScanPlan(
                    audit_id="test-audit-789",
                    agent_type="agent_auth",
                    target_url="https://api.target.local/chat",
                    selected_probes=["auth_bypass", "privilege_escalation"],
                    probe_reasoning={"auth_bypass": "Test auth", "privilege_escalation": "Test privesc"},
                    generations=5,
                    scan_config=ScanConfig(),
                )
                tool_msg = ToolMessage(
                    content=json.dumps({"status": "planned", "plan": plan.model_dump()}),
                    name="plan_scan",
                    tool_call_id="test",
                )
                return {"messages": [tool_msg]}

            mock_agent.ainvoke = mock_ainvoke
            mock_create.return_value = mock_agent

            result = await run_planning_agent("agent_auth", scan_input)

            assert result.success is True
            assert result.plan is not None
            assert result.plan.agent_type == "agent_auth"

    @pytest.mark.asyncio
    async def test_invalid_agent_type(self):
        """Test that invalid agent type raises error."""
        scan_input = ScanInput(
            audit_id="test-audit",
            agent_type="invalid_agent",
            target_url="https://target.local",
        )

        result = await run_scanning_agent("invalid_agent", scan_input)

        assert result["success"] is False
        assert "error" in result
