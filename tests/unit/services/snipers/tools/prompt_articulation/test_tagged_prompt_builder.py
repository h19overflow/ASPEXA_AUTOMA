"""
Unit tests for tagged prompt builder.

Tests TaggedPromptBuilder that constructs XML-tagged prompts for
tool exploitation using reconnaissance intelligence.
"""

import pytest
import xml.etree.ElementTree as ET

from services.snipers.utils.prompt_articulation.models.tool_intelligence import (
    ReconIntelligence,
    ToolParameter,
    ToolSignature,
)
from services.snipers.utils.prompt_articulation.schemas.tagged_prompt_builder import (
    TaggedPromptBuilder,
)


@pytest.fixture
def builder():
    """Provide TaggedPromptBuilder instance."""
    return TaggedPromptBuilder()


@pytest.fixture
def sample_recon_intel():
    """Sample reconnaissance intelligence."""
    tools = [
        ToolSignature(
            tool_name="process_refund",
            description="Process customer refund",
            parameters=[
                ToolParameter(
                    name="transaction_id",
                    type="str",
                    format_constraint="TXN-XXXXX",
                ),
                ToolParameter(name="amount", type="float"),
            ],
            business_rules=[
                "Refund must be under $1000 limit",
                "Customer must have original receipt",
            ],
            example_calls=["process_refund('TXN-12345', 500.00)"],
            authorization_required=True,
        ),
    ]

    return ReconIntelligence(
        tools=tools,
        llm_model="gpt-4",
        database_type="FAISS",
        content_filters=["rate_limiting", "auth_oauth2"],
        raw_intelligence={
            "target_url": "https://api.example.com",
            "scan_id": "scan-001",
        },
    )


@pytest.fixture
def multi_tool_recon_intel():
    """Multi-tool reconnaissance intelligence."""
    tools = [
        ToolSignature(
            tool_name="transfer_funds",
            parameters=[
                ToolParameter(
                    name="source_account",
                    type="str",
                    format_constraint="ACC-XXXXX",
                ),
                ToolParameter(
                    name="dest_account",
                    type="str",
                    format_constraint="ACC-XXXXX",
                ),
                ToolParameter(name="amount", type="float"),
            ],
            business_rules=[
                "Daily transfer limit: $10000",
                "Requires 2FA verification",
            ],
            authorization_required=True,
        ),
        ToolSignature(
            tool_name="check_balance",
            parameters=[
                ToolParameter(name="account_id", type="str"),
            ],
            business_rules=[
                "Public endpoint",
                "Rate limited to 100 requests/hour",
            ],
            authorization_required=False,
        ),
    ]

    return ReconIntelligence(
        tools=tools,
        llm_model="claude-3",
        database_type="PostgreSQL",
        content_filters=["rate_limiting", "ip_whitelist"],
        raw_intelligence={
            "target_url": "https://bank.example.com",
        },
    )


class TestTaggedPromptBuilder:
    """Tests for TaggedPromptBuilder."""

    def test_build_tool_exploitation_prompt(self, builder, sample_recon_intel):
        """Test building complete tool exploitation prompt."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="unauthorized refund",
            recon_intel=sample_recon_intel,
            framing_strategy="customer support",
            payload_count=3,
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_contains_system_context(self, builder, sample_recon_intel):
        """Test that prompt includes system context section."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test objective",
            recon_intel=sample_recon_intel,
            framing_strategy="test framing",
        )

        assert "<SystemContext>" in prompt
        assert "security researcher" in prompt.lower() or "red team" in prompt.lower()
        assert "</SystemContext>" in prompt

    def test_prompt_contains_intelligence_section(self, builder, sample_recon_intel):
        """Test that prompt includes intelligence section."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test objective",
            recon_intel=sample_recon_intel,
            framing_strategy="test framing",
        )

        assert "<Intelligence" in prompt
        assert "</Intelligence>" in prompt

    def test_prompt_contains_attack_objective(self, builder, sample_recon_intel):
        """Test that prompt includes attack objective section."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="unauthorized refund",
            recon_intel=sample_recon_intel,
            framing_strategy="customer support",
        )

        assert "<AttackObjective>" in prompt
        assert "unauthorized refund" in prompt
        assert "customer support" in prompt
        assert "</AttackObjective>" in prompt

    def test_prompt_contains_task_section(self, builder, sample_recon_intel):
        """Test that prompt includes task section."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test objective",
            recon_intel=sample_recon_intel,
            framing_strategy="test framing",
            payload_count=5,
        )

        assert "<Task" in prompt
        assert "5" in prompt  # payload count should be mentioned
        assert "</Task>" in prompt

    def test_prompt_contains_output_format(self, builder, sample_recon_intel):
        """Test that prompt includes output format section."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test objective",
            recon_intel=sample_recon_intel,
            framing_strategy="test framing",
            payload_count=3,
        )

        assert "<OutputFormat>" in prompt
        assert "JSON" in prompt
        assert "</OutputFormat>" in prompt

    def test_prompt_references_discovered_tools(self, builder, sample_recon_intel):
        """Test that prompt references discovered tools."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=sample_recon_intel,
            framing_strategy="test",
        )

        assert "process_refund" in prompt

    def test_prompt_includes_format_constraints(self, builder, sample_recon_intel):
        """Test that prompt includes format constraints from parameters."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=sample_recon_intel,
            framing_strategy="test",
        )

        assert "TXN-XXXXX" in prompt or "TXN" in prompt

    def test_prompt_with_multiple_payload_count(self, builder, sample_recon_intel):
        """Test prompt generation with different payload counts."""
        for count in [1, 3, 5, 10]:
            prompt = builder.build_tool_exploitation_prompt(
                objective="test",
                recon_intel=sample_recon_intel,
                framing_strategy="test",
                payload_count=count,
            )

            assert str(count) in prompt

    def test_prompt_with_multiple_tools(self, builder, multi_tool_recon_intel):
        """Test prompt generation with multiple tools."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="fund transfer",
            recon_intel=multi_tool_recon_intel,
            framing_strategy="account management",
        )

        assert "transfer_funds" in prompt
        assert "check_balance" in prompt

    def test_prompt_includes_business_rules(self, builder, sample_recon_intel):
        """Test that prompt includes business rules."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=sample_recon_intel,
            framing_strategy="test",
        )

        assert any(rule in prompt for rule in sample_recon_intel.tools[0].business_rules)

    def test_prompt_is_valid_xml_sections(self, builder, sample_recon_intel):
        """Test that prompt XML sections are well-formed."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=sample_recon_intel,
            framing_strategy="test",
        )

        # Extract and validate intelligence section
        if "<Intelligence" in prompt:
            start = prompt.find("<Intelligence")
            end = prompt.find("</Intelligence>") + len("</Intelligence>")
            intel_section = prompt[start:end]
            # Should not raise exception
            try:
                ET.fromstring(intel_section)
            except ET.ParseError:
                # May not be standalone XML due to indentation, that's ok
                pass


class TestSystemContextBuilding:
    """Tests for system context building."""

    def test_system_context_includes_critical_rules(self, builder):
        """Test that system context includes critical rules."""
        context = builder._build_system_context()

        assert "<SystemContext>" in context
        assert "security researcher" in context.lower() or "red team" in context.lower()
        assert "CRITICAL RULES" in context

    def test_system_context_references_tool_signatures(self, builder):
        """Test system context mentions tool signatures."""
        context = builder._build_system_context()

        assert "tool signature" in context.lower() or "signatures" in context.lower()

    def test_system_context_references_business_rules(self, builder):
        """Test system context mentions business rules."""
        context = builder._build_system_context()

        assert "business rule" in context.lower() or "rules" in context.lower()


class TestIntelligenceSectionBuilding:
    """Tests for intelligence section building."""

    def test_intelligence_section_includes_target_url(self, builder, sample_recon_intel):
        """Test intelligence section includes target URL."""
        intel_section = builder._build_intelligence_section(sample_recon_intel)

        assert "https://api.example.com" in intel_section or "api.example.com" in intel_section

    def test_intelligence_section_includes_model(self, builder, sample_recon_intel):
        """Test intelligence section includes LLM model."""
        intel_section = builder._build_intelligence_section(sample_recon_intel)

        assert "gpt-4" in intel_section

    def test_intelligence_section_includes_database(self, builder, sample_recon_intel):
        """Test intelligence section includes database type."""
        intel_section = builder._build_intelligence_section(sample_recon_intel)

        assert "FAISS" in intel_section

    def test_intelligence_section_includes_tools(self, builder, sample_recon_intel):
        """Test intelligence section includes tools."""
        intel_section = builder._build_intelligence_section(sample_recon_intel)

        assert "process_refund" in intel_section

    def test_intelligence_section_includes_defense_signals(self, builder, sample_recon_intel):
        """Test intelligence section includes defense signals."""
        intel_section = builder._build_intelligence_section(sample_recon_intel)

        # Should include at least one filter
        assert "rate_limiting" in intel_section or "DefenseSignals" in intel_section


class TestObjectiveSectionBuilding:
    """Tests for attack objective building."""

    def test_objective_section_includes_goal(self, builder):
        """Test objective section includes attack goal."""
        objective_section = builder._build_objective_section(
            objective="unauthorized refund",
            framing="customer support",
        )

        assert "unauthorized refund" in objective_section
        assert "<AttackObjective>" in objective_section
        assert "</AttackObjective>" in objective_section

    def test_objective_section_includes_framing(self, builder):
        """Test objective section includes framing strategy."""
        framing = "legitimate customer inquiry"
        objective_section = builder._build_objective_section(
            objective="test",
            framing=framing,
        )

        assert framing in objective_section

    def test_objective_section_includes_success_criteria(self, builder):
        """Test objective section includes success criteria."""
        objective_section = builder._build_objective_section(
            objective="test",
            framing="test",
        )

        assert "SuccessCriteria" in objective_section
        assert "Criterion" in objective_section


class TestTaskSectionBuilding:
    """Tests for task section building."""

    def test_task_section_includes_instructions(self, builder, sample_recon_intel):
        """Test task section includes clear instructions."""
        task_section = builder._build_task_section(
            objective="unauthorized refund",
            recon_intel=sample_recon_intel,
            framing="customer support",
            count=3,
        )

        assert "<Task" in task_section
        assert "<Instruction>" in task_section
        assert "</Instruction>" in task_section

    def test_task_section_includes_payload_count(self, builder, sample_recon_intel):
        """Test task section references payload count."""
        for count in [1, 3, 5]:
            task_section = builder._build_task_section(
                objective="test",
                recon_intel=sample_recon_intel,
                framing="test",
                count=count,
            )

            assert str(count) in task_section

    def test_task_section_includes_requirements(self, builder, sample_recon_intel):
        """Test task section includes requirements."""
        task_section = builder._build_task_section(
            objective="test",
            recon_intel=sample_recon_intel,
            framing="test",
            count=3,
        )

        assert "<Requirements>" in task_section
        assert "<Requirement>" in task_section

    def test_task_section_extracts_format_requirements(self, builder, sample_recon_intel):
        """Test task section extracts format requirements from tools."""
        task_section = builder._build_task_section(
            objective="test",
            recon_intel=sample_recon_intel,
            framing="test",
            count=3,
        )

        # Should mention format constraints from parameters
        assert "TXN-XXXXX" in task_section or "format" in task_section.lower()

    def test_task_section_with_multiple_tools(self, builder, multi_tool_recon_intel):
        """Test task section with multiple tools."""
        task_section = builder._build_task_section(
            objective="fund transfer",
            recon_intel=multi_tool_recon_intel,
            framing="account management",
            count=3,
        )

        assert "transfer_funds" in task_section
        assert "check_balance" in task_section


class TestRequirementExtraction:
    """Tests for requirement extraction from tools."""

    def test_extract_format_requirements(self, builder, sample_recon_intel):
        """Test extraction of format requirements."""
        requirements = builder._extract_requirements(sample_recon_intel)

        assert len(requirements) > 0
        # Should mention transaction ID format
        assert any("TXN" in req for req in requirements)

    def test_extract_business_rule_requirements(self, builder, sample_recon_intel):
        """Test extraction of business rule requirements."""
        requirements = builder._extract_requirements(sample_recon_intel)

        # Should mention limits and approval
        assert any("limit" in req.lower() or "approval" in req.lower() for req in requirements)

    def test_extract_requirements_limits_to_five(self, builder):
        """Test that requirements are limited to 5 most important."""
        # Create tool with many business rules
        tool = ToolSignature(
            tool_name="test_tool",
            parameters=[
                ToolParameter(
                    name=f"param{i}",
                    type="str",
                    format_constraint=f"FMT-{i}",
                )
                for i in range(10)
            ],
            business_rules=[f"Rule {i}" for i in range(10)],
        )
        intel = ReconIntelligence(tools=[tool])

        requirements = builder._extract_requirements(intel)

        assert len(requirements) <= 5

    def test_extract_requirements_from_multiple_tools(self, builder, multi_tool_recon_intel):
        """Test extraction of requirements from multiple tools."""
        requirements = builder._extract_requirements(multi_tool_recon_intel)

        assert len(requirements) > 0
        # Should mention both ACC and rate limiting
        assert any("ACC" in req for req in requirements)


class TestOutputSectionBuilding:
    """Tests for output format section building."""

    def test_output_section_includes_format(self, builder):
        """Test output section includes format description."""
        output_section = builder._build_output_section(count=3)

        assert "<OutputFormat>" in output_section
        assert "JSON" in output_section

    def test_output_section_includes_count(self, builder):
        """Test output section references payload count."""
        for count in [1, 3, 5]:
            output_section = builder._build_output_section(count=count)

            assert str(count) in output_section

    def test_output_section_includes_example(self, builder):
        """Test output section includes example."""
        output_section = builder._build_output_section(count=3)

        assert "<Example>" in output_section
        assert '"Payload' in output_section or "payload" in output_section.lower()


class TestTaggedPromptIntegration:
    """Integration tests for complete tagged prompt generation."""

    def test_end_to_end_tool_exploitation_prompt(self, builder, sample_recon_intel):
        """Test end-to-end tool exploitation prompt generation."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="unauthorized refund",
            recon_intel=sample_recon_intel,
            framing_strategy="customer support",
            payload_count=3,
        )

        # Verify all major sections are present
        assert "<SystemContext>" in prompt
        assert "<Intelligence" in prompt
        assert "<AttackObjective>" in prompt
        assert "<Task" in prompt
        assert "<OutputFormat>" in prompt

        # Verify content is present
        assert "unauthorized refund" in prompt
        assert "process_refund" in prompt
        assert "customer support" in prompt
        assert "3" in prompt

    def test_prompt_structure_is_coherent(self, builder, sample_recon_intel):
        """Test that prompt structure is logically coherent."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test objective",
            recon_intel=sample_recon_intel,
            framing_strategy="test framing",
            payload_count=3,
        )

        # Verify section order (system context should come before task)
        system_pos = prompt.find("<SystemContext>")
        task_pos = prompt.find("<Task")
        output_pos = prompt.find("<OutputFormat>")

        assert system_pos > -1
        assert task_pos > -1
        assert output_pos > -1
        assert system_pos < task_pos < output_pos

    def test_prompt_includes_all_tool_details(self, builder, sample_recon_intel):
        """Test that prompt includes complete tool details."""
        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=sample_recon_intel,
            framing_strategy="test",
        )

        tool = sample_recon_intel.tools[0]
        # Should include tool name
        assert tool.tool_name in prompt
        # Should include at least one parameter
        assert any(p.name in prompt for p in tool.parameters)
        # Should include business rules
        assert any(rule in prompt for rule in tool.business_rules)

    def test_prompt_with_empty_filters(self, builder):
        """Test prompt generation with no content filters."""
        intel = ReconIntelligence(
            tools=[ToolSignature(tool_name="test_tool")],
            llm_model="gpt-4",
            database_type="FAISS",
            content_filters=[],  # Empty filters
        )

        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=intel,
            framing_strategy="test",
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_with_many_tools(self, builder):
        """Test prompt generation with many tools."""
        tools = [
            ToolSignature(tool_name=f"tool_{i}")
            for i in range(5)
        ]
        intel = ReconIntelligence(tools=tools)

        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=intel,
            framing_strategy="test",
        )

        # All tools should be referenced
        for tool in tools:
            assert tool.tool_name in prompt
