"""
Unit tests for tool intelligence models.

Tests ToolParameter, ToolSignature, and ReconIntelligence data models
that represent discovered tool signatures and business rules.
"""

import pytest
from pydantic import ValidationError

from services.snipers.core.phases.articulation.models.tool_intelligence import (
    ReconIntelligence,
    ToolParameter,
    ToolSignature,
)


class TestToolParameter:
    """Tests for ToolParameter model."""

    def test_create_minimal_parameter(self):
        """Test creating ToolParameter with required fields only."""
        param = ToolParameter(name="user_id", type="str")
        assert param.name == "user_id"
        assert param.type == "str"
        assert param.required is True
        assert param.format_constraint is None
        assert param.validation_pattern is None
        assert param.default_value is None

    def test_create_parameter_with_all_fields(self):
        """Test creating ToolParameter with all fields specified."""
        param = ToolParameter(
            name="transaction_id",
            type="str",
            required=True,
            format_constraint="TXN-XXXXX",
            validation_pattern=r"^TXN-\d{5}$",
            default_value=None,
        )
        assert param.name == "transaction_id"
        assert param.type == "str"
        assert param.required is True
        assert param.format_constraint == "TXN-XXXXX"
        assert param.validation_pattern == r"^TXN-\d{5}$"

    def test_parameter_optional_field(self):
        """Test creating optional parameter."""
        param = ToolParameter(name="reason", type="str", required=False)
        assert param.required is False

    def test_parameter_with_default_value(self):
        """Test parameter with default value."""
        param = ToolParameter(
            name="amount", type="float", default_value="0.0"
        )
        assert param.default_value == "0.0"

    def test_parameter_with_multiple_constraints(self):
        """Test parameter with both format and validation constraints."""
        param = ToolParameter(
            name="order_id",
            type="str",
            format_constraint="ORD-XXXXX",
            validation_pattern=r"^ORD-[A-Z0-9]{5}$",
        )
        assert param.format_constraint == "ORD-XXXXX"
        assert param.validation_pattern == r"^ORD-[A-Z0-9]{5}$"

    def test_parameter_missing_required_name(self):
        """Test ToolParameter validation fails without name."""
        with pytest.raises(ValidationError):
            ToolParameter(type="str")

    def test_parameter_missing_required_type(self):
        """Test ToolParameter validation fails without type."""
        with pytest.raises(ValidationError):
            ToolParameter(name="param")


class TestToolSignature:
    """Tests for ToolSignature model."""

    def test_create_minimal_tool_signature(self):
        """Test creating ToolSignature with required fields only."""
        sig = ToolSignature(tool_name="refund_transaction")
        assert sig.tool_name == "refund_transaction"
        assert sig.description is None
        assert sig.parameters == []
        assert sig.business_rules == []
        assert sig.example_calls == []
        assert sig.authorization_required is True

    def test_create_complete_tool_signature(self):
        """Test creating ToolSignature with all fields."""
        params = [
            ToolParameter(name="txn_id", type="str", format_constraint="TXN-XXXXX"),
            ToolParameter(name="amount", type="float"),
        ]
        rules = [
            "Refund must be for original transaction",
            "Amount must be under $1000",
        ]
        examples = ["refund_transaction(TXN-12345, 500.00)"]

        sig = ToolSignature(
            tool_name="refund_transaction",
            description="Process refund for transaction",
            parameters=params,
            business_rules=rules,
            example_calls=examples,
            authorization_required=True,
        )

        assert sig.tool_name == "refund_transaction"
        assert sig.description == "Process refund for transaction"
        assert len(sig.parameters) == 2
        assert len(sig.business_rules) == 2
        assert len(sig.example_calls) == 1
        assert sig.authorization_required is True

    def test_tool_signature_no_authorization(self):
        """Test tool signature that doesn't require authorization."""
        sig = ToolSignature(
            tool_name="read_public_data",
            authorization_required=False,
        )
        assert sig.authorization_required is False

    def test_tool_signature_with_parameters_list(self):
        """Test tool signature with multiple parameters."""
        params = [
            ToolParameter(name="user_id", type="str"),
            ToolParameter(name="action", type="str"),
            ToolParameter(name="amount", type="float", required=False),
        ]
        sig = ToolSignature(tool_name="audit_log", parameters=params)
        assert len(sig.parameters) == 3
        assert params[2].required is False

    def test_tool_signature_missing_tool_name(self):
        """Test ToolSignature validation fails without tool_name."""
        with pytest.raises(ValidationError):
            ToolSignature()


class TestReconIntelligence:
    """Tests for ReconIntelligence model."""

    def test_create_empty_recon_intelligence(self):
        """Test creating ReconIntelligence with defaults."""
        intel = ReconIntelligence()
        assert intel.tools == []
        assert intel.llm_model is None
        assert intel.database_type is None
        assert intel.content_filters == []
        assert intel.raw_intelligence == {}

    def test_create_recon_intelligence_with_tools(self):
        """Test creating ReconIntelligence with discovered tools."""
        tools = [
            ToolSignature(
                tool_name="refund_transaction",
                parameters=[
                    ToolParameter(name="txn_id", type="str"),
                ],
            ),
            ToolSignature(
                tool_name="check_balance",
                parameters=[
                    ToolParameter(name="account_id", type="str"),
                ],
            ),
        ]

        intel = ReconIntelligence(tools=tools)
        assert len(intel.tools) == 2
        assert intel.tools[0].tool_name == "refund_transaction"
        assert intel.tools[1].tool_name == "check_balance"

    def test_recon_intelligence_with_metadata(self):
        """Test ReconIntelligence with system metadata."""
        intel = ReconIntelligence(
            llm_model="gpt-4",
            database_type="FAISS",
            content_filters=["rate_limiting", "refusal_detection"],
            raw_intelligence={
                "target_url": "http://target.example.com",
                "scan_timestamp": "2025-01-01T00:00:00Z",
            },
        )

        assert intel.llm_model == "gpt-4"
        assert intel.database_type == "FAISS"
        assert len(intel.content_filters) == 2
        assert intel.raw_intelligence["target_url"] == "http://target.example.com"

    def test_recon_intelligence_with_complete_data(self):
        """Test ReconIntelligence with all fields populated."""
        tools = [
            ToolSignature(
                tool_name="process_refund",
                description="Handle refund requests",
                parameters=[
                    ToolParameter(
                        name="transaction_id",
                        type="str",
                        format_constraint="TXN-XXXXX",
                    ),
                    ToolParameter(name="amount", type="float"),
                ],
                business_rules=[
                    "Amount must be under $1000",
                    "Only for original transactions",
                ],
                authorization_required=True,
            ),
        ]

        intel = ReconIntelligence(
            tools=tools,
            llm_model="gemini-3-flash-preview",
            database_type="ChromaDB",
            content_filters=[
                "rate_limiting_100_per_hour",
                "auth_oauth2",
                "refusal_detection",
            ],
            raw_intelligence={
                "target_url": "https://api.example.com",
                "scan_id": "scan-001",
            },
        )

        assert len(intel.tools) == 1
        assert intel.tools[0].tool_name == "process_refund"
        assert len(intel.tools[0].parameters) == 2
        assert len(intel.tools[0].business_rules) == 2
        assert len(intel.content_filters) == 3
        assert intel.llm_model == "gemini-3-flash-preview"
        assert intel.database_type == "ChromaDB"

    def test_recon_intelligence_empty_content_filters(self):
        """Test ReconIntelligence with no content filters."""
        intel = ReconIntelligence(
            tools=[
                ToolSignature(
                    tool_name="test_tool",
                ),
            ],
        )
        assert intel.content_filters == []

    def test_recon_intelligence_multiple_tools_multiple_rules(self):
        """Test ReconIntelligence with multiple tools and rules."""
        tools = [
            ToolSignature(
                tool_name="tool1",
                business_rules=["rule1", "rule2"],
            ),
            ToolSignature(
                tool_name="tool2",
                business_rules=["rule3", "rule4", "rule5"],
            ),
        ]
        intel = ReconIntelligence(tools=tools)
        assert len(intel.tools) == 2
        assert sum(len(t.business_rules) for t in intel.tools) == 5


class TestToolIntelligenceIntegration:
    """Integration tests for tool intelligence models working together."""

    def test_realistic_e_commerce_tool_signatures(self):
        """Test realistic e-commerce tool signatures."""
        refund_tool = ToolSignature(
            tool_name="process_refund",
            description="Process customer refunds",
            parameters=[
                ToolParameter(
                    name="transaction_id",
                    type="str",
                    format_constraint="TXN-XXXXX",
                    validation_pattern=r"^TXN-\d{5}$",
                ),
                ToolParameter(
                    name="refund_amount",
                    type="float",
                ),
            ],
            business_rules=[
                "Refund must be under $1000 limit",
                "Customer must have original receipt",
                "Refund can only be processed within 30 days",
            ],
            example_calls=[
                "process_refund('TXN-12345', 500.00)",
                "process_refund('TXN-67890', 750.50)",
            ],
            authorization_required=True,
        )

        intel = ReconIntelligence(
            tools=[refund_tool],
            llm_model="gpt-4",
            database_type="PostgreSQL",
            content_filters=["rate_limiting_1000_per_hour", "auth_jwt"],
        )

        assert intel.tools[0].tool_name == "process_refund"
        assert len(intel.tools[0].parameters) == 2
        assert len(intel.tools[0].business_rules) == 3
        assert len(intel.tools[0].example_calls) == 2

    def test_multi_tool_intelligence_banking_scenario(self):
        """Test multiple tools in banking scenario."""
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
                    "Blocked from weekends",
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

        intel = ReconIntelligence(
            tools=tools,
            llm_model="claude-3-sonnet",
            database_type="Oracle",
            content_filters=[
                "rate_limiting_100_per_hour",
                "auth_2fa",
                "ip_whitelist",
            ],
            raw_intelligence={
                "target": "banking-api.internal",
                "discovered_at": "2025-01-01T10:00:00Z",
            },
        )

        assert len(intel.tools) == 2
        assert intel.tools[0].authorization_required is True
        assert intel.tools[1].authorization_required is False
        assert len(intel.content_filters) == 3
        assert intel.database_type == "Oracle"
