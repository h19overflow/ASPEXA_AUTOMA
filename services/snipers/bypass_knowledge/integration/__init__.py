"""
Integration module for bypass knowledge VDB.

Purpose: Connect bypass knowledge to the adaptive attack system
Role: Provide non-invasive hooks for adapt_node and evaluate_node
Dependencies: Phase 5 (Capture), Phase 6 (Query)

Provides:
    - AdaptNodeHook: Query historical knowledge before strategy generation
    - EvaluateNodeHook: Capture successful episodes after evaluation
    - BypassKnowledgeConfig: Feature flags and settings
    - BypassKnowledgeLogger: Local JSON logging for review

Feature Flags (environment variables):
    - BYPASS_KNOWLEDGE_ENABLED: Master switch (default: true)
    - BYPASS_KNOWLEDGE_LOG_ONLY: Only log, no S3 ops (default: false)
    - BYPASS_KNOWLEDGE_INJECT_CONTEXT: Inject history into prompts (default: true)

Usage in adapt_node:
    from services.snipers.bypass_knowledge.integration import get_adapt_hook
    history_context = await get_adapt_hook().query_history(dict(state))

Usage in evaluate_node:
    from services.snipers.bypass_knowledge.integration import get_evaluate_hook
    capture_result = await get_evaluate_hook().maybe_capture(dict(state))
"""

from .config import (
    BypassKnowledgeConfig,
    get_config,
    reset_config,
)
from .models import (
    HistoryContext,
    CaptureResult,
)
from .local_logger import (
    BypassKnowledgeLogger,
    get_bypass_logger,
    reset_bypass_logger,
)
from .adapt_hook import (
    AdaptNodeHook,
    get_adapt_hook,
    reset_adapt_hook,
)
from .evaluate_hook import (
    EvaluateNodeHook,
    get_evaluate_hook,
    reset_evaluate_hook,
)

__all__ = [
    # Config
    "BypassKnowledgeConfig",
    "get_config",
    "reset_config",
    # Models
    "HistoryContext",
    "CaptureResult",
    # Logger
    "BypassKnowledgeLogger",
    "get_bypass_logger",
    "reset_bypass_logger",
    # Adapt hook
    "AdaptNodeHook",
    "get_adapt_hook",
    "reset_adapt_hook",
    # Evaluate hook
    "EvaluateNodeHook",
    "get_evaluate_hook",
    "reset_evaluate_hook",
]
