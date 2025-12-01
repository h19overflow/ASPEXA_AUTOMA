"""
Turn Logger.

Purpose: Log attack turns (payload + response) to JSON for analysis
Role: Persist turn data for debugging and observation
Dependencies: None (pure Python)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default output directory
DEFAULT_LOG_DIR = Path("logs/adaptive_attack")


class TurnLogger:
    """
    Logs attack turns to JSON file for observation.

    Each run creates a new timestamped file with all turns.
    """

    def __init__(self, log_dir: Path | str | None = None):
        """
        Initialize turn logger.

        Args:
            log_dir: Directory for log files (default: logs/adaptive_attack)
        """
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"turns_{timestamp}.json"

        self.turns: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {
            "started_at": datetime.now().isoformat(),
            "campaign_id": None,
            "target_url": None,
        }

    def set_metadata(self, campaign_id: str, target_url: str) -> None:
        """Set campaign metadata."""
        self.metadata["campaign_id"] = campaign_id
        self.metadata["target_url"] = target_url

    def log_turn(
        self,
        iteration: int,
        payload_index: int,
        payload_original: str,
        payload_converted: str,
        response: str,
        framing_type: str | None = None,
        converters: list[str] | None = None,
        scores: dict[str, float] | None = None,
        custom_framing: dict[str, str] | None = None,
    ) -> None:
        """
        Log a single attack turn.

        Args:
            iteration: Current iteration number
            payload_index: Index of payload within iteration
            payload_original: Original articulated payload
            payload_converted: Payload after converter chain
            response: Target's response
            framing_type: Framing strategy used
            converters: Converter chain applied
            scores: Scorer results (optional)
            custom_framing: LLM-generated custom framing (optional)
        """
        turn = {
            "iteration": iteration,
            "payload_index": payload_index,
            "timestamp": datetime.now().isoformat(),
            "framing_type": framing_type,
            "custom_framing": custom_framing,
            "converters": converters or [],
            "payload_original": payload_original,
            "payload_converted": payload_converted,
            "response": response,
            "scores": scores or {},
        }

        self.turns.append(turn)
        self._save()

        logger.debug(f"Logged turn: iteration={iteration}, payload={payload_index}")

    def log_adaptation(
        self,
        iteration: int,
        failure_cause: str,
        defense_analysis: dict[str, Any],
        strategy_reasoning: str,
        new_framing: str | dict | None,
        new_converters: list[str] | None,
        confidence: float,
    ) -> None:
        """
        Log adaptation decision.

        Args:
            iteration: Iteration that triggered adaptation
            failure_cause: Why adaptation was needed
            defense_analysis: Analysis of target defenses
            strategy_reasoning: LLM's reasoning
            new_framing: New framing (preset name or custom dict)
            new_converters: New converter chain
            confidence: LLM confidence in strategy
        """
        adaptation = {
            "type": "adaptation",
            "after_iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "failure_cause": failure_cause,
            "defense_analysis": defense_analysis,
            "strategy_reasoning": strategy_reasoning,
            "new_framing": new_framing,
            "new_converters": new_converters,
            "confidence": confidence,
        }

        self.turns.append(adaptation)
        self._save()

        logger.debug(f"Logged adaptation after iteration {iteration}")

    def log_result(
        self,
        is_successful: bool,
        total_iterations: int,
        best_score: float,
        best_iteration: int,
    ) -> None:
        """Log final result."""
        self.metadata["completed_at"] = datetime.now().isoformat()
        self.metadata["is_successful"] = is_successful
        self.metadata["total_iterations"] = total_iterations
        self.metadata["best_score"] = best_score
        self.metadata["best_iteration"] = best_iteration
        self._save()

        logger.info(f"Turn log saved to: {self.log_file}")

    def _save(self) -> None:
        """Save current state to JSON file."""
        data = {
            "metadata": self.metadata,
            "turns": self.turns,
        }

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Global instance for easy access
_global_logger: TurnLogger | None = None


def get_turn_logger() -> TurnLogger:
    """Get or create global turn logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = TurnLogger()
    return _global_logger


def reset_turn_logger() -> TurnLogger:
    """Reset global turn logger (creates new log file)."""
    global _global_logger
    _global_logger = TurnLogger()
    return _global_logger
