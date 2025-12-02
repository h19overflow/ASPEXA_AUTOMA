"""
Unit tests for reconnaissance intelligence extraction.

Tests ReconIntelligenceExtractor that parses IF-02 format blueprints
into structured ToolSignature models.
"""

import pytest

from services.snipers.utils.prompt_articulation.extractors.recon_extractor import (
    ReconIntelligenceExtractor,
)
from services.snipers.utils.prompt_articulation.models.tool_intelligence import (
    ReconIntelligence,
    ToolParameter,
    ToolSignature,
)


@pytest.fixture
def extractor():
    """Provide ReconIntelligenceExtractor instance."""
    return ReconIntelligenceExtractor()


@pytest.fixture
def sample_if02_blueprint():
    """Sample IF-02 format recon blueprint."""
    return {
        "intelligence": {
            "infrastructure": {
                "model_family": "gpt-4",
                "vector_db": "FAISS",
                "rate_limits": "1000_per_hour",
            },
            "auth_structure": {
                "type": "oauth2",
                "rules": ["Refunds under $1000 are auto-approved"],
                "vulnerabilities": [],
            },
            "system_prompt_leak": ["You are helpful assistant"],
            "detected_tools": [
                {
                    "name": "process_refund",
                    "description": "Process customer refund",
                    "arguments": ["transaction_id", "refund_amount"],
                    "requires_auth": True,
                    "business_rules": [
                        "Amount must be under $1000",
                        "Customer must have original receipt",
                    ],
                    "example_calls": [
                        "process_refund('TXN-12345', 500.00)",
                        "process_refund('TXN-67890', 750.50)",
                    ],
                },
                {
                    "name": "check_balance",
                    "arguments": ["customer_id"],
                    "requires_auth": False,
                },
            ],
        },
        "raw_observations": {},
        "structured_deductions": {},
    }


@pytest.fixture
def sample_if02_with_parameters():
    """IF-02 blueprint with detailed parameter specifications."""
    return {
        "intelligence": {
            "infrastructure": {
                "model_family": "claude-3-sonnet",
                "vector_db": "ChromaDB",
            },
            "auth_structure": {
                "type": "jwt",
                "rules": [],
                "vulnerabilities": [],
            },
            "detected_tools": [
                {
                    "name": "transfer_funds",
                    "description": "Transfer money between accounts",
                    "parameters": {
                        "source_account": {
                            "type": "str",
                            "required": True,
                            "format": "ACC-XXXXX",
                            "description": "Source account ID in format ACC-XXXXX",
                        },
                        "dest_account": {
                            "type": "str",
                            "required": True,
                            "format": "ACC-XXXXX",
                        },
                        "amount": {
                            "type": "float",
                            "required": True,
                            "description": "Transfer amount",
                        },
                    },
                    "business_rules": [
                        "Daily limit: $10000",
                        "Requires 2FA verification",
                    ],
                    "constraints": {
                        "daily_limit": "$10000",
                        "min_amount": "$0.01",
                    },
                    "validation": {
                        "account_format": "Must be ACC-[0-9]{5}",
                    },
                },
            ],
        },
    }


class TestReconIntelligenceExtractor:
    """Tests for ReconIntelligenceExtractor."""

    def test_extract_empty_blueprint(self, extractor):
        """Test extraction from empty blueprint."""
        blueprint = {}
        intel = extractor.extract(blueprint)

        assert isinstance(intel, ReconIntelligence)
        assert intel.tools == []
        assert intel.llm_model is None
        assert intel.database_type is None
        assert intel.content_filters == []

    def test_extract_none_blueprint(self, extractor):
        """Test extraction from None blueprint."""
        intel = extractor.extract(None)

        assert isinstance(intel, ReconIntelligence)
        assert intel.tools == []
        assert intel.raw_intelligence == {}

    def test_extract_basic_blueprint(self, extractor, sample_if02_blueprint):
        """Test extraction from basic IF-02 blueprint."""
        intel = extractor.extract(sample_if02_blueprint)

        assert isinstance(intel, ReconIntelligence)
        assert len(intel.tools) == 2
        assert intel.llm_model == "gpt-4"
        assert intel.database_type == "FAISS"

    def test_extract_tool_names(self, extractor, sample_if02_blueprint):
        """Test that tool names are correctly extracted."""
        intel = extractor.extract(sample_if02_blueprint)

        tool_names = [tool.tool_name for tool in intel.tools]
        assert "process_refund" in tool_names
        assert "check_balance" in tool_names

    def test_extract_tool_descriptions(self, extractor, sample_if02_blueprint):
        """Test that tool descriptions are extracted."""
        intel = extractor.extract(sample_if02_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert refund_tool.description == "Process customer refund"

    def test_extract_tool_arguments_as_parameters(self, extractor, sample_if02_blueprint):
        """Test extraction of tool arguments as parameters."""
        intel = extractor.extract(sample_if02_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert len(refund_tool.parameters) == 2
        assert refund_tool.parameters[0].name == "transaction_id"
        assert refund_tool.parameters[1].name == "refund_amount"

    def test_extract_authorization_requirements(self, extractor, sample_if02_blueprint):
        """Test extraction of authorization requirements."""
        intel = extractor.extract(sample_if02_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        balance_tool = next(t for t in intel.tools if t.tool_name == "check_balance")

        assert refund_tool.authorization_required is True
        assert balance_tool.authorization_required is False

    def test_extract_business_rules(self, extractor, sample_if02_blueprint):
        """Test extraction of business rules."""
        intel = extractor.extract(sample_if02_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert len(refund_tool.business_rules) >= 2
        assert any("$1000" in rule for rule in refund_tool.business_rules)

    def test_extract_example_calls(self, extractor, sample_if02_blueprint):
        """Test extraction of example calls."""
        intel = extractor.extract(sample_if02_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert len(refund_tool.example_calls) == 2
        assert "TXN-12345" in refund_tool.example_calls[0]

    def test_extract_content_filters_from_rate_limits(self, extractor, sample_if02_blueprint):
        """Test extraction of content filters from rate limits."""
        intel = extractor.extract(sample_if02_blueprint)

        assert any("rate_limiting" in cf for cf in intel.content_filters)

    def test_extract_content_filters_from_auth(self, extractor, sample_if02_blueprint):
        """Test extraction of content filters from auth structure."""
        intel = extractor.extract(sample_if02_blueprint)

        assert any("auth_" in cf for cf in intel.content_filters)

    def test_extract_content_filters_from_system_prompt_leak(self, extractor, sample_if02_blueprint):
        """Test extraction of refusal detection from system prompt leak."""
        intel = extractor.extract(sample_if02_blueprint)

        assert "refusal_detection" in intel.content_filters

    def test_extract_detailed_parameters(self, extractor, sample_if02_with_parameters):
        """Test extraction of detailed parameter specifications."""
        intel = extractor.extract(sample_if02_with_parameters)

        transfer_tool = intel.tools[0]
        assert len(transfer_tool.parameters) == 3

        # Find source_account parameter
        source_param = next(p for p in transfer_tool.parameters if p.name == "source_account")
        assert source_param.format_constraint == "ACC-XXXXX"
        assert source_param.required is True

    def test_extract_inferred_format_from_description(self, extractor, sample_if02_with_parameters):
        """Test format inference from description."""
        intel = extractor.extract(sample_if02_with_parameters)

        transfer_tool = intel.tools[0]
        # Check that format is extracted or inferred
        assert any(
            p.format_constraint for p in transfer_tool.parameters if p.name == "source_account"
        )

    def test_extract_constraints_as_business_rules(self, extractor, sample_if02_with_parameters):
        """Test extraction of constraints as business rules."""
        intel = extractor.extract(sample_if02_with_parameters)

        transfer_tool = intel.tools[0]
        constraint_rules = [r for r in transfer_tool.business_rules if "daily_limit" in r.lower() or "amount" in r.lower()]
        assert len(constraint_rules) > 0

    def test_extract_raw_intelligence_preserved(self, extractor, sample_if02_blueprint):
        """Test that raw intelligence is preserved."""
        intel = extractor.extract(sample_if02_blueprint)

        assert intel.raw_intelligence == sample_if02_blueprint


class TestParameterExtraction:
    """Tests for parameter extraction from tool definitions."""

    def test_extract_simple_string_arguments(self, extractor):
        """Test extraction of simple string arguments."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "test_tool",
                        "arguments": ["arg1", "arg2", "arg3"],
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert len(tool.parameters) == 3
        assert all(p.type == "str" for p in tool.parameters)
        assert all(p.required for p in tool.parameters)

    def test_extract_dict_arguments(self, extractor):
        """Test extraction of dictionary-format arguments."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "test_tool",
                        "arguments": [
                            {"name": "param1", "type": "str", "required": True},
                            {"name": "param2", "type": "int", "required": False},
                        ],
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert len(tool.parameters) == 2
        assert tool.parameters[0].type == "str"
        assert tool.parameters[1].type == "int"

    def test_extract_parameters_dict(self, extractor):
        """Test extraction from parameters dictionary."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "test_tool",
                        "parameters": {
                            "param1": {"type": "str", "required": True},
                            "param2": {"type": "float", "required": False},
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert len(tool.parameters) == 2
        param_names = {p.name for p in tool.parameters}
        assert param_names == {"param1", "param2"}

    def test_extract_parameter_with_default_value(self, extractor):
        """Test extraction of parameter with default value."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "test_tool",
                        "parameters": {
                            "param1": {
                                "type": "str",
                                "default": "default_value",
                            },
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        param = intel.tools[0].parameters[0]
        assert param.default_value == "default_value"


class TestFormatInference:
    """Tests for format constraint inference from descriptions."""

    def test_infer_txn_format(self, extractor):
        """Test inference of TXN-XXXXX format."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "refund_tool",
                        "parameters": {
                            "transaction_id": {
                                "type": "str",
                                "description": "Transaction ID in format TXN-XXXXX",
                            },
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        param = intel.tools[0].parameters[0]
        assert param.format_constraint == "TXN-XXXXX"

    def test_infer_order_format(self, extractor):
        """Test inference of ORD-XXXXX format."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "order_tool",
                        "parameters": {
                            "order_id": {
                                "type": "str",
                                "description": "Order ID like ORD-12345",
                            },
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        param = intel.tools[0].parameters[0]
        assert param.format_constraint == "ORD-XXXXX"

    def test_infer_uuid_format(self, extractor):
        """Test inference of UUID format."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "user_tool",
                        "parameters": {
                            "user_id": {
                                "type": "str",
                                "description": "Unique UUID identifier",
                            },
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        param = intel.tools[0].parameters[0]
        assert param.format_constraint == "UUID"

    def test_infer_email_format(self, extractor):
        """Test inference of email format."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "contact_tool",
                        "parameters": {
                            "email": {
                                "type": "str",
                                "description": "User email address",
                            },
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        param = intel.tools[0].parameters[0]
        assert param.format_constraint == "email"


class TestBusinessRuleExtraction:
    """Tests for business rule extraction from various sources."""

    def test_extract_explicit_business_rules(self, extractor):
        """Test extraction of explicit business rules."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "refund_tool",
                        "business_rules": [
                            "Maximum refund amount: $1000",
                            "Refund only within 30 days",
                        ],
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert len(tool.business_rules) >= 2

    def test_extract_constraints_as_rules(self, extractor):
        """Test extraction of constraints as business rules."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "transfer_tool",
                        "constraints": {
                            "daily_limit": "$10000",
                            "min_transfer": "$1",
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert any("daily_limit" in r for r in tool.business_rules)

    def test_extract_validation_as_rules(self, extractor):
        """Test extraction of validation rules."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "validate_tool",
                        "validation": {
                            "format_check": "Must be alphanumeric",
                            "length_check": "Must be 10-50 chars",
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert any("format_check" in r for r in tool.business_rules)

    def test_extract_vulnerabilities_as_rules(self, extractor):
        """Test extraction of vulnerabilities as business rules."""
        blueprint = {
            "intelligence": {
                "auth_structure": {
                    "type": "oauth2",
                    "vulnerabilities": [
                        "CSRF not implemented",
                        "Token refresh vulnerable",
                    ],
                },
                "detected_tools": [
                    {
                        "name": "protected_tool",
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert any("vulnerability" in r.lower() for r in tool.business_rules)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_extract_tool_missing_name(self, extractor):
        """Test extraction skips tools without name."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {"description": "Tool without name"},
                    {"name": "valid_tool"},
                ],
            },
        }
        intel = extractor.extract(blueprint)

        assert len(intel.tools) == 1
        assert intel.tools[0].tool_name == "valid_tool"

    def test_extract_tool_non_dict_in_list(self, extractor):
        """Test extraction handles non-dict items in detected_tools."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    "not a dict",
                    {"name": "valid_tool"},
                    123,
                ],
            },
        }
        intel = extractor.extract(blueprint)

        assert len(intel.tools) == 1
        assert intel.tools[0].tool_name == "valid_tool"

    def test_extract_parameter_missing_name(self, extractor):
        """Test parameter extraction skips params without name."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "test_tool",
                        "parameters": {
                            "valid_param": {"type": "str"},
                            "": {"type": "str"},  # No name
                        },
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "valid_param"

    def test_extract_infrastructure_missing_fields(self, extractor):
        """Test extraction handles missing infrastructure fields."""
        blueprint = {
            "intelligence": {
                "infrastructure": {},
                "detected_tools": [{"name": "tool1"}],
            },
        }
        intel = extractor.extract(blueprint)

        assert intel.llm_model is None
        assert intel.database_type is None

    def test_extract_auth_structure_missing_fields(self, extractor):
        """Test extraction handles missing auth structure fields."""
        blueprint = {
            "intelligence": {
                "auth_structure": {},
                "detected_tools": [{"name": "tool1"}],
            },
        }
        intel = extractor.extract(blueprint)

        # Should not crash, auth filter extraction is optional
        assert isinstance(intel, ReconIntelligence)

    def test_extract_empty_detected_tools_list(self, extractor):
        """Test extraction with empty detected_tools list."""
        blueprint = {
            "intelligence": {
                "detected_tools": [],
            },
        }
        intel = extractor.extract(blueprint)

        assert intel.tools == []

    def test_extract_multiple_tools_with_mixed_data(self, extractor):
        """Test extraction with multiple tools with varying detail levels."""
        blueprint = {
            "intelligence": {
                "infrastructure": {
                    "model_family": "gpt-4",
                    "vector_db": "FAISS",
                },
                "detected_tools": [
                    {
                        "name": "simple_tool",
                    },
                    {
                        "name": "complex_tool",
                        "description": "Complex tool description",
                        "parameters": {
                            "param1": {"type": "str", "format": "ABC-XXXXX"},
                        },
                        "business_rules": ["Rule 1"],
                    },
                    {
                        "name": "minimal_tool",
                        "arguments": ["arg1"],
                    },
                ],
            },
        }
        intel = extractor.extract(blueprint)

        assert len(intel.tools) == 3
        assert intel.tools[0].tool_name == "simple_tool"
        assert len(intel.tools[1].parameters) > 0
        assert len(intel.tools[2].parameters) > 0
