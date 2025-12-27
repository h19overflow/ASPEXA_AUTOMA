# Plan: Documentation Revamp

This plan outlines the steps to upgrade the project documentation into a comprehensive guide for new contributors.

## Phase 1: Foundation & Audit
Audit all existing markdown files to identify outdated information and missing links.

- [x] Task: Audit root `README.md` and `docs/main.md` for accuracy
- [x] Task: Update project overview and high-level architecture description in `docs/main.md`

## Phase 2: Architecture & Diagrams
Create visual representations of the system using Mermaid.

- [x] Task: Create Mermaid system architecture diagram in `docs/code_base_structure.md`
- [x] Task: Create Mermaid sequence diagrams for Cartographer reconnaissance flow
- [x] Task: Create Mermaid flow diagrams for Swarm scanner and Sniper attack phases

## Phase 3: Technical Deep Dive & Linking
Ensure all technical docs link to actual code files and reflect the current tech stack.

- [x] Task: Update `docs/db_schema.md` with links to Pydantic models in `libs/persistence/scan_models.py`
- [x] Task: Update `docs/faststream_topics.md` (or relevant doc) to reflect current service communication
- [x] Task: Update `docs/data_contracts.md` with links to `libs/contracts/`

## Phase 4: Onboarding & Final Polish
Create the final guide for new developers.

- [x] Task: Create `docs/onboarding.md` (or update `README.md`) with a step-by-step setup and contribution guide
- [x] Task: Final project-wide link verification and typo check
