# Sniper Enhancement Plan: Overview

**Version**: 1.0
**Status**: Ready for Implementation
**Total Timeline**: 5 days
**Expected Impact**: 2-3x improvement in success rate (20% → 45-60%)

---

## Executive Summary

This enhancement plan addresses three critical gaps in the adaptive attack system:

1. **Missing recon-based framing** - Generate custom strategies from discovered tools/infrastructure
2. **No adversarial suffix augmentation** - Add GCG/AutoDAN patterns to bypass filters
3. **Converter over-stacking** - Limit chains to prevent unrecognizable payloads

Each phase is independently testable with clear success criteria.

---

## Current System Analysis

### ✅ What's Working
- Tool intelligence extraction (XML-tagged prompts) ✓
- Chain discovery agent ✓
- Strategy generator ✓
- Defense signal detection ✓

### ❌ What's Missing
- Recon intelligence not used for framing generation
- No adversarial suffix library
- Converter chains too long (4-6 converters → gibberish)

### ⏸️ Explicitly Delayed
- Multi-turn conversation (requires target agent changes)

---

## Implementation Phases

### Phase 1: Recon-Based Dynamic Framing
**Priority**: ⭐⭐⭐⭐⭐ HIGHEST
**Timeline**: 2 days
**Impact**: Custom framing from tools/infrastructure
**Document**: [PHASE_1_RECON_FRAMING.md](./PHASE_1_RECON_FRAMING.md)

**Milestone 1.1**: Tool-to-Role Mapping (Day 1 AM)
- Map tool names to testing roles
- Test with refund_transaction → "Financial QA Analyst"

**Milestone 1.2**: Infrastructure-to-Context Mapping (Day 1 PM)
- Map database types to contexts
- Test with PostgreSQL → "Database migration testing"

**Milestone 1.3**: Integration with Strategy Generator (Day 2 AM)
- Pass recon intelligence through adapt_node
- Generate custom FramingStrategy objects

**Milestone 1.4**: End-to-End Testing (Day 2 PM)
- Verify custom framing used in payloads
- Validate logging shows generated strategies

---

### Phase 2: Adversarial Suffix Library
**Priority**: ⭐⭐⭐⭐ HIGH
**Timeline**: 1 day
**Impact**: Bypass content filters
**Document**: [PHASE_2_ADVERSARIAL_SUFFIX.md](./PHASE_2_ADVERSARIAL_SUFFIX.md)

**Milestone 2.1**: Suffix Library Creation (AM)
- Implement GCG suffix collection
- Implement AutoDAN patterns
- Add defense-specific suffixes

**Milestone 2.2**: Augmentation Engine (PM)
- Implement suffix selection logic
- Integrate with payload articulation node
- Test suffix rotation

**Milestone 2.3**: Validation Testing (PM)
- Verify suffixes appended on iteration 2+
- Test defense-specific selection
- Validate logging

---

### Phase 3: Converter Chain Optimization
**Priority**: ⭐⭐⭐⭐ HIGH
**Timeline**: 1 day
**Impact**: Fix over-stacking bug
**Document**: [PHASE_3_CONVERTER_OPTIMIZATION.md](./PHASE_3_CONVERTER_OPTIMIZATION.md)

**Milestone 3.1**: Chain Length Limiting (AM)
- Implement MAX_CHAIN_LENGTH = 3
- Add length penalty to scoring
- Filter out chains exceeding limit

**Milestone 3.2**: Prompt Updates (PM)
- Update chain discovery prompt with constraints
- Test chain generation with limits
- Verify intelligibility maintained

**Milestone 3.3**: Validation Testing (PM)
- Test edge cases (all chains too long)
- Verify fallback logic
- Validate logging shows length reasoning

---

### Phase 4: Integration & Benchmarking
**Priority**: ⭐⭐⭐ MEDIUM
**Timeline**: 1 day
**Impact**: Validation and metrics
**Document**: [PHASE_4_INTEGRATION.md](./PHASE_4_INTEGRATION.md)

**Milestone 4.1**: End-to-End Integration Test (AM)
- Run full adaptive attack with all enhancements
- Verify all 3 features working together
- Check for integration bugs

**Milestone 4.2**: Benchmark Testing (PM)
- Compare baseline vs. enhanced system
- Measure success rate improvement
- Document performance metrics

**Milestone 4.3**: Documentation (PM)
- Update system documentation
- Create usage examples
- Document configuration options

---

## Success Criteria

### Phase 1 Success Criteria
- [ ] Custom framing generated for tools (refund → Financial QA)
- [ ] Custom framing generated for infrastructure (PostgreSQL → DB migration)
- [ ] Custom FramingStrategy objects created
- [ ] Framing used in payload generation
- [ ] Logs show "Generated recon-based framing: [name]"

### Phase 2 Success Criteria
- [ ] Adversarial suffixes appended on iteration 2+
- [ ] Defense-specific suffixes selected correctly
- [ ] Suffix type logged (GCG/AutoDAN/defense-specific)
- [ ] Payload length increases with suffix
- [ ] Suffixes rotate across iterations

### Phase 3 Success Criteria
- [ ] Chains limited to max 3 converters
- [ ] Longer chains penalized in scoring
- [ ] Fallback works when all chains exceed limit
- [ ] Selection reasoning includes length
- [ ] Payloads remain intelligible (manual review)

### Phase 4 Success Criteria
- [ ] All enhancements working together
- [ ] Success rate improvement documented (target: 2-3x)
- [ ] No regression in existing functionality
- [ ] Performance benchmarks recorded
- [ ] Documentation complete

---

## File Structure

```
docs/sniper_enhancements/
├── 00_OVERVIEW.md                      # This file
├── PHASE_1_RECON_FRAMING.md           # Day 1-2 implementation
├── PHASE_2_ADVERSARIAL_SUFFIX.md      # Day 3 implementation
├── PHASE_3_CONVERTER_OPTIMIZATION.md  # Day 4 implementation
├── PHASE_4_INTEGRATION.md             # Day 5 implementation
└── TEST_SCENARIOS.md                   # Test cases for each phase
```

---

## Dependencies Between Phases

```
Phase 1 (Recon Framing)
    ↓ (Independent)
Phase 2 (Adversarial Suffix)
    ↓ (Independent)
Phase 3 (Converter Optimization)
    ↓ (Requires all above)
Phase 4 (Integration & Benchmarking)
```

**Note**: Phases 1, 2, and 3 are independent and can be implemented in parallel if needed.

---

## Risk Mitigation

### Technical Risks

**Risk**: Custom framing generates poor strategies
- **Mitigation**: Fallback to built-in framing types
- **Test**: Validate framing quality in milestone 1.4

**Risk**: Adversarial suffixes break payload formatting
- **Mitigation**: Optional suffix toggle, validation checks
- **Test**: Manual review in milestone 2.3

**Risk**: Chain length limit too restrictive
- **Mitigation**: MAX_CHAIN_LENGTH is configurable
- **Test**: Test with various defense types in milestone 3.3

### Integration Risks

**Risk**: Enhancements conflict with each other
- **Mitigation**: Phase 4 dedicated to integration testing
- **Test**: End-to-end test in milestone 4.1

**Risk**: Performance degradation from added logic
- **Mitigation**: Benchmark in Phase 4
- **Test**: Performance metrics in milestone 4.2

---

## Expected Impact Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Framing Quality** | Generic (QA_TESTING) | Tool-specific (Financial QA) | Contextual |
| **Filter Bypass** | None | GCG/AutoDAN suffixes | +20-40% |
| **Payload Intelligibility** | 4-6 converters (poor) | Max 3 converters (good) | 2x better |
| **Overall Success Rate** | ~20% | ~45-60% | **2-3x** |

---

## Getting Started

1. **Read this overview** to understand the full plan
2. **Start with Phase 1** ([PHASE_1_RECON_FRAMING.md](./PHASE_1_RECON_FRAMING.md))
3. **Complete each milestone** before moving to next
4. **Run tests** after each milestone
5. **Document results** as you go

---

## Phase Navigation

- **Next**: [Phase 1: Recon-Based Framing →](./PHASE_1_RECON_FRAMING.md)
- **All Phases**: See file list above
- **Test Scenarios**: [TEST_SCENARIOS.md](./TEST_SCENARIOS.md)

---

**Last Updated**: 2025-12-02
**Maintained By**: AI Red Teaming Team
