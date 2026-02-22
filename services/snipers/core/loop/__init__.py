"""Loop orchestration package for the adaptive attack loop.

Sub-packages:
- runner/      Main while-loop, per-phase runners, and mutable loop state
- adaptation/  LLM-powered strategy adaptation, failure evaluation, pause handling
- persistence/ S3 checkpoint save/load helpers
- events/      SSE event builders (shared across all sub-packages)
"""

from services.snipers.core.loop.adaptation.constants import ALL_SCORERS, FRAMING_TYPES
from services.snipers.core.loop.adaptation.evaluation import check_success, determine_failure_cause
from services.snipers.core.loop.events.builders import build_complete_event, make_event
from services.snipers.core.loop.persistence.checkpoints import save_checkpoint_events
from services.snipers.core.loop.runner.loop_runner import run_loop
from services.snipers.core.loop.runner.phase_runners import run_phase1, run_phase2, run_phase3
from services.snipers.core.loop.runner.state import LoopState, create_initial_checkpoint

__all__ = [
    "ALL_SCORERS",
    "FRAMING_TYPES",
    "LoopState",
    "build_complete_event",
    "check_success",
    "create_initial_checkpoint",
    "determine_failure_cause",
    "make_event",
    "run_loop",
    "run_phase1",
    "run_phase2",
    "run_phase3",
    "save_checkpoint_events",
]
