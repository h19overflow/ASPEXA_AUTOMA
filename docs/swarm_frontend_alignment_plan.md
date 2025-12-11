# Swarm Frontend Alignment Plan

## Overview

The backend swarm probe selection system was simplified to remove the "generations" concept. This plan aligns the frontend (`viper-command-center/src/pages/Swarm.tsx`) with those changes.

## Backend Changes Summary

### What Was Removed
1. **Generations concept** - Each probe now runs once (no retry attempts)
2. **`generations` field** from `ScanConfig`, `ScanPlan`
3. **`max_generations`** from config
4. **`allow_agent_override`** - Removed from config
5. **`max_concurrent_generations`** - Removed (only `max_concurrent_probes` remains)
6. **Safety check node** - Removed from graph flow

### New Simplified Flow
```
User selects agent -> Agent (LLM) selects probes -> Execute each probe ONCE -> Persist
```

---

## Frontend Files to Modify

### 1. `viper-command-center/src/pages/Swarm.tsx`

#### Remove Generations UI Elements

**Lines 65-84**: Remove `generations` from `APPROACH_INFO`
```typescript
// BEFORE
const APPROACH_INFO: Record<ScanApproach, { label: string; description: string; probes: number; generations: number }> = {
  quick: { ..., generations: 5 },
  standard: { ..., generations: 10 },
  thorough: { ..., generations: 20 },
};

// AFTER
const APPROACH_INFO: Record<ScanApproach, { label: string; description: string; probes: number }> = {
  quick: { label: "Quick", description: "Fast initial assessment. ~3 probes.", probes: 3 },
  standard: { label: "Standard", description: "Balanced coverage. ~6 probes.", probes: 6 },
  thorough: { label: "Thorough", description: "Deep comprehensive scan. ~10 probes.", probes: 10 },
};
```

**Lines 121-122**: Remove `generations` and `allowAgentOverride` from store destructuring
```typescript
// REMOVE these from useSwarmStore destructuring:
// - generations
// - allowAgentOverride
// - maxGenerations
// - maxConcurrentGenerations
// - setGenerations
// - setAllowAgentOverride
// - setMaxConcurrentGenerations
```

**Lines 388-404**: Simplify `ScanConfigRequest` in `handleStartScan`
```typescript
// BEFORE
const config: ScanConfigRequest = {
  approach,
  generations,
  allow_agent_override: allowAgentOverride,
  max_probes: maxProbes,
  max_generations: maxGenerations,
  enable_parallel_execution: enableParallel,
  max_concurrent_probes: maxConcurrentProbes,
  max_concurrent_generations: maxConcurrentGenerations,
  ...
};

// AFTER
const config: ScanConfigRequest = {
  approach,
  max_probes: maxProbes,
  enable_parallel_execution: enableParallel,
  max_concurrent_probes: maxConcurrentProbes,
  requests_per_second: requestsPerSecond || undefined,
  max_concurrent_connections: maxConnections,
  request_timeout: requestTimeout,
  max_retries: maxRetries,
  retry_backoff: retryBackoff,
  connection_type: connectionType,
};
```

**Lines 466-470**: Simplify `handleApproachChange`
```typescript
// BEFORE
const handleApproachChange = (newApproach: ScanApproach) => {
  setApproach(newApproach);
  setMaxProbes(APPROACH_INFO[newApproach].probes);
  setGenerations(APPROACH_INFO[newApproach].generations);
};

// AFTER
const handleApproachChange = (newApproach: ScanApproach) => {
  setApproach(newApproach);
  setMaxProbes(APPROACH_INFO[newApproach].probes);
};
```

**Lines 824-837**: Remove Generations slider from Config tab
```typescript
// REMOVE this entire block:
<div>
  <div className="flex items-center justify-between mb-2">
    <Label className="text-xs text-white/50">Generations</Label>
    <span className="text-sm text-[#2997ff] font-mono">{generations}</span>
  </div>
  <input
    type="range"
    min={1}
    max={30}
    value={generations}
    onChange={(e) => setGenerations(parseInt(e.target.value))}
    className="w-full accent-[#2997ff]"
  />
</div>
```

**Lines 839-854**: Remove AI Override toggle
```typescript
// REMOVE this entire block:
<div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/5">
  <div>
    <Label className="text-sm text-white/70 block">AI Override</Label>
    <span className="text-xs text-white/30">Let AI adjust based on recon</span>
  </div>
  <button ...>...</button>
</div>
```

**Lines 904-918**: Remove Concurrent Generations slider
```typescript
// REMOVE this entire block:
<div>
  <div className="flex items-center justify-between mb-2">
    <Label className="text-xs text-white/50">Concurrent Generations</Label>
    <span className="text-sm text-[#2997ff] font-mono">{maxConcurrentGenerations}</span>
  </div>
  <input
    type="range"
    min={1}
    max={5}
    value={maxConcurrentGenerations}
    onChange={(e) => setMaxConcurrentGenerations(parseInt(e.target.value))}
    className="w-full accent-[#2997ff]"
  />
</div>
```

---

### 2. `viper-command-center/src/stores/swarmStore.ts`

Remove generations-related state:
```typescript
// REMOVE from state interface and initial state:
// - generations: number
// - allowAgentOverride: boolean
// - maxGenerations: number
// - maxConcurrentGenerations: number

// REMOVE actions:
// - setGenerations
// - setAllowAgentOverride
// - setMaxConcurrentGenerations
```

---

### 3. `viper-command-center/src/lib/api.ts`

Update `ScanConfigRequest` type:
```typescript
// BEFORE
export interface ScanConfigRequest {
  approach?: ScanApproach;
  generations?: number;
  allow_agent_override?: boolean;
  max_probes?: number;
  max_generations?: number;
  enable_parallel_execution?: boolean;
  max_concurrent_probes?: number;
  max_concurrent_generations?: number;
  ...
}

// AFTER
export interface ScanConfigRequest {
  approach?: ScanApproach;
  max_probes?: number;
  enable_parallel_execution?: boolean;
  max_concurrent_probes?: number;
  requests_per_second?: number;
  max_concurrent_connections?: number;
  request_timeout?: number;
  max_retries?: number;
  retry_backoff?: number;
  connection_type?: ConnectionType;
}
```

---

### 4. Event Handling Updates (Optional Cleanup)

In `handleStreamEvent`, remove generations references from event data:
- Line 246: Remove `const generations = event.generations || event.data?.generations;`
- Any other references to generations in event handling

---

## Implementation Order

1. **Update API types** (`lib/api.ts`) - Remove generations from `ScanConfigRequest`
2. **Update store** (`stores/swarmStore.ts`) - Remove generations state and actions
3. **Update Swarm.tsx**:
   - Remove imports/destructuring of generations-related items
   - Update `APPROACH_INFO` constant
   - Simplify `handleStartScan` config object
   - Simplify `handleApproachChange`
   - Remove UI elements (generations slider, AI override toggle, concurrent generations)
4. **Test** - Verify scan flow works without generations

---

## UI Changes Summary

### Removed UI Elements
| Element | Location | Reason |
|---------|----------|--------|
| Generations slider | Config tab | Concept removed |
| AI Override toggle | Config tab | `allow_agent_override` removed |
| Concurrent Generations slider | Advanced settings | Only probe concurrency remains |

### Updated UI Elements
| Element | Change |
|---------|--------|
| Approach buttons | No longer show generations count |
| Config request | Simplified payload |

---

## Verification Checklist

- [ ] API types updated in `lib/api.ts`
- [ ] Store updated in `swarmStore.ts`
- [ ] `APPROACH_INFO` simplified
- [ ] `handleStartScan` simplified
- [ ] `handleApproachChange` simplified
- [ ] Generations slider removed
- [ ] AI Override toggle removed
- [ ] Concurrent Generations slider removed
- [ ] Scan flow tested end-to-end
- [ ] No TypeScript errors
- [ ] No console errors during scan

---

## Notes

- The backend now runs each probe exactly once per prompt
- Parallelism still exists at the **probe level** (`max_concurrent_probes`)
- Rate limiting still available (`requests_per_second`)
- The simplified flow: User picks agent -> LLM picks probes -> Execute once each
