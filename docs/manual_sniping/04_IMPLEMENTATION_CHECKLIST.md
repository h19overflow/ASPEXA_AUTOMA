# Manual Sniping Service - Implementation Checklist

> **Document**: 04_IMPLEMENTATION_CHECKLIST.md
> **Status**: Draft
> **Last Updated**: 2025-11-28

---

## Overview

This checklist breaks down implementation into 6 phases. Each task includes:
- [ ] Checkbox for tracking completion
- **File(s)**: Target file paths
- **Acceptance Criteria**: Definition of done
- **Est. Time**: Estimated hours

---

## Phase 1: Backend Data Models & Core (Day 1-2)

### 1.1 Service Directory Setup

- [ ] **Create service directory structure**
  - Files: `services/manual_sniping/__init__.py`, all subdirectories
  - Criteria: All directories exist, `__init__.py` files have proper exports
  - Est: 0.5h

### 1.2 Data Models

- [ ] **Implement Session models**
  - File: `services/manual_sniping/models/session.py`
  - Criteria: `Session`, `AttackAttempt`, `SessionStatus`, `AttemptStatus` classes with validation
  - Est: 1h

- [ ] **Implement Converter models**
  - File: `services/manual_sniping/models/converter.py`
  - Criteria: `TransformStep`, `TransformResult`, `ConverterInfo`, `ConverterChainConfig`
  - Est: 0.5h

- [ ] **Implement Target models**
  - File: `services/manual_sniping/models/target.py`
  - Criteria: `TargetConfig`, `AuthConfig`, `Protocol`, `AuthType` enums
  - Est: 0.5h

- [ ] **Implement Insights models**
  - File: `services/manual_sniping/models/insights.py`
  - Criteria: `CampaignInsights`, `VulnerabilityPattern`, `ReconInsights`, `ScanInsights`
  - Est: 0.5h

- [ ] **Create models package exports**
  - File: `services/manual_sniping/models/__init__.py`
  - Criteria: All models importable from `services.manual_sniping.models`
  - Est: 0.25h

### 1.3 Core Components

- [ ] **Implement SessionManager**
  - File: `services/manual_sniping/core/session_manager.py`
  - Criteria:
    - In-memory Dict storage
    - TTL-based cleanup (background task)
    - CRUD operations for sessions
    - Attempt management
  - Est: 2h

- [ ] **Implement ConverterChainExecutor**
  - File: `services/manual_sniping/core/converter_chain.py`
  - Criteria:
    - Reuses `ConverterFactory` from snipers
    - Step-by-step transformation tracking
    - `CONVERTER_CATALOG` for UI metadata
  - Est: 1.5h

- [ ] **Unit tests for core**
  - File: `tests/unit/services/manual_sniping/test_session_manager.py`
  - File: `tests/unit/services/manual_sniping/test_converter_chain.py`
  - Criteria: >90% coverage, all edge cases
  - Est: 2h

**Phase 1 Total: ~8.5h**

---

## Phase 2: Backend Execution & Persistence (Day 3-4)

### 2.1 Execution Layer

- [ ] **Implement AttackExecutor**
  - File: `services/manual_sniping/execution/executor.py`
  - Criteria:
    - Orchestrates transform → execute flow
    - Progress callbacks for WebSocket streaming
    - Error handling with graceful degradation
  - Est: 2h

- [ ] **Implement HTTP executor**
  - File: `services/manual_sniping/execution/http_executor.py`
  - Criteria:
    - Uses `libs/connectivity/AsyncHttpClient`
    - Auth header injection
    - Latency tracking
  - Est: 1h

- [ ] **Implement WebSocket executor**
  - File: `services/manual_sniping/execution/websocket_executor.py`
  - Criteria:
    - WebSocket connection management
    - Timeout handling
  - Est: 1h

### 2.2 Persistence Layer

- [ ] **Implement S3 adapter**
  - File: `services/manual_sniping/persistence/s3_adapter.py`
  - Criteria:
    - Reuses `libs/persistence/s3.py`
    - Session serialization to S3
    - Campaign update on save
  - Est: 1.5h

- [ ] **Implement CampaignInsightsLoader**
  - File: `services/manual_sniping/insights/campaign_loader.py`
  - Criteria:
    - Loads recon/garak/exploit data from S3
    - Extracts vulnerability patterns
    - Graceful handling of missing data
  - Est: 1.5h

### 2.3 Unit Tests

- [ ] **Executor tests**
  - File: `tests/unit/services/manual_sniping/test_executor.py`
  - Criteria: Mock HTTP/WS clients, verify transform flow
  - Est: 1.5h

- [ ] **Persistence tests**
  - File: `tests/unit/services/manual_sniping/test_s3_adapter.py`
  - Criteria: Mock S3 client, verify serialization
  - Est: 1h

**Phase 2 Total: ~9.5h**

---

## Phase 3: Backend API Layer (Day 5)

### 3.1 API Schemas (in api_gateway)

- [ ] **Implement request/response schemas**
  - File: `services/api_gateway/schemas/manual_sniping.py`
  - Criteria: All schemas from API_SPECIFICATIONS.md
  - Est: 1h

### 3.2 REST Router (in api_gateway)

- [ ] **Implement FastAPI router**
  - File: `services/api_gateway/routers/manual_sniping.py`
  - Criteria:
    - All REST endpoints from spec
    - Calls service entrypoint functions
    - Proper error responses
  - Est: 1.5h

### 3.3 WebSocket Manager (in service)

- [ ] **Implement WebSocket manager**
  - File: `services/manual_sniping/core/websocket_manager.py`
  - Criteria:
    - Connection management per session
    - Broadcast to session clients
    - Ping/pong keep-alive
  - Est: 1.5h

### 3.4 Service Entrypoint

- [ ] **Implement service entrypoint functions**
  - File: `services/manual_sniping/entrypoint.py`
  - Criteria:
    - Public functions called by router
    - Initialize components (session manager, executor, etc.)
    - Lifecycle management (start/stop)
  - Est: 1.5h

### 3.5 API Gateway Integration

- [ ] **Register router in API gateway**
  - File: `services/api_gateway/main.py` (modify)
  - File: `services/api_gateway/routers/__init__.py` (modify)
  - Criteria: Router mounted at `/manual-sniping`
  - Est: 0.5h

### 3.6 Integration Tests

- [ ] **API integration tests**
  - File: `tests/integration/test_manual_sniping_api.py`
  - Criteria: Full request/response cycle, WebSocket events
  - Est: 2h

**Phase 3 Total: ~8h**

---

## Phase 4: Frontend Core Components (Day 6-7)

### 4.1 Feature Setup

- [ ] **Create feature directory structure**
  - Files: `viper-command-center/src/features/manual-sniping/`
  - Criteria: All directories, index.ts exports
  - Est: 0.5h

- [ ] **Define TypeScript types**
  - File: `viper-command-center/src/features/manual-sniping/types/index.ts`
  - Criteria: All interfaces matching backend schemas
  - Est: 1h

### 4.2 API Client

- [ ] **Implement REST client**
  - File: `viper-command-center/src/features/manual-sniping/api/client.ts`
  - Criteria: All endpoints, error handling, types
  - Est: 1h

- [ ] **Implement WebSocket hook**
  - File: `viper-command-center/src/features/manual-sniping/api/websocket.ts`
  - Criteria: Connection lifecycle, message handling, reconnection
  - Est: 1.5h

### 4.3 State Management

- [ ] **Implement Zustand store**
  - File: `viper-command-center/src/features/manual-sniping/stores/session-store.ts`
  - Criteria: All state, actions, persistence
  - Est: 2h

- [ ] **Implement transform hook**
  - File: `viper-command-center/src/features/manual-sniping/hooks/use-payload-transform.ts`
  - Criteria: React Query integration, debouncing
  - Est: 0.5h

### 4.4 Core UI Components

- [ ] **Implement ConverterPanel**
  - File: `viper-command-center/src/features/manual-sniping/components/converter-panel/ConverterPanel.tsx`
  - Criteria: Converter list, drag-and-drop chain, category badges
  - Est: 2h

- [ ] **Implement PayloadEditor**
  - File: `viper-command-center/src/features/manual-sniping/components/payload-editor/PayloadEditor.tsx`
  - Criteria: Tabs (payload/preview/target), Fire button
  - Est: 1.5h

- [ ] **Implement TransformPreview**
  - File: `viper-command-center/src/features/manual-sniping/components/payload-editor/TransformPreview.tsx`
  - Criteria: Step-by-step display, loading state
  - Est: 1h

- [ ] **Implement TargetConfig**
  - File: `viper-command-center/src/features/manual-sniping/components/payload-editor/TargetConfig.tsx`
  - Criteria: URL, protocol, headers, auth forms
  - Est: 1.5h

**Phase 4 Total: ~12.5h**

---

## Phase 5: Frontend Response & Integration (Day 8-9)

### 5.1 Response Components

- [ ] **Implement ResponsePanel**
  - File: `viper-command-center/src/features/manual-sniping/components/response-panel/ResponsePanel.tsx`
  - Criteria: Tabs (live/history/insights), stats badges, save button
  - Est: 1.5h

- [ ] **Implement LiveResponse**
  - File: `viper-command-center/src/features/manual-sniping/components/response-panel/LiveResponse.tsx`
  - Criteria: Streaming display, auto-scroll
  - Est: 1h

- [ ] **Implement SessionHistory**
  - File: `viper-command-center/src/features/manual-sniping/components/response-panel/SessionHistory.tsx`
  - Criteria: Attempt cards, expandable details, status indicators
  - Est: 1.5h

- [ ] **Implement AttemptCard**
  - File: `viper-command-center/src/features/manual-sniping/components/response-panel/AttemptCard.tsx`
  - Criteria: Collapsible, payload/response display, metadata
  - Est: 1h

### 5.2 Insights Components

- [ ] **Implement InsightsSidebar**
  - File: `viper-command-center/src/features/manual-sniping/components/insights-sidebar/InsightsSidebar.tsx`
  - Criteria: Pattern list, quick-insert buttons
  - Est: 1.5h

- [ ] **Implement PatternCard**
  - File: `viper-command-center/src/features/manual-sniping/components/insights-sidebar/PatternCard.tsx`
  - Criteria: Pattern display, copy payload button
  - Est: 1h

### 5.3 Main Page

- [ ] **Implement ManualSniping page**
  - File: `viper-command-center/src/pages/ManualSniping.tsx`
  - Criteria: Three-panel layout, WebSocket connection, session lifecycle
  - Est: 1.5h

- [ ] **Add page to router**
  - File: `viper-command-center/src/App.tsx` (modify)
  - Criteria: Route at `/manual-sniping`
  - Est: 0.25h

- [ ] **Add navigation link**
  - File: `viper-command-center/src/components/TopBar.tsx` (modify)
  - Criteria: Link in navigation
  - Est: 0.25h

### 5.4 Frontend Testing

- [ ] **Component tests**
  - Files: `viper-command-center/src/features/manual-sniping/**/*.test.tsx`
  - Criteria: Key components tested
  - Est: 2h

**Phase 5 Total: ~11.5h**

---

## Phase 6: Testing & Polish (Day 10)

### 6.1 End-to-End Testing

- [ ] **E2E test: Full attack flow**
  - Criteria:
    - Create session
    - Select converters
    - Enter payload
    - Configure target
    - Execute attack
    - Verify WebSocket response
    - Save session
  - Est: 2h

- [ ] **E2E test: Campaign insights integration**
  - Criteria:
    - Load campaign
    - View insights
    - Quick-insert payload
    - Execute attack
  - Est: 1h

### 6.2 Performance Optimization

- [ ] **Transform preview debouncing**
  - Criteria: <300ms debounce, no redundant API calls
  - Est: 0.5h

- [ ] **WebSocket reconnection testing**
  - Criteria: Reconnects within 5s, maintains state
  - Est: 0.5h

### 6.3 UX Polish

- [ ] **Loading states**
  - Criteria: All async operations show loading indicators
  - Est: 0.5h

- [ ] **Error handling**
  - Criteria: User-friendly error messages, toast notifications
  - Est: 0.5h

- [ ] **Keyboard shortcuts**
  - Criteria: Ctrl+Enter to fire, Ctrl+S to save
  - Est: 0.5h

### 6.4 Documentation

- [ ] **Update README.md**
  - Criteria: Manual Sniping section added
  - Est: 0.5h

- [ ] **API documentation**
  - Criteria: OpenAPI schema updated
  - Est: 0.5h

**Phase 6 Total: ~6.5h**

---

## Summary

| Phase | Focus | Estimated Hours |
|-------|-------|-----------------|
| 1 | Backend Models & Core | 8.5h |
| 2 | Backend Execution & Persistence | 9.5h |
| 3 | Backend API Layer | 8h |
| 4 | Frontend Core Components | 12.5h |
| 5 | Frontend Response & Integration | 11.5h |
| 6 | Testing & Polish | 6.5h |
| **Total** | | **56.5h** |

**Timeline**: ~7-10 working days for single developer

---

## Dependencies Between Phases

```
Phase 1 ──┬── Phase 2 ──┬── Phase 3
          │             │
          └─────────────┴── Phase 4 ── Phase 5 ── Phase 6
```

- Phases 1-3 (backend) can be developed in sequence
- Phase 4-5 (frontend) can start after Phase 3 API is defined
- Phase 6 requires both backend and frontend complete

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| PyRIT converter changes | Pin PyRIT version, wrap with stable interface |
| WebSocket complexity | Use established patterns from existing code |
| State management issues | Zustand simplifies vs Redux; persist subset only |
| S3 access issues | Mock S3 in dev; use LocalStack for integration tests |
| Performance | Debounce transforms; lazy load insights |

---

## Definition of Done (Feature Level)

- [ ] All Phase 1-6 tasks completed
- [ ] Unit test coverage >85%
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] No TypeScript errors
- [ ] No ESLint warnings
- [ ] Performance: <500ms transform preview, <100ms UI response
- [ ] Documentation updated
- [ ] Code reviewed and approved
