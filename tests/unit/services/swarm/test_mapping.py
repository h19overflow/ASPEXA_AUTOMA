"""Unit tests for services.swarm.core.config probe mapping functions."""

import pytest
from services.swarm.core.config import (
    get_probes_for_agent,
    get_generations_for_approach,
    AgentType,
    ScanApproach,
    PROBE_MAP,
)


class TestGetProbesForAgent:
    """Tests for get_probes_for_agent function."""

    def test_sql_agent_returns_probes(self):
        """SQL agent should return probe list."""
        probes = get_probes_for_agent(AgentType.SQL.value)
        assert isinstance(probes, list)
        assert len(probes) > 0

    def test_auth_agent_returns_probes(self):
        """Auth agent should return probe list."""
        probes = get_probes_for_agent(AgentType.AUTH.value)
        assert isinstance(probes, list)
        assert len(probes) > 0

    def test_jailbreak_agent_returns_probes(self):
        """Jailbreak agent should return probe list."""
        probes = get_probes_for_agent(AgentType.JAILBREAK.value)
        assert isinstance(probes, list)
        assert len(probes) > 0

    def test_custom_probes_override_defaults(self):
        """Custom probes should override default probe selection."""
        custom = ["dan", "promptinj"]
        probes = get_probes_for_agent(
            AgentType.SQL.value,
            custom_probes=custom,
        )
        assert probes == custom

    def test_invalid_custom_probes_filtered(self):
        """Invalid custom probes should be filtered out."""
        custom = ["dan", "invalid_probe", "promptinj"]
        probes = get_probes_for_agent(
            AgentType.SQL.value,
            custom_probes=custom,
        )
        assert "dan" in probes
        assert "promptinj" in probes
        assert "invalid_probe" not in probes

    def test_infrastructure_adds_extra_probes(self):
        """Infrastructure details should add relevant probes."""
        base_probes = get_probes_for_agent(AgentType.JAILBREAK.value)
        infra_probes = get_probes_for_agent(
            AgentType.JAILBREAK.value,
            infrastructure={"model_family": "gpt-4"},
        )
        # Infrastructure may add probes, so infra_probes >= base_probes
        assert len(infra_probes) >= len(base_probes)

    def test_approach_affects_probe_count(self):
        """Different approaches should affect probe selection."""
        quick = get_probes_for_agent(AgentType.SQL.value, approach=ScanApproach.QUICK.value)
        standard = get_probes_for_agent(AgentType.SQL.value, approach=ScanApproach.STANDARD.value)
        thorough = get_probes_for_agent(AgentType.SQL.value, approach=ScanApproach.THOROUGH.value)

        # Thorough should have >= standard >= quick
        assert len(thorough) >= len(standard)
        assert len(standard) >= len(quick)


class TestGetGenerationsForApproach:
    """Tests for get_generations_for_approach function."""

    def test_quick_returns_low_generations(self):
        """Quick approach should return low generation count."""
        gens = get_generations_for_approach(ScanApproach.QUICK.value)
        assert gens >= 1
        assert gens <= 10  # Reasonable upper bound for quick approach

    def test_standard_returns_medium_generations(self):
        """Standard approach should return medium generation count."""
        gens = get_generations_for_approach(ScanApproach.STANDARD.value)
        assert gens >= 3

    def test_thorough_returns_high_generations(self):
        """Thorough approach should return high generation count."""
        gens = get_generations_for_approach(ScanApproach.THOROUGH.value)
        assert gens >= 5

    def test_thorough_more_than_quick(self):
        """Thorough should have more generations than quick."""
        quick = get_generations_for_approach(ScanApproach.QUICK.value)
        thorough = get_generations_for_approach(ScanApproach.THOROUGH.value)
        assert thorough >= quick


class TestProbeMap:
    """Tests for PROBE_MAP constants."""

    def test_probe_map_has_entries(self):
        """PROBE_MAP should have probe entries."""
        assert len(PROBE_MAP) > 0

    def test_all_probes_have_garak_paths(self):
        """All probes should map to garak module paths."""
        for short_name, full_path in PROBE_MAP.items():
            assert full_path.startswith("garak.probes.")
            assert len(full_path) > len("garak.probes.")

    def test_common_probes_exist(self):
        """Common probe short names should exist."""
        common_probes = ["dan", "promptinj", "encoding", "leak"]
        for probe in common_probes:
            assert probe in PROBE_MAP
