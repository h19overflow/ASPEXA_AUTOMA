"""Unit tests for new snipers models (AttackMode, ProbeCategory, AttackEvent, ExploitStreamRequest).

Tests Pydantic model validation for multi-mode attack support.
"""
import pytest
import logging
from datetime import datetime
from pydantic import ValidationError

from services.snipers.models import (
    AttackMode,
    ProbeCategory,
    AttackEvent,
    ExploitStreamRequest,
)

logger = logging.getLogger(__name__)


class TestAttackModeEnum:
    """Test AttackMode enum."""

    def test_attack_mode_values(self):
        """Test AttackMode enum has expected values."""
        assert AttackMode.GUIDED.value == "guided"
        assert AttackMode.MANUAL.value == "manual"
        assert AttackMode.SWEEP.value == "sweep"

    def test_attack_mode_count(self):
        """Test AttackMode has exactly 3 modes."""
        modes = list(AttackMode)
        assert len(modes) == 3

    def test_attack_mode_string_comparison(self):
        """Test AttackMode enum comparison."""
        assert AttackMode.GUIDED == AttackMode("guided")
        assert AttackMode.MANUAL == AttackMode("manual")
        assert AttackMode.SWEEP == AttackMode("sweep")

    def test_attack_mode_string_representation(self):
        """Test string representation of AttackMode."""
        assert str(AttackMode.GUIDED) == "AttackMode.GUIDED"
        assert str(AttackMode.MANUAL) == "AttackMode.MANUAL"

    def test_all_modes_can_be_iterated(self):
        """Test all modes can be iterated."""
        modes = [m for m in AttackMode]
        assert len(modes) == 3
        assert AttackMode.GUIDED in modes
        assert AttackMode.MANUAL in modes
        assert AttackMode.SWEEP in modes


class TestProbeCategoryEnum:
    """Test ProbeCategory enum."""

    def test_probe_category_values(self):
        """Test ProbeCategory enum has expected values."""
        assert ProbeCategory.JAILBREAK.value == "jailbreak"
        assert ProbeCategory.PROMPT_INJECTION.value == "prompt_injection"
        assert ProbeCategory.ENCODING.value == "encoding"
        assert ProbeCategory.DATA_EXTRACTION.value == "data_extraction"
        assert ProbeCategory.TOOL_EXPLOITATION.value == "tool_exploitation"

    def test_probe_category_count(self):
        """Test ProbeCategory has exactly 5 categories."""
        categories = list(ProbeCategory)
        assert len(categories) == 5

    def test_probe_category_string_comparison(self):
        """Test ProbeCategory enum comparison."""
        assert ProbeCategory.JAILBREAK == ProbeCategory("jailbreak")
        assert ProbeCategory.ENCODING == ProbeCategory("encoding")

    def test_probe_category_from_string(self):
        """Test creating ProbeCategory from string value."""
        cat = ProbeCategory("jailbreak")
        assert cat == ProbeCategory.JAILBREAK

    def test_invalid_probe_category_raises_error(self):
        """Test invalid category value raises error."""
        with pytest.raises(ValueError):
            ProbeCategory("invalid_category")

    def test_all_categories_can_be_iterated(self):
        """Test all categories can be iterated."""
        categories = list(ProbeCategory)
        assert len(categories) == 5
        for cat in ProbeCategory:
            assert cat in categories


class TestAttackEvent:
    """Test AttackEvent Pydantic model."""

    def test_valid_attack_event_minimal(self):
        """Test creating AttackEvent with minimal fields."""
        event = AttackEvent(
            type="plan",
            data={"test": "data"}
        )
        assert event.type == "plan"
        assert event.data == {"test": "data"}
        assert event.timestamp  # Should have auto-generated timestamp

    def test_valid_attack_event_all_types(self):
        """Test all valid event types."""
        valid_types = [
            "plan",
            "approval_required",
            "payload",
            "response",
            "result",
            "error",
            "complete",
        ]
        for event_type in valid_types:
            event = AttackEvent(type=event_type, data={})
            assert event.type == event_type

    def test_attack_event_empty_data(self):
        """Test AttackEvent with empty data dict."""
        event = AttackEvent(type="complete", data={})
        assert event.data == {}

    def test_attack_event_nested_data(self):
        """Test AttackEvent with nested data."""
        data = {
            "nested": {
                "level2": {
                    "level3": "value"
                }
            },
            "array": [1, 2, 3]
        }
        event = AttackEvent(type="result", data=data)
        assert event.data == data
        assert event.data["nested"]["level2"]["level3"] == "value"

    def test_attack_event_invalid_type(self):
        """Test invalid event type raises validation error."""
        with pytest.raises(ValidationError):
            AttackEvent(type="invalid_type", data={})

    def test_attack_event_timestamp_format(self):
        """Test timestamp is ISO format."""
        event = AttackEvent(type="plan", data={})
        # Should be parseable as ISO format
        ts = datetime.fromisoformat(event.timestamp)
        assert isinstance(ts, datetime)

    def test_attack_event_custom_timestamp(self):
        """Test providing custom timestamp."""
        custom_ts = "2025-11-29T12:00:00"
        event = AttackEvent(type="plan", data={}, timestamp=custom_ts)
        assert event.timestamp == custom_ts

    def test_attack_event_model_dump(self):
        """Test exporting AttackEvent to dict."""
        event = AttackEvent(type="payload", data={"step": 1})
        dumped = event.model_dump()
        assert dumped["type"] == "payload"
        assert dumped["data"]["step"] == 1
        assert "timestamp" in dumped

    def test_attack_event_model_dump_json(self):
        """Test exporting AttackEvent to JSON."""
        event = AttackEvent(type="error", data={"message": "test"})
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        assert "type" in json_str
        assert "error" in json_str

    def test_attack_event_with_large_data(self):
        """Test AttackEvent with large data payload."""
        large_data = {
            "payload": "x" * 10000,
            "response": "y" * 5000,
        }
        event = AttackEvent(type="response", data=large_data)
        assert len(event.data["payload"]) == 10000


class TestExploitStreamRequest:
    """Test ExploitStreamRequest Pydantic model."""

    def test_valid_manual_request(self):
        """Test valid manual mode request."""
        request = ExploitStreamRequest(
            target_url="http://localhost:8000/api/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test payload"
        )
        assert request.target_url == "http://localhost:8000/api/chat"
        assert request.mode == AttackMode.MANUAL
        assert request.custom_payload == "test payload"

    def test_valid_sweep_request(self):
        """Test valid sweep mode request."""
        request = ExploitStreamRequest(
            target_url="https://target.com/api",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK, ProbeCategory.ENCODING]
        )
        assert request.mode == AttackMode.SWEEP
        assert len(request.categories) == 2

    def test_valid_guided_request(self):
        """Test valid guided mode request."""
        request = ExploitStreamRequest(
            target_url="http://api.example.com",
            mode=AttackMode.GUIDED,
            probe_name="encoding"
        )
        assert request.mode == AttackMode.GUIDED
        assert request.probe_name == "encoding"

    def test_request_with_campaign_id(self):
        """Test request with campaign_id."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            campaign_id="campaign-001"
        )
        assert request.campaign_id == "campaign-001"

    def test_request_with_converters(self):
        """Test request with converter list."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            converters=["base64", "rot13"]
        )
        assert request.converters == ["base64", "rot13"]

    def test_request_require_plan_approval_default(self):
        """Test default value for require_plan_approval."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload"
        )
        assert request.require_plan_approval is True

    def test_request_require_plan_approval_false(self):
        """Test setting require_plan_approval to False."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            require_plan_approval=False
        )
        assert request.require_plan_approval is False

    def test_probes_per_category_default(self):
        """Test default value for probes_per_category."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK]
        )
        assert request.probes_per_category == 5

    def test_probes_per_category_custom(self):
        """Test custom probes_per_category."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK],
            probes_per_category=10
        )
        assert request.probes_per_category == 10

    def test_probes_per_category_validation_min(self):
        """Test probes_per_category validation (minimum 1)."""
        with pytest.raises(ValidationError):
            ExploitStreamRequest(
                target_url="http://localhost/chat",
                mode=AttackMode.SWEEP,
                categories=[ProbeCategory.JAILBREAK],
                probes_per_category=0  # Invalid: < 1
            )

    def test_probes_per_category_validation_max(self):
        """Test probes_per_category validation (maximum 20)."""
        with pytest.raises(ValidationError):
            ExploitStreamRequest(
                target_url="http://localhost/chat",
                mode=AttackMode.SWEEP,
                categories=[ProbeCategory.JAILBREAK],
                probes_per_category=25  # Invalid: > 20
            )

    def test_probes_per_category_boundary_values(self):
        """Test probes_per_category boundary values."""
        # Min valid: 1
        req1 = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK],
            probes_per_category=1
        )
        assert req1.probes_per_category == 1

        # Max valid: 20
        req20 = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK],
            probes_per_category=20
        )
        assert req20.probes_per_category == 20

    def test_missing_required_target_url(self):
        """Test that target_url is required."""
        with pytest.raises(ValidationError):
            ExploitStreamRequest(
                mode=AttackMode.MANUAL,
                custom_payload="payload"
                # Missing: target_url
            )

    def test_missing_required_mode(self):
        """Test that mode is required."""
        with pytest.raises(ValidationError):
            ExploitStreamRequest(
                target_url="http://localhost/chat",
                custom_payload="payload"
                # Missing: mode
            )

    def test_invalid_target_url_format(self):
        """Test invalid URL format."""
        # Pydantic doesn't validate URL format by default, but we can test
        request = ExploitStreamRequest(
            target_url="not-a-valid-url",  # This might not raise if URL validation is not strict
            mode=AttackMode.MANUAL,
            custom_payload="payload"
        )
        # If strict URL validation is enabled, this would raise ValidationError
        # For now, just verify it was accepted
        assert request.target_url == "not-a-valid-url"

    def test_empty_custom_payload(self):
        """Test with empty custom_payload."""
        # Empty payload is allowed at model level (validation happens at flow level)
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload=""
        )
        assert request.custom_payload == ""

    def test_none_custom_payload(self):
        """Test with None custom_payload."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL
            # custom_payload not provided, defaults to None
        )
        assert request.custom_payload is None

    def test_empty_categories_list(self):
        """Test with empty categories list."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[]
        )
        assert request.categories == []

    def test_none_categories(self):
        """Test with None categories."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP
            # categories not provided, defaults to None
        )
        assert request.categories is None

    def test_single_category(self):
        """Test with single category."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK]
        )
        assert len(request.categories) == 1

    def test_all_categories(self):
        """Test with all categories."""
        all_cats = list(ProbeCategory)
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=all_cats
        )
        assert len(request.categories) == 5

    def test_empty_converters_list(self):
        """Test with empty converters list."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            converters=[]
        )
        assert request.converters == []

    def test_single_converter(self):
        """Test with single converter."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            converters=["base64"]
        )
        assert request.converters == ["base64"]

    def test_multiple_converters(self):
        """Test with multiple converters."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            converters=["base64", "rot13", "caesar_cipher"]
        )
        assert len(request.converters) == 3

    def test_model_dump_manual_mode(self):
        """Test exporting manual request to dict."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="test payload",
            converters=["base64"]
        )
        dumped = request.model_dump()
        assert dumped["target_url"] == "http://localhost/chat"
        assert dumped["mode"] == "manual"
        assert dumped["custom_payload"] == "test payload"

    def test_model_dump_json_sweep_mode(self):
        """Test exporting sweep request to JSON."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.SWEEP,
            categories=[ProbeCategory.JAILBREAK]
        )
        json_str = request.model_dump_json()
        assert isinstance(json_str, str)
        assert "sweep" in json_str
        assert "jailbreak" in json_str

    def test_request_with_all_optional_fields(self):
        """Test request with all optional fields provided."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            campaign_id="campaign-001",
            custom_payload="payload",
            converters=["base64", "rot13"],
            require_plan_approval=False
        )
        assert request.campaign_id == "campaign-001"
        assert request.custom_payload == "payload"
        assert request.converters == ["base64", "rot13"]
        assert request.require_plan_approval is False

    def test_guided_mode_with_probe_name(self):
        """Test guided mode request with probe_name."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.GUIDED,
            probe_name="dan"
        )
        assert request.probe_name == "dan"

    def test_guided_mode_without_probe_name(self):
        """Test guided mode request without probe_name."""
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.GUIDED
            # probe_name not provided, defaults to None
        )
        assert request.probe_name is None


class TestExploitStreamRequestEdgeCases:
    """Edge case tests for ExploitStreamRequest."""

    def test_very_long_target_url(self):
        """Test with very long target URL."""
        long_url = "http://localhost/api/" + "path/" * 100
        request = ExploitStreamRequest(
            target_url=long_url,
            mode=AttackMode.MANUAL,
            custom_payload="payload"
        )
        assert request.target_url == long_url

    def test_very_long_custom_payload(self):
        """Test with very long custom payload."""
        long_payload = "a" * 100000
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload=long_payload
        )
        assert len(request.custom_payload) == 100000

    def test_special_characters_in_payload(self):
        """Test with special characters in payload."""
        special_payload = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload=special_payload
        )
        assert request.custom_payload == special_payload

    def test_unicode_in_payload(self):
        """Test with Unicode characters in payload."""
        unicode_payload = "你好世界 مرحبا بالعالم"
        request = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload=unicode_payload
        )
        assert request.custom_payload == unicode_payload

    def test_multiple_campaign_ids(self):
        """Test changing campaign_id (should be allowed)."""
        req1 = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            campaign_id="campaign-001"
        )
        req2 = ExploitStreamRequest(
            target_url="http://localhost/chat",
            mode=AttackMode.MANUAL,
            custom_payload="payload",
            campaign_id="campaign-002"
        )
        assert req1.campaign_id != req2.campaign_id
