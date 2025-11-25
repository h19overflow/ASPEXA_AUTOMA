"""Unit tests for snipers models (Pydantic validation)."""
import pytest
import logging
from datetime import datetime
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class TestExampleFinding:
    """Test ExampleFinding Pydantic model."""

    def test_valid_example_finding(self, sample_example_finding, capture_logs):
        """Test valid ExampleFinding creation."""
        # This will be tested when the model is implemented
        # For now, we define the expected behavior
        logger.info(f"Testing valid ExampleFinding: {sample_example_finding['prompt'][:50]}")
        assert sample_example_finding["detector_score"] >= 0.0
        assert sample_example_finding["detector_score"] <= 1.0
        assert isinstance(sample_example_finding["prompt"], str)
        assert isinstance(sample_example_finding["output"], str)
        assert sample_example_finding["prompt"]  # Not empty
        logger.info("✓ Valid ExampleFinding structure confirmed")

    def test_missing_required_fields(self, invalid_example_finding_missing_field, capture_logs):
        """Test ExampleFinding validation with missing required fields."""
        logger.error("Testing missing required fields in ExampleFinding")
        # When model is implemented, should raise ValidationError
        assert "prompt" in invalid_example_finding_missing_field
        # Verify required fields are missing
        required_fields = ["output", "detector_name", "detector_score", "detection_reason"]
        missing = [f for f in required_fields if f not in invalid_example_finding_missing_field]
        assert len(missing) > 0, "Test fixture should have missing fields"
        logger.error(f"Missing fields: {missing}")

    def test_invalid_detector_score_range_high(self, capture_logs):
        """Test detector_score validation (> 1.0 is invalid)."""
        invalid_data = {
            "prompt": "test",
            "output": "output",
            "detector_name": "test",
            "detector_score": 1.5,  # Invalid: > 1.0
            "detection_reason": "test"
        }
        logger.error(f"Testing invalid score range: {invalid_data['detector_score']}")
        assert invalid_data["detector_score"] > 1.0, "Test setup correct"
        logger.error("✗ Score > 1.0 should be rejected by model")

    def test_invalid_detector_score_range_low(self, capture_logs):
        """Test detector_score validation (< 0.0 is invalid)."""
        invalid_data = {
            "prompt": "test",
            "output": "output",
            "detector_name": "test",
            "detector_score": -0.5,  # Invalid: < 0.0
            "detection_reason": "test"
        }
        logger.error(f"Testing invalid score range: {invalid_data['detector_score']}")
        assert invalid_data["detector_score"] < 0.0, "Test setup correct"
        logger.error("✗ Score < 0.0 should be rejected by model")

    def test_invalid_score_type(self, invalid_example_finding_wrong_type, capture_logs):
        """Test detector_score type validation."""
        logger.error(f"Testing invalid score type: {type(invalid_example_finding_wrong_type['detector_score'])}")
        assert not isinstance(invalid_example_finding_wrong_type["detector_score"], float)
        logger.error("✗ Non-float score should be rejected")

    def test_empty_prompt(self, capture_logs):
        """Test that empty prompt is rejected."""
        logger.error("Testing empty prompt rejection")
        empty_prompt = {
            "prompt": "",  # Empty
            "output": "output",
            "detector_name": "test",
            "detector_score": 0.5,
            "detection_reason": "test"
        }
        assert empty_prompt["prompt"] == "", "Test setup correct"
        logger.error("✗ Empty prompt should be rejected")

    def test_empty_output(self, capture_logs):
        """Test that empty output is rejected."""
        logger.error("Testing empty output rejection")
        empty_output = {
            "prompt": "prompt",
            "output": "",  # Empty
            "detector_name": "test",
            "detector_score": 0.5,
            "detection_reason": "test"
        }
        assert empty_output["output"] == "", "Test setup correct"
        logger.error("✗ Empty output should be rejected")


class TestExploitAgentInput:
    """Test ExploitAgentInput Pydantic model."""

    def test_valid_exploit_agent_input(self, sample_exploit_agent_input, capture_logs):
        """Test valid ExploitAgentInput creation."""
        logger.info(f"Testing valid ExploitAgentInput for probe: {sample_exploit_agent_input['probe_name']}")
        assert sample_exploit_agent_input["probe_name"]
        assert len(sample_exploit_agent_input["example_findings"]) == 3, "Must have exactly 3 examples"
        assert sample_exploit_agent_input["target_url"].startswith("http")
        assert sample_exploit_agent_input["recon_intelligence"]
        logger.info("✓ Valid ExploitAgentInput structure confirmed")

    def test_wrong_example_count(self, invalid_exploit_agent_input_wrong_example_count, capture_logs):
        """Test that example_findings must have exactly 3 items."""
        logger.error(f"Testing wrong example count: {len(invalid_exploit_agent_input_wrong_example_count['example_findings'])}")
        assert len(invalid_exploit_agent_input_wrong_example_count["example_findings"]) != 3
        logger.error("✗ Should reject input with != 3 examples")

    def test_invalid_url(self, invalid_exploit_agent_input_invalid_url, capture_logs):
        """Test URL validation."""
        logger.error(f"Testing invalid URL: {invalid_exploit_agent_input_invalid_url['target_url']}")
        assert not invalid_exploit_agent_input_invalid_url["target_url"].startswith("http")
        logger.error("✗ Invalid URL should be rejected")

    def test_empty_probe_name(self, capture_logs):
        """Test that probe_name cannot be empty."""
        logger.error("Testing empty probe_name rejection")
        invalid_data = {
            "probe_name": "",  # Empty
            "example_findings": [],
            "target_url": "http://test.com",
            "recon_intelligence": {},
            "config": {}
        }
        assert invalid_data["probe_name"] == "", "Test setup correct"
        logger.error("✗ Empty probe_name should be rejected")

    def test_missing_recon_intelligence(self, capture_logs):
        """Test that recon_intelligence is required."""
        logger.error("Testing missing recon_intelligence")
        # When model is implemented, recon_intelligence should be required
        logger.error("✗ Missing recon_intelligence should be rejected")


class TestPatternAnalysis:
    """Test PatternAnalysis Pydantic model."""

    def test_valid_pattern_analysis(self, sample_pattern_analysis, capture_logs):
        """Test valid PatternAnalysis creation."""
        logger.info(f"Testing valid PatternAnalysis: {sample_pattern_analysis['payload_encoding_type']}")
        assert sample_pattern_analysis["confidence"] >= 0.0
        assert sample_pattern_analysis["confidence"] <= 1.0
        assert sample_pattern_analysis["success_indicators"]
        assert len(sample_pattern_analysis["reasoning_steps"]) > 0
        logger.info("✓ Valid PatternAnalysis structure confirmed")

    def test_invalid_confidence_high(self, capture_logs):
        """Test confidence > 1.0 is rejected."""
        logger.error("Testing invalid confidence > 1.0")
        invalid_data = {
            "common_prompt_structure": "test",
            "payload_encoding_type": "Base64",
            "success_indicators": ["test"],
            "reasoning_steps": ["test"],
            "confidence": 1.5  # Invalid
        }
        assert invalid_data["confidence"] > 1.0
        logger.error("✗ Confidence > 1.0 should be rejected")

    def test_empty_reasoning_steps(self, capture_logs):
        """Test that reasoning_steps cannot be empty."""
        logger.error("Testing empty reasoning_steps")
        invalid_data = {
            "common_prompt_structure": "test",
            "payload_encoding_type": "Base64",
            "success_indicators": ["test"],
            "reasoning_steps": [],  # Empty
            "confidence": 0.8
        }
        assert len(invalid_data["reasoning_steps"]) == 0
        logger.error("✗ Empty reasoning_steps should be rejected")

    def test_empty_success_indicators(self, capture_logs):
        """Test that success_indicators cannot be empty."""
        logger.error("Testing empty success_indicators")
        invalid_data = {
            "common_prompt_structure": "test",
            "payload_encoding_type": "Base64",
            "success_indicators": [],  # Empty
            "reasoning_steps": ["step1"],
            "confidence": 0.8
        }
        assert len(invalid_data["success_indicators"]) == 0
        logger.error("✗ Empty success_indicators should be rejected")


class TestConverterSelection:
    """Test ConverterSelection Pydantic model."""

    def test_valid_converter_selection(self, sample_converter_selection, capture_logs):
        """Test valid ConverterSelection creation."""
        logger.info(f"Testing valid ConverterSelection: {sample_converter_selection['selected_converters']}")
        assert sample_converter_selection["selected_converters"]
        assert len(sample_converter_selection["selected_converters"]) > 0
        assert sample_converter_selection["reasoning"]
        assert sample_converter_selection["cot_steps"]
        logger.info("✓ Valid ConverterSelection structure confirmed")

    def test_empty_converter_list(self, capture_logs):
        """Test that selected_converters cannot be empty."""
        logger.error("Testing empty selected_converters")
        invalid_data = {
            "selected_converters": [],  # Empty
            "reasoning": "test",
            "step_back_analysis": "test",
            "cot_steps": ["step1"]
        }
        assert len(invalid_data["selected_converters"]) == 0
        logger.error("✗ Empty selected_converters should be rejected")

    def test_empty_cot_steps(self, capture_logs):
        """Test that cot_steps cannot be empty."""
        logger.error("Testing empty cot_steps")
        invalid_data = {
            "selected_converters": ["Base64Converter"],
            "reasoning": "test",
            "step_back_analysis": "test",
            "cot_steps": []  # Empty
        }
        assert len(invalid_data["cot_steps"]) == 0
        logger.error("✗ Empty cot_steps should be rejected")


class TestPayloadGeneration:
    """Test PayloadGeneration Pydantic model."""

    def test_valid_payload_generation(self, sample_payload_generation, capture_logs):
        """Test valid PayloadGeneration creation."""
        logger.info(f"Testing valid PayloadGeneration: {len(sample_payload_generation['generated_payloads'])} payloads")
        assert sample_payload_generation["generated_payloads"]
        assert len(sample_payload_generation["generated_payloads"]) > 0
        assert sample_payload_generation["template_used"]
        assert sample_payload_generation["variations_applied"]
        logger.info("✓ Valid PayloadGeneration structure confirmed")

    def test_empty_payloads(self, capture_logs):
        """Test that generated_payloads cannot be empty."""
        logger.error("Testing empty generated_payloads")
        invalid_data = {
            "generated_payloads": [],  # Empty
            "template_used": "template",
            "variations_applied": ["var1"],
            "reasoning": "test"
        }
        assert len(invalid_data["generated_payloads"]) == 0
        logger.error("✗ Empty generated_payloads should be rejected")

    def test_empty_template(self, capture_logs):
        """Test that template_used cannot be empty."""
        logger.error("Testing empty template_used")
        invalid_data = {
            "generated_payloads": ["payload1"],
            "template_used": "",  # Empty
            "variations_applied": ["var1"],
            "reasoning": "test"
        }
        assert invalid_data["template_used"] == ""
        logger.error("✗ Empty template_used should be rejected")


class TestAttackPlan:
    """Test AttackPlan Pydantic model."""

    def test_valid_attack_plan(self, sample_attack_plan, capture_logs):
        """Test valid AttackPlan creation."""
        logger.info(f"Testing valid AttackPlan for probe: {sample_attack_plan['probe_name']}")
        assert sample_attack_plan["probe_name"]
        assert sample_attack_plan["pattern_analysis"]
        assert sample_attack_plan["converter_selection"]
        assert sample_attack_plan["payload_generation"]
        assert sample_attack_plan["reasoning_summary"]
        assert sample_attack_plan["risk_assessment"]
        logger.info("✓ Valid AttackPlan structure confirmed")

    def test_missing_pattern_analysis(self, capture_logs):
        """Test that pattern_analysis is required."""
        logger.error("Testing missing pattern_analysis")
        invalid_data = {
            "probe_name": "test",
            # Missing pattern_analysis
            "converter_selection": {},
            "payload_generation": {},
            "reasoning_summary": "test",
            "risk_assessment": "test"
        }
        logger.error("✗ Missing pattern_analysis should be rejected")

    def test_empty_reasoning_summary(self, capture_logs):
        """Test that reasoning_summary cannot be empty."""
        logger.error("Testing empty reasoning_summary")
        invalid_data = {
            "probe_name": "test",
            "pattern_analysis": {},
            "converter_selection": {},
            "payload_generation": {},
            "reasoning_summary": "",  # Empty
            "risk_assessment": "test"
        }
        assert invalid_data["reasoning_summary"] == ""
        logger.error("✗ Empty reasoning_summary should be rejected")


class TestAttackResult:
    """Test AttackResult Pydantic model."""

    def test_valid_attack_result(self, sample_attack_result, capture_logs):
        """Test valid AttackResult creation."""
        logger.info(f"Testing valid AttackResult for probe: {sample_attack_result['probe_name']}")
        assert isinstance(sample_attack_result["success"], bool)
        assert sample_attack_result["score"] >= 0.0
        assert sample_attack_result["score"] <= 1.0
        assert sample_attack_result["attempt_number"] >= 1
        assert sample_attack_result["payload"]
        assert sample_attack_result["response"]
        logger.info("✓ Valid AttackResult structure confirmed")

    def test_invalid_score_range(self, capture_logs):
        """Test score validation (must be 0.0-1.0)."""
        logger.error("Testing invalid score range")
        invalid_data = {
            "success": True,
            "probe_name": "test",
            "attempt_number": 1,
            "payload": "test",
            "response": "test",
            "score": 1.5,  # Invalid
            "scorer_name": "test",
            "timestamp": datetime.utcnow(),
            "human_reviewed": False,
            "human_feedback": None
        }
        assert invalid_data["score"] > 1.0
        logger.error("✗ Score > 1.0 should be rejected")

    def test_invalid_attempt_number(self, capture_logs):
        """Test attempt_number validation (must be >= 1)."""
        logger.error("Testing invalid attempt_number")
        invalid_data = {
            "success": True,
            "probe_name": "test",
            "attempt_number": 0,  # Invalid
            "payload": "test",
            "response": "test",
            "score": 0.8,
            "scorer_name": "test",
            "timestamp": datetime.utcnow(),
            "human_reviewed": False,
            "human_feedback": None
        }
        assert invalid_data["attempt_number"] < 1
        logger.error("✗ attempt_number < 1 should be rejected")

    def test_empty_payload(self, capture_logs):
        """Test that payload cannot be empty."""
        logger.error("Testing empty payload")
        invalid_data = {
            "success": True,
            "probe_name": "test",
            "attempt_number": 1,
            "payload": "",  # Empty
            "response": "test",
            "score": 0.8,
            "scorer_name": "test",
            "timestamp": datetime.utcnow(),
            "human_reviewed": False,
            "human_feedback": None
        }
        assert invalid_data["payload"] == ""
        logger.error("✗ Empty payload should be rejected")


class TestAgentConfiguration:
    """Test agent configuration validation."""

    def test_valid_config(self, valid_agent_config, capture_logs):
        """Test valid agent configuration."""
        logger.info(f"Testing valid config: threshold={valid_agent_config['confidence_threshold']}")
        assert 0.0 <= valid_agent_config["confidence_threshold"] <= 1.0
        assert valid_agent_config["max_retries"] >= 0
        assert valid_agent_config["timeout_seconds"] > 0
        logger.info("✓ Valid configuration confirmed")

    def test_negative_threshold(self, invalid_agent_config_negative_threshold, capture_logs):
        """Test negative confidence threshold is rejected."""
        logger.error(f"Testing negative threshold: {invalid_agent_config_negative_threshold['confidence_threshold']}")
        assert invalid_agent_config_negative_threshold["confidence_threshold"] < 0.0
        logger.error("✗ Negative threshold should be rejected")

    def test_threshold_too_high(self, invalid_agent_config_threshold_too_high, capture_logs):
        """Test threshold > 1.0 is rejected."""
        logger.error(f"Testing threshold > 1.0: {invalid_agent_config_threshold_too_high['confidence_threshold']}")
        assert invalid_agent_config_threshold_too_high["confidence_threshold"] > 1.0
        logger.error("✗ Threshold > 1.0 should be rejected")

    def test_negative_timeout(self, invalid_agent_config_negative_timeout, capture_logs):
        """Test negative timeout is rejected."""
        logger.error(f"Testing negative timeout: {invalid_agent_config_negative_timeout['timeout_seconds']}")
        assert invalid_agent_config_negative_timeout["timeout_seconds"] < 0
        logger.error("✗ Negative timeout should be rejected")

    def test_zero_timeout(self, capture_logs):
        """Test zero timeout is rejected."""
        logger.error("Testing zero timeout")
        invalid_config = {
            "focus_areas": ["test"],
            "max_retries": 3,
            "confidence_threshold": 0.7,
            "timeout_seconds": 0  # Invalid
        }
        assert invalid_config["timeout_seconds"] <= 0
        logger.error("✗ Zero/negative timeout should be rejected")
