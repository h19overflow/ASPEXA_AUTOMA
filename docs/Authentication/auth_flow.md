# Authentication & Authorization Flow

## Overview

The system uses **Clerk** for authentication with a two-tier access control:
1. **Authentication** - Verifies user identity via JWT tokens
2. **Authorization** - Restricts access to "friends" (whitelisted users)

This enables controlled soft-launch access while maintaining security.

---

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Browser
    participant Frontend as Frontend<br/>(React + Clerk)
    participant Backend as API Gateway<br/>(FastAPI)
    participant ClerkAPI as Clerk API

    %% Initial Authentication
    Note over Browser,ClerkAPI: 1. User Authentication (Clerk-managed)
    Browser->>Frontend: Navigate to protected page
    Frontend->>Frontend: Check Clerk session
    alt Not signed in
        Frontend->>Browser: Redirect to Clerk Sign-In
        Browser->>ClerkAPI: Authenticate (OAuth/Email)
        ClerkAPI->>Browser: Set session cookie
        Browser->>Frontend: Redirect back
    end

    %% API Request Flow
    Note over Browser,ClerkAPI: 2. API Request with JWT
    Frontend->>Frontend: useAuthToken() / useApi()
    Frontend->>ClerkAPI: getToken()
    ClerkAPI-->>Frontend: JWT Token (contains sub, sid, azp)

    Frontend->>Backend: API Request<br/>Authorization: Bearer {JWT}

    %% Backend Validation
    Note over Backend,ClerkAPI: 3. Backend Authentication
    Backend->>Backend: Extract JWT from header
    Backend->>Backend: clerk.authenticate_request()

    alt Invalid/Expired Token
        Backend-->>Frontend: 401 Unauthorized
        Frontend->>Browser: Redirect to sign-in
    end

    %% Authorization Check
    Note over Backend,ClerkAPI: 4. Friend Authorization
    Backend->>Backend: Check JWT for public_metadata

    alt public_metadata not in JWT
        Backend->>ClerkAPI: GET /users/{user_id}
        ClerkAPI-->>Backend: User data with public_metadata
        Backend->>Backend: Cache metadata
    end

    Backend->>Backend: Check isFriend == true

    alt Not a friend
        Backend-->>Frontend: 403 Forbidden<br/>"Access restricted to friends only"
        Frontend->>Browser: Redirect to /waitlist
    else Is a friend
        Backend->>Backend: Process request
        Backend-->>Frontend: 200 OK + Response data
        Frontend->>Browser: Render data
    end
```

---

## Component Responsibilities

### Frontend (`viper-command-center`)

| Component | File | Purpose |
|-----------|------|---------|
| `ClerkProvider` | `main.tsx` | Wraps app with Clerk context |
| `ProtectedRoute` | `components/auth/ProtectedRoute.tsx` | Redirects unauthenticated/non-friends |
| `AuthenticatedApiProvider` | `lib/api/AuthenticatedApiContext.tsx` | Provides authenticated API client |
| `useApi()` | `lib/api/AuthenticatedApiContext.tsx` | Hook for authenticated API calls |
| `useAuthToken()` | `lib/api/AuthenticatedApiContext.tsx` | Hook for streaming endpoints |

### Backend (`services/api_gateway`)

| Component | File | Purpose |
|-----------|------|---------|
| `get_current_user` | `auth/clerk_auth.py` | Validates JWT, returns ClerkUser |
| `require_friend` | `auth/permissions.py` | Checks `isFriend` in metadata |
| `ClerkUser` | `auth/clerk_auth.py` | User data model |

---

## JWT Token Structure

Clerk JWTs contain standard claims:

```json
{
  "azp": "http://localhost:8080",      // Authorized party (frontend origin)
  "exp": 1765270613,                   // Expiration timestamp
  "iat": 1765270553,                   // Issued at timestamp
  "iss": "https://xxx.clerk.accounts.dev", // Issuer
  "nbf": 1765270543,                   // Not before timestamp
  "sid": "sess_xxxxx",                 // Session ID
  "sub": "user_xxxxx",                 // User ID
  "sts": "active"                      // Session status
}
```

> **Note:** `public_metadata` is NOT included in the JWT by default. The backend fetches it from Clerk API and caches it.

---

## Access Control States

```
┌─────────────────┐
│  Unauthenticated │ ──► 401 ──► Clerk Sign-In
└────────┬────────┘
         │ Valid JWT
         ▼
┌─────────────────┐
│  Authenticated   │
│  (Not Friend)    │ ──► 403 ──► /waitlist page
└────────┬────────┘
         │ isFriend: true
         ▼
┌─────────────────┐
│   Authorized     │ ──► 200 ──► Full API access
│   (Friend)       │
└─────────────────┘
```

---

## How to Grant Friend Access

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Navigate to **Users** → Select user
3. Edit **Public Metadata**:
   ```json
   {
     "isFriend": true
   }
   ```
4. Save changes

The backend caches metadata, so changes may take a few minutes to propagate (or restart the backend).

---

## Key Files Reference

| Purpose | File Path |
|---------|-----------|
| Frontend auth context | `viper-command-center/src/lib/api/AuthenticatedApiContext.tsx` |
| Frontend route protection | `viper-command-center/src/components/auth/ProtectedRoute.tsx` |
| Backend JWT validation | `services/api_gateway/auth/clerk_auth.py` |
| Backend friend check | `services/api_gateway/auth/permissions.py` |
| Route dependencies | `services/api_gateway/main.py:45-84` |

---

## Future Enhancements

- [ ] Configure Clerk JWT Template to include `public_metadata` (eliminates API fetch)
- [ ] Add role-based access control (RBAC) beyond binary friend/non-friend
- [ ] Implement subscription tiers via Clerk metadata
- [ ] Add API key authentication for programmatic access
