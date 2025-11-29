"""
Unit tests for PyRIT initialization module.

Tests:
- init_pyrit() idempotency
- init_pyrit() with persistent and in-memory modes
- get_adversarial_chat() returns PromptChatTarget (Gemini or OpenAI based on env)
- get_scoring_target() returns PromptChatTarget (Gemini or OpenAI based on env)
- get_memory() error when not initialized
- get_memory() success after initialization
- cleanup_pyrit() resets state
- cleanup_pyrit() handles errors gracefully
- _get_llm_provider() detects credentials correctly
"""
import pytest
from unittest.mock import MagicMock, patch, call
import logging
import os
import sys

# Mock PyRIT imports before importing services.snipers.core.pyrit_init
mock_pyrit_modules = {
    'pyrit': MagicMock(),
    'pyrit.common': MagicMock(),
    'pyrit.memory': MagicMock(),
    'pyrit.prompt_target': MagicMock(),
}

for module_name, mock_module in mock_pyrit_modules.items():
    sys.modules[module_name] = mock_module

logger = logging.getLogger(__name__)


class TestInitPyrit:
    """Test init_pyrit() function."""

    def test_init_pyrit_with_in_memory(self):
        """Test init_pyrit initializes with IN_MEMORY mode."""
        # Reset global state before test
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit") as mock_init:
            with patch("services.snipers.core.pyrit_init.IN_MEMORY", "IN_MEMORY"):
                pyrit_module.init_pyrit(persistent=False)

                mock_init.assert_called_once_with(memory_db_type="IN_MEMORY")
                assert pyrit_module._initialized is True

    def test_init_pyrit_with_persistent(self):
        """Test init_pyrit initializes with DUCK_DB mode."""
        # Reset global state before test
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit") as mock_init:
            with patch("services.snipers.core.pyrit_init.DUCK_DB", "DUCK_DB"):
                pyrit_module.init_pyrit(persistent=True)

                mock_init.assert_called_once_with(memory_db_type="DUCK_DB")
                assert pyrit_module._initialized is True

    def test_init_pyrit_idempotent_second_call(self):
        """Test init_pyrit is idempotent - second call doesn't reinitialize."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit") as mock_init:
            with patch("services.snipers.core.pyrit_init.IN_MEMORY", "IN_MEMORY"):
                # First call
                pyrit_module.init_pyrit(persistent=False)
                assert mock_init.call_count == 1

                # Second call - should not reinitialize
                pyrit_module.init_pyrit(persistent=False)
                assert mock_init.call_count == 1

    def test_init_pyrit_logs_initialization(self):
        """Test init_pyrit logs when initialized."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit"):
            with patch("services.snipers.core.pyrit_init.IN_MEMORY", "IN_MEMORY"):
                with patch("services.snipers.core.pyrit_init.logger") as mock_logger:
                    pyrit_module.init_pyrit(persistent=False)
                    mock_logger.info.assert_called()


class TestGetLLMProvider:
    """Test _get_llm_provider() function."""

    def test_provider_returns_gemini_when_google_key_set(self):
        """Test _get_llm_provider returns 'gemini' when GOOGLE_API_KEY is set."""
        from services.snipers.core.pyrit_init import _get_llm_provider

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False):
            result = _get_llm_provider()
            assert result == "gemini"

    def test_provider_returns_openai_when_openai_key_set(self):
        """Test _get_llm_provider returns 'openai' when OPENAI_API_KEY is set."""
        from services.snipers.core.pyrit_init import _get_llm_provider

        env = {"OPENAI_API_KEY": "test-key"}
        # Remove GOOGLE_API_KEY if present
        with patch.dict(os.environ, env, clear=False):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False):
                result = _get_llm_provider()
                assert result == "openai"

    def test_provider_prefers_gemini_over_openai(self):
        """Test _get_llm_provider prefers Gemini when both keys set."""
        from services.snipers.core.pyrit_init import _get_llm_provider

        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "google-key",
            "OPENAI_API_KEY": "openai-key"
        }, clear=False):
            result = _get_llm_provider()
            assert result == "gemini"

    def test_provider_raises_when_no_credentials(self):
        """Test _get_llm_provider raises ValueError when no credentials set."""
        from services.snipers.core.pyrit_init import _get_llm_provider

        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "OPENAI_CHAT_ENDPOINT": ""
        }, clear=False):
            with pytest.raises(ValueError, match="No LLM credentials found"):
                _get_llm_provider()


class TestGetAdversarialChat:
    """Test get_adversarial_chat() function."""

    def test_get_adversarial_chat_returns_target(self):
        """Test get_adversarial_chat returns a PromptChatTarget instance."""
        from services.snipers.core.pyrit_init import get_adversarial_chat

        # Mock GeminiChatTarget where it's imported in pyrit_init
        mock_gemini_class = MagicMock()
        mock_instance = MagicMock()
        mock_gemini_class.return_value = mock_instance

        with patch("services.snipers.core.pyrit_init._get_llm_provider", return_value="gemini"):
            with patch.dict("sys.modules", {"libs.connectivity.adapters": MagicMock(GeminiChatTarget=mock_gemini_class)}):
                result = get_adversarial_chat()

                assert result == mock_instance

    def test_get_adversarial_chat_uses_openai_when_provider_is_openai(self):
        """Test get_adversarial_chat returns OpenAIChatTarget when provider is OpenAI."""
        from services.snipers.core.pyrit_init import get_adversarial_chat

        with patch("services.snipers.core.pyrit_init._get_llm_provider", return_value="openai"):
            with patch("pyrit.prompt_target.OpenAIChatTarget") as mock_class:
                mock_instance = MagicMock()
                mock_class.return_value = mock_instance

                result = get_adversarial_chat()

                assert result == mock_instance
                mock_class.assert_called_once()

    def test_get_adversarial_chat_creates_new_instance_each_time(self):
        """Test get_adversarial_chat creates new instance on each call."""
        from services.snipers.core.pyrit_init import get_adversarial_chat

        mock_gemini_class = MagicMock()
        instance1 = MagicMock(name="instance1")
        instance2 = MagicMock(name="instance2")
        mock_gemini_class.side_effect = [instance1, instance2]

        with patch("services.snipers.core.pyrit_init._get_llm_provider", return_value="gemini"):
            with patch.dict("sys.modules", {"libs.connectivity.adapters": MagicMock(GeminiChatTarget=mock_gemini_class)}):
                chat1 = get_adversarial_chat()
                chat2 = get_adversarial_chat()

                assert chat1 is instance1
                assert chat2 is instance2
                assert mock_gemini_class.call_count == 2


class TestGetScoringTarget:
    """Test get_scoring_target() function."""

    def test_get_scoring_target_returns_target(self):
        """Test get_scoring_target returns a PromptChatTarget instance."""
        from services.snipers.core.pyrit_init import get_scoring_target

        mock_gemini_class = MagicMock()
        mock_instance = MagicMock()
        mock_gemini_class.return_value = mock_instance

        with patch("services.snipers.core.pyrit_init._get_llm_provider", return_value="gemini"):
            with patch.dict("sys.modules", {"libs.connectivity.adapters": MagicMock(GeminiChatTarget=mock_gemini_class)}):
                result = get_scoring_target()

                assert result == mock_instance

    def test_get_scoring_target_uses_openai_when_provider_is_openai(self):
        """Test get_scoring_target returns OpenAIChatTarget when provider is OpenAI."""
        from services.snipers.core.pyrit_init import get_scoring_target

        with patch("services.snipers.core.pyrit_init._get_llm_provider", return_value="openai"):
            with patch("pyrit.prompt_target.OpenAIChatTarget") as mock_class:
                mock_instance = MagicMock()
                mock_class.return_value = mock_instance

                result = get_scoring_target()

                assert result == mock_instance
                mock_class.assert_called_once()

    def test_get_scoring_target_creates_new_instance_each_time(self):
        """Test get_scoring_target creates new instance on each call."""
        from services.snipers.core.pyrit_init import get_scoring_target

        mock_gemini_class = MagicMock()
        instance1 = MagicMock(name="instance1")
        instance2 = MagicMock(name="instance2")
        mock_gemini_class.side_effect = [instance1, instance2]

        with patch("services.snipers.core.pyrit_init._get_llm_provider", return_value="gemini"):
            with patch.dict("sys.modules", {"libs.connectivity.adapters": MagicMock(GeminiChatTarget=mock_gemini_class)}):
                target1 = get_scoring_target()
                target2 = get_scoring_target()

                assert target1 is instance1
                assert target2 is instance2
                assert mock_gemini_class.call_count == 2


class TestGetMemory:
    """Test get_memory() function."""

    def test_get_memory_fails_when_not_initialized(self):
        """Test get_memory raises ValueError when PyRIT not initialized."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with pytest.raises(ValueError, match="PyRIT not initialized"):
            pyrit_module.get_memory()

    def test_get_memory_succeeds_after_initialization(self):
        """Test get_memory returns CentralMemory after init_pyrit."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = True

        mock_memory = MagicMock()
        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", return_value=mock_memory):
            result = pyrit_module.get_memory()

            assert result == mock_memory

    def test_get_memory_returns_same_instance(self):
        """Test get_memory returns CentralMemory singleton."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = True

        mock_memory = MagicMock()
        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", return_value=mock_memory):
            memory1 = pyrit_module.get_memory()
            memory2 = pyrit_module.get_memory()

            assert memory1 == memory2


class TestCleanupPyrit:
    """Test cleanup_pyrit() function."""

    def test_cleanup_pyrit_disposes_memory(self):
        """Test cleanup_pyrit calls dispose_engine on memory."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = True

        mock_memory = MagicMock()
        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", return_value=mock_memory):
            pyrit_module.cleanup_pyrit()

            mock_memory.dispose_engine.assert_called_once()

    def test_cleanup_pyrit_resets_initialized_flag(self):
        """Test cleanup_pyrit sets _initialized to False."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = True

        mock_memory = MagicMock()
        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", return_value=mock_memory):
            pyrit_module.cleanup_pyrit()

            assert pyrit_module._initialized is False

    def test_cleanup_pyrit_logs_on_success(self):
        """Test cleanup_pyrit logs when successful."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = True

        mock_memory = MagicMock()
        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", return_value=mock_memory):
            with patch("services.snipers.core.pyrit_init.logger") as mock_logger:
                pyrit_module.cleanup_pyrit()

                mock_logger.info.assert_called()

    def test_cleanup_pyrit_handles_memory_not_initialized(self):
        """Test cleanup_pyrit handles case where memory is not initialized."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = True

        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", side_effect=Exception("Memory not initialized")):
            with patch("services.snipers.core.pyrit_init.logger") as mock_logger:
                # Should not raise exception
                pyrit_module.cleanup_pyrit()

                mock_logger.warning.assert_called()

    def test_cleanup_pyrit_handles_dispose_error(self):
        """Test cleanup_pyrit handles errors during dispose gracefully."""
        import services.snipers.core.pyrit_init as pyrit_module
        original_initialized = pyrit_module._initialized
        pyrit_module._initialized = True

        mock_memory = MagicMock()
        mock_memory.dispose_engine.side_effect = Exception("Dispose error")

        with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance", return_value=mock_memory):
            with patch("services.snipers.core.pyrit_init.logger") as mock_logger:
                # Should not raise exception
                pyrit_module.cleanup_pyrit()

                # Verify warning was logged
                mock_logger.warning.assert_called()
                # Note: _initialized stays True on error (current implementation)
                # This is expected behavior to avoid silent failures

        # Clean up for other tests
        pyrit_module._initialized = original_initialized


class TestInitPyritIntegration:
    """Integration tests for PyRIT initialization workflow."""

    def test_init_then_get_memory_workflow(self):
        """Test init_pyrit -> get_memory workflow."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit"):
            with patch("services.snipers.core.pyrit_init.IN_MEMORY", "IN_MEMORY"):
                with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance") as mock_memory_factory:
                    mock_memory = MagicMock()
                    mock_memory_factory.return_value = mock_memory

                    # Initialize
                    pyrit_module.init_pyrit(persistent=False)

                    # Get memory - should succeed
                    result = pyrit_module.get_memory()
                    assert result == mock_memory

    def test_full_lifecycle_init_use_cleanup(self):
        """Test full lifecycle: init -> use -> cleanup."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit"):
            with patch("services.snipers.core.pyrit_init.IN_MEMORY", "IN_MEMORY"):
                with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance") as mock_memory_factory:
                    mock_memory = MagicMock()
                    mock_memory_factory.return_value = mock_memory

                    # Initialize
                    pyrit_module.init_pyrit(persistent=False)
                    assert pyrit_module._initialized is True

                    # Use memory
                    memory = pyrit_module.get_memory()
                    assert memory == mock_memory

                    # Cleanup
                    pyrit_module.cleanup_pyrit()
                    assert pyrit_module._initialized is False
                    mock_memory.dispose_engine.assert_called_once()

    def test_get_memory_after_cleanup_fails(self):
        """Test get_memory fails after cleanup."""
        import services.snipers.core.pyrit_init as pyrit_module
        pyrit_module._initialized = False

        with patch("services.snipers.core.pyrit_init.initialize_pyrit"):
            with patch("services.snipers.core.pyrit_init.IN_MEMORY", "IN_MEMORY"):
                with patch("services.snipers.core.pyrit_init.CentralMemory.get_memory_instance") as mock_memory_factory:
                    mock_memory = MagicMock()
                    mock_memory_factory.return_value = mock_memory

                    # Initialize
                    pyrit_module.init_pyrit(persistent=False)

                    # Cleanup
                    pyrit_module.cleanup_pyrit()

                    # Try to get memory - should fail
                    with pytest.raises(ValueError, match="PyRIT not initialized"):
                        pyrit_module.get_memory()
