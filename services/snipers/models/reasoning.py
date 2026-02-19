"""Agent reasoning and scoring output models."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PatternAnalysis(BaseModel):
    """Structured output from agent's pattern learning step."""
    common_prompt_structure: str = Field(
        ..., description="Identified common prompt pattern across examples"
    )
    payload_encoding_type: str = Field(
        ..., description="Encoding/transformation used in successful attacks"
    )
    success_indicators: List[str] = Field(
        ..., description="Output patterns that indicate successful exploitation"
    )
    reasoning_steps: List[str] = Field(
        ..., description="Chain of Thought reasoning steps"
    )
    step_back_analysis: str = Field(
        ..., description="High-level step-back analysis of the vulnerability"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in pattern analysis"
    )


class ConverterSelection(BaseModel):
    """Structured output from agent's converter selection step."""
    selected_converters: List[str] = Field(
        ..., description="PyRIT converter names selected for attack"
    )
    reasoning: str = Field(..., description="Why these converters were chosen")
    step_back_analysis: str = Field(
        ..., description="High-level analysis before converter selection"
    )
    cot_steps: List[str] = Field(
        ..., description="Chain of thought reasoning steps"
    )


class PayloadGeneration(BaseModel):
    """Structured output from agent's payload generation step."""
    generated_payloads: List[str] = Field(
        ..., min_length=1, description="Generated attack payloads"
    )
    template_used: str = Field(
        ..., description="Template structure applied to generate payloads"
    )
    variations_applied: List[str] = Field(
        ..., description="Variations from example patterns"
    )
    reasoning: str = Field(
        ..., description="Chain of Thought reasoning for payload generation"
    )


class ScoringResult(BaseModel):
    """Structured output from agent's attack scoring step."""
    success: bool = Field(..., description="Whether the attack was successful")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence score for success evaluation"
    )
    reasoning: str = Field(
        ..., description="Step-by-step explanation of why the attack succeeded or failed"
    )
    matched_indicators: List[str] = Field(
        ..., description="List of success indicators that matched in the response"
    )
    comparison_to_examples: str = Field(
        ..., description="How this response compares to the example successful outputs"
    )


class AttackPlan(BaseModel):
    """Complete attack plan presented to human for review/approval."""
    probe_name: str = Field(..., description="Probe being exploited")
    pattern_analysis: PatternAnalysis = Field(
        ..., description="Learned attack pattern"
    )
    converter_selection: ConverterSelection = Field(
        ..., description="Selected PyRIT converters"
    )
    payload_generation: PayloadGeneration = Field(
        ..., description="Generated attack payloads"
    )
    reasoning_summary: str = Field(
        ..., description="Agent's overall reasoning for the attack plan"
    )
    risk_assessment: str = Field(
        ..., description="Risk assessment of the planned attack"
    )


class HumanFeedback(BaseModel):
    """Human feedback on agent decisions."""
    approved: bool = Field(..., description="Whether human approved the action")
    feedback_text: Optional[str] = Field(
        None, description="Textual feedback from human"
    )
    modifications: Optional[Dict[str, Any]] = Field(
        None, description="Modifications requested by human"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of human feedback"
    )
