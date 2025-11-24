"""Unit tests for services.swarm.policies.mapping module."""

import pytest
from services.swarm.policies.mapping import get_probe_config


class TestGetProbeConfig:
    """Tests for get_probe_config function."""

    def test_sql_agent_with_postgresql(self):
        """SQL agent should select SQL injection probes for PostgreSQL."""
        infrastructure = {"database": "PostgreSQL"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.SQL" in config["probes"]
        assert config["generations"] == 5
        assert config["format"] == "json"

    def test_sql_agent_with_mysql(self):
        """SQL agent should select SQL injection probes for MySQL."""
        infrastructure = {"database": "MySQL"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.SQL" in config["probes"]

    def test_sql_agent_with_mongodb(self):
        """SQL agent should select NoSQL injection probes for MongoDB."""
        infrastructure = {"database": "MongoDB"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.NoSQL" in config["probes"]

    def test_sql_agent_with_nosql(self):
        """SQL agent should select NoSQL probes for generic NoSQL databases."""
        infrastructure = {"database": "NoSQL"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.NoSQL" in config["probes"]

    def test_sql_agent_with_unknown_database(self):
        """SQL agent should select both SQL and NoSQL for unknown databases."""
        infrastructure = {"database": "UnknownDB"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.SQL" in config["probes"]
        assert "probes.injection.NoSQL" in config["probes"]

    def test_sql_agent_without_database(self):
        """SQL agent should default to SQL injection when no database detected."""
        infrastructure = {}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.SQL" in config["probes"]

    def test_sql_agent_always_includes_xss(self):
        """SQL agent should always include XSS probe."""
        infrastructure = {"database": "PostgreSQL"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.xss.MarkdownImageExfil" in config["probes"]

    def test_sql_agent_always_includes_encoding(self):
        """SQL agent should always include encoding probe."""
        infrastructure = {"database": "PostgreSQL"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.encoding" in config["probes"]

    def test_auth_agent_probes(self):
        """Auth agent should always use auth-specific probes."""
        infrastructure = {}
        config = get_probe_config("agent_auth", infrastructure)

        expected_probes = [
            "probes.malwaregen",
            "probes.realtoxicityprompts",
            "probes.snowball",
        ]
        assert config["probes"] == expected_probes

    def test_jailbreak_agent_base_probes(self):
        """Jailbreak agent should include base prompt injection probes."""
        infrastructure = {}
        config = get_probe_config("agent_jailbreak", infrastructure)

        assert "probes.jailbreak" in config["probes"]
        assert "probes.promptinject" in config["probes"]
        assert "probes.leakreplay" in config["probes"]
        assert "probes.encoding" in config["probes"]

    def test_jailbreak_agent_with_gpt_model(self):
        """Jailbreak agent should add ChatGPT-specific probe for GPT models."""
        infrastructure = {"model_family": "GPT-4"}
        config = get_probe_config("agent_jailbreak", infrastructure)

        assert "probes.jailbreak.ChatGPT" in config["probes"]

    def test_jailbreak_agent_with_chatgpt_model(self):
        """Jailbreak agent should add ChatGPT-specific probe for ChatGPT models."""
        infrastructure = {"model_family": "ChatGPT"}
        config = get_probe_config("agent_jailbreak", infrastructure)

        assert "probes.jailbreak.ChatGPT" in config["probes"]

    def test_jailbreak_agent_without_gpt_model(self):
        """Jailbreak agent should not add ChatGPT probe for non-GPT models."""
        infrastructure = {"model_family": "Claude"}
        config = get_probe_config("agent_jailbreak", infrastructure)

        assert "probes.jailbreak.ChatGPT" not in config["probes"]

    def test_invalid_agent_type(self):
        """Invalid agent type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown agent_type"):
            get_probe_config("invalid_agent", {})

    def test_case_insensitive_database_detection(self):
        """Database detection should be case-insensitive."""
        infrastructure = {"database": "postgresql"}
        config = get_probe_config("agent_sql", infrastructure)

        assert "probes.injection.SQL" in config["probes"]

    def test_case_insensitive_model_detection(self):
        """Model family detection should be case-insensitive."""
        infrastructure = {"model_family": "gpt-3.5"}
        config = get_probe_config("agent_jailbreak", infrastructure)

        assert "probes.jailbreak.ChatGPT" in config["probes"]
