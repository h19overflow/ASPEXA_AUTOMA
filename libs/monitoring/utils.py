"""Utility functions for Langfuse monitoring initialization.

Provides helper functions to create callback handlers with proper configuration.

Dependencies:
- langfuse.callback: CallbackHandler
- libs.config: Settings management

System Role:
Simplifies initialization of Langfuse handlers with environment-based config.
"""

from typing import Optional

from langfuse.langchain import CallbackHandler

from libs.config import get_settings


def create_langfuse_handler() -> Optional[CallbackHandler]:
    """Create a Langfuse callback handler if monitoring is enabled.

    Automatically reads Langfuse credentials from environment variables:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_HOST (optional, defaults to https://cloud.langfuse.com)

    Args:
        session_id: Optional session identifier for grouping traces
        user_id: Optional user identifier for trace attribution
        trace_name: Optional name for the trace

    Returns:
        CallbackHandler instance if monitoring is enabled, None otherwise

    Example:
        >>> handler = create_langfuse_handler(
        ...     session_id="exploit-campaign-001",
        ...     trace_name="pattern-analysis"
        ... )
        >>> llm.invoke(prompt, config={"callbacks": [handler]})
    """
    settings = get_settings()

    if not settings.langfuse_enabled:
        return None

    # CallbackHandler automatically reads LANGFUSE_* env vars
    handler = CallbackHandler()

    return handler


def get_callbacks_config() -> dict:
    """Get LangChain config dict with Langfuse callback handler.

    Convenience function that returns a config dict ready to pass to
    LangChain invoke/stream/batch methods.

    Args:
        session_id: Optional session identifier for grouping traces
        user_id: Optional user identifier for trace attribution
        trace_name: Optional name for the trace

    Returns:
        Config dict with callbacks list (empty if monitoring disabled)

    Example:
        >>> config = get_callbacks_config(trace_name="payload-generation")
        >>> llm.invoke(prompt, config=config)
    """
    handler = create_langfuse_handler()

    if handler is None:
        return {"callbacks": []}

    return {"callbacks": [handler]}
