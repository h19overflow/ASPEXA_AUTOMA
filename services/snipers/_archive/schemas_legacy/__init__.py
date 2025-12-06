"""
XML tag schemas for structured prompt generation.

Purpose: Export tag classes for building XML-tagged prompts
"""

from .prompt_tags import (
    IntelligenceTag,
    OutputFormatTag,
    TaggedPromptBuilder,
    TaskTag,
    ToolSignatureTag,
    XMLTagSchema,
)

__all__ = [
    "XMLTagSchema",
    "ToolSignatureTag",
    "IntelligenceTag",
    "TaskTag",
    "OutputFormatTag",
    "TaggedPromptBuilder",
]
