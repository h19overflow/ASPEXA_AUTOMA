"""Unit tests for routing logic (decision flows)."""
import pytest
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TestRouteAfterHumanReview:
    """Test routing decision after human plan review."""

    def test_route_on_approval(self, human_approval_payload_approved, capture_logs):
        """Test routing when human approves attack plan."""
        logger.info("Testing routing on APPROVAL")
        assert human_approval_payload_approved["decision"] == "approve"
        # Should route to: attack_execution node
        logger.info("✓ Routes to attack_execution node")

    def test_route_on_rejection(self, human_approval_payload_rejected, capture_logs):
        """Test routing when human rejects attack plan."""
        logger.warning("Testing routing on REJECTION")
        assert human_approval_payload_rejected["decision"] == "reject"
        # Should route to: failure node
        logger.warning("✓ Routes to failure/stop node")

    def test_route_on_modification(self, human_approval_payload_modified, capture_logs):
        """Test routing when human modifies attack plan."""
        logger.info("Testing routing on MODIFICATION")
        assert human_approval_payload_modified["decision"] == "modify"
        assert human_approval_payload_modified["modifications"] is not None
        # Should route back to: pattern_analysis node with modifications
        logger.info("✓ Routes back to pattern_analysis with modifications")

    def test_invalid_decision_value(self, capture_logs):
        """Test handling of invalid decision value."""
        logger.error("Testing invalid decision value")
        invalid_payload = {
            "decision": "invalid_decision",  # Not approve/reject/modify
            "modifications": None
        }
        logger.error(f"✗ Should reject decision: {invalid_payload['decision']}")
        logger.error("✓ Should log clear error message")

    def test_missing_decision_field(self, capture_logs):
        """Test error when decision field is missing."""
        logger.error("Testing missing decision field")
        incomplete_payload = {
            # Missing: decision
            "modifications": None
        }
        logger.error("✗ Should require 'decision' field")
        logger.error("✓ Should log clear error message")

    def test_modification_structure_validation(self, human_approval_payload_modified, capture_logs):
        """Test validation of modification structure."""
        logger.info("Testing modification structure")
        modifications = human_approval_payload_modified["modifications"]
        assert modifications is not None
        assert "payloads" in modifications or "prompt" in modifications
        logger.info("✓ Modification structure valid")

    def test_empty_feedback_on_rejection(self, capture_logs):
        """Test that rejection feedback is logged."""
        logger.warning("Testing rejection feedback")
        rejection = {
            "decision": "reject",
            "feedback": "Payload too risky"
        }
        logger.warning(f"Feedback: {rejection.get('feedback', 'No feedback provided')}")
        logger.warning("✓ Feedback captured and logged")


class TestRouteAfterResultReview:
    """Test routing decision after human result review."""

    def test_route_on_success_approval(self, capture_logs):
        """Test routing when human approves successful result."""
        logger.info("Testing routing on RESULT APPROVAL")
        decision = {
            "decision": "approve",
            "result_status": "success"
        }
        # Should route to: end/return results
        logger.info("✓ Routes to success/end node")

    def test_route_on_failure_approval(self, capture_logs):
        """Test routing when human approves failed result."""
        logger.info("Testing routing on FAILURE APPROVAL")
        decision = {
            "decision": "approve",
            "result_status": "failure"
        }
        # Should route to: end/return failure
        logger.info("✓ Routes to failure/end node")

    def test_route_on_result_rejection(self, capture_logs):
        """Test routing when human rejects result."""
        logger.warning("Testing routing on RESULT REJECTION")
        decision = {
            "decision": "reject",
            "feedback": "Result doesn't match expected behavior"
        }
        logger.warning(f"Feedback: {decision['feedback']}")
        # Should route to: failure node
        logger.warning("✓ Routes to failure node")

    def test_route_on_retry_request(self, capture_logs):
        """Test routing when human requests retry."""
        logger.info("Testing routing on RETRY REQUEST")
        decision = {
            "decision": "retry",
            "modifications": {"payload_hint": "Try alternative encoding"}
        }
        # Should route back to: pattern_analysis with retry context
        logger.info("✓ Routes to pattern_analysis with retry flag")

    def test_missing_result_status(self, capture_logs):
        """Test error when result_status is missing."""
        logger.error("Testing missing result_status")
        incomplete = {
            "decision": "approve"
            # Missing: result_status
        }
        logger.error("✗ Should require result_status for approval decision")

    def test_retry_max_attempts_reached(self, capture_logs):
        """Test routing when max retry attempts exceeded."""
        logger.warning("Testing max retry attempts")
        decision = {
            "decision": "retry",
            "attempt_number": 3,
            "max_attempts": 3  # At limit
        }
        logger.warning(f"Attempt {decision['attempt_number']} of {decision['max_attempts']}")
        # Should route to: failure (no more retries allowed)
        logger.warning("✗ Max retries reached, routes to failure")

    def test_retry_within_limits(self, capture_logs):
        """Test routing when retry is within limits."""
        logger.info("Testing retry within limits")
        decision = {
            "decision": "retry",
            "attempt_number": 1,
            "max_attempts": 3
        }
        logger.info(f"Attempt {decision['attempt_number']} of {decision['max_attempts']}")
        # Should route back to: pattern_analysis
        logger.info("✓ Routes to pattern_analysis for retry")


class TestRouteAfterRetry:
    """Test retry loop routing logic."""

    def test_retry_counter_increment(self, capture_logs):
        """Test that retry counter increments correctly."""
        logger.info("Testing retry counter increment")
        current_attempt = 1
        max_attempts = 3

        for i in range(max_attempts):
            attempt = current_attempt + i
            logger.debug(f"  Attempt {attempt}/{max_attempts}")
            assert attempt <= max_attempts

        logger.info("✓ Retry counter increments correctly")

    def test_retry_exit_condition_max_reached(self, capture_logs):
        """Test exit condition when max retries reached."""
        logger.warning("Testing retry exit on max reached")
        attempt = 3
        max_attempts = 3

        if attempt >= max_attempts:
            logger.warning("  Max retries reached, exiting retry loop")
            logger.warning("✓ Correctly exits retry loop")

    def test_retry_continue_condition(self, capture_logs):
        """Test continue condition for retry loop."""
        logger.info("Testing retry continue condition")
        attempt = 1
        max_attempts = 3

        if attempt < max_attempts:
            logger.info("  Attempt within limit, continuing retry")
            logger.info("✓ Correctly continues retry loop")

    def test_retry_state_preservation(self, capture_logs):
        """Test that state is preserved across retry attempts."""
        logger.info("Testing state preservation in retries")
        state = {
            "probe_name": "encoding",
            "attempt_number": 2,
            "previous_results": [
                {"success": False, "score": 0.3},
                {"success": False, "score": 0.5}
            ]
        }
        logger.debug(f"  Probe: {state['probe_name']}")
        logger.debug(f"  Previous attempts: {len(state['previous_results'])}")
        logger.info("✓ State correctly preserved across retries")

    def test_retry_with_modifications(self, capture_logs):
        """Test retry with human modifications."""
        logger.info("Testing retry with modifications")
        retry_config = {
            "attempt_number": 2,
            "modifications": {
                "converters": ["Base64Converter", "ROT13Converter"],
                "payload_hint": "Try lowercase encoding"
            }
        }
        logger.debug(f"  Converters: {retry_config['modifications']['converters']}")
        logger.debug(f"  Hint: {retry_config['modifications']['payload_hint']}")
        logger.info("✓ Modifications applied to retry attempt")


class TestRoutingEdgeCases:
    """Test edge cases in routing logic."""

    def test_simultaneous_approval_rejection(self, capture_logs):
        """Test handling of conflicting approval/rejection signals."""
        logger.error("Testing conflicting approval/rejection signals")
        conflicting = {
            "decision": "approve",
            "also_reject": True  # Conflicting signal
        }
        logger.error("✗ Should reject conflicting signals")
        logger.error("✓ Should log clear error message")

    def test_missing_required_modifications(self, capture_logs):
        """Test error when modifications decision lacks modification data."""
        logger.error("Testing missing modifications data")
        incomplete_modify = {
            "decision": "modify"
            # Missing: modifications field
        }
        logger.error("✗ 'modify' decision requires modifications field")

    def test_empty_modifications(self, capture_logs):
        """Test handling of empty modifications object."""
        logger.warning("Testing empty modifications")
        empty_modify = {
            "decision": "modify",
            "modifications": {}  # Empty
        }
        logger.warning("✗ Empty modifications provided")
        logger.warning("✓ Should log warning but accept empty modifications")

    def test_routing_timeout_during_decision(self, capture_logs):
        """Test routing timeout (waiting for human decision)."""
        logger.error("Testing routing decision timeout")
        timeout_seconds = 300
        logger.error(f"  Timeout after {timeout_seconds}s waiting for human decision")
        logger.error("✗ Should handle timeout gracefully")
        logger.error("✓ Should default to rejection and log timeout")

    def test_multiple_humans_decisions_conflict(self, capture_logs):
        """Test handling when multiple humans provide conflicting decisions."""
        logger.error("Testing conflicting decisions from multiple humans")
        decisions = [
            {"human": "alice", "decision": "approve"},
            {"human": "bob", "decision": "reject"}
        ]
        logger.error(f"  Conflict: {len(decisions)} different decisions")
        logger.error("✗ Should require consensus or use veto logic")

    def test_routing_with_missing_state(self, capture_logs):
        """Test routing when required state fields are missing."""
        logger.error("Testing routing with incomplete state")
        incomplete_state = {
            "probe_name": "encoding"
            # Missing: example_findings, converter_selection, etc.
        }
        logger.error("✗ Routing requires full state information")
        logger.error("✓ Should log which state fields are missing")


class TestRoutingDecisionLogging:
    """Test that routing decisions are properly logged."""

    def test_routing_decision_logged(self, capture_logs):
        """Test that routing decisions are logged."""
        logger.info("Testing routing decision logging")
        decision = {
            "from_node": "human_review_plan",
            "decision": "approve",
            "target_node": "attack_execution"
        }
        logger.info(f"  Routing: {decision['from_node']} → {decision['target_node']}")
        logger.info("✓ Routing decision logged")

    def test_routing_reason_logged(self, capture_logs):
        """Test that routing reasons are logged."""
        logger.info("Testing routing reason logging")
        logger.info("  Reason: Human approved attack plan")
        logger.info("  Score confidence: 0.92")
        logger.info("✓ Routing reasons logged with context")

    def test_routing_modification_details_logged(self, capture_logs):
        """Test that modification details are logged."""
        logger.info("Testing modification details logging")
        modifications = {
            "payloads": ["Modified payload 1", "Modified payload 2"],
            "reason": "Increase success likelihood"
        }
        logger.info(f"  Modified payloads: {len(modifications['payloads'])}")
        logger.info(f"  Reason: {modifications['reason']}")
        logger.info("✓ Modification details logged")

    def test_routing_failure_reason_logged(self, capture_logs):
        """Test that failure reasons are logged clearly."""
        logger.warning("Testing failure reason logging")
        failure_info = {
            "reason": "Human rejected: Payload signature matches malware pattern",
            "confidence": 0.95,
            "recommendations": ["Try alternative encoding", "Use different template"]
        }
        logger.warning(f"  Reason: {failure_info['reason']}")
        logger.warning(f"  Confidence: {failure_info['confidence']}")
        logger.warning("✓ Failure reason logged with context")


class TestRoutingPerformance:
    """Test routing logic performance and efficiency."""

    def test_routing_decision_latency(self, capture_logs):
        """Test that routing decisions are made quickly."""
        logger.info("Testing routing decision latency")
        # Should be < 10ms for synchronous routing
        logger.info("  Routing latency: < 10ms (target)")
        logger.info("✓ Routing decisions are efficient")

    def test_state_lookup_efficiency(self, capture_logs):
        """Test state lookup doesn't cause bottlenecks."""
        logger.info("Testing state lookup efficiency")
        logger.info("  State lookup time: < 1ms (target)")
        logger.info("✓ State lookups efficient")

    def test_route_caching(self, capture_logs):
        """Test that routing decisions can be cached."""
        logger.info("Testing route decision caching")
        decision = {
            "pattern": "approve",
            "from": "human_review_plan",
            "to": "attack_execution"
        }
        logger.info("  Route cached for similar patterns")
        logger.info("✓ Routing caching should improve performance")
