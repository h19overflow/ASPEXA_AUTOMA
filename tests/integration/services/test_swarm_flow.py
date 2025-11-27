"""Integration tests for the Swarm scanning service end-to-end flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.contracts.scanning import ScanJobDispatch, SafetyPolicy
from libs.contracts.recon import (
    ReconBlueprint,
    Intelligence,
    InfrastructureIntel,
    AuthStructure,
    DetectedTool,
)
from services.swarm.agents import run_scanning_agent
from services.swarm.core import ScanInput, AgentType, ScanContext
from services.swarm.garak_scanner import parse_results_to_clusters
from libs.contracts.common import VulnerabilityCategory, SeverityLevel


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


@pytest.fixture
def sample_scan_job_dispatch():
    """Sample ScanJobDispatch message."""
    blueprint = ReconBlueprint(
        audit_id="test-audit-123",
        timestamp="2024-11-23T12:00:00Z",
        intelligence=Intelligence(
            system_prompt_leak=["You are a helpful assistant"],
            detected_tools=[DetectedTool(name="search_database", arguments=["query"])],
            infrastructure=InfrastructureIntel(
                vector_db="pinecone",
                model_family="gpt-4",
                rate_limits="strict",
            ),
            auth_structure=AuthStructure(
                type="RBAC",
                rules=["Users can only access their own data"],
                vulnerabilities=["potential_idor"],
            ),
        ),
    )

    return ScanJobDispatch(
        job_id="scan-001",
        blueprint_context=blueprint.model_dump(),
        safety_policy=SafetyPolicy(
            allowed_attack_vectors=["injection", "jailbreak"],
            blocked_attack_vectors=["dos"],
            aggressiveness="medium",
        ),
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

    def test_parse_and_aggregate_findings(self):
        """Test parsing scan output and aggregating findings."""
        results = [
            {
                "probe_name": "promptinj",
                "status": "fail",
                "prompt": "injection payload",
                "output": "Syntax error",
            },
            {
                "probe_name": "dan",
                "status": "fail",
                "prompt": "Ignore previous instructions",
                "output": "I understand",
            },
        ]

        clusters = parse_results_to_clusters(
            results,
            audit_id="test-audit-123",
            affected_component="model:default",
        )

        assert len(clusters) == 2  # Two different probe types

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

    def test_multiple_vulnerabilities_deduplication(self):
        """Test that multiple similar vulnerabilities are grouped."""
        # 5 failures from the same probe
        results = [
            {
                "probe_name": "promptinj",
                "status": "fail",
                "prompt": f"payload-{i}",
                "output": "Syntax error",
            }
            for i in range(5)
        ]

        clusters = parse_results_to_clusters(results, audit_id="test-audit")

        # Should have only 1 cluster despite 5 failures
        assert len(clusters) == 1

    def test_affected_component_tracking(self):
        """Test that affected component is correctly tracked."""
        results = [
            {
                "probe_name": "dan",
                "status": "fail",
                "prompt": "test",
                "output": "response",
            }
        ]

        clusters = parse_results_to_clusters(
            results,
            audit_id="test-audit-123",
            affected_component="tool:search_database",
        )

        assert all(c.affected_component == "tool:search_database" for c in clusters)

    def test_scan_context_from_job(self, sample_scan_job_dispatch):
        """Test ScanContext creation from ScanJobDispatch."""
        blueprint = ReconBlueprint(**sample_scan_job_dispatch.blueprint_context)

        context = ScanContext.from_scan_job(
            request=sample_scan_job_dispatch,
            blueprint=blueprint,
            agent_type="agent_sql",
            default_target_url="https://default.local",
        )

        assert context.audit_id == "test-audit-123"
        assert context.agent_type == "agent_sql"
        # target_url may come from job or default
        assert context.target_url is not None
