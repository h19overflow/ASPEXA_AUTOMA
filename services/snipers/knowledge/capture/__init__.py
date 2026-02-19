"""
Capture module for extracting episodes from attack state.

Provides the EpisodeCapturer class that extracts successful
bypass episodes from adaptive attack runs and stores them
for future learning. Uses LangChain v1 create_agent with
ToolStrategy for structured reasoning extraction.

Structure:
    - capturer_models.py: Pydantic models (ReasoningOutput, CaptureConfig)
    - capturer_prompt.py: System prompt for reasoning agent
    - episode_capturer.py: Main EpisodeCapturer class
"""

from .capturer_models import CaptureConfig, ReasoningOutput
from .capturer_prompt import REASONING_SYSTEM_PROMPT
from .episode_capturer import EpisodeCapturer, get_episode_capturer

__all__ = [
    # Models
    "CaptureConfig",
    "ReasoningOutput",
    # Prompt
    "REASONING_SYSTEM_PROMPT",
    # Main class
    "EpisodeCapturer",
    "get_episode_capturer",
]
