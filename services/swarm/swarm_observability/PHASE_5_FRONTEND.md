# Phase 5: Frontend Integration

## Files to Modify

| File | Changes |
|------|---------|
| `lib/api/services.ts` | Add control API functions |
| `stores/swarmStore.ts` | Add scan_id, isPaused state |
| `pages/Swarm.tsx` | Add control buttons, new event handlers |

---

## 5.1 API Functions (services.ts)

```typescript
export async function cancelScan(scanId: string) {
  return apiClient.post(`/scan/${scanId}/cancel`);
}

export async function pauseScan(scanId: string) {
  return apiClient.post(`/scan/${scanId}/pause`);
}

export async function resumeScan(scanId: string) {
  return apiClient.post(`/scan/${scanId}/resume`);
}
```

---

## 5.2 Store Updates (swarmStore.ts)

```typescript
interface SwarmState {
  // ... existing
  scanId: string | null;
  isPaused: boolean;
}

// Actions
setScanId: (id: string | null) => void;
setIsPaused: (paused: boolean) => void;
```

---

## 5.3 Event Handlers (Swarm.tsx)

```typescript
case "scan_started":
  setScanId(event.data?.scan_id);
  break;

case "scan_paused":
  setIsPaused(true);
  toast({ title: "Scan Paused" });
  break;

case "scan_cancelled":
  setIsScanning(false);
  setScanResult(event.data?.snapshot);
  toast({ title: "Scan Cancelled", description: "Partial results saved" });
  break;

case "node_progress":
  setProgress(event.progress * 100);
  break;
```

---

## 5.4 Control Buttons

```tsx
{isScanning && (
  <div className="flex gap-2">
    {isPaused ? (
      <Button onClick={() => resumeScan(scanId!)}>
        <Play className="w-4 h-4 mr-1" /> Resume
      </Button>
    ) : (
      <Button onClick={() => pauseScan(scanId!)}>
        <Pause className="w-4 h-4 mr-1" /> Pause
      </Button>
    )}
    <Button variant="destructive" onClick={() => cancelScan(scanId!)}>
      <StopCircle className="w-4 h-4 mr-1" /> Cancel
    </Button>
  </div>
)}
```

---

## Done When

- [x] Pause/Resume buttons work
- [x] Cancel persists partial results
- [x] Progress bar updates from node_progress events
- [x] scan_id captured from scan_started event

---

## Implementation Complete

**Date:** 2024-12-07

### Files Modified

| File | Changes |
|------|---------|
| `viper-command-center/src/lib/api/types.ts` | Added `scan_started`, `scan_paused`, `scan_resumed`, `scan_cancelled`, `node_progress` event types; Added `ScanControlResponse` interface |
| `viper-command-center/src/lib/api/services.ts` | Added `cancelScan`, `pauseScan`, `resumeScan`, `getScanStatus` functions; Updated `garakService` object |
| `viper-command-center/src/stores/swarmStore.ts` | Added `scanId` and `isPaused` state with setters; Updated `resetScanState` |
| `viper-command-center/src/pages/Swarm.tsx` | Added event handlers for scan lifecycle; Added Pause/Resume/Cancel buttons; Added PAUSED badge display |

### Tests

All 54 existing frontend tests pass. Build completes without type errors.
