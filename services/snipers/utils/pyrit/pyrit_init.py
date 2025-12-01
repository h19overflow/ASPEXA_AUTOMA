"""
PyRIT Initialization Module

Centralizes PyRIT memory and configuration setup.
Must be called before any PyRIT operations.

Supports both Google Gemini (via GOOGLE_API_KEY) and OpenAI (via OPENAI_API_KEY).
Gemini is preferred if GOOGLE_API_KEY is available.
"""
import logging
import os

from pyrit.common import IN_MEMORY, DUCK_DB, initialize_pyrit
from pyrit.memory import CentralMemory
from pyrit.prompt_target import PromptChatTarget

logger = logging.getLogger(__name__)

_initialized = False


def init_pyrit(persistent: bool = False) -> None:
    """
    Initialize PyRIT memory system.

    Args:
        persistent: If True, use DuckDB for persistence. Otherwise in-memory.
    """
    global _initialized
    if _initialized:
        return

    memory_type = DUCK_DB if persistent else IN_MEMORY
    initialize_pyrit(memory_db_type=memory_type)
    _initialized = True
    logger.info(f"PyRIT initialized with {memory_type} memory")


def _get_llm_provider() -> str:
    """
    Determine which LLM provider to use based on available credentials.

    Returns:
        'gemini' if GOOGLE_API_KEY is set, 'openai' otherwise

    Raises:
        ValueError: If no credentials are found
    """
    if os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    elif os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_CHAT_ENDPOINT"):
        return "openai"
    else:
        raise ValueError(
            "No LLM credentials found. Set either GOOGLE_API_KEY or OPENAI_API_KEY"
        )


def get_adversarial_chat() -> PromptChatTarget:
    """
    Get the adversarial LLM for attack generation.

    Uses Gemini if GOOGLE_API_KEY is set, otherwise OpenAI.

    Returns:
        PromptChatTarget configured for adversarial prompts
    """
    provider = _get_llm_provider()

    if provider == "gemini":
        from libs.connectivity.adapters import GeminiChatTarget
        logger.debug("Using GeminiChatTarget for adversarial chat")
        return GeminiChatTarget(
            model_name="gemini-2.0-flash",
            temperature=0.9,  # Higher temperature for creative attacks
        )
    else:
        from pyrit.prompt_target import OpenAIChatTarget
        logger.debug("Using OpenAIChatTarget for adversarial chat")
        return OpenAIChatTarget()


def get_scoring_target() -> PromptChatTarget:
    """
    Get LLM target for scoring responses.

    Uses Gemini if GOOGLE_API_KEY is set, otherwise OpenAI.

    Returns:
        PromptChatTarget configured for scoring
    """
    provider = _get_llm_provider()

    if provider == "gemini":
        from libs.connectivity.adapters import GeminiChatTarget
        logger.debug("Using GeminiChatTarget for scoring")
        return GeminiChatTarget(
            model_name="gemini-2.0-flash",
            temperature=0.3,  # Lower temperature for consistent scoring
        )
    else:
        from pyrit.prompt_target import OpenAIChatTarget
        logger.debug("Using OpenAIChatTarget for scoring")
        return OpenAIChatTarget()


def get_memory() -> CentralMemory:
    """
    Get PyRIT central memory instance.

    Returns:
        CentralMemory instance

    Raises:
        ValueError: If PyRIT not initialized
    """
    if not _initialized:
        raise ValueError("PyRIT not initialized. Call init_pyrit() first.")
    return CentralMemory.get_memory_instance()


def cleanup_pyrit() -> None:
    """Dispose of PyRIT memory engine."""
    global _initialized
    try:
        memory = CentralMemory.get_memory_instance()
        memory.dispose_engine()
        _initialized = False
        logger.info("PyRIT memory disposed")
    except Exception as e:
        logger.warning(f"PyRIT cleanup warning: {e}")
