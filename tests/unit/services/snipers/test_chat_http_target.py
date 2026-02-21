"""
Unit tests for ChatHTTPTarget adapter.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import json
import sys

# Mock PyRIT imports before importing ChatHTTPTarget
mock_pyrit_modules = {
    "pyrit": MagicMock(),
    "pyrit.prompt_target": MagicMock(),
    "pyrit.models": MagicMock(),
}

for module_name, mock_module in mock_pyrit_modules.items():
    sys.modules[module_name] = mock_module


class MockPromptTarget:
    def __init__(self):
        pass


sys.modules["pyrit.prompt_target"].PromptTarget = MockPromptTarget

from services.snipers.infrastructure.pyrit.http_targets import ChatHTTPTarget  # noqa: E402


class MockPromptRequestResponse:
    def __init__(self, request_pieces=None):
        self.request_pieces = request_pieces or []


class MockPromptRequestPiece:
    def __init__(self, converted_value=None, original_value=None):
        self.converted_value = converted_value
        self.original_value = original_value


sys.modules["pyrit.models"].PromptRequestResponse = MockPromptRequestResponse
sys.modules["pyrit.models"].PromptRequestPiece = MockPromptRequestPiece

PromptRequestResponse = MockPromptRequestResponse
PromptRequestPiece = MockPromptRequestPiece  # noqa: F841


def make_request(converted_value=None, original_value=None):
    piece = MagicMock()
    piece.converted_value = converted_value
    piece.original_value = original_value
    request = MagicMock()
    request.request_pieces = [piece]
    return request, piece


class TestChatHTTPTargetInit:
    def test_init_with_defaults(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com/api")
        assert target._endpoint_url == "http://example.com/api"
        assert target._prompt_template == '{"message": "{PROMPT}"}'
        assert target._response_path == "response"
        assert target._headers == {"Content-Type": "application/json"}
        assert target._timeout == 30

    def test_init_with_custom_template(self):
        template = '{"query": "{PROMPT}", "model": "gpt-4"}'
        target = ChatHTTPTarget(endpoint_url="http://example.com/api", prompt_template=template)
        assert target._prompt_template == template

    def test_init_with_custom_response_path(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com/api", response_path="data.result.text")
        assert target._response_path == "data.result.text"

    def test_init_with_custom_headers(self):
        headers = {"Content-Type": "application/json", "Authorization": "Bearer token123"}
        target = ChatHTTPTarget(endpoint_url="http://example.com/api", headers=headers)
        assert target._headers == headers

    def test_init_with_custom_timeout(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com/api", timeout=60)
        assert target._timeout == 60


class TestValidateRequest:
    def test_validate_request_valid(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com")
        request, _ = make_request(converted_value="test prompt")
        target._validate_request(prompt_request=request)

    def test_validate_request_with_original_value(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com")
        request, _ = make_request(converted_value=None, original_value="original prompt")
        target._validate_request(prompt_request=request)

    def test_validate_request_no_pieces(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com")
        request = MagicMock()
        request.request_pieces = []
        with pytest.raises(ValueError, match="No request pieces provided"):
            target._validate_request(prompt_request=request)

    def test_validate_request_piece_has_no_value(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com")
        request, _ = make_request(converted_value=None, original_value=None)
        with pytest.raises(ValueError, match="Request piece has no value"):
            target._validate_request(prompt_request=request)

    def test_validate_request_empty_converted_value(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com")
        request, _ = make_request(converted_value="", original_value=None)
        with pytest.raises(ValueError, match="Request piece has no value"):
            target._validate_request(prompt_request=request)


class TestEscapeJson:
    def test_escape_json_simple_text(self):
        assert ChatHTTPTarget._escape_json("hello world") == "hello world"

    def test_escape_json_double_quotes(self):
        assert ChatHTTPTarget._escape_json('He said "hello"') == 'He said \\"hello\\"'

    def test_escape_json_backslash(self):
        assert ChatHTTPTarget._escape_json("C:\\path\\to\\file") == "C:\\\\path\\\\to\\\\file"

    def test_escape_json_newline(self):
        assert ChatHTTPTarget._escape_json("line1\nline2") == "line1\\nline2"

    def test_escape_json_mixed_special_chars(self):
        result = ChatHTTPTarget._escape_json('Path: C:\\file\nText: "hello"')
        assert result == 'Path: C:\\\\file\\nText: \\"hello\\"'

    def test_escape_json_empty_string(self):
        assert ChatHTTPTarget._escape_json("") == ""

    def test_escape_json_unicode(self):
        assert ChatHTTPTarget._escape_json("Hello 世界 مرحبا") == "Hello 世界 مرحبا"


class TestExtractResponse:
    def test_extract_response_simple_path(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com", response_path="response")
        assert target._extract_response('{"response": "success"}') == "success"

    def test_extract_response_nested_path(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com", response_path="data.message")
        assert target._extract_response('{"data": {"message": "hello"}}') == "hello"

    def test_extract_response_invalid_json_returns_original(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com", response_path="response")
        assert target._extract_response("not valid json") == "not valid json"

    def test_extract_response_path_not_found_returns_original(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com", response_path="missing.path")
        raw = '{"response": "success"}'
        assert target._extract_response(raw) == raw


class TestSendPromptAsync:
    @pytest.mark.asyncio
    async def test_send_prompt_async_success(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com/api", response_path="response")
        request, piece = make_request(converted_value="test prompt")

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value='{"response": "success"}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await target.send_prompt_async(prompt_request=request)
            assert result == request
            assert piece.converted_value == "success"

    @pytest.mark.asyncio
    async def test_send_prompt_async_invalid_request_fails(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com/api")
        request = MagicMock()
        request.request_pieces = []
        with pytest.raises(ValueError, match="No request pieces provided"):
            await target.send_prompt_async(prompt_request=request)

    @pytest.mark.asyncio
    async def test_send_prompt_async_handles_http_error(self):
        target = ChatHTTPTarget(endpoint_url="http://example.com/api")
        request, _ = make_request(converted_value="test")

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(aiohttp.ClientError):
                await target.send_prompt_async(prompt_request=request)
