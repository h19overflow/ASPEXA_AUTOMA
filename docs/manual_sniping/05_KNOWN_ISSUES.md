# Manual Sniping Service - Known Issues & Fix Plan

> **Document**: 05_KNOWN_ISSUES.md
> **Status**: Active Investigation
> **Created**: 2025-11-28
> **Last Updated**: 2025-11-28

---

## Issue 1: API Connection Failure (ERR_EMPTY_RESPONSE)

### Symptoms
```
Failed to load resource: net::ERR_EMPTY_RESPONSE
:8000/api/campaigns:1  Failed to load resource: net::ERR_EMPTY_RESPONSE
:8000/api/manual-sniping/sessions:1  Failed to load resource: net::ERR_EMPTY_RESPONSE
:8000/api/manual-sniping/insights/1236546846:1  Failed to load resource: net::ERR_EMPTY_RESPONSE
```

### Root Cause Analysis

**Finding 1: Port Mismatch**
- Frontend is configured to call `http://localhost:8000`
- API Gateway main.py runs on port **8081** by default (line 43: `uvicorn.run(app, host="0.0.0.0", port=8081)`)
- Port 8000 is occupied by a different process ("Manager" - PID 6748)

**Finding 2: API Gateway May Not Be Running**
- No Python process running uvicorn on the correct port
- The campaigns router exists at `/campaigns` (not `/api/campaigns`)
- The manual_sniping router exists at `/manual-sniping` (not `/api/manual-sniping`)

**Finding 3: Route Prefix Mismatch**
Frontend client calls:
- `/api/campaigns`
- `/api/manual-sniping/transform`
- `/api/manual-sniping/sessions`

But backend routers are mounted at:
- `/campaigns` (campaigns.py line 12)
- `/manual-sniping` (manual_sniping.py line 40)

There is NO `/api` prefix in the backend routers.

### Fix Plan

#### Option A: Add `/api` prefix to API Gateway (Recommended)
**File**: `services/api_gateway/main.py`

```python
# Change from:
app.include_router(campaigns.router)
app.include_router(manual_sniping.router)

# To:
app.include_router(campaigns.router, prefix="/api")
app.include_router(manual_sniping.router, prefix="/api")
```

#### Option B: Remove `/api` prefix from Frontend
**File**: `viper-command-center/src/features/manual-sniping/api/client.ts`

Change all endpoints from `/api/...` to `/...`

#### Option C: Fix Port Configuration
**File**: `viper-command-center/.env` or environment

```
VITE_API_BASE_URL=http://localhost:8081
```

### Recommended Solution
1. Add `/api` prefix to all routers in `main.py`
2. Change default port from 8081 to 8000 (or configure frontend to use 8081)
3. Ensure API Gateway is running before frontend

---

## Issue 2: Transform Preview Not Displaying

### Symptoms
- User adds converters to the chain
- User enters a payload
- "Final Output" tab shows nothing or "Add converters to see the transformed output"
- No transformation steps visible

### Root Cause Analysis

**Finding 1: API Not Reachable**
- Primary cause is Issue 1 - API connection failure
- Transform endpoint `/api/manual-sniping/transform` cannot be reached

**Finding 2: React Query Conditional Enabling**
```typescript
// hooks/use-payload-transform.ts:33
const shouldTransform = enabled && rawPayload.length > 0 && activeConverters.length > 0;

// hooks/use-payload-transform.ts:41
enabled: shouldTransform,
```
Query only runs when:
1. Hook is enabled (passed as prop)
2. rawPayload has content
3. activeConverters array has items

**Finding 3: Store Update Dependency**
```typescript
// hooks/use-payload-transform.ts:48-58
useEffect(() => {
  if (data) {
    const steps: PayloadTransformStep[] = data.steps.map((step, index) => ({
      converterName: activeConverters[index],
      input: index === 0 ? rawPayload : data.steps[index - 1].output,
      output: step.output,
    }));
    setTransformedPayload(data.transformed, steps);
  }
}, [data, activeConverters, rawPayload, setTransformedPayload]);
```
The store is only updated when `data` exists (API response received).

**Finding 4: PayloadEditor Display Logic**
```tsx
// components/payload-editor.tsx:103
} : transformedValue ? (
  // ... show transformed output
) : (
  <Alert>
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      Add converters to see the transformed output
    </AlertDescription>
  </Alert>
)}
```
The component shows "Add converters" message when `transformedValue` is empty/falsy.

### Fix Plan

1. **Fix API Connection (Issue 1)** - Primary fix
   - Once API is reachable, transform will work

2. **Add Error State Display**
   - Show API errors to user instead of silent failure
   - Add error boundary around transform preview

3. **Add Loading State**
   - Already implemented (`isTransforming`) but not visible when API fails

4. **Add Offline/Mock Transform**
   - For development: implement client-side transform preview
   - Use same converter logic as backend (Base64, ROT13, etc.)

### Recommended Solution
```tsx
// In payload-editor.tsx, add error handling:
{isTransforming ? (
  // loading state
) : transformError ? (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      Transform failed: {transformError.message}. Is the API running?
    </AlertDescription>
  </Alert>
) : transformedValue ? (
  // show result
) : (
  // show placeholder
)}
```

---

## Issue 3: Campaign Insights Not Loading

### Symptoms
- After selecting a campaign, insights sidebar shows "No insights available"
- API call to `/api/manual-sniping/insights/{campaign_id}` fails

### Root Cause Analysis

Same as Issue 1 - API connection failure. Additionally:

**Finding 1: Insights Loader Dependency**
```python
# services/manual_sniping/insights/campaign_loader.py
# Loads from S3 - requires:
# 1. S3 configured and accessible
# 2. Campaign has completed recon/scan phases
# 3. S3 artifacts exist at expected paths
```

**Finding 2: Campaign Must Have Completed Phases**
The insights are loaded from:
- Recon phase artifacts (`01_recon/`)
- Garak scan artifacts (`02_scan/`)
- Exploit artifacts (`03_exploit/`)

If a campaign has no completed phases, insights will be empty.

### Fix Plan

1. **Fix API Connection (Issue 1)**
2. **Handle Empty Insights Gracefully**
   - Show message: "No insights yet. Complete recon/scan phases first."
3. **Add Mock Insights for Development**
   - Return sample data when no real insights exist

---

## Quick Start Fix

### Step 1: Start the API Gateway

```powershell
cd C:\Users\User\Projects\Aspexa_Automa
.\.venv\Scripts\python.exe -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Add `/api` prefix to routers

Edit `services/api_gateway/main.py`:

```python
# Service execution endpoints
app.include_router(recon.router, prefix="/api")
app.include_router(scan.router, prefix="/api")
app.include_router(exploit.router, prefix="/api")
app.include_router(manual_sniping.router, prefix="/api")

# Persistence endpoints
app.include_router(campaigns.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
```

### Step 3: Verify API is running

```powershell
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"api_gateway"}

curl http://localhost:8000/api/campaigns
# Should return: [] or list of campaigns

curl http://localhost:8000/api/manual-sniping/converters
# Should return: {"converters":[...], "categories":[...]}
```

### Step 4: Test Transform

```powershell
curl -X POST http://localhost:8000/api/manual-sniping/transform `
  -H "Content-Type: application/json" `
  -d '{"payload":"hello","converters":["Base64Converter"]}'
# Should return: {"original_payload":"hello","final_payload":"aGVsbG8=","steps":[...],...}
```

---

## Summary Table

| Issue | Severity | Root Cause | Fix |
|-------|----------|------------|-----|
| API ERR_EMPTY_RESPONSE | Critical | Port mismatch + missing `/api` prefix | Add prefix, fix port |
| Transform not showing | High | API unreachable | Fix Issue 1 |
| Insights not loading | Medium | API unreachable + empty data | Fix Issue 1 + handle empty |

---

## Files to Modify

| File | Change Required |
|------|-----------------|
| `services/api_gateway/main.py` | Add `/api` prefix to all routers |
| `viper-command-center/.env` | Set `VITE_API_BASE_URL` if needed |
| `viper-command-center/src/features/manual-sniping/components/payload-editor.tsx` | Add error state display |
| `viper-command-center/src/features/manual-sniping/hooks/use-payload-transform.ts` | Expose error to component |

---

## Fixes Applied (2025-11-28)

### Issue 1 Fixes:
- [x] Added `/api` prefix to all routers in `services/api_gateway/main.py`
- [x] Changed frontend API client default port from 8000 to 8081
- [x] Changed frontend WebSocket URL from 8000 to 8081

### Issue 2 Fixes:
- [x] Added `transformError` prop to PayloadEditor component
- [x] Added error display in transform preview tab
- [x] Fixed `create_session` to return `updated_at` and `saved_chains` fields

### Issue 4 Fixes (Infinite Re-render Loop):
- [x] Replaced `ScrollArea` with plain `div` in CampaignSelector to avoid Radix UI bug
- [x] Fixed `use-payload-transform.ts` hook:
  - Added `useMemo` for `activeConverters` to prevent recreation on each render
  - Added `convertersKey` for stable query key
  - Added `useRef` to track previous data and prevent unnecessary store updates

### Files Modified:
- `services/api_gateway/main.py` - Added `/api` prefix
- `services/manual_sniping/entrypoint.py` - Fixed session response fields
- `viper-command-center/src/features/manual-sniping/api/client.ts` - Port 8081
- `viper-command-center/src/features/manual-sniping/api/websocket.ts` - Port 8081
- `viper-command-center/src/features/manual-sniping/components/payload-editor.tsx` - Error display
- `viper-command-center/src/features/manual-sniping/components/campaign-selector.tsx` - Replaced ScrollArea with div
- `viper-command-center/src/features/manual-sniping/hooks/use-payload-transform.ts` - Fixed infinite loop
- `viper-command-center/src/features/manual-sniping/pages/manual-sniping.tsx` - Pass error prop

## Next Steps

1. [x] Verify endpoints are accessible via curl
2. [x] Test campaign listing in UI
3. [ ] Test transform endpoint with converters
4. [ ] Create a test campaign to verify insights loading
