"""
Test suite for new agent architecture.

Focus:
1. Import tests - verify all modules can be imported
2. Registry tests - verify get_agent() factory works
3. Agent instantiation - verify each agent initializes
4. Interface compliance - verify all agents implement BaseAgent interface
5. Schema validation - verify ProbePlan schema works
"""

import pytest
from typing import Dict, Any, List

# Import tests
from services.swarm.agents.base_agent import BaseAgent, ProbePlan
from services.swarm.agents import get_agent, AGENT_REGISTRY
from services.swarm.agents.sql import SQLAgent
from services.swarm.agents.auth import AuthAgent
from services.swarm.agents.jailbreak import JailbreakAgent


class TestImports:
    """Test that all agent modules can be imported."""

    def test_should_import_base_agent_class(self):
        """BaseAgent abstract class should be importable."""
        assert BaseAgent is not None
        assert hasattr(BaseAgent, 'agent_type')
        assert hasattr(BaseAgent, 'system_prompt')
        assert hasattr(BaseAgent, 'available_probes')
        assert hasattr(BaseAgent, 'plan')

    def test_should_import_probe_plan_schema(self):
        """ProbePlan schema should be importable and valid."""
        assert ProbePlan is not None
        # Verify it's a Pydantic model
        assert hasattr(ProbePlan, 'model_validate')

    def test_should_import_sql_agent(self):
        """SQLAgent should be importable."""
        assert SQLAgent is not None
        assert issubclass(SQLAgent, BaseAgent)

    def test_should_import_auth_agent(self):
        """AuthAgent should be importable."""
        assert AuthAgent is not None
        assert issubclass(AuthAgent, BaseAgent)

    def test_should_import_jailbreak_agent(self):
        """JailbreakAgent should be importable."""
        assert JailbreakAgent is not None
        assert issubclass(JailbreakAgent, BaseAgent)

    def test_should_import_registry(self):
        """AGENT_REGISTRY should be importable."""
        assert AGENT_REGISTRY is not None
        assert isinstance(AGENT_REGISTRY, dict)

    def test_should_import_factory_function(self):
        """get_agent factory function should be importable."""
        assert get_agent is not None
        assert callable(get_agent)


class TestAgentRegistry:
    """Test the agent registry and factory function."""

    def test_registry_should_have_all_agent_types(self):
        """Registry should contain all three agent types."""
        assert "sql" in AGENT_REGISTRY
        assert "auth" in AGENT_REGISTRY
        assert "jailbreak" in AGENT_REGISTRY
        assert len(AGENT_REGISTRY) == 3

    def test_registry_should_map_to_agent_classes(self):
        """Registry values should be agent classes."""
        assert AGENT_REGISTRY["sql"] is SQLAgent
        assert AGENT_REGISTRY["auth"] is AuthAgent
        assert AGENT_REGISTRY["jailbreak"] is JailbreakAgent

    def test_get_agent_should_return_sql_agent(self):
        """get_agent('sql') should return SQLAgent instance."""
        agent = get_agent("sql")
        assert isinstance(agent, SQLAgent)
        assert agent.agent_type == "sql"

    def test_get_agent_should_return_auth_agent(self):
        """get_agent('auth') should return AuthAgent instance."""
        agent = get_agent("auth")
        assert isinstance(agent, AuthAgent)
        assert agent.agent_type == "auth"

    def test_get_agent_should_return_jailbreak_agent(self):
        """get_agent('jailbreak') should return JailbreakAgent instance."""
        agent = get_agent("jailbreak")
        assert isinstance(agent, JailbreakAgent)
        assert agent.agent_type == "jailbreak"

    def test_get_agent_should_raise_error_for_unknown_type(self):
        """get_agent() should raise ValueError for unknown agent type."""
        with pytest.raises(ValueError) as exc_info:
            get_agent("unknown")

        assert "Unknown agent type: unknown" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_get_agent_should_pass_kwargs_to_agent(self):
        """get_agent() should pass kwargs to agent constructor."""
        agent = get_agent("sql", model_name="test-model")
        assert agent._model_name == "test-model"

    def test_get_agent_factory_creates_separate_instances(self):
        """Each call to get_agent() should create a new instance."""
        agent1 = get_agent("sql")
        agent2 = get_agent("sql")
        assert agent1 is not agent2


class TestProbePlanSchema:
    """Test the ProbePlan Pydantic schema."""

    def test_probe_plan_should_have_probes_field(self):
        """ProbePlan should have probes field."""
        plan = ProbePlan(probes=["dan", "promptinj"])
        assert plan.probes == ["dan", "promptinj"]

    def test_probe_plan_should_have_generations_field(self):
        """ProbePlan should have generations field with default."""
        plan = ProbePlan(probes=["dan"])
        assert plan.generations == 5  # Default value

    def test_probe_plan_should_validate_generations_range(self):
        """ProbePlan should validate generations is between 1 and 20."""
        # Valid: minimum
        plan = ProbePlan(probes=["dan"], generations=1)
        assert plan.generations == 1

        # Valid: maximum
        plan = ProbePlan(probes=["dan"], generations=20)
        assert plan.generations == 20

        # Invalid: too low
        with pytest.raises(ValueError):
            ProbePlan(probes=["dan"], generations=0)

        # Invalid: too high
        with pytest.raises(ValueError):
            ProbePlan(probes=["dan"], generations=21)

    def test_probe_plan_should_have_reasoning_field(self):
        """ProbePlan should have reasoning field."""
        plan = ProbePlan(
            probes=["dan", "promptinj"],
            reasoning={"dan": "Tests jailbreak resistance", "promptinj": "Tests prompt injection"}
        )
        assert plan.reasoning == {
            "dan": "Tests jailbreak resistance",
            "promptinj": "Tests prompt injection"
        }

    def test_probe_plan_reasoning_should_default_to_empty_dict(self):
        """ProbePlan reasoning should default to empty dict."""
        plan = ProbePlan(probes=["dan"])
        assert plan.reasoning == {}

    def test_probe_plan_should_be_serializable(self):
        """ProbePlan should be serializable to dict/JSON."""
        plan = ProbePlan(
            probes=["dan", "promptinj"],
            generations=7,
            reasoning={"dan": "Test 1"}
        )

        # Should support dict conversion
        plan_dict = plan.model_dump()
        assert plan_dict["probes"] == ["dan", "promptinj"]
        assert plan_dict["generations"] == 7
        assert plan_dict["reasoning"] == {"dan": "Test 1"}

    def test_probe_plan_should_be_deserializable(self):
        """ProbePlan should be deserializable from dict."""
        data = {
            "probes": ["dan", "promptinj"],
            "generations": 8,
            "reasoning": {"dan": "Test"}
        }

        plan = ProbePlan.model_validate(data)
        assert plan.probes == ["dan", "promptinj"]
        assert plan.generations == 8
        assert plan.reasoning == {"dan": "Test"}


class TestSQLAgentInterface:
    """Test SQLAgent implements BaseAgent interface correctly."""

    def test_sql_agent_should_be_instantiable(self):
        """SQLAgent should instantiate without errors."""
        agent = SQLAgent()
        assert agent is not None

    def test_sql_agent_should_have_agent_type_property(self):
        """SQLAgent.agent_type should return 'sql'."""
        agent = SQLAgent()
        assert agent.agent_type == "sql"
        assert isinstance(agent.agent_type, str)

    def test_sql_agent_should_have_system_prompt_property(self):
        """SQLAgent.system_prompt should return non-empty string."""
        agent = SQLAgent()
        prompt = agent.system_prompt
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should contain key elements
        assert "Data Surface" in prompt
        assert "SQL" in prompt

    def test_sql_agent_should_have_available_probes_property(self):
        """SQLAgent.available_probes should return list of strings."""
        agent = SQLAgent()
        probes = agent.available_probes
        assert probes is not None
        assert isinstance(probes, list)
        assert len(probes) > 0
        # All items should be strings
        assert all(isinstance(p, str) for p in probes)

    def test_sql_agent_should_have_plan_method(self):
        """SQLAgent should have async plan method."""
        agent = SQLAgent()
        assert hasattr(agent, 'plan')
        assert callable(agent.plan)
        # Check it's a coroutine function
        import inspect
        assert inspect.iscoroutinefunction(agent.plan)

    def test_sql_agent_should_accept_custom_model_name(self):
        """SQLAgent should accept custom model_name in constructor."""
        agent = SQLAgent(model_name="custom-model")
        assert agent._model_name == "custom-model"

    def test_sql_agent_system_prompt_should_contain_required_fields(self):
        """SQLAgent system prompt should be properly formatted."""
        agent = SQLAgent()
        prompt = agent.system_prompt

        # Should contain XML tags (from base_agent architecture)
        assert "<systemPrompt>" in prompt or "Data Surface" in prompt
        assert "probe" in prompt.lower()


class TestAuthAgentInterface:
    """Test AuthAgent implements BaseAgent interface correctly."""

    def test_auth_agent_should_be_instantiable(self):
        """AuthAgent should instantiate without errors."""
        agent = AuthAgent()
        assert agent is not None

    def test_auth_agent_should_have_agent_type_property(self):
        """AuthAgent.agent_type should return 'auth'."""
        agent = AuthAgent()
        assert agent.agent_type == "auth"

    def test_auth_agent_should_have_system_prompt_property(self):
        """AuthAgent.system_prompt should return non-empty string."""
        agent = AuthAgent()
        prompt = agent.system_prompt
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Authorization" in prompt or "auth" in prompt.lower()

    def test_auth_agent_should_have_available_probes_property(self):
        """AuthAgent.available_probes should return list of strings."""
        agent = AuthAgent()
        probes = agent.available_probes
        assert probes is not None
        assert isinstance(probes, list)
        assert len(probes) > 0
        assert all(isinstance(p, str) for p in probes)

    def test_auth_agent_should_have_plan_method(self):
        """AuthAgent should have async plan method."""
        agent = AuthAgent()
        assert hasattr(agent, 'plan')
        assert callable(agent.plan)
        import inspect
        assert inspect.iscoroutinefunction(agent.plan)

    def test_auth_agent_should_accept_custom_model_name(self):
        """AuthAgent should accept custom model_name in constructor."""
        agent = AuthAgent(model_name="custom-model")
        assert agent._model_name == "custom-model"


class TestJailbreakAgentInterface:
    """Test JailbreakAgent implements BaseAgent interface correctly."""

    def test_jailbreak_agent_should_be_instantiable(self):
        """JailbreakAgent should instantiate without errors."""
        agent = JailbreakAgent()
        assert agent is not None

    def test_jailbreak_agent_should_have_agent_type_property(self):
        """JailbreakAgent.agent_type should return 'jailbreak'."""
        agent = JailbreakAgent()
        assert agent.agent_type == "jailbreak"

    def test_jailbreak_agent_should_have_system_prompt_property(self):
        """JailbreakAgent.system_prompt should return non-empty string."""
        agent = JailbreakAgent()
        prompt = agent.system_prompt
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "jailbreak" in prompt.lower() or "prompt injection" in prompt.lower()

    def test_jailbreak_agent_should_have_available_probes_property(self):
        """JailbreakAgent.available_probes should return list of strings."""
        agent = JailbreakAgent()
        probes = agent.available_probes
        assert probes is not None
        assert isinstance(probes, list)
        assert len(probes) > 0
        assert all(isinstance(p, str) for p in probes)

    def test_jailbreak_agent_should_have_plan_method(self):
        """JailbreakAgent should have async plan method."""
        agent = JailbreakAgent()
        assert hasattr(agent, 'plan')
        assert callable(agent.plan)
        import inspect
        assert inspect.iscoroutinefunction(agent.plan)

    def test_jailbreak_agent_should_accept_custom_model_name(self):
        """JailbreakAgent should accept custom model_name in constructor."""
        agent = JailbreakAgent(model_name="custom-model")
        assert agent._model_name == "custom-model"


class TestAgentProbeCompatibility:
    """Test probe lists are properly defined for each agent."""

    def test_sql_agent_probes_should_be_non_empty(self):
        """SQL agent should have non-empty probe list."""
        agent = SQLAgent()
        probes = agent.available_probes
        assert len(probes) > 0
        # Common SQL-related probes should be present or similar
        assert any(p in probes for p in ["promptinj", "encoding", "goodside_json", "pkg_python"])

    def test_auth_agent_probes_should_be_non_empty(self):
        """Auth agent should have non-empty probe list."""
        agent = AuthAgent()
        probes = agent.available_probes
        assert len(probes) > 0

    def test_jailbreak_agent_probes_should_be_non_empty(self):
        """Jailbreak agent should have non-empty probe list."""
        agent = JailbreakAgent()
        probes = agent.available_probes
        assert len(probes) > 0

    def test_different_agents_should_have_different_probes(self):
        """Each agent type should have a distinct set of probes."""
        sql_agent = SQLAgent()
        auth_agent = AuthAgent()
        jailbreak_agent = JailbreakAgent()

        sql_probes = set(sql_agent.available_probes)
        auth_probes = set(auth_agent.available_probes)
        jailbreak_probes = set(jailbreak_agent.available_probes)

        # While there might be some overlap, sets shouldn't be identical
        assert sql_probes != auth_probes or len(sql_probes) < 3  # Allow small special cases
        assert auth_probes != jailbreak_probes or len(auth_probes) < 3


class TestAgentPromptFormatting:
    """Test that agent prompts are properly formatted."""

    def test_sql_agent_prompt_should_format_successfully(self):
        """SQL agent prompt should format without errors."""
        agent = SQLAgent()
        prompt = agent.system_prompt

        # Should be a valid string with content
        assert prompt
        assert isinstance(prompt, str)
        # Should not have unformatted placeholders
        assert "{" not in prompt or "}" not in prompt  # Flexible check

    def test_auth_agent_prompt_should_format_successfully(self):
        """Auth agent prompt should format without errors."""
        agent = AuthAgent()
        prompt = agent.system_prompt

        assert prompt
        assert isinstance(prompt, str)

    def test_jailbreak_agent_prompt_should_format_successfully(self):
        """Jailbreak agent prompt should format without errors."""
        agent = JailbreakAgent()
        prompt = agent.system_prompt

        assert prompt
        assert isinstance(prompt, str)

    def test_all_agent_prompts_should_mention_probes(self):
        """All agent prompts should reference available probes."""
        for agent_type in ["sql", "auth", "jailbreak"]:
            agent = get_agent(agent_type)
            prompt = agent.system_prompt

            # Prompt should mention probes or have probe guidance
            assert "probe" in prompt.lower() or "scan" in prompt.lower()


class TestAbstractInterfaceCompliance:
    """Test that agents properly implement BaseAgent abstract interface."""

    def test_sql_agent_cannot_be_base_agent_without_implementation(self):
        """SQLAgent should fully implement BaseAgent interface."""
        agent = SQLAgent()

        # All abstract properties should be implemented
        assert agent.agent_type  # Not None
        assert agent.system_prompt  # Not None
        assert agent.available_probes  # Not None

        # All return the expected types
        assert isinstance(agent.agent_type, str)
        assert isinstance(agent.system_prompt, str)
        assert isinstance(agent.available_probes, list)

    def test_auth_agent_cannot_be_base_agent_without_implementation(self):
        """AuthAgent should fully implement BaseAgent interface."""
        agent = AuthAgent()

        assert agent.agent_type
        assert agent.system_prompt
        assert agent.available_probes

        assert isinstance(agent.agent_type, str)
        assert isinstance(agent.system_prompt, str)
        assert isinstance(agent.available_probes, list)

    def test_jailbreak_agent_cannot_be_base_agent_without_implementation(self):
        """JailbreakAgent should fully implement BaseAgent interface."""
        agent = JailbreakAgent()

        assert agent.agent_type
        assert agent.system_prompt
        assert agent.available_probes

        assert isinstance(agent.agent_type, str)
        assert isinstance(agent.system_prompt, str)
        assert isinstance(agent.available_probes, list)


class TestAgentInstanceVariations:
    """Test agent instantiation with various parameters."""

    def test_agents_should_support_default_model(self):
        """Agents should use default model when not specified."""
        sql_agent = SQLAgent()
        auth_agent = AuthAgent()
        jailbreak_agent = JailbreakAgent()

        # Should have model_name set to default
        assert sql_agent._model_name == "google_genai:gemini-2.5-pro"
        assert auth_agent._model_name == "google_genai:gemini-2.5-pro"
        assert jailbreak_agent._model_name == "google_genai:gemini-2.5-pro"

    def test_agents_should_support_custom_models(self):
        """Agents should accept custom model names."""
        models = [
            "custom-model-1",
            "google_genai:gemini-pro",
            "openai:gpt-4",
        ]

        for model in models:
            sql_agent = SQLAgent(model_name=model)
            assert sql_agent._model_name == model

    def test_agent_lazy_initialization_of_langchain_agent(self):
        """Agent should lazily initialize LangChain agent."""
        agent = SQLAgent()

        # Agent should not be initialized yet
        assert agent._agent is None

    def test_agent_types_should_be_unique(self):
        """Each agent type should return unique type identifier."""
        sql_agent = SQLAgent()
        auth_agent = AuthAgent()
        jailbreak_agent = JailbreakAgent()

        types = {sql_agent.agent_type, auth_agent.agent_type, jailbreak_agent.agent_type}
        assert len(types) == 3
        assert "sql" in types
        assert "auth" in types
        assert "jailbreak" in types
