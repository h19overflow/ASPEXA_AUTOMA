# Context Passing Analysis: Recon & Garak Data Flow

## Overview

This document analyzes how recon and garak intelligence flows through the sniper services, identifying where context is properly threaded and where critical gaps exist in the adaptive attack pipeline.

---

## 1. Data Source Loading

**File**: `utils/persistence/s3_adapter.py:69-116`

Both recon and garak are loaded together at the entry point:

```python
intel = {
    "recon": load_scan(ScanType.RECON, campaign.recon_scan_id),
    "garak": load_scan(ScanType.GARAK, campaign.garak_scan_id)
}
```

- Both sources are optional (campaign may have one or both)
- Returns dict with `'recon'` and `'garak'` keys
- No filtering or validation at load time

---

## 2. Campaign Intelligence Parsing

**File**: `utils/prompt_articulation/loaders/campaign_loader.py:70-109`

### GARAK Processing:
```python
garak_data = intel.get("garak", {})

# Extracts:
vulnerabilities = garak_data.get("vulnerabilities", [])
objective = self._build_objective(vulnerabilities)  # Attack goal
probe_name = vulnerabilities[0].get("detector", "unknown")  # Probe name
defense_patterns = self._infer_defense_patterns(vulnerabilities)  # Defense types
```

**Produces**: Attack objective + defense pattern types

### RECON Processing:
```python
recon_data = intel.get("recon", {})

# Basic extraction:
tools = self._extract_tools(recon_data)  # Just tool names (List[str])
recon_raw = recon_data  # Stored unprocessed for later extraction
```

**Produces**: Tool names list + raw recon data

### Output: `CampaignIntelligence`
```
├─ objective (from GARAK)
├─ tools (from RECON, names only)
├─ defense_patterns (from GARAK)
├─ vulnerabilities (from GARAK)
├─ recon_raw (raw RECON blueprint, unprocessed)
└─ probe_name (from GARAK)
```

---

## 3. Recon Intelligence Extraction

**File**: `utils/prompt_articulation/extractors/recon_extractor.py:24-110`

Deep extraction of raw recon data happens here:

```python
class ReconIntelligenceExtractor:
    def extract(recon_blueprint: dict) -> ReconIntelligence:
        # From intelligence.infrastructure:
        llm_model = recon_blueprint.get("intelligence", {}).get("infrastructure", {}).get("llm_model")
        database_type = ...
        rate_limiting = ...
        system_prompt_leak = ...

        # From intelligence.auth_structure → content filters
        content_filters = [filter names]

        # From intelligence.detected_tools → structured tool metadata
        tools = [ToolSignature(name, params, rules, examples, auth) for each tool]

        # From intelligence.system_prompt_leak
        system_prompt = ...

        # From target_self_description
        target_self_description = {}
```

### Output: `ReconIntelligence` Model
```
├─ tools: List[ToolSignature]          # Detailed tool metadata
├─ llm_model: str                      # Model family
├─ database_type: str                  # Vector DB if detected
├─ content_filters: List[str]          # Defense mechanisms
├─ system_prompt_leak: str             # Leaked system prompt
├─ target_self_description: dict       # Parsed self-description
└─ raw_intelligence: dict              # Original blueprint
```

**Critical**: This comprehensive extraction happens but must be explicitly invoked and threaded through the pipeline.

---

## 4. Mode 1: Full Attack (Non-Adaptive)

**File**: `entrypoint.py:101-200`

### Data Flow:
```
execute_full_attack(campaign_id)
  │
  ├─ Phase 1: PayloadArticulation.execute(campaign_id)
  │   ├─ CampaignLoader.load()
  │   │   ├─ Extract: garak_objective, probe_name, defense_patterns
  │   │   └─ Extract: tool names (basic)
  │   │
  │   ├─ ReconExtractor.extract(recon_raw)
  │   │   └─ Full extraction: tools, llm_model, filters, system_prompt, etc.
  │   │
  │   └─ PayloadGenerator.generate(context)
  │       ├─ Uses: garak_objective ✓
  │       ├─ Uses: recon_intelligence (IF XML-tagged prompts enabled)
  │       └─ Uses: recon_custom_framing (IF provided)
  │
  ├─ Phase 2: Conversion.execute(payloads)
  │   └─ No recon or garak context used
  │
  └─ Phase 3: AttackExecution.execute(payloads)
      └─ No recon or garak context used
```

### Context Usage in Full Attack:
- **GARAK**: ✓ Used to set attack goal
- **RECON**: ⚠️ Extracted but only used if XML-tagged prompts enabled
- **Gap**: Most detailed recon intelligence unused in standard execution

---

## 5. Mode 2: Adaptive Attack

**File**: `entrypoint.py:549-710`

### Per-Iteration Data Flow:

```
execute_adaptive_attack(campaign_id)
  │
  └─ Loop: for each iteration until success
      │
      ├─ adapt_node(adapt.py:47-214)
      │   │
      │   ├─ Input: phase1_result
      │   │   ├─ garak_objective ✓
      │   │   ├─ defense_patterns ✓
      │   │   └─ context_summary.recon_intelligence
      │   │       └─ ⚠️ Must be manually extracted from nested dict
      │   │
      │   ├─ FailureAnalyzerAgent.analyze() ❌ CRITICAL GAP
      │   │   ├─ Input: objective (GARAK only)
      │   │   ├─ Input: phase3_result (scoring results)
      │   │   ├─ Input: target_responses (model outputs)
      │   │   ├─ Input: tried_converters (failed chains)
      │   │   └─ MISSING: recon_intelligence
      │   │
      │   ├─ ChainDiscoveryAgent.generate() ❌ INHERITS GAP
      │   │   ├─ Input: chain_discovery_context
      │   │   │   └─ Created by FailureAnalyzer (has no recon)
      │   │   └─ MISSING: recon_intelligence (inherited)
      │   │
      │   └─ StrategyGenerator.generate() ✓ HAS RECON
      │       ├─ Input: recon_intelligence (in config dict)
      │       └─ Output: recon_custom_framing
      │
      ├─ articulate_node(articulation_phase.py)
      │   └─ Uses: custom_framing + recon_custom_framing from adapt_node
      │
      ├─ convert_node
      │   └─ Uses: selected converter chain from ChainDiscoveryAgent
      │
      ├─ execute_node
      │   └─ Runs attacks + scorers
      │
      └─ evaluate_node → determine success/failure → loop if needed
```

---

## 6. Critical Gap 1: FailureAnalyzerAgent

**File**: `adaptive_attack/components/failure_analyzer_agent.py:58-97`

### Function Signature:
```python
async def analyze(
    phase3_result: Any | None,
    failure_cause: str | None,
    target_responses: list[str],
    iteration_history: list[dict[str, Any]],
    tried_converters: list[list[str]],
    objective: str = "test security boundaries",  # ← GARAK only
    config: dict | None = None,  # ← NO recon context
) -> ChainDiscoveryContext:
```

### Where Called (adapt.py:142-160):
```python
failure_intelligence = await failure_analyzer.analyze(
    phase3_result=phase3_result,
    objective=objective,  # ← From GARAK
    target_responses=responses,
    iteration_history=iteration_history,
    tried_converters=tried_converters,
    config={"garak_objective": objective}  # ← Only GARAK objective
)
```

### Missing Context:
- ❌ Tool signatures from recon (can't explain tool validation failures)
- ❌ System prompt leak (can't adjust strategy based on target structure)
- ❌ Detected content filters (can't avoid blocked patterns)
- ❌ Rate limiting info (can't adjust payload timing)
- ❌ LLM model type (can't select encoding strategy)
- ❌ Detected defenses from garak analysis

### Impact:
Chain discovery becomes **reactive** instead of **intelligent**:
- Analyzes failure symptoms only
- Cannot correlate failure to specific tool/defense
- Cannot recommend tool-specific converters
- Must rely on generic failure patterns

---

## 7. Critical Gap 2: ChainDiscoveryAgent

**File**: `adaptive_attack/components/chain_discovery_agent.py`

### Where Called (adapt.py:161-190):
```python
chain_decision = await chain_agent.generate(
    context=chain_discovery_context,  # ← Came from FailureAnalyzer
    tried_converters=tried_converters,
    objective=objective,  # ← GARAK objective only
)
```

### Missing Context (Inherited from FailureAnalyzer):
- ❌ Tool information
- ❌ System prompt structure
- ❌ Detected defenses
- ❌ LLM capabilities/restrictions

### Impact:
Converter chain selection is **blind to target characteristics**:
- Cannot select chains based on tool parameter types
- Cannot avoid converters known to fail with detected defenses
- Cannot choose encoding that matches system prompt style
- Must select chains using only failure history

---

## 8. Proper Context Passing: StrategyGenerator

**File**: `adaptive_attack/components/strategy_generator.py:50-131`

### Where Called (adapt.py:195-210):
```python
config = {
    "recon_intelligence": recon_intelligence  # ✓ PASSED
}
decision = await generator.generate(
    responses=responses,
    ...
    config=config,  # ✓ HAS RECON
    objective=objective,
)
```

### Context Usage:
```python
async def generate(
    responses: list[str],
    config: dict = None,
):
    recon_intelligence = None
    if config:
        recon_intelligence = config.get("recon_intelligence")
        if recon_intelligence:
            logger.info("Recon intelligence available for strategy generation")

    user_prompt = build_adaptation_user_prompt(
        responses=responses,
        recon_intelligence=recon_intelligence,  # ✓ Used
    )
```

### Output:
```
AdaptationDecision:
├─ recon_custom_framing: dict  # LLM-generated framing from recon
└─ [other adaptation decisions]
```

**Proper model**: Context is passed, extracted, and used for decision-making.

---

## 9. Recon Extraction & Storage

**File**: `utils/prompt_articulation/articulation_phase.py:74-164`

### Where Recon is Extracted:
```python
async def execute(campaign_id: str):
    # Load campaign intel (recon + garak)
    intel = await loader.load(campaign_id)

    # FULL extraction happens here
    recon_intel = extractor.extract(intel.recon_raw)

    # Build context with extracted recon
    context = PayloadContext(
        target=TargetInfo(...),
        objective=intel.objective,
        recon_intelligence=recon_intel,  # ✓ Stored
        recon_custom_framing=recon_custom_framing
    )

    # Store in result
    phase1_result.context_summary = {
        "recon_intelligence": asdict(recon_intel)  # ✓ Stored in phase1
    }
```

### How it's Retrieved (adapt.py:120-135):
```python
# Must manually dig out from phase1_result
recon_intelligence = None
if phase1_result and hasattr(phase1_result, "context_summary"):
    context_summary = phase1_result.context_summary
    recon_intel_dict = context_summary.get("recon_intelligence")
    if recon_intel_dict:
        recon_intelligence = ReconIntelligence(**recon_intel_dict)
```

**Problem**: Manual extraction only happens for StrategyGenerator. Not done for FailureAnalyzer or ChainDiscovery.

---

## 10. Payload Generation Context

**File**: `utils/prompt_articulation/components/payload_generator.py:142-224`

### Where RECON is Used:
```python
async def generate(context: PayloadContext, ...):
    # Check for recon-based framing
    if use_tagged_prompts and context.recon_intelligence and context.recon_intelligence.tools:
        user_prompt = tagged_prompt_builder.build_tool_exploitation_prompt(
            objective=context.objective,
            recon_intel=context.recon_intelligence,  # ✓ RECON used
            framing_strategy=strategy.name,
        )

    # Check for recon custom framing from LLM
    if context.recon_custom_framing:
        role = context.recon_custom_framing.get("role")
        context = context.recon_custom_framing.get("context")
```

### Conditions for RECON Usage:
- XML-tagged prompts must be enabled
- Recon intelligence must have tool signatures
- OR recon_custom_framing must be provided by StrategyGenerator

**Gap**: RECON only used in payload generation if specific conditions met. Otherwise it's loaded but not utilized.

---

## Summary Table: Context by Component

| Component | GARAK Objective | GARAK Vulns | RECON Tools | RECON Defenses | RECON System Prompt | RECON LLM Model | Status |
|-----------|---|---|---|---|---|---|---|
| CampaignLoader | ✓ | ✓ | ✓ (names only) | ✗ | ✗ | ✗ | Initial extraction |
| ReconExtractor | — | — | ✓ (full) | ✓ | ✓ | ✓ | Deep extraction |
| ArticulationPhase | ✓ | ✗ | ✓ (if tagged) | ✗ | ✗ | ✗ | Conditional use |
| PayloadGenerator | ✓ | ✗ | ✓ (custom framing) | ✗ | ✗ | ✗ | Limited use |
| FailureAnalyzer | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | **MISSING** |
| ChainDiscovery | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | **MISSING (inherited)** |
| StrategyGenerator | ✓ | ✗ | ✓ (framing) | ✗ | ✗ | ✗ | Proper passing |
| Execution/Scoring | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | Not needed |

---

## Root Cause Analysis

### Design Problem:
The adaptive attack pipeline has **decision nodes** (FailureAnalyzer, ChainDiscovery) that must make intelligent choices but are designed as **context-blind**.

### Why This Matters:
These nodes determine:
1. **Why attacks failed** (failure analysis)
2. **Which converters to try next** (chain discovery)
3. **How to adapt strategy** (adaptation direction)

Without recon context, they can only:
- Observe that attacks failed
- Guess which converters might work
- Recommend generic adaptations

### What They Should Know:
- Tool structures that might require specific encoding
- System prompt style that might need matching framing
- Detected defenses that certain converters can't bypass
- LLM quirks that favor certain payload formats

---

## Fixing the Gap

### Solution: Thread Recon Through Decision Nodes

**Change 1**: Extract recon in adapt_node
```python
# In adapt.py, after line 120
recon_intelligence = None
if phase1_result and hasattr(phase1_result, "context_summary"):
    context_summary = phase1_result.context_summary
    recon_intel_dict = context_summary.get("recon_intelligence")
    if recon_intel_dict:
        recon_intelligence = ReconIntelligence(**recon_intel_dict)
```

**Change 2**: Pass recon to FailureAnalyzer
```python
# In adapt.py, around line 142
failure_intelligence = await failure_analyzer.analyze(
    phase3_result=phase3_result,
    objective=objective,
    target_responses=responses,
    iteration_history=iteration_history,
    tried_converters=tried_converters,
    recon_intelligence=recon_intelligence,  # ← ADD THIS
    config={"garak_objective": objective}
)
```

**Change 3**: Update FailureAnalyzerAgent signature
```python
# In failure_analyzer_agent.py
async def analyze(
    phase3_result: Any | None,
    failure_cause: str | None,
    target_responses: list[str],
    iteration_history: list[dict[str, Any]],
    tried_converters: list[list[str]],
    objective: str = "test security boundaries",
    recon_intelligence: ReconIntelligence | None = None,  # ← ADD THIS
    config: dict | None = None,
) -> ChainDiscoveryContext:
```

**Change 4**: Use recon in failure analysis
```python
# In failure_analyzer_agent.py, incorporate recon in prompt
user_prompt = build_failure_analysis_prompt(
    responses=target_responses,
    objective=objective,
    recon_intelligence=recon_intelligence,  # ← Use this
    tried_converters=tried_converters,
)
```

---

## Current State Summary

✓ **Working properly:**
- GARAK data flows to decision nodes (objective)
- RECON is fully extracted (ReconExtractor)
- StrategyGenerator receives and uses recon for framing

❌ **Broken/Missing:**
- FailureAnalyzerAgent receives no recon data
- ChainDiscoveryAgent inherits no recon data
- Decision making is context-blind regarding tool/defense specifics

⚠️ **Conditional:**
- RECON in payload generation (only if XML-tagged enabled)
- GARAK vulnerabilities not used after objective extraction

---

## Files Involved

- `utils/persistence/s3_adapter.py` - Data loading
- `utils/prompt_articulation/loaders/campaign_loader.py` - Campaign intel parsing
- `utils/prompt_articulation/extractors/recon_extractor.py` - Deep recon extraction
- `utils/prompt_articulation/articulation_phase.py` - Phase 1 execution
- `utils/prompt_articulation/components/payload_generator.py` - Payload generation
- `adaptive_attack/nodes/adapt.py` - Orchestration of adaptation
- `adaptive_attack/components/failure_analyzer_agent.py` - **NEEDS FIX**
- `adaptive_attack/components/chain_discovery_agent.py` - **NEEDS FIX (inherited)**
- `adaptive_attack/components/strategy_generator.py` - Proper model
- `entrypoint.py` - Attack mode selection
- `attack_phases/attack_execution.py` - Phase 3 execution
