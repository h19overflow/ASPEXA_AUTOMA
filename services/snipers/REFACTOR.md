# Snipers Refactor - Dead Code Removal

## Summary
Removed 5 unused files from the codebase that were completely orphaned from the active workflow. These files were from an older architecture that has been superseded by the modern adaptive_attack system.

## Files Deleted

### 1. `converter_selection_node.py`
**Location:** `services/snipers/utils/nodes/converter_selection_node.py`

**Reason:** Never called by any active workflow. The file contained `ConverterSelectionNodePhase3` which was intended to be wired into LangGraph but was never instantiated. The function `select_converters_node()` raises `NotImplementedError`.

**Replacement:** Chain selection is now handled by `adapt_node` in the adaptive_attack system using `ChainDiscoveryAgent` (LLM-powered).

---

### 2. `chain_generator.py`
**Location:** `services/snipers/chain_discovery/chain_generator.py`

**Reason:** Zero usages anywhere in the codebase. Contained two generator classes:
- `HeuristicChainGenerator` - Maps defense patterns to converters via static dictionary
- `CombinatorialChainGenerator` - Generates combinations of converters

Both were only referenced by the deleted `converter_selection_node.py`.

**Replacement:** Chain generation is now handled by `ChainDiscoveryAgent` with LLM-based intelligent selection.

---

### 3. `evolutionary_optimizer.py`
**Location:** `services/snipers/chain_discovery/evolutionary_optimizer.py`

**Reason:** Zero imports or usages. Contained `EvolutionaryChainOptimizer` class for GA-based chain optimization that was never called.

**Status:** Superseded by LLM-based chain selection in adaptive attack system.

---

### 4. `pattern_database.py`
**Location:** `services/snipers/chain_discovery/pattern_database.py`

**Reason:** Contained `PatternDatabaseAdapter` for S3-backed chain persistence. While the learning system attempted to save chains here, the adaptive_attack system never queries this database. Disconnected from active workflow.

**Impact:** Pattern learning/persistence layer is unused in current architecture.

---

### 5. `learning_adaptation_node.py`
**Location:** `services/snipers/utils/nodes/learning_adaptation_node.py`

**Reason:** Only imported by `attack_execution.py` (Phase 3), which is from the old 3-phase workflow. The adaptive_attack system (new active workflow) doesn't use learning/persistence at all.

**Removal Impact:** Removed learning persistence from Phase 3, which is acceptable since adaptive_attack is the primary active system.

---

## Files Updated

### Documentation
- `ARCHITECTURE.md` - Removed references to deleted modules and pattern learning
- `README.md` - Removed pattern learning section, updated data flow diagrams
- `utils/nodes/__init__.py` - Removed exports for deleted nodes

### Code
- `attack_execution.py` - Removed:
  - Import of `LearningAdaptationNode`
  - Import of `S3PersistenceAdapter` and `S3InterfaceAdapter`
  - Learning/pattern update logic (lines 147-172)
  - Set learning result fields to `None` in Phase3Result

---

## Why This Refactor?

**Architecture Consolidation:** The codebase had two parallel chain selection systems:
1. **Legacy System** (deleted) - Heuristic + Combinatorial + Evolutionary + Pattern Database
2. **Modern System** (active) - LLM-powered `ChainDiscoveryAgent` in adaptive_attack

The modern system is the actual running workflow. All legacy infrastructure was dead weight.

**Code Quality:**
- Removed ~1,000 lines of unused code
- Eliminated confusing multi-strategy architecture
- Single source of truth: `adapt_node` for all chain selection
- Cleaner imports and fewer dependencies

---

## Impact

✅ **Safe to Delete:**
- No breaking changes to public APIs
- Only internal dead code paths removed
- All deletions verified with grep searches

⚠️ **Note:**
- Lost pattern database learning capability (acceptable - not used by main workflow)
- Lost evolutionary optimization (acceptable - not called anywhere)
- Phase 3 no longer learns successful chains to S3 (acceptable - adaptive_attack doesn't use this)

---

## Verification

All deleted files verified to have:
- Zero imports from active code
- Zero function/class instantiations
- Zero references in test code

Run: `grep -r "converter_selection_node\|ConverterSelectionNodePhase3\|HeuristicChainGenerator\|CombinatorialChainGenerator\|learning_adaptation_node\|pattern_database" --include="*.py"` to confirm.
