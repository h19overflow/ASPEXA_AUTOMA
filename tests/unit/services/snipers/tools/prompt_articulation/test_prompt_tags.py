"""
Unit tests for XML tag generation.

Tests ToolSignatureTag, IntelligenceTag, TaskTag, and OutputFormatTag
XML generation for structured prompt creation.
"""

import pytest
import xml.etree.ElementTree as ET

from services.snipers.utils.prompt_articulation.models.tool_intelligence import (
    ReconIntelligence,
    ToolParameter,
    ToolSignature,
)
from services.snipers.utils.prompt_articulation.schemas.prompt_tags import (
    IntelligenceTag,
    OutputFormatTag,
    TaskTag,
    ToolSignatureTag,
)


class TestToolSignatureTag:
    """Tests for ToolSignatureTag XML generation."""

    def test_basic_tool_signature_xml(self):
        """Test basic tool signature XML generation."""
        tool = ToolSignature(tool_name="simple_tool")
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert "<ToolSignature" in xml
        assert 'id="simple_tool"' in xml
        assert "<Name>simple_tool</Name>" in xml
        assert "</ToolSignature>" in xml

    def test_tool_signature_with_parameters(self):
        """Test tool signature XML with parameters."""
        params = [
            ToolParameter(name="param1", type="str"),
            ToolParameter(name="param2", type="int"),
        ]
        tool = ToolSignature(tool_name="tool_with_params", parameters=params)
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert "<Parameters>" in xml
        assert '<Parameter name="param1" type="str"/>' in xml
        assert '<Parameter name="param2" type="int"/>' in xml
        assert "</Parameters>" in xml

    def test_tool_signature_with_format_constraints(self):
        """Test tool signature with format constraints."""
        params = [
            ToolParameter(
                name="transaction_id",
                type="str",
                format_constraint="TXN-XXXXX",
            ),
        ]
        tool = ToolSignature(tool_name="refund_tool", parameters=params)
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert 'format="TXN-XXXXX"' in xml

    def test_tool_signature_with_validation_pattern(self):
        """Test tool signature with validation pattern."""
        params = [
            ToolParameter(
                name="email",
                type="str",
                validation_pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            ),
        ]
        tool = ToolSignature(tool_name="user_tool", parameters=params)
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert "pattern=" in xml

    def test_tool_signature_with_description(self):
        """Test tool signature with description."""
        tool = ToolSignature(
            tool_name="transfer_funds",
            description="Transfer money between accounts",
        )
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert "<Description>Transfer money between accounts</Description>" in xml

    def test_tool_signature_with_business_rules(self):
        """Test tool signature with business rules."""
        tool = ToolSignature(
            tool_name="refund_tool",
            business_rules=[
                "Must require approval",
                "Amount under $1000",
                "Should validate receipt",
            ],
        )
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert "<BusinessRules>" in xml
        assert "<Rule" in xml
        assert "Must require approval" in xml
        assert "Amount under $1000" in xml
        assert "Should validate receipt" in xml

    def test_tool_signature_rule_priority_inference(self):
        """Test automatic rule priority inference."""
        tool = ToolSignature(
            tool_name="test_tool",
            business_rules=[
                "Must have approval",  # Should be HIGH
                "Should validate input",  # Should be MEDIUM
                "This is informational",  # Should be LOW
            ],
        )
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        # Check that rules have priority attributes
        assert 'priority="HIGH"' in xml or 'priority="MEDIUM"' in xml or 'priority="LOW"' in xml

    def test_tool_signature_with_example_calls(self):
        """Test tool signature with example calls."""
        tool = ToolSignature(
            tool_name="refund_tool",
            example_calls=[
                "refund_tool(TXN-12345, 100.00)",
                "refund_tool(TXN-67890, 250.50)",
            ],
        )
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        assert "<ExampleCalls>" in xml
        assert "<Example>refund_tool(TXN-12345, 100.00)</Example>" in xml
        assert "<Example>refund_tool(TXN-67890, 250.50)</Example>" in xml

    def test_tool_signature_xml_is_valid(self):
        """Test that generated XML is valid and can be parsed."""
        tool = ToolSignature(
            tool_name="test_tool",
            description="Test tool",
            parameters=[ToolParameter(name="param1", type="str")],
            business_rules=["Rule 1"],
            example_calls=["example()"],
        )
        tag = ToolSignatureTag(tool=tool)

        xml = tag.to_xml()
        # Should not raise exception
        root = ET.fromstring(xml)
        assert root.tag == "ToolSignature"
        assert root.get("id") == "test_tool"

    def test_tool_signature_with_custom_priority(self):
        """Test tool signature tag with custom priority."""
        tool = ToolSignature(tool_name="critical_tool")
        tag = ToolSignatureTag(tool=tool, priority="CRITICAL")

        xml = tag.to_xml()
        assert 'priority="CRITICAL"' in xml


class TestIntelligenceTag:
    """Tests for IntelligenceTag XML generation."""

    def test_basic_intelligence_tag(self):
        """Test basic intelligence tag generation."""
        tag = IntelligenceTag(target_url="http://api.example.com")

        xml = tag.to_xml()
        assert "<Intelligence" in xml
        assert 'source="Cartographer_Recon"' in xml
        assert "<TargetSystem>" in xml
        assert "<URL>http://api.example.com</URL>" in xml
        assert "</Intelligence>" in xml

    def test_intelligence_tag_with_model_info(self):
        """Test intelligence tag with model information."""
        tag = IntelligenceTag(
            target_url="http://api.example.com",
            target_model="gpt-4",
            database_type="FAISS",
        )

        xml = tag.to_xml()
        assert "<Model>gpt-4</Model>" in xml
        assert "<Database>FAISS</Database>" in xml

    def test_intelligence_tag_with_tools(self):
        """Test intelligence tag with discovered tools."""
        tools = [
            ToolSignature(tool_name="tool1"),
            ToolSignature(tool_name="tool2"),
        ]
        tag = IntelligenceTag(
            target_url="http://api.example.com",
            tools=tools,
        )

        xml = tag.to_xml()
        assert "<DiscoveredTools>" in xml
        assert "tool1" in xml
        assert "tool2" in xml
        assert "</DiscoveredTools>" in xml

    def test_intelligence_tag_with_defense_signals(self):
        """Test intelligence tag with defense signals."""
        signals = ["rate_limiting", "content_filter", "refusal_detection"]
        tag = IntelligenceTag(
            target_url="http://api.example.com",
            defense_signals=signals,
        )

        xml = tag.to_xml()
        assert "<DefenseSignals>" in xml
        for signal in signals:
            assert f'type="{signal}"' in xml
        assert "</DefenseSignals>" in xml

    def test_intelligence_tag_severity_inference(self):
        """Test automatic severity inference for defense signals."""
        signals = [
            "rate_limit_100_per_hour",  # Should be medium
            "content_filter_active",  # Should be high
            "monitoring_enabled",  # Should be low
        ]
        tag = IntelligenceTag(
            target_url="http://api.example.com",
            defense_signals=signals,
        )

        xml = tag.to_xml()
        # Should contain severity attributes
        assert 'severity=' in xml

    def test_intelligence_tag_with_confidence(self):
        """Test intelligence tag with custom confidence."""
        tag = IntelligenceTag(
            target_url="http://api.example.com",
            confidence=0.85,
        )

        xml = tag.to_xml()
        assert 'confidence="0.85"' in xml

    def test_intelligence_tag_complete_payload(self):
        """Test intelligence tag with complete payload."""
        tools = [
            ToolSignature(
                tool_name="refund_tool",
                parameters=[
                    ToolParameter(name="txn_id", type="str"),
                ],
                business_rules=["Amount under $1000"],
            ),
        ]
        tag = IntelligenceTag(
            source="CustomRecon",
            confidence=0.95,
            target_url="https://api.bank.com",
            target_model="claude-3",
            database_type="PostgreSQL",
            tools=tools,
            defense_signals=["rate_limiting", "auth_required"],
        )

        xml = tag.to_xml()
        assert 'source="CustomRecon"' in xml
        assert 'confidence="0.95"' in xml
        assert "claude-3" in xml
        assert "PostgreSQL" in xml
        assert "refund_tool" in xml
        assert "rate_limiting" in xml

    def test_intelligence_tag_xml_valid(self):
        """Test that generated intelligence XML is valid."""
        tools = [ToolSignature(tool_name="test_tool")]
        tag = IntelligenceTag(
            target_url="http://test.com",
            tools=tools,
            defense_signals=["signal1"],
        )

        xml = tag.to_xml()
        # Should not raise exception
        root = ET.fromstring(xml)
        assert root.tag == "Intelligence"


class TestTaskTag:
    """Tests for TaskTag XML generation."""

    def test_basic_task_tag(self):
        """Test basic task tag generation."""
        tag = TaskTag(instructions="Generate 3 payloads")

        xml = tag.to_xml()
        assert "<Task" in xml
        assert "<Instruction>Generate 3 payloads</Instruction>" in xml
        assert "</Task>" in xml

    def test_task_tag_with_priority(self):
        """Test task tag with priority."""
        tag = TaskTag(
            instructions="Generate payloads",
            priority="CRITICAL",
        )

        xml = tag.to_xml()
        assert 'priority="CRITICAL"' in xml

    def test_task_tag_with_type(self):
        """Test task tag with task type."""
        tag = TaskTag(
            instructions="Do something",
            task_type="exploit_discovery",
        )

        xml = tag.to_xml()
        assert 'type="exploit_discovery"' in xml

    def test_task_tag_with_requirements(self):
        """Test task tag with requirements."""
        requirements = [
            "Use TXN-XXXXX format",
            "Amount under $1000",
            "Include refund reason",
        ]
        tag = TaskTag(
            instructions="Generate payloads",
            requirements=requirements,
        )

        xml = tag.to_xml()
        assert "<Requirements>" in xml
        for req in requirements:
            assert f"<Requirement>{req}</Requirement>" in xml
        assert "</Requirements>" in xml

    def test_task_tag_complete(self):
        """Test task tag with all fields."""
        requirements = ["Req1", "Req2"]
        tag = TaskTag(
            instructions="Complex task with detailed instructions",
            priority="HIGH",
            task_type="payload_generation",
            requirements=requirements,
        )

        xml = tag.to_xml()
        assert 'priority="HIGH"' in xml
        assert 'type="payload_generation"' in xml
        assert "Complex task with detailed instructions" in xml
        assert "Req1" in xml

    def test_task_tag_xml_valid(self):
        """Test that generated task XML is valid."""
        tag = TaskTag(
            instructions="Test instruction",
            requirements=["Test requirement"],
        )

        xml = tag.to_xml()
        root = ET.fromstring(xml)
        assert root.tag == "Task"


class TestOutputFormatTag:
    """Tests for OutputFormatTag XML generation."""

    def test_basic_output_format_tag(self):
        """Test basic output format tag."""
        tag = OutputFormatTag(format_description="JSON array")

        xml = tag.to_xml()
        assert "<OutputFormat>" in xml
        assert "<Format>JSON array</Format>" in xml
        assert "</OutputFormat>" in xml

    def test_output_format_with_example(self):
        """Test output format tag with example."""
        example = '["payload1", "payload2", "payload3"]'
        tag = OutputFormatTag(
            format_description="JSON array of strings",
            example=example,
        )

        xml = tag.to_xml()
        assert example in xml

    def test_output_format_xml_valid(self):
        """Test that generated output format XML is valid."""
        tag = OutputFormatTag(
            format_description="Format description",
            example="Example content",
        )

        xml = tag.to_xml()
        root = ET.fromstring(xml)
        assert root.tag == "OutputFormat"


class TestXMLTagIntegration:
    """Integration tests for XML tag generation."""

    def test_complete_tool_exploitation_xml(self):
        """Test complete tool exploitation XML structure."""
        # Build a realistic scenario
        tool = ToolSignature(
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
                "Must require approval",
                "Amount under $1000 limit",
                "Customer must have original receipt",
            ],
            example_calls=["process_refund('TXN-12345', 500.00)"],
        )

        tool_tag = ToolSignatureTag(tool=tool, priority="HIGH")

        xml = tool_tag.to_xml()

        # Verify structure
        root = ET.fromstring(xml)
        assert root.tag == "ToolSignature"
        assert root.get("priority") == "HIGH"

        # Verify parameters
        params = root.find("Parameters")
        assert params is not None
        assert len(params.findall("Parameter")) == 2

        # Verify business rules
        rules = root.find("BusinessRules")
        assert rules is not None
        assert len(rules.findall("Rule")) == 3

    def test_all_tags_together(self):
        """Test all tag types working together."""
        # Create comprehensive intelligence
        tools = [
            ToolSignature(
                tool_name="refund",
                parameters=[ToolParameter(name="txn_id", type="str")],
            ),
        ]

        intelligence_tag = IntelligenceTag(
            target_url="http://api.example.com",
            target_model="gpt-4",
            tools=tools,
            defense_signals=["rate_limiting"],
        )

        task_tag = TaskTag(
            instructions="Generate payloads",
            requirements=["Use format TXN-XXXXX"],
        )

        output_tag = OutputFormatTag(
            format_description="JSON array",
            example='["payload1"]',
        )

        # All should generate valid XML
        intel_xml = intelligence_tag.to_xml()
        task_xml = task_tag.to_xml()
        output_xml = output_tag.to_xml()

        # All should be parseable
        ET.fromstring(intel_xml)
        ET.fromstring(task_xml)
        ET.fromstring(output_xml)

    def test_nested_tool_signatures_in_intelligence(self):
        """Test nested tool signatures within intelligence tag."""
        tools = [
            ToolSignature(tool_name="tool1", description="First tool"),
            ToolSignature(tool_name="tool2", description="Second tool"),
            ToolSignature(tool_name="tool3", description="Third tool"),
        ]

        tag = IntelligenceTag(
            target_url="http://api.example.com",
            tools=tools,
        )

        xml = tag.to_xml()

        # Parse and verify structure
        root = ET.fromstring(xml)
        discovered_tools = root.find("DiscoveredTools")
        assert discovered_tools is not None

        # Should contain all three tools
        tool_sigs = discovered_tools.findall("ToolSignature")
        assert len(tool_sigs) == 3
