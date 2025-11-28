"""Langfuse monitoring integration for AI agent observability.

Provides two core functionalities:
1. CallbackHandler - LangChain callback handler for tracing LLM/agent calls
2. observe - Decorator for tracking function inputs/outputs

Dependencies:
- langfuse: Core SDK for observability
- libs.config: Environment configuration

System Role:
Thin wrapper over Langfuse SDK to provide observability for Cartographer
and Snipers AI agents with minimal code changes.

Usage:
    # Pattern 1: Callback Handler for LangChain
    from libs.monitoring import CallbackHandler
    handler = CallbackHandler()
    llm.invoke(prompt, config={"callbacks": [handler]})

    # Pattern 2: Function Decorator
    from libs.monitoring import observe
    @observe()
    def my_function(param):
        return result
"""
from langfuse.langchain import CallbackHandler
from langfuse import observe
from libs.monitoring.utils import create_langfuse_handler, get_callbacks_config

__all__ = [
    "CallbackHandler",
    "observe",
    "create_langfuse_handler",
    "get_callbacks_config",
]
