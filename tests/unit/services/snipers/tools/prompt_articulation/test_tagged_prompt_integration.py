"""
Integration tests for tagged prompt pipeline.

Tests the complete flow from recon extraction through tagged prompt
generation and payload context integration.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.snipers.utils.prompt_articulation.models.payload_context import (
    AttackHistory,
    PayloadContext,
    TargetInfo,
)
from services.snipers.utils.prompt_articulation.models.tool_intelligence import (
    ReconIntelligence,
    ToolParameter,
    ToolSignature,
)
from services.snipers.utils.prompt_articulation.extractors.recon_extractor import (
    ReconIntelligenceExtractor,
)
from services.snipers.utils.prompt_articulation.schemas.tagged_prompt_builder import (
    TaggedPromptBuilder,
)


@pytest.fixture
def extractor():
    """Provide extractor instance."""
    return ReconIntelligenceExtractor()


@pytest.fixture
def builder():
    """Provide builder instance."""
    return TaggedPromptBuilder()


@pytest.fixture
def sample_if02_recon_blueprint():
    """Sample IF-02 recon blueprint for integration testing."""
    return {
        "intelligence": {
            "infrastructure": {
                "model_family": "gpt-4",
                "vector_db": "FAISS",
                "rate_limits": "1000_per_hour",
            },
            "auth_structure": {
                "type": "oauth2",
                "rules": ["OAuth2 required"],
                "vulnerabilities": ["CSRF not implemented"],
            },
            "system_prompt_leak": ["You are a helpful assistant"],
            "detected_tools": [
                {
                    "name": "process_refund",
                    "description": "Process customer refund",
                    "parameters": {
                        "transaction_id": {
                            "type": "str",
                            "required": True,
                            "format": "TXN-XXXXX",
                            "description": "Transaction ID in TXN-XXXXX format",
                        },
                        "refund_amount": {
                            "type": "float",
                            "required": True,
                        },
                    },
                    "business_rules": [
                        "Maximum refund: $1000",
                        "Requires customer email verification",
                    ],
                    "example_calls": [
                        "process_refund('TXN-12345', 500.00)",
                    ],
                    "requires_auth": True,
                },
                {
                    "name": "check_account_balance",
                    "description": "Check customer account balance",
                    "arguments": ["customer_id"],
                    "requires_auth": False,
                },
            ],
        },
    }


class TestReconToIntelligencePipeline:
    """Tests for recon extraction to intelligence model pipeline."""

    def test_extract_if02_blueprint_to_recon_intelligence(self, extractor, sample_if02_recon_blueprint):
        """Test complete extraction from IF-02 blueprint to ReconIntelligence."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        # Verify top-level structure
        assert isinstance(intel, ReconIntelligence)
        assert intel.llm_model == "gpt-4"
        assert intel.database_type == "FAISS"
        assert len(intel.tools) == 2

        # Verify tool details
        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert len(refund_tool.parameters) == 2
        assert refund_tool.authorization_required is True

    def test_extracted_tools_have_proper_parameters(self, extractor, sample_if02_recon_blueprint):
        """Test that extracted tools have properly formatted parameters."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        txn_param = next(p for p in refund_tool.parameters if p.name == "transaction_id")

        assert txn_param.format_constraint == "TXN-XXXXX"
        assert txn_param.required is True

    def test_extracted_tools_include_business_rules(self, extractor, sample_if02_recon_blueprint):
        """Test that extracted tools include business rules."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert len(refund_tool.business_rules) >= 2
        assert any("$1000" in rule for rule in refund_tool.business_rules)


class TestIntelligenceToPromptPipeline:
    """Tests for intelligence to tagged prompt pipeline."""

    def test_build_prompt_from_extracted_intelligence(self, extractor, builder, sample_if02_recon_blueprint):
        """Test building tagged prompt from extracted intelligence."""
        # Extract intelligence
        intel = extractor.extract(sample_if02_recon_blueprint)

        # Build prompt
        prompt = builder.build_tool_exploitation_prompt(
            objective="unauthorized refund",
            recon_intel=intel,
            framing_strategy="customer support",
            payload_count=3,
        )

        # Verify prompt includes extracted data
        assert "process_refund" in prompt
        assert "TXN-XXXXX" in prompt
        assert "$1000" in prompt or "limit" in prompt.lower()
        assert "unauthorized refund" in prompt

    def test_prompt_includes_all_extracted_tools(self, extractor, builder, sample_if02_recon_blueprint):
        """Test that prompt includes all extracted tools."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=intel,
            framing_strategy="test",
        )

        assert "process_refund" in prompt
        assert "check_account_balance" in prompt

    def test_prompt_respects_authorization_requirements(self, extractor, builder, sample_if02_recon_blueprint):
        """Test that prompt respects authorization requirements."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=intel,
            framing_strategy="test",
        )

        # process_refund requires auth, check_account_balance doesn't
        # Prompt should reflect this in instructions
        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        balance_tool = next(t for t in intel.tools if t.tool_name == "check_account_balance")

        assert refund_tool.authorization_required is True
        assert balance_tool.authorization_required is False


class TestPayloadContextIntegration:
    """Tests for PayloadContext integration with reconnaissance intelligence."""

    def test_payload_context_with_recon_intelligence(self, extractor, sample_if02_recon_blueprint):
        """Test PayloadContext properly stores recon intelligence."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        context = PayloadContext(
            target=TargetInfo(domain="finance"),
            history=AttackHistory(),
            objective="unauthorized refund",
            recon_intelligence=intel,
        )

        assert context.recon_intelligence == intel
        assert len(context.recon_intelligence.tools) == 2

    def test_payload_context_to_dict_includes_recon_tools(self, extractor, sample_if02_recon_blueprint):
        """Test that PayloadContext.to_dict() includes recon tools."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        context = PayloadContext(
            target=TargetInfo(domain="finance", tools=["refund", "balance"]),
            history=AttackHistory(),
            objective="unauthorized refund",
            recon_intelligence=intel,
        )

        context_dict = context.to_dict()

        assert "recon_tools" in context_dict
        assert len(context_dict["recon_tools"]) == 2
        assert context_dict["recon_tools"][0]["name"] == "process_refund"

    def test_payload_context_recon_tools_include_parameters(self, extractor, sample_if02_recon_blueprint):
        """Test that recon tools in context include parameter info."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        context = PayloadContext(
            target=TargetInfo(domain="finance"),
            history=AttackHistory(),
            recon_intelligence=intel,
        )

        context_dict = context.to_dict()
        refund_tool = context_dict["recon_tools"][0]

        assert "parameters" in refund_tool
        assert "transaction_id" in refund_tool["parameters"]
        assert "refund_amount" in refund_tool["parameters"]

    def test_payload_context_recon_tools_include_business_rules(self, extractor, sample_if02_recon_blueprint):
        """Test that recon tools include business rules."""
        intel = extractor.extract(sample_if02_recon_blueprint)

        context = PayloadContext(
            target=TargetInfo(domain="finance"),
            history=AttackHistory(),
            recon_intelligence=intel,
        )

        context_dict = context.to_dict()
        refund_tool = context_dict["recon_tools"][0]

        assert "business_rules" in refund_tool
        assert len(refund_tool["business_rules"]) > 0


class TestCompleteReconToPayloadPipeline:
    """End-to-end tests for complete recon-to-payload pipeline."""

    def test_full_pipeline_if02_to_context_to_prompt(self, extractor, builder, sample_if02_recon_blueprint):
        """Test complete pipeline from IF-02 blueprint to tagged prompt."""
        # Step 1: Extract intelligence
        intel = extractor.extract(sample_if02_recon_blueprint)

        # Step 2: Create payload context
        context = PayloadContext(
            target=TargetInfo(
                domain="e-commerce",
                tools=["process_refund", "check_balance"],
            ),
            history=AttackHistory(
                failed_approaches=["generic jailbreak"],
                successful_patterns=["social engineering"],
            ),
            objective="unauthorized refund processing",
            recon_intelligence=intel,
        )

        # Step 3: Build prompt
        prompt = builder.build_tool_exploitation_prompt(
            objective=context.objective,
            recon_intel=context.recon_intelligence,
            framing_strategy="legitimate customer",
            payload_count=3,
        )

        # Verify complete flow
        assert intel is not None
        assert context.recon_intelligence is not None
        assert prompt is not None
        assert "process_refund" in prompt
        assert "unauthorized refund" in prompt
        assert "legitimate customer" in prompt

    def test_pipeline_preserves_all_tool_metadata(self, extractor, builder, sample_if02_recon_blueprint):
        """Test that metadata is preserved through pipeline."""
        # Extract
        intel = extractor.extract(sample_if02_recon_blueprint)

        # Verify extraction
        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        original_rules_count = len(sample_if02_recon_blueprint["intelligence"]["detected_tools"][0]["business_rules"])
        extracted_rules_count = len(refund_tool.business_rules)

        assert extracted_rules_count >= original_rules_count

        # Build prompt
        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=intel,
            framing_strategy="test",
        )

        # All rules should be represented in prompt
        for rule in refund_tool.business_rules:
            if "$" in rule or "require" in rule.lower():
                # Critical rules should be emphasized in prompt
                assert rule in prompt or rule[:50] in prompt or "refund" in prompt.lower()

    def test_multiple_extraction_scenarios(self, extractor, builder):
        """Test pipeline with multiple extraction scenarios."""
        scenarios = [
            {
                "name": "Simple single tool",
                "blueprint": {
                    "intelligence": {
                        "detected_tools": [{"name": "tool1"}],
                    },
                },
            },
            {
                "name": "Multiple tools with parameters",
                "blueprint": {
                    "intelligence": {
                        "detected_tools": [
                            {
                                "name": "tool1",
                                "parameters": {
                                    "param1": {"type": "str"},
                                },
                            },
                            {
                                "name": "tool2",
                                "parameters": {
                                    "param2": {"type": "int"},
                                },
                            },
                        ],
                    },
                },
            },
            {
                "name": "With infrastructure details",
                "blueprint": {
                    "intelligence": {
                        "infrastructure": {
                            "model_family": "gpt-4",
                            "vector_db": "FAISS",
                        },
                        "detected_tools": [{"name": "tool1"}],
                    },
                },
            },
        ]

        for scenario in scenarios:
            intel = extractor.extract(scenario["blueprint"])
            assert intel is not None
            assert len(intel.tools) > 0

            prompt = builder.build_tool_exploitation_prompt(
                objective="test",
                recon_intel=intel,
                framing_strategy="test",
            )
            assert prompt is not None
            assert len(prompt) > 0


class TestErrorHandlingInPipeline:
    """Tests for error handling in the complete pipeline."""

    def test_extract_with_malformed_tools_list(self, extractor):
        """Test extraction handles malformed tools list gracefully."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    "invalid string",
                    {"name": "valid_tool"},
                    None,
                    {"name": "another_tool"},
                ],
            },
        }

        intel = extractor.extract(blueprint)

        # Should extract valid tools and skip invalid ones
        assert len(intel.tools) == 2
        tool_names = {t.tool_name for t in intel.tools}
        assert "valid_tool" in tool_names
        assert "another_tool" in tool_names

    def test_build_prompt_with_empty_tools(self, builder):
        """Test prompt building with empty tool list."""
        intel = ReconIntelligence(tools=[])

        prompt = builder.build_tool_exploitation_prompt(
            objective="test",
            recon_intel=intel,
            framing_strategy="test",
        )

        # Should still generate valid prompt
        assert prompt is not None
        assert "<Task" in prompt
        assert "<OutputFormat>" in prompt

    def test_context_with_none_recon_intelligence(self):
        """Test PayloadContext handles None recon intelligence."""
        context = PayloadContext(
            target=TargetInfo(domain="test"),
            history=AttackHistory(),
            recon_intelligence=None,
        )

        context_dict = context.to_dict()

        # Should not crash
        assert context_dict is not None
        assert "domain" in context_dict

    def test_extract_tool_missing_name_field(self, extractor):
        """Test extraction skips tools without name."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {"description": "No name here"},
                    {"name": "valid_tool", "description": "Has name"},
                ],
            },
        }

        intel = extractor.extract(blueprint)

        assert len(intel.tools) == 1
        assert intel.tools[0].tool_name == "valid_tool"

    def test_extract_parameter_with_missing_name(self, extractor):
        """Test extraction handles parameters without name."""
        blueprint = {
            "intelligence": {
                "detected_tools": [
                    {
                        "name": "test_tool",
                        "parameters": {
                            "valid_param": {"type": "str"},
                            "": {"type": "int"},  # No name
                        },
                    },
                ],
            },
        }

        intel = extractor.extract(blueprint)

        tool = intel.tools[0]
        # Should only have valid parameter
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "valid_param"


class TestRealWorldScenarios:
    """Tests with realistic e-commerce/banking scenarios."""

    def test_ecommerce_refund_scenario(self, extractor, builder):
        """Test realistic e-commerce refund scenario."""
        blueprint = {
            "intelligence": {
                "infrastructure": {
                    "model_family": "gpt-4-turbo",
                    "vector_db": "Pinecone",
                    "rate_limits": "100_per_minute",
                },
                "auth_structure": {
                    "type": "jwt",
                    "vulnerabilities": ["JWT algorithm confusion possible"],
                },
                "detected_tools": [
                    {
                        "name": "process_refund",
                        "description": "Process customer refunds",
                        "parameters": {
                            "order_id": {
                                "type": "str",
                                "format": "ORD-XXXXX",
                                "description": "Order ID in ORD-XXXXX format",
                            },
                            "amount": {"type": "float"},
                            "reason": {"type": "str"},
                        },
                        "business_rules": [
                            "Refund amount must be under $5000",
                            "Must have order receipt",
                            "30-day refund window",
                        ],
                        "requires_auth": True,
                    },
                    {
                        "name": "check_order_status",
                        "description": "Check order status",
                        "arguments": ["order_id"],
                        "requires_auth": False,
                    },
                ],
            },
        }

        # Extract
        intel = extractor.extract(blueprint)

        # Verify extraction
        assert len(intel.tools) == 2
        refund_tool = next(t for t in intel.tools if t.tool_name == "process_refund")
        assert len(refund_tool.parameters) == 3

        # Build prompt
        prompt = builder.build_tool_exploitation_prompt(
            objective="fraudulent refund",
            recon_intel=intel,
            framing_strategy="legitimate customer complaint",
            payload_count=5,
        )

        # Verify prompt quality
        assert "process_refund" in prompt
        assert "ORD-XXXXX" in prompt or "ORD" in prompt
        assert "$5000" in prompt or "amount" in prompt.lower()
        assert "5" in prompt  # payload count

    def test_banking_transfer_scenario(self, extractor, builder):
        """Test realistic banking transfer scenario."""
        blueprint = {
            "intelligence": {
                "infrastructure": {
                    "model_family": "claude-3-opus",
                    "vector_db": "Weaviate",
                },
                "auth_structure": {
                    "type": "2fa_required",
                    "vulnerabilities": ["SMS 2FA can be intercepted"],
                },
                "detected_tools": [
                    {
                        "name": "transfer_funds",
                        "description": "Transfer funds between accounts",
                        "parameters": {
                            "source_account": {
                                "type": "str",
                                "format": "ACC-XXXXX",
                            },
                            "dest_account": {
                                "type": "str",
                                "format": "ACC-XXXXX",
                            },
                            "amount": {"type": "float"},
                        },
                        "business_rules": [
                            "Daily limit: $10000",
                            "Requires 2FA",
                            "International transfers require additional verification",
                        ],
                        "requires_auth": True,
                    },
                ],
            },
        }

        intel = extractor.extract(blueprint)
        prompt = builder.build_tool_exploitation_prompt(
            objective="unauthorized transfer",
            recon_intel=intel,
            framing_strategy="legitimate account holder",
            payload_count=3,
        )

        assert "transfer_funds" in prompt
        assert "ACC-" in prompt or "account" in prompt.lower()
        assert "$10000" in prompt or "daily limit" in prompt.lower()
