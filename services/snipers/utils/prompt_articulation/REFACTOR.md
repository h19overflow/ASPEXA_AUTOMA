# Payload Generation Refactor

## Issue
Two conflicting payload generation prompts exist:

1. **`payload_generator.py`** - Has inline `PAYLOAD_GENERATION_TEMPLATE` (ChatPromptTemplate)
2. **`payload_generator_prompt.py`** - Has `PAYLOAD_GENERATION_SYSTEM_PROMPT` (detailed system prompt)

The system prompt in `payload_generator_prompt.py` is the authoritative, comprehensive version designed for the LLM. It should be used instead of the template in `payload_generator.py`.

## Solution Required

**Update `payload_generator.py` to:**
1. Import from `payload_generator_prompt.py`:
   ```python
   from services.snipers.utils.prompt_articulation.components.payload_generator_prompt import (
       PAYLOAD_GENERATION_SYSTEM_PROMPT,
   )
   ```

2. Replace the inline `PAYLOAD_GENERATION_TEMPLATE` with the imported system prompt

3. Use `PAYLOAD_GENERATION_SYSTEM_PROMPT` when initializing the agent or building prompts

## Why
- **Single Source of Truth**: One comprehensive prompt definition, not two
- **Maintainability**: Update the prompt in one place (`payload_generator_prompt.py`)
- **Clarity**: System prompt is explicitly separated from implementation

## Current State
- `payload_generator_prompt.py` ✅ Contains the full, detailed system prompt
- `payload_generator.py` ❌ Has duplicate/simpler template that should be removed
