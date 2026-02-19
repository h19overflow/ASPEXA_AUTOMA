"""
Local logger for bypass knowledge operations.

Purpose: Log all bypass knowledge operations to JSON files for review
Role: Enable observation of what the integration is doing before trusting it
Dependencies: Standard library (json, pathlib, datetime)

Output Structure:
    logs/bypass_knowledge/
    ├── queries/
    │   └── 2025-12-11_campaign-abc_query_001.json
    ├── captures/
    │   └── 2025-12-11_campaign-abc_capture_001.json
    └── injections/
        └── 2025-12-11_campaign-abc_inject_001.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BypassKnowledgeLogger:
    """
    Logs all bypass knowledge operations to JSON files for review.

    Creates timestamped JSON files in structured subdirectories,
    allowing easy review of what the integration is doing.
    """

    def __init__(self, log_dir: str = "logs/bypass_knowledge") -> None:
        """
        Initialize logger with directory structure.

        Args:
            log_dir: Base directory for log files
        """
        self._log_dir = Path(log_dir)
        self._query_dir = self._log_dir / "queries"
        self._capture_dir = self._log_dir / "captures"
        self._injection_dir = self._log_dir / "injections"

        # Create directories
        self._query_dir.mkdir(parents=True, exist_ok=True)
        self._capture_dir.mkdir(parents=True, exist_ok=True)
        self._injection_dir.mkdir(parents=True, exist_ok=True)

        # Counter for unique filenames within same second
        self._counter = 0

    def log_query(
        self,
        campaign_id: str,
        fingerprint: dict[str, Any],
        result: dict[str, Any],
        action_taken: str,
        context_injected: bool = False,
        prompt_context_preview: str = "",
    ) -> Path:
        """
        Log a historical knowledge query operation.

        Args:
            campaign_id: Campaign identifier
            fingerprint: DefenseFingerprint as dict
            result: HistoricalInsight as dict (empty if no results)
            action_taken: "queried_s3_vectors" or "log_only_mode"
            context_injected: Whether context was injected into prompts
            prompt_context_preview: Preview of injected context (first 500 chars)

        Returns:
            Path to the created log file
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "query",
            "campaign_id": campaign_id,
            "input": fingerprint,
            "output": result,
            "action_taken": action_taken,
            "context_injected": context_injected,
        }

        if prompt_context_preview:
            log_entry["prompt_context_preview"] = prompt_context_preview[:500]

        return self._write_log(self._query_dir, campaign_id, "query", log_entry)

    def log_capture(
        self,
        campaign_id: str,
        episode: dict[str, Any],
        stored: bool,
        reason: str = "",
    ) -> Path:
        """
        Log an episode capture operation.

        Args:
            campaign_id: Campaign identifier
            episode: BypassEpisode as dict
            stored: Whether episode was stored to S3 Vectors
            reason: Additional context (e.g., why capture was skipped)

        Returns:
            Path to the created log file
        """
        action = "captured_and_stored" if stored else "captured_logged_only"
        if not episode:
            action = "skipped"

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "capture",
            "campaign_id": campaign_id,
            "episode": episode,
            "action_taken": action,
            "stored_to_s3": stored,
        }

        if episode and episode.get("episode_id"):
            log_entry["vector_id"] = episode["episode_id"]

        if reason:
            log_entry["reason"] = reason

        return self._write_log(self._capture_dir, campaign_id, "capture", log_entry)

    def log_injection(
        self,
        campaign_id: str,
        context_text: str,
        applied: bool,
        confidence: float,
        reason: str = "",
    ) -> Path:
        """
        Log a prompt injection operation.

        Args:
            campaign_id: Campaign identifier
            context_text: The historical context that was (or would be) injected
            applied: Whether injection was actually applied
            confidence: Confidence score that triggered (or blocked) injection
            reason: Why injection was/wasn't applied

        Returns:
            Path to the created log file
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "injection",
            "campaign_id": campaign_id,
            "context_text": context_text,
            "applied": applied,
            "confidence": confidence,
        }

        if reason:
            log_entry["reason"] = reason

        return self._write_log(self._injection_dir, campaign_id, "inject", log_entry)

    def _write_log(
        self,
        directory: Path,
        campaign_id: str,
        operation: str,
        data: dict[str, Any],
    ) -> Path:
        """
        Write log entry to JSON file.

        Args:
            directory: Target directory
            campaign_id: Campaign identifier for filename
            operation: Operation type for filename
            data: Data to write

        Returns:
            Path to created file
        """
        # Generate filename: YYYY-MM-DD_campaign-id_operation_counter.json
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_campaign = campaign_id.replace("/", "-").replace("\\", "-")[:50]
        self._counter += 1

        filename = f"{date_str}_{safe_campaign}_{operation}_{self._counter:03d}.json"
        file_path = directory / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)

            logger.debug(f"Logged {operation} to {file_path}")
            return file_path

        except Exception as e:
            logger.warning(f"Failed to write log file {file_path}: {e}")
            # Return path even on failure for consistent interface
            return file_path


# === SINGLETON ===
_logger: BypassKnowledgeLogger | None = None


def get_bypass_logger(log_dir: str | None = None) -> BypassKnowledgeLogger:
    """
    Get or create singleton logger instance.

    Args:
        log_dir: Optional log directory (only used on first call)

    Returns:
        BypassKnowledgeLogger instance
    """
    global _logger
    if _logger is None:
        from services.snipers.knowledge.integration.config import get_config

        config = get_config()
        _logger = BypassKnowledgeLogger(log_dir or config.log_dir)

    return _logger


def reset_bypass_logger() -> None:
    """Clear singleton logger (useful for testing)."""
    global _logger
    _logger = None
