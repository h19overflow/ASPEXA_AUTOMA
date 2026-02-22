"""Loop runner sub-package.

- loop_runner.py    Main while-loop: Phase 1→2→3, evaluate, checkpoint, adapt
- phase_runners.py  Thin wrappers that call each phase class and return result + events
- state.py          LoopState (mutable per-run state) + initial checkpoint creation
"""
