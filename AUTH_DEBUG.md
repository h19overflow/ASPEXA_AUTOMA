# Authentication Issue Debug

## Problem
401 Unauthorized errors on all protected API endpoints despite being logged in via Clerk.

## Error Messages
```
Suffixed cookie failed due to Cannot read properties of undefined (reading 'digest') (secure-context: false)
GET http://localhost:8081/api/campaigns 401 (Unauthorized)
```

## Suspected Root Causes

### 1. JWT Not Being Passed in Requests
**Location**: `viper-command-center/src/lib/api/services.ts`

The streaming functions (SSE endpoints) create their own `fetch()` calls WITHOUT using the authenticated client:
```typescript
// Lines 125, 192, 323, 542, 662
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8081/api";
const response = await fetch(`${API_BASE_URL}/...`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },  // NO Authorization header!
  body: JSON.stringify(data),
});
```

### 2. Clerk getToken() Returning Null
**Location**: `viper-command-center/src/lib/api/AuthenticatedApiContext.tsx`

```typescript
const client = useMemo(() => {
  return new ApiClient(undefined, async () => {
    return await getToken();  // May return null if not in secure context
  });
}, [getToken]);
```

### 3. Backend Auth Validation
**Location**: `services/api_gateway/auth/clerk_auth.py`

Clerk SDK `authenticate_request()` may be failing silently or rejecting the token.

## Files to Check

| File | Issue |
|------|-------|
| `src/lib/api/client.ts:30-35` | Token injection logic |
| `src/lib/api/AuthenticatedApiContext.tsx` | `getToken()` call |
| `src/lib/api/services.ts` (lines 125, 192, 323, 542, 662) | Streaming endpoints bypass auth |
| `services/api_gateway/auth/clerk_auth.py:70-83` | Backend token validation |

## Quick Debug Steps

1. **Check if token exists** - Add console.log in `AuthenticatedApiContext.tsx`:
   ```typescript
   const token = await getToken();
   console.log("Clerk token:", token ? "EXISTS" : "NULL");
   ```

2. **Check request headers** - In browser DevTools Network tab, verify `Authorization: Bearer ...` header is present

3. **Check backend logs** - See what error `clerk.authenticate_request()` throws

## Potential Fixes

1. **Fix streaming functions** - Pass token to SSE fetch calls
2. **Debug getToken()** - Ensure Clerk session is valid
3. **Add error logging** - In `clerk_auth.py` to see exact failure reason
