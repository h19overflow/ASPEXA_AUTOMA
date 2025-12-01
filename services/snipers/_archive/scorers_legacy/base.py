"""
Base Scorer Interface

Defines the abstract base class for all scorers.
"""
from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel


class ScoreResult(BaseModel):
    """Result from a scorer evaluation."""
    success: bool
    score: float  # 0.0 to 1.0
    matched_patterns: List[str]
    reasoning: str


class BaseScorer(ABC):
    """Abstract base class for all scorers."""

    @abstractmethod
    def score(self, response: str, success_indicators: List[str]) -> ScoreResult:
        """
        Score a response against success indicators.

        Args:
            response: Target response to evaluate
            success_indicators: List of patterns indicating success

        Returns:
            ScoreResult with success determination and confidence
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Scorer name for identification."""
        pass
