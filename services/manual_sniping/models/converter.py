"""Converter chain models for payload transformation.

Defines data structures for transformation steps and results.
Dependencies: pydantic
System role: Models for converter chain tracking
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TransformStep(BaseModel):
    """Single step in a transformation chain.

    Captures input/output of one converter application.
    """

    converter_name: str
    input_payload: str
    output_payload: str
    success: bool = True
    error: Optional[str] = None


class TransformResult(BaseModel):
    """Complete transformation result with all steps.

    Tracks entire chain execution with success/failure details.
    """

    original_payload: str
    final_payload: str
    steps: List[TransformStep]
    total_converters: int
    successful_converters: int
    errors: List[str] = Field(default_factory=list)


class ConverterInfo(BaseModel):
    """Converter metadata for UI display.

    Provides human-readable information about available converters.
    """

    name: str
    display_name: str
    description: str
    category: str  # "encoding", "obfuscation", "escape"
    example_input: str
    example_output: str


class ConverterChainConfig(BaseModel):
    """User-defined converter chain configuration.

    Allows users to save and reuse favorite converter combinations.
    """

    chain_id: Optional[str] = None
    name: Optional[str] = None  # User-friendly name
    converters: List[str]  # Ordered list of converter names
    is_favorite: bool = False
