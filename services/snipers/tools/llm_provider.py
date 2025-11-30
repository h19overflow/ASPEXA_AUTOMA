"""
LLM Provider for Phase 3 & 4 exploit agent.

Provides factory functions for creating LLM agents using langchain.agents.create_agent
with google_genai:gemini-2.5-flash model.
"""

import logging
from typing import Any, Optional

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)

# Singleton instances for efficiency
_default_agent: Optional[Any] = None
_default_chat_model: Optional[Any] = None
_default_chat_target: Optional[Any] = None

from dotenv import load_dotenv
load_dotenv()


def get_default_agent(
    model_id: str = "google_genai:gemini-2.5-pro",
    temperature: float = 0.7,
    system_prompt: str = "You are an intelligent exploit agent. Analyze and respond accurately.",
) -> Any:
    """
    Get or create default LangChain agent.

    Uses singleton pattern to avoid recreating agent on each call.

    Args:
        model_id: LangChain model identifier
        temperature: Sampling temperature (0.0-1.0)
        system_prompt: System prompt for agent

    Returns:
        LangChain agent instance
    """
    global _default_agent

    if _default_agent is None:
        _default_agent = create_agent(
            model=model_id,
            system_prompt=system_prompt,
        )
        logger.info(f"Created default agent with model {model_id}")

    return _default_agent


def create_gemini_agent(
    model_id: str = "google_genai:gemini-2.5-flash",
    temperature: float = 0.7,
    tools: list[Any] | None = None,
    system_prompt: str | None = None,
) -> Any:
    """
    Create a new LangChain agent with specified configuration.

    Args:
        model_id: Model identifier (e.g., "google_genai:gemini-2.5-flash")
        temperature: Sampling temperature (0.0-1.0)
        tools: Optional list of tools for the agent
        system_prompt: Optional system prompt

    Returns:
        LangChain agent instance
    """
    if system_prompt is None:
        system_prompt = "You are an intelligent assistant."

    agent = create_agent(
        model=model_id,
        tools=tools or [],
        system_prompt=system_prompt,
    )

    logger.info(
        f"Created Gemini agent",
        extra={"model": model_id, "temperature": temperature},
    )

    return agent


def get_default_chat_model(
    model_id: str = "google_genai:gemini-2.5-flash",
    temperature: float = 0.7,
) -> Any:
    """
    Get or create default LLM chat model (without agent wrapping).

    Uses singleton pattern for efficiency.

    Args:
        model_id: LangChain model identifier
        temperature: Sampling temperature (0.0-1.0)

    Returns:
        Chat model instance
    """
    global _default_chat_model

    if _default_chat_model is None:
        _default_chat_model = init_chat_model(model_id, temperature=temperature)
        logger.info(f"Created default chat model with {model_id}")

    return _default_chat_model


def create_specialized_agent(
    purpose: str,
    temperature: float = 0.7,
    system_prompt: str | None = None,
) -> Any:
    """
    Create a specialized agent for a specific purpose.

    Args:
        purpose: Purpose of the agent (e.g., "pattern_analysis", "converter_selection")
        temperature: Sampling temperature (0.0-1.0)
        system_prompt: Optional system prompt (will be generated from purpose if not provided)

    Returns:
        LangChain agent instance
    """
    if system_prompt is None:
        system_prompt = f"You are an expert in {purpose}. Provide accurate, detailed analysis."

    agent = create_agent(
        model="google_genai:gemini-2.5-flash",
        system_prompt=system_prompt,
    )

    logger.info(
        f"Created specialized agent",
        extra={"purpose": purpose, "temperature": temperature},
    )

    return agent


def get_chat_target(
    model_name: str = "gemini-2.0-flash",
    temperature: float = 0.7,
) -> Any:
    """
    Get or create PyRIT-compatible chat target for scoring.

    Uses singleton pattern for efficiency.
    Ensures PyRIT is initialized before creating target.

    Args:
        model_name: Gemini model name
        temperature: Sampling temperature (0.0-1.0)

    Returns:
        GeminiChatTarget instance (PyRIT PromptChatTarget)
    """
    global _default_chat_target

    if _default_chat_target is None:
        # Ensure PyRIT is initialized
        from services.snipers.core.pyrit_init import init_pyrit
        init_pyrit()

        from libs.connectivity.adapters.gemini_chat_target import GeminiChatTarget

        _default_chat_target = GeminiChatTarget(
            model_name=model_name,
            temperature=temperature,
        )
        logger.info(f"Created default chat target with model {model_name}")

    return _default_chat_target
