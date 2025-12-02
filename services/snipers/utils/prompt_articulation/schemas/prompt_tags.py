"""
XML tag schemas for structured prompt generation.

Purpose: Define XML tag structure for LLM prompts to ensure proper parsing
and emphasis of tool exploitation using reconnaissance intelligence.

Dependencies: ToolIntelligence models
System Role: Prompt structure layer - converts data to XML format
"""

from dataclasses import dataclass

from services.snipers.utils.prompt_articulation.models.tool_intelligence import (
    ToolSignature,
)


@dataclass
class XMLTagSchema:
    """Base class for XML tag generation."""

    def to_xml(self) -> str:
        """Convert to XML string."""
        raise NotImplementedError


@dataclass
class ToolSignatureTag(XMLTagSchema):
    """
    <ToolSignature> tag with parameters and constraints.

    Example:
    <ToolSignature id="refund_transaction" priority="HIGH">
      <Name>refund_transaction</Name>
      <Parameters>...</Parameters>
      <BusinessRules>...</BusinessRules>
    </ToolSignature>
    """

    tool: ToolSignature
    priority: str = "HIGH"

    def to_xml(self) -> str:
        """Generate XML representation of tool signature."""
        xml_parts = [
            f'<ToolSignature id="{self.tool.tool_name}" priority="{self.priority}">',
            f"  <Name>{self.tool.tool_name}</Name>",
        ]

        # Add description if available
        if self.tool.description:
            xml_parts.append(f"  <Description>{self.tool.description}</Description>")

        # Parameters section
        xml_parts.append("  <Parameters>")
        for param in self.tool.parameters:
            param_attrs = [f'name="{param.name}"', f'type="{param.type}"']

            if param.format_constraint:
                param_attrs.append(f'format="{param.format_constraint}"')

            if param.validation_pattern:
                param_attrs.append(f'pattern="{param.validation_pattern}"')

            xml_parts.append(f'    <Parameter {" ".join(param_attrs)}/>')
        xml_parts.append("  </Parameters>")

        # Business rules section
        if self.tool.business_rules:
            xml_parts.append("  <BusinessRules>")
            for i, rule in enumerate(self.tool.business_rules):
                # Determine rule priority based on content
                rule_priority = self._infer_rule_priority(rule)
                xml_parts.append(
                    f'    <Rule id="rule_{i+1}" priority="{rule_priority}">{rule}</Rule>'
                )
            xml_parts.append("  </BusinessRules>")

        # Example calls if available
        if self.tool.example_calls:
            xml_parts.append("  <ExampleCalls>")
            for example in self.tool.example_calls:
                xml_parts.append(f"    <Example>{example}</Example>")
            xml_parts.append("  </ExampleCalls>")

        xml_parts.append("</ToolSignature>")
        return "\n".join(xml_parts)

    def _infer_rule_priority(self, rule: str) -> str:
        """Infer priority from rule content."""
        rule_lower = rule.lower()

        # High priority: format constraints, limits, approval requirements
        if any(
            kw in rule_lower
            for kw in ["must", "format", "require", "approval", "limit"]
        ):
            return "HIGH"

        # Medium priority: recommendations, best practices
        if any(kw in rule_lower for kw in ["should", "recommend", "prefer"]):
            return "MEDIUM"

        # Low priority: informational
        return "LOW"


@dataclass
class IntelligenceTag(XMLTagSchema):
    """
    <Intelligence> tag wrapping all recon data.

    Example:
    <Intelligence source="Cartographer_Recon" confidence="0.95">
      <TargetSystem>...</TargetSystem>
      <DiscoveredTools>...</DiscoveredTools>
    </Intelligence>
    """

    source: str = "Cartographer_Recon"
    confidence: float = 1.0
    target_url: str = ""
    target_model: str | None = None
    database_type: str | None = None
    tools: list[ToolSignature] | None = None
    defense_signals: list[str] | None = None

    def to_xml(self) -> str:
        """Generate XML representation of intelligence."""
        xml_parts = [
            f'<Intelligence source="{self.source}" confidence="{self.confidence}">',
            "  <TargetSystem>",
            f"    <URL>{self.target_url}</URL>",
        ]

        if self.target_model:
            xml_parts.append(f"    <Model>{self.target_model}</Model>")

        if self.database_type:
            xml_parts.append(f"    <Database>{self.database_type}</Database>")

        xml_parts.append("  </TargetSystem>")

        # Tools section
        if self.tools:
            xml_parts.append("  <DiscoveredTools>")
            for tool in self.tools:
                tool_tag = ToolSignatureTag(tool=tool)
                # Indent tool XML
                tool_xml = tool_tag.to_xml()
                indented = "\n".join(["    " + line for line in tool_xml.split("\n")])
                xml_parts.append(indented)
            xml_parts.append("  </DiscoveredTools>")

        # Defense signals
        if self.defense_signals:
            xml_parts.append("  <DefenseSignals>")
            for signal in self.defense_signals:
                severity = self._infer_severity(signal)
                xml_parts.append(
                    f'    <Signal type="{signal}" severity="{severity}"/>'
                )
            xml_parts.append("  </DefenseSignals>")

        xml_parts.append("</Intelligence>")
        return "\n".join(xml_parts)

    def _infer_severity(self, signal: str) -> str:
        """Infer severity from signal name."""
        if "rate" in signal.lower() or "limit" in signal.lower():
            return "medium"
        if "filter" in signal.lower() or "block" in signal.lower():
            return "high"
        return "low"


@dataclass
class TaskTag(XMLTagSchema):
    """
    <Task> tag with clear instructions.

    Example:
    <Task priority="CRITICAL" type="payload_generation">
      <Instruction>Generate 3 adversarial prompts...</Instruction>
      <Requirements>
        <Requirement>Must use TXN-XXXXX format</Requirement>
      </Requirements>
    </Task>
    """

    instructions: str
    priority: str = "HIGH"
    task_type: str = "payload_generation"
    requirements: list[str] | None = None

    def to_xml(self) -> str:
        """Generate XML representation of task."""
        xml_parts = [
            f'<Task priority="{self.priority}" type="{self.task_type}">',
            f"  <Instruction>{self.instructions}</Instruction>",
        ]

        if self.requirements:
            xml_parts.append("  <Requirements>")
            for req in self.requirements:
                xml_parts.append(f"    <Requirement>{req}</Requirement>")
            xml_parts.append("  </Requirements>")

        xml_parts.append("</Task>")
        return "\n".join(xml_parts)


@dataclass
class OutputFormatTag(XMLTagSchema):
    """
    <OutputFormat> tag specifying expected response structure.

    Example:
    <OutputFormat>
      <Format>JSON array of strings</Format>
      <Example>["payload 1", "payload 2", "payload 3"]</Example>
    </OutputFormat>
    """

    format_description: str
    example: str | None = None

    def to_xml(self) -> str:
        """Generate XML representation of output format."""
        xml_parts = [
            "<OutputFormat>",
            f"  <Format>{self.format_description}</Format>",
        ]

        if self.example:
            xml_parts.append(f"  <Example>{self.example}</Example>")

        xml_parts.append("</OutputFormat>")
        return "\n".join(xml_parts)


# Export for convenience
from .tagged_prompt_builder import TaggedPromptBuilder  # noqa: E402

__all__ = [
    "XMLTagSchema",
    "ToolSignatureTag",
    "IntelligenceTag",
    "TaskTag",
    "OutputFormatTag",
    "TaggedPromptBuilder",
]
