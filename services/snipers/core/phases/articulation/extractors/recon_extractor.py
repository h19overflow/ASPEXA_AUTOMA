"""
Extract structured intelligence from reconnaissance blueprints (IF-02 format).

Purpose: Parse raw reconnaissance data into ToolSignature models with
parameters, format constraints, and business rules for payload generation.

Dependencies: ToolIntelligence models
System Role: Data extraction layer - bridges recon and payload generation
"""

import logging
import re
from typing import Any

from services.snipers.core.phases.articulation.models.tool_intelligence import (
    ReconIntelligence,
    ToolParameter,
    ToolSignature,
)

logger = logging.getLogger(__name__)


class ReconIntelligenceExtractor:
    """Extract structured tool intelligence from reconnaissance blueprints."""

    def extract(self, recon_blueprint: dict[str, Any]) -> ReconIntelligence:
        """
        Extract ReconIntelligence from IF-02 format blueprint.

        Args:
            recon_blueprint: Raw recon data (IF-02 format or similar)

        Returns:
            Structured ReconIntelligence with tool signatures
        """
        if not recon_blueprint:
            logger.warning("Empty recon blueprint provided")
            return ReconIntelligence(raw_intelligence={})

        # Extract basic metadata
        intelligence_section = recon_blueprint.get("intelligence", {})
        infrastructure = intelligence_section.get("infrastructure", {})

        # Extract LLM model
        llm_model = infrastructure.get("model_family") or infrastructure.get(
            "llm_model"
        )

        # Extract database type
        database_type = infrastructure.get("vector_db") or infrastructure.get(
            "database_type"
        )

        # Extract content filters/defenses
        content_filters = []
        if infrastructure.get("rate_limits"):
            content_filters.append(f"rate_limiting_{infrastructure['rate_limits']}")

        auth_structure = intelligence_section.get("auth_structure", {})
        if auth_structure.get("type"):
            content_filters.append(f"auth_{auth_structure['type'].lower()}")

        # Check for system prompt leak (indicates refusal detection)
        if intelligence_section.get("system_prompt_leak"):
            content_filters.append("refusal_detection")

        # Extract tools
        detected_tools = intelligence_section.get("detected_tools", [])
        tool_signatures = self._extract_tool_signatures(
            detected_tools, intelligence_section
        )

        # Extract system prompt leaks (handle list or string)
        system_prompt_leak_raw = intelligence_section.get("system_prompt_leak")
        if isinstance(system_prompt_leak_raw, list):
            # Join list elements into single string
            system_prompt_leak = "\n".join(str(item) for item in system_prompt_leak_raw)
        elif isinstance(system_prompt_leak_raw, str):
            system_prompt_leak = system_prompt_leak_raw
        else:
            system_prompt_leak = None

        target_self_description = intelligence_section.get("target_self_description")

        # Try to extract from responses if not explicitly provided
        if not target_self_description:
            responses = recon_blueprint.get("responses", [])
            if responses:
                target_self_description = self._extract_self_description(responses)

        logger.info(
            f"Extracted {len(tool_signatures)} tool signatures from recon blueprint",
            extra={
                "tools": [t.tool_name for t in tool_signatures],
                "llm_model": llm_model,
                "database": database_type,
                "target_description": target_self_description,
            },
        )

        return ReconIntelligence(
            tools=tool_signatures,
            llm_model=llm_model,
            database_type=database_type,
            content_filters=content_filters,
            system_prompt_leak=system_prompt_leak,
            target_self_description=target_self_description,
            raw_intelligence=recon_blueprint,
        )

    def _extract_tool_signatures(
        self, detected_tools: list[dict], intelligence: dict
    ) -> list[ToolSignature]:
        """
        Extract ToolSignature objects from detected_tools array.

        Args:
            detected_tools: List of tool definitions from IF-02
            intelligence: Full intelligence section for context

        Returns:
            List of ToolSignature objects with parameters and rules
        """
        signatures = []

        for tool_def in detected_tools:
            if not isinstance(tool_def, dict):
                continue

            tool_name = tool_def.get("name")
            if not tool_name:
                continue

            # Extract parameters
            parameters = self._extract_parameters(tool_def)

            # Extract business rules (from various sources)
            business_rules = self._extract_business_rules(tool_def, intelligence)

            # Extract example calls
            example_calls = tool_def.get("example_calls", [])

            # Check authorization requirements
            auth_required = tool_def.get("requires_auth", True)

            signature = ToolSignature(
                tool_name=tool_name,
                description=tool_def.get("description"),
                parameters=parameters,
                business_rules=business_rules,
                example_calls=example_calls,
                authorization_required=auth_required,
            )

            signatures.append(signature)

        return signatures

    def _extract_parameters(self, tool_def: dict) -> list[ToolParameter]:
        """
        Extract ToolParameter objects from tool definition.

        Args:
            tool_def: Single tool definition from detected_tools

        Returns:
            List of ToolParameter objects
        """
        parameters = []

        # Handle arguments list (simple format)
        arguments = tool_def.get("arguments", [])
        if isinstance(arguments, list):
            for arg in arguments:
                if isinstance(arg, str):
                    # Simple string argument
                    parameters.append(
                        ToolParameter(name=arg, type="str", required=True)
                    )
                elif isinstance(arg, dict):
                    # Detailed argument specification
                    param = self._parse_parameter_dict(arg)
                    if param:
                        parameters.append(param)

        # Handle parameters dict (detailed format)
        params_dict = tool_def.get("parameters", {})
        if isinstance(params_dict, dict):
            for param_name, param_spec in params_dict.items():
                if isinstance(param_spec, dict):
                    param = self._parse_parameter_dict(
                        {**param_spec, "name": param_name}
                    )
                    if param:
                        parameters.append(param)

        return parameters

    def _parse_parameter_dict(self, param_dict: dict) -> ToolParameter | None:
        """
        Parse a parameter dictionary into ToolParameter.

        Args:
            param_dict: Parameter specification

        Returns:
            ToolParameter or None if invalid
        """
        name = param_dict.get("name")
        if not name:
            return None

        param_type = param_dict.get("type", "str")
        required = param_dict.get("required", True)
        format_constraint = param_dict.get("format")
        validation_pattern = param_dict.get("pattern")
        default_value = param_dict.get("default")

        # Try to infer format from description or constraints
        if not format_constraint:
            description = param_dict.get("description", "")
            format_constraint = self._infer_format_from_description(description)

        return ToolParameter(
            name=name,
            type=param_type,
            required=required,
            format_constraint=format_constraint,
            validation_pattern=validation_pattern,
            default_value=default_value,
        )

    def _infer_format_from_description(self, description: str) -> str | None:
        """
        Infer format constraint from parameter description.

        Args:
            description: Parameter description text

        Returns:
            Format pattern or None
        """
        # Look for common patterns in descriptions
        patterns = {
            r"TXN-\w+": "TXN-XXXXX",
            r"ORD-\d+": "ORD-XXXXX",
            r"USR-\d+": "USR-XXXXX",
            r"ID-\d+": "ID-XXXXX",
            r"uuid|UUID": "UUID",
            r"email": "email",
            r"phone": "phone",
            r"date": "YYYY-MM-DD",
        }

        for pattern, format_name in patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return format_name

        return None

    def _extract_business_rules(
        self, tool_def: dict, intelligence: dict
    ) -> list[str]:
        """
        Extract business rules from tool definition and intelligence context.

        Args:
            tool_def: Tool definition
            intelligence: Full intelligence section

        Returns:
            List of business rule strings
        """
        rules = []

        # Extract explicit rules from tool definition
        explicit_rules = tool_def.get("business_rules", [])
        if isinstance(explicit_rules, list):
            rules.extend(explicit_rules)

        # Extract from constraints
        constraints = tool_def.get("constraints", {})
        if isinstance(constraints, dict):
            for constraint_key, constraint_value in constraints.items():
                rules.append(f"{constraint_key}: {constraint_value}")

        # Extract from validation rules
        validation = tool_def.get("validation", {})
        if isinstance(validation, dict):
            for rule_key, rule_value in validation.items():
                rules.append(f"{rule_key} validation: {rule_value}")

        # Extract from authorization structure
        auth_structure = intelligence.get("auth_structure", {})
        vulnerabilities = auth_structure.get("vulnerabilities", [])
        if vulnerabilities:
            for vuln in vulnerabilities:
                rules.append(f"Known vulnerability: {vuln}")

        return rules

    def _extract_self_description(self, responses: list[str]) -> str | None:
        """
        Extract target self-description from responses.

        Looks for patterns like:
        - "I am a [X] chatbot"
        - "I can only help with [Y]"
        - "As a [Z] assistant"

        Args:
            responses: List of target response strings

        Returns:
            Extracted self-description or None
        """
        patterns = [
            r"I am (?:a |an )?([^.!?\n]+(?:chatbot|assistant|agent|bot))",
            r"I can only help with ([^.!?\n]+)",
            r"As (?:a |an )?([^,]+(?:chatbot|assistant|agent)),",
            r"(?:I'm|I am) (?:here to |designed to )?(?:help|assist) (?:with )?([^.!?\n]+)",
        ]

        for response in responses:
            if not isinstance(response, str):
                continue

            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None
