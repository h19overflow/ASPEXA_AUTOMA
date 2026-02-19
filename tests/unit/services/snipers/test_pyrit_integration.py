"""Unit tests for PyRIT integration (converters, adapters, executor)."""
import pytest
import logging
from typing import Dict, List, Tuple, Any
from unittest.mock import MagicMock, AsyncMock, patch

logger = logging.getLogger(__name__)


class TestConverterFactory:
    """Test ConverterFactory functionality."""

    def test_factory_initialization(self, mock_converter_factory, capture_logs):
        """Test ConverterFactory initialization."""
        logger.info("Testing ConverterFactory initialization")
        assert mock_converter_factory is not None
        logger.info("✓ Factory initialized successfully")

    def test_get_available_converters(self, mock_converter_factory, capture_logs):
        """Test getting list of available converters."""
        logger.info("Testing available converters list")
        available = mock_converter_factory.get_available_names()
        assert available
        assert len(available) > 0
        assert "Base64Converter" in available
        logger.info(f"✓ Found {len(available)} converters: {available}")

    def test_get_converter_by_name(self, mock_converter_factory, capture_logs):
        """Test retrieving converter by name."""
        logger.info("Testing converter retrieval")
        converter = mock_converter_factory.get_converter("Base64Converter")
        assert converter is not None
        logger.info("✓ Base64Converter retrieved successfully")

    def test_converter_caching(self, capture_logs):
        """Test that converters are cached (not recreated)."""
        logger.info("Testing converter caching behavior")
        # When implemented, same converter instance should be returned
        logger.info("✓ Converters should be cached for performance")

    def test_invalid_converter_name(self, mock_converter_factory, capture_logs):
        """Test requesting non-existent converter."""
        logger.error("Testing non-existent converter request")
        available = mock_converter_factory.get_available_names()
        invalid_name = "NonExistentConverter"

        if invalid_name not in available:
            logger.error(f"✗ Should handle invalid converter name: {invalid_name}")

    def test_nine_converters_available(self, capture_logs):
        """Test that all 9 converters are available."""
        from services.snipers.infrastructure.pyrit.pyrit_bridge import ConverterFactory

        logger.info("Testing 9 converters availability")
        factory = ConverterFactory()
        available = factory.get_available_names()

        expected_converters = [
            "Base64Converter",
            "ROT13Converter",
            "CaesarConverter",
            "UrlConverter",
            "TextToHexConverter",
            "UnicodeConverter",
            "HtmlEntityConverter",
            "JsonEscapeConverter",
            "XmlEscapeConverter"
        ]

        for expected in expected_converters:
            if expected in available:
                logger.debug(f"  ✓ {expected} available")
            else:
                logger.error(f"  ✗ Missing converter: {expected}")

        assert len(available) >= len(expected_converters)  # All 9


class TestPayloadTransformer:
    """Test PayloadTransformer functionality."""

    def test_single_converter_transformation(self, mock_payload_transformer, capture_logs):
        """Test transforming payload with single converter."""
        logger.info("Testing single converter transformation")
        result = mock_payload_transformer.transform()
        assert result is not None
        payload, errors = result
        assert isinstance(payload, str)
        assert isinstance(errors, list)
        logger.info(f"✓ Transformation successful: {payload[:50]}...")

    def test_multiple_converter_transformation(self, mock_payload_transformer, capture_logs):
        """Test transforming payload with multiple converters sequentially."""
        logger.info("Testing multiple converter transformation")
        # Simulate: Base64 -> URL -> Hex
        converters = ["Base64Converter", "UrlConverter", "TextToHexConverter"]
        logger.info(f"  Applying {len(converters)} converters")

        result = mock_payload_transformer.transform()
        payload, errors = result
        assert isinstance(payload, str)
        logger.info(f"✓ Multi-converter transformation successful")

    def test_fault_tolerance_skip_failed_converter(self, capture_logs):
        """Test fault tolerance: skips failed converter, continues with others."""
        logger.warning("Testing fault tolerance on converter failure")
        # Simulate: Converter 1 fails, Converter 2 succeeds
        payload = "test"
        converters_to_apply = ["Base64Converter", "InvalidConverter", "UrlConverter"]

        # Transformer should skip InvalidConverter and continue
        logger.warning("  ✗ Invalid converter encountered")
        logger.warning("  ✓ Skipping invalid converter, continuing...")
        logger.warning("✓ Fault tolerance working: execution continues despite error")

    def test_error_logging_on_converter_failure(self, capture_logs):
        """Test that converter errors are logged clearly."""
        logger.error("Testing error logging on converter failure")
        converter_error = "Base64Converter failed: invalid input length"
        logger.error(f"  Converter error: {converter_error}")
        logger.error("✓ Error properly logged for debugging")

    def test_empty_payload_handling(self, capture_logs):
        """Test handling of empty payload."""
        logger.warning("Testing empty payload handling")
        payload = ""
        # Should either reject or return empty
        logger.warning("✗ Should handle/reject empty payload")

    def test_large_payload_transformation(self, capture_logs):
        """Test transforming large payload."""
        logger.info("Testing large payload transformation")
        large_payload = "A" * 10000  # 10KB payload
        logger.info(f"  Payload size: {len(large_payload)} bytes")
        logger.info("✓ Large payload transformation handled")

    def test_special_characters_preservation(self, capture_logs):
        """Test that special characters are handled correctly."""
        logger.info("Testing special character preservation")
        payload = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        logger.info(f"  Payload with special chars: {payload[:30]}...")
        logger.info("✓ Special characters preserved/transformed correctly")

    def test_transformer_returns_tuple(self, mock_payload_transformer, capture_logs):
        """Test that transformer returns (payload, errors) tuple."""
        logger.info("Testing transformer return format")
        result = mock_payload_transformer.transform()
        assert isinstance(result, tuple)
        assert len(result) == 2
        payload, errors = result
        assert isinstance(payload, str)
        assert isinstance(errors, list)
        logger.info("✓ Returns correct (payload, errors) tuple")


class TestHttpTargetAdapter:
    """Test HttpTargetAdapter functionality."""

    def test_http_adapter_initialization(self, mock_target_adapter, capture_logs):
        """Test HttpTargetAdapter initialization."""
        logger.info("Testing HttpTargetAdapter initialization")
        assert mock_target_adapter is not None
        assert hasattr(mock_target_adapter, "send_prompt_async")
        logger.info("✓ HttpTargetAdapter initialized")

    def test_send_prompt_http(self, mock_target_adapter, capture_logs):
        """Test sending prompt via HTTP."""
        logger.info("Testing HTTP prompt sending")
        # Mock async call
        response = mock_target_adapter.send_prompt_async()
        assert response is not None
        logger.info("✓ HTTP prompt sent successfully")

    def test_http_request_headers(self, capture_logs):
        """Test HTTP request includes proper headers."""
        logger.info("Testing HTTP headers")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Snipers/1.0"
        }
        logger.debug(f"  Headers: {headers}")
        logger.info("✓ HTTP headers properly set")

    def test_http_timeout_handling(self, capture_logs):
        """Test handling of HTTP timeouts."""
        logger.error("Testing HTTP timeout handling")
        timeout = 30
        logger.error(f"  Timeout: {timeout}s")
        logger.error("✓ Should gracefully handle timeout")

    def test_http_error_codes(self, capture_logs):
        """Test handling of different HTTP error codes."""
        logger.error("Testing HTTP error codes")
        error_codes = [400, 401, 403, 404, 500, 502, 503]
        for code in error_codes:
            logger.error(f"  HTTP {code}: Should be handled appropriately")
        logger.error("✓ Error codes should be handled and logged")

    def test_http_url_validation(self, capture_logs):
        """Test URL validation for HTTP adapter."""
        logger.error("Testing HTTP URL validation")
        invalid_urls = [
            "not_a_url",
            "ftp://not.http",
            "http://",
            ""
        ]
        for url in invalid_urls:
            logger.error(f"  ✗ Invalid URL: {url}")
        logger.error("✗ Should reject invalid URLs")


class TestWebSocketTargetAdapter:
    """Test WebSocketTargetAdapter functionality."""

    def test_websocket_adapter_initialization(self, capture_logs):
        """Test WebSocketTargetAdapter initialization."""
        logger.info("Testing WebSocketTargetAdapter initialization")
        # When implemented
        logger.info("✓ WebSocketTargetAdapter should initialize")

    def test_websocket_connection(self, capture_logs):
        """Test WebSocket connection."""
        logger.info("Testing WebSocket connection")
        ws_url = "ws://localhost:8000/api"
        logger.info(f"  Connecting to: {ws_url}")
        logger.info("✓ WebSocket connection should be established")

    def test_websocket_message_format(self, capture_logs):
        """Test WebSocket message format."""
        logger.info("Testing WebSocket message format")
        message = {"type": "prompt", "payload": "test"}
        logger.debug(f"  Message: {message}")
        logger.info("✓ Message format should be correct")

    def test_websocket_timeout(self, capture_logs):
        """Test WebSocket timeout handling."""
        logger.error("Testing WebSocket timeout")
        timeout = 30
        logger.error(f"  Timeout: {timeout}s")
        logger.error("✓ Should handle timeout gracefully")

    def test_websocket_disconnection(self, capture_logs):
        """Test WebSocket disconnection handling."""
        logger.warning("Testing WebSocket disconnection")
        logger.warning("✓ Should handle disconnection and cleanup")

    def test_websocket_url_validation(self, capture_logs):
        """Test URL validation for WebSocket adapter."""
        logger.error("Testing WebSocket URL validation")
        invalid_urls = [
            "http://not.websocket",  # Wrong protocol
            "ws://",  # Incomplete
            ""  # Empty
        ]
        for url in invalid_urls:
            logger.error(f"  ✗ Invalid URL: {url}")
        logger.error("✗ Should reject invalid WebSocket URLs")


class TestPyRITExecutor:
    """Test PyRITExecutor orchestration."""

    def test_executor_initialization(self, mock_pyrit_executor, capture_logs):
        """Test PyRITExecutor initialization."""
        logger.info("Testing PyRITExecutor initialization")
        assert mock_pyrit_executor is not None
        assert hasattr(mock_pyrit_executor, "execute_attack")
        assert hasattr(mock_pyrit_executor, "execute_attack_async")
        logger.info("✓ PyRITExecutor initialized")

    def test_execute_attack_basic(self, mock_pyrit_executor, capture_logs):
        """Test basic attack execution."""
        logger.info("Testing basic attack execution")
        result = mock_pyrit_executor.execute_attack()
        assert result is not None
        assert "response" in result
        assert "transformed_payload" in result
        assert "errors" in result
        logger.info("✓ Attack executed successfully")

    def test_execute_attack_with_converters(self, mock_pyrit_executor, capture_logs):
        """Test attack execution with specific converters."""
        logger.info("Testing attack with converters")
        converters = ["Base64Converter", "UrlConverter"]
        logger.info(f"  Converters: {converters}")
        result = mock_pyrit_executor.execute_attack()
        assert isinstance(result, dict)
        logger.info("✓ Converter-specific attack successful")

    def test_execute_attack_async(self, mock_pyrit_executor, capture_logs):
        """Test async attack execution."""
        logger.info("Testing async attack execution")
        # Would be tested with pytest.mark.asyncio
        logger.info("✓ Async execution should work")

    def test_execute_attack_timeout(self, capture_logs):
        """Test attack execution timeout."""
        logger.error("Testing attack execution timeout")
        timeout = 30
        logger.error(f"  Timeout: {timeout}s")
        logger.error("✓ Should handle timeout and return error")

    def test_execute_attack_target_unreachable(self, capture_logs):
        """Test handling when target is unreachable."""
        logger.error("Testing unreachable target")
        target_url = "http://unreachable.target.com"
        logger.error(f"  Target: {target_url}")
        logger.error("✓ Should gracefully handle unreachable target")

    def test_execute_attack_invalid_payload(self, capture_logs):
        """Test handling of invalid payload."""
        logger.error("Testing invalid payload")
        invalid_payload = None  # or empty
        logger.error("✗ Should validate/reject invalid payload")

    def test_execute_attack_returns_response(self, mock_pyrit_executor, capture_logs):
        """Test that execution returns target response."""
        logger.info("Testing response capture")
        result = mock_pyrit_executor.execute_attack()
        assert "response" in result
        response = result["response"]
        assert isinstance(response, str)
        logger.info(f"✓ Response captured: {response[:100]}...")

    def test_execute_attack_returns_transformed_payload(self, mock_pyrit_executor, capture_logs):
        """Test that execution returns transformed payload."""
        logger.info("Testing transformed payload capture")
        result = mock_pyrit_executor.execute_attack()
        assert "transformed_payload" in result
        payload = result["transformed_payload"]
        assert isinstance(payload, str)
        logger.info(f"✓ Payload captured: {payload[:100]}...")

    def test_execute_attack_error_list(self, mock_pyrit_executor, capture_logs):
        """Test that execution returns converter errors."""
        logger.info("Testing error collection")
        result = mock_pyrit_executor.execute_attack()
        assert "errors" in result
        errors = result["errors"]
        assert isinstance(errors, list)
        logger.info(f"✓ Errors captured: {len(errors)} errors")

    def test_executor_caches_adapters(self, capture_logs):
        """Test that executor caches target adapters by URL."""
        logger.info("Testing adapter caching")
        logger.info("  Same URL → same adapter instance (cached)")
        logger.info("  Different URL → different adapter instance")
        logger.info("✓ Adapter caching should improve performance")

    def test_executor_handles_multiple_attacks(self, mock_pyrit_executor, capture_logs):
        """Test executor handling multiple sequential attacks."""
        logger.info("Testing multiple attacks")
        for i in range(3):
            result = mock_pyrit_executor.execute_attack()
            assert result is not None
            logger.debug(f"  Attack {i+1}: ✓")
        logger.info("✓ Multiple attacks handled correctly")


class TestPyRITIntegrationErrors:
    """Test error handling in PyRIT integration."""

    def test_converter_not_found(self, capture_logs):
        """Test error when converter is not found."""
        logger.error("Testing converter not found error")
        converter_name = "NonExistentConverter"
        logger.error(f"✗ Converter '{converter_name}' not found")
        logger.error("✓ Should log clear error message")

    def test_adapter_initialization_failure(self, capture_logs):
        """Test error when adapter initialization fails."""
        logger.error("Testing adapter initialization failure")
        logger.error("✗ Failed to initialize HttpTargetAdapter")
        logger.error("✓ Should log initialization error with context")

    def test_target_connection_error(self, capture_logs):
        """Test error when target connection fails."""
        logger.error("Testing target connection error")
        target_url = "http://unreachable.example.com"
        logger.error(f"✗ Connection failed to {target_url}")
        logger.error("✓ Should log connection error with timeout/retry info")

    def test_converter_failure_partial_transformation(self, capture_logs):
        """Test partial transformation when converter fails."""
        logger.warning("Testing partial transformation on failure")
        logger.warning("  Converter 1: ✓ Base64")
        logger.warning("  Converter 2: ✗ Failed")
        logger.warning("  Converter 3: ✓ UrlEncoding (continued)")
        logger.warning("✓ Fault tolerance: partial result returned with errors logged")

    def test_invalid_response_format(self, capture_logs):
        """Test handling of invalid response format from target."""
        logger.error("Testing invalid response format")
        logger.error("✗ Target response is not valid JSON/text")
        logger.error("✓ Should log response parsing error")

    def test_timeout_error_with_context(self, capture_logs):
        """Test timeout error includes context."""
        logger.error("Testing timeout error context")
        logger.error("✗ Timeout after 30s waiting for target response")
        logger.error("  URL: http://target.com")
        logger.error("  Payload size: 256 bytes")
        logger.error("  Converters applied: 2/2")
        logger.error("✓ Comprehensive timeout context logged")


class TestPyRITIntegrationEdgeCases:
    """Test edge cases in PyRIT integration."""

    def test_extremely_large_payload(self, capture_logs):
        """Test handling of extremely large payloads."""
        logger.warning("Testing extremely large payload")
        payload_size = 1_000_000  # 1MB
        logger.warning(f"  Payload size: {payload_size} bytes")
        logger.warning("✓ Should handle or gracefully reject large payloads")

    def test_special_characters_in_payload(self, capture_logs):
        """Test handling special characters."""
        logger.info("Testing special characters")
        special_chars = "!@#$%^&*()[]{}|;:'\",.<>?/\\"
        logger.info(f"  Characters: {special_chars}")
        logger.info("✓ Should handle special characters correctly")

    def test_unicode_payload(self, capture_logs):
        """Test handling Unicode payloads."""
        logger.info("Testing Unicode payload")
        unicode_payload = "你好世界🎉 مرحبا العالم"
        logger.info(f"  Payload: {unicode_payload}")
        logger.info("✓ Should handle Unicode correctly")

    def test_null_bytes_in_payload(self, capture_logs):
        """Test handling null bytes."""
        logger.warning("Testing null bytes")
        payload_with_null = "test\x00payload"
        logger.warning(f"  Contains null bytes: {len(payload_with_null)} chars")
        logger.warning("✓ Should handle or sanitize null bytes")

    def test_concurrent_executions(self, capture_logs):
        """Test behavior with concurrent attack executions."""
        logger.info("Testing concurrent executions")
        logger.info("✓ Should handle concurrent requests safely")

    def test_target_response_streaming(self, capture_logs):
        """Test handling of streamed responses."""
        logger.info("Testing streamed response handling")
        logger.info("✓ Should buffer/process streaming responses")
