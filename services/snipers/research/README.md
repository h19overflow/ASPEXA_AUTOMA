# Snipers Research Documentation

This directory contains research and planning documentation for enhancing the Snipers exploitation service with PyRIT (Python Risk Identification Toolkit) integration.

---

## Documents

### 1. [PYRIT_INTEGRATION_GUIDE.md](PYRIT_INTEGRATION_GUIDE.md)

**Purpose:** Comprehensive guide to integrating PyRIT features into Aspexa_Automa

**Contents:**
- Detailed analysis of 8 key PyRIT features (VariationConverter, RedTeamingOrchestrator, etc.)
- "What It Is" + "How It Works" + "What It Adds" for each feature
- Specific integration points in Aspexa_Automa codebase (exact file paths)
- Concrete use cases demonstrating value
- Phased integration roadmap (Quick Wins → Transformative features)
- Cost-benefit analysis table
- Architectural fit assessment

**Target Audience:** Technical leads, architects, developers implementing PyRIT integration

**Status:** ✅ Complete - Ready for implementation planning

---

### 2. [CUSTOM_PYRIT_COMPONENTS_FOR_ARABIC.md](CUSTOM_PYRIT_COMPONENTS_FOR_ARABIC.md)

**Purpose:** Technical specification for building custom PyRIT components for Arabic language red-teaming

**Contents:**
- PyRIT extensibility architecture (base classes, interfaces)
- Building custom converters (step-by-step guide with code examples)
- **Arabic-specific converters** (9 converters for Arabic obfuscation):
  - ArabicDiacriticConverter (tashkeel manipulation)
  - ArabicHomoglyphConverter (Unicode lookalikes)
  - ArabicRTLInjectConverter (bidirectional text attacks)
  - ArabicRephraserConverter (LLM-based dialect conversion)
  - And 5 more...
- Building custom orchestrators (extending MultiTurnOrchestrator)
- **ArabicRedTeamingOrchestrator** (full implementation example)
- Custom scorers for Arabic vulnerability detection
- Integration with Aspexa_Automa pipeline
- 6-week implementation roadmap
- Arabic language best practices

**Target Audience:** Developers implementing Arabic support, security researchers

**Status:** ✅ Complete - Ready for implementation

**Key Finding:** PyRIT is **fully extensible** - custom orchestrators and converters are encouraged by design

---

### 3. [DATASETS_AND_SEED_PROMPTS.md](DATASETS_AND_SEED_PROMPTS.md)

**Purpose:** Guide to PyRIT's dataset system for managing reusable prompt libraries

**Contents:**
- SeedPrompt, SeedPromptDataset, SeedPromptGroup core concepts
- YAML template format with parameterization
- Integration with Swarm (probe library), Snipers (exploit templates), Manual Sniping
- Arabic-specific dataset structure (5 dialects × 3 formality levels)
- Cross-campaign pattern storage via PyRIT Memory
- Built-in PyRIT datasets (illegal.prompt, jailbreak templates, etc.)

**Target Audience:** Developers building prompt libraries, security researchers

**Status:** ✅ Complete - Ready for implementation

**Timeline:** 1-2 days to migrate existing probe templates to SeedPrompt format

---

### 4. [CRESCENDO_ATTACK.md](CRESCENDO_ATTACK.md)

**Purpose:** Technical guide to Crescendo multi-turn attack (gradual escalation)

**Contents:**
- Core mechanism: Build trust → Incremental requests → Backtrack on refusal → Achieve goal
- Implementation with CrescendoOrchestrator (max_turns, max_backtracks, scoring)
- Integration with Snipers (ArabicCrescendoOrchestrator), Manual Sniping (guided mode)
- Arabic-specific: Dialect progression (MSA → casual), cultural framing, formality escalation
- Performance: 78% success rate (2.3x better than direct attacks)

**Target Audience:** Developers implementing multi-turn attacks

**Status:** ✅ Complete - Ready for implementation

**Timeline:** 1 week basic, 4 weeks full Arabic support

---

### 5. [SKELETON_KEY_ATTACK.md](SKELETON_KEY_ATTACK.md)

**Purpose:** Technical guide to Skeleton Key single-turn bypass

**Contents:**
- Core mechanism: `[Skeleton Key Prompt] + [Malicious Request] → Target`
- Implementation with SkeletonKeyOrchestrator (custom keys, default keys)
- Skeleton key library for Arabic (4 variants: MSA formal, Levantine, Egyptian, Gulf)
- Integration with Swarm (probe library), Snipers (initial bypass), Manual Sniping (quick action)
- Effectiveness: 8-60% success rate depending on target
- Combination strategies: Skeleton Key + Converter, + Crescendo

**Target Audience:** Developers implementing bypass techniques

**Status:** ✅ Complete - Ready for implementation

**Timeline:** 2-3 days to build skeleton key library + integration

---

### 6. [PDF_CONVERTER.md](PDF_CONVERTER.md)

**Purpose:** Technical guide to PDFConverter for document-based attacks

**Contents:**
- Core mechanism: Embed malicious prompts in PDF to bypass text filters
- Template-based and direct conversion
- Arabic PDF generation with RTL support and Arabic fonts
- Integration: Swarm (document injection tests), Cartographer (document processing probe), Snipers (multi-modal exploits)
- Use cases: RAG document injection, resume/CV injection, invoice injection
- PDF template library structure

**Target Audience:** Developers implementing multi-modal attacks

**Status:** ✅ Complete - Ready for implementation

**Timeline:** 1-2 days integration with Swarm/Snipers

---

### 7. [SELECTIVELY_CONVERTING.md](SELECTIVELY_CONVERTING.md)

**Purpose:** Technical guide to selective conversion using `⟪⟫` delimiters

**Contents:**
- Core mechanism: Apply converters only to marked parts `"Text ⟪convert this⟫ text"`
- Delimiters: `⟪` (U+27EA) and `⟫` (U+27EB)
- Integration: Snipers (pattern-based selective obfuscation), Manual Sniping (text selection UI)
- Arabic selective conversion: Obfuscate keywords while preserving sentence structure
- Advanced patterns: Nested obfuscation, contextual preservation
- Automatic keyword detection from Cartographer

**Target Audience:** Developers implementing precision obfuscation

**Status:** ✅ Complete - Ready for implementation

**Timeline:** 1 day to add selective marking to Snipers/Manual Sniping

---

### 8. [HUMAN_IN_THE_LOOP_CONVERTER.md](HUMAN_IN_THE_LOOP_CONVERTER.md)

**Purpose:** Technical guide to HumanInTheLoopConverter for hybrid automation

**Contents:**
- Core mechanism: `Automation → Pause → Human Decision → Continue`
- Implementation with HumanInTheLoopConverter (present options, wait for selection)
- Integration: Snipers (enhanced approval gates), Manual Sniping (guided mode)
- Confidence-based gating: Only pause if confidence < threshold
- Learning from human choices: Track selections to improve automation
- Arabic-specific: Present Arabic converter options with previews

**Target Audience:** Developers implementing hybrid workflows

**Status:** ✅ Complete - Ready for implementation

**Timeline:** 3-4 days to integrate with Snipers approval gates

---

## Why PyRIT for Aspexa_Automa?

**Alignment:**
- PyRIT's modular orchestration + Aspexa's intelligence-driven planning = Hybrid adaptive system
- PyRIT handles tactical execution (converters, scorers) while Aspexa handles strategic planning (Cartographer recon)

**Arabic Language Support:**
- MENA market opportunity (22 countries, 400M+ Arabic speakers)
- No existing red-teaming tools have comprehensive Arabic support
- Competitive differentiation

**Technical Feasibility:**
- Base classes designed for extension
- 50+ existing converters prove extensibility
- MultiTurnOrchestrator provides standardized interface
- Dependency injection throughout (testable, swappable)

---

## Implementation Priority

### Quick Wins (4 days)
1. PromptConverterConfiguration - Standardize converter chaining
2. SelfAskCategoryScorer - Semantic vulnerability detection
3. Batch Scoring - Parallel execution

### High Value (2 weeks)
4. VariationConverter - Dynamic prompt generation
5. PyRIT Memory - Unified query layer + cross-campaign learning

### Transformative (3 weeks)
6. RedTeamingOrchestrator - Autonomous iterative attacks
7. Arabic Converters Suite - 9 Arabic-specific transformations
8. ArabicRedTeamingOrchestrator - Arabic attack automation

---

## Integration with Existing Services

| Service | PyRIT Integration | Benefit |
|---------|-------------------|---------|
| **Cartographer** | Pattern extraction feeds VariationConverter | Dynamic attack generation |
| **Swarm** | SelfAskCategoryScorer + batch scoring | Reduced false positives, faster detection |
| **Snipers** | RedTeamingOrchestrator + Arabic converters | Autonomous exploitation, international support |
| **Manual Sniping** | HumanInTheLoopConverter | Guided mode (faster than full manual) |
| **Campaign Memory** | PyRIT Memory integration | Cross-campaign analytics |

---

## Next Steps

1. **Technical Review** - Review both documents with team, identify questions/concerns
2. **POC Selection** - Choose Phase 1 feature for proof-of-concept (recommend: PromptConverterConfiguration)
3. **Arabic Validation** - Consult Arabic native speakers for dialect/converter accuracy
4. **Architecture Decision** - Decide on PyRIT Memory adoption strategy (gradual migration vs dual-write)
5. **Timeline Planning** - Map features to sprint/release schedule

---

## References

- **PyRIT Repository:** https://github.com/Azure/PyRIT
- **PyRIT Documentation:** https://github.com/Azure/PyRIT/tree/main/doc
- **Arabic NLP Resources:** https://www.arabicnlp.pro/
- **Unicode Arabic Standard:** https://unicode.org/charts/PDF/U0600.pdf

---

## Questions / Discussion

For questions or discussion about PyRIT integration or Arabic support:
- Open issue in project repository
- Tag: `research`, `pyrit`, `arabic-support`
- Cc: @snipers-team @architecture-team

---

**Last Updated:** November 2024
**Maintained By:** Snipers Team
**Status:** Active Research
