# Plan: Documentation Revamp

This plan outlines the steps to upgrade the project documentation into a comprehensive guide for new contributors.

## Phase 1: Foundation & Audit
Audit all existing markdown files to identify outdated information and missing links.

- [ ] Task: Audit root `README.md` and `docs/main.md` for accuracy
- [ ] Task: Update project overview and high-level architecture description in `docs/main.md`
- [ ] Task: Conductor - User Manual Verification 'Foundation & Audit' (Protocol in workflow.md)

## Phase 2: Architecture & Diagrams
Create visual representations of the system using Mermaid.

- [ ] Task: Create Mermaid system architecture diagram in `docs/code_base_structure.md`
- [ ] Task: Create Mermaid sequence diagrams for Cartographer reconnaissance flow
- [ ] Task: Create Mermaid flow diagrams for Swarm scanner and Sniper attack phases
- [ ] Task: Conductor - User Manual Verification 'Architecture & Diagrams' (Protocol in workflow.md)

## Phase 3: Technical Deep Dive & Linking
Ensure all technical docs link to actual code files and reflect the current tech stack.

- [ ] Task: Update `docs/db_schema.md` with links to Pydantic models in `libs/persistence/scan_models.py`
- [ ] Task: Update `docs/faststream_topics.md` (or relevant doc) to reflect current service communication
- [ ] Task: Update `docs/data_contracts.md` with links to `libs/contracts/`
- [ ] Task: Conductor - User Manual Verification 'Technical Deep Dive & Linking' (Protocol in workflow.md)

## Phase 4: Onboarding & Final Polish
Create the final guide for new developers.

- [ ] Task: Create `docs/onboarding.md` (or update `README.md`) with a step-by-step setup and contribution guide
- [ ] Task: Final project-wide link verification and typo check
- [ ] Task: Conductor - User Manual Verification 'Onboarding & Final Polish' (Protocol in workflow.md)
