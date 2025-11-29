# Manual Sniping Service - Implementation Plan

> **Status**: Planning Phase
> **Created**: 2025-11-28
> **Owner**: Development Team

## Overview

The Manual Sniping Service is the **"bread and butter"** feature of Aspexa Automa - a hands-on, real-time attack interface that gives security researchers complete control over payload crafting, converter chaining, and attack execution.

Unlike the automated Snipers service (LangGraph workflow), Manual Sniping puts the human in direct control while providing intelligent tooling support.

---

## Document Index

| # | Document | Purpose |
|---|----------|---------|
| 01 | [ARCHITECTURE.md](./01_ARCHITECTURE.md) | Service architecture, data models, component design |
| 02 | [API_SPECIFICATIONS.md](./02_API_SPECIFICATIONS.md) | REST endpoints, WebSocket protocol, data contracts |
| 03 | [FRONTEND_DESIGN.md](./03_FRONTEND_DESIGN.md) | React components, state management, UI/UX |
| 04 | [IMPLEMENTATION_CHECKLIST.md](./04_IMPLEMENTATION_CHECKLIST.md) | Phase-by-phase tasks with acceptance criteria |
| 05 | [KNOWN_ISSUES.md](./05_KNOWN_ISSUES.md) | Known issues, root cause analysis, fix plans |

---

## Feature Requirements

### Core Capabilities

1. **Converter Selection & Chaining**
   - Select from 9 available converters (Base64, ROT13, Caesar, URL, TextToHex, Unicode, HtmlEntity, JsonEscape, XmlEscape)
   - Chain multiple converters in custom order
   - Preview payload transformation at each step
   - Save favorite converter chains

2. **Real-Time Attack Execution**
   - Send payloads to HTTP or WebSocket targets
   - Stream responses back in real-time via WebSocket
   - Display response metadata (status, timing, headers)
   - Support for authentication (Bearer, API Key, Basic)

3. **Session Management**
   - Accumulate all requests/responses in memory during session
   - Store metadata (timestamps, converter chains, target info)
   - Keep session in JSON format until user saves
   - Persist to S3 only when user clicks "Save"

4. **Campaign Insights Integration**
   - Load intelligence from Cartographer reconnaissance
   - Display vulnerability patterns from Swarm/Garak scans
   - Show successful payloads from automated Snipers runs
   - Quick-insert discovered patterns into payload editor

---

## Technical Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| WebSocket | FastAPI WebSocket + Starlette |
| Converters | PyRIT PromptConverter (reuse from Snipers) |
| State | In-memory Dict with TTL cleanup |
| Persistence | S3 via `libs/persistence/s3.py` |
| HTTP Client | `libs/connectivity/` async client |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Next.js + React |
| UI Library | Shadcn UI (Tailwind-based) |
| State | Zustand (client) + React Query (server) |
| WebSocket | Native WebSocket with reconnection |
| Drag & Drop | @dnd-kit/core |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Viper Command Center                               │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    Manual Sniping Page                             │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │  │
│  │  │  Converter   │ │   Payload    │ │   Response Stream          │  │  │
│  │  │   Chain      │ │   Editor     │ │   + Session History        │  │  │
│  │  │   Builder    │ │   + Preview  │ │   + Campaign Insights      │  │  │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTP + WebSocket
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        API Gateway                                        │
│  services/api_gateway/routers/manual_sniping.py                          │
│  services/api_gateway/schemas/manual_sniping.py                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Prefix: /manual-sniping                                           │  │
│  │  - POST /sessions          Create new session                      │  │
│  │  - GET  /sessions/{id}     Get session state                       │  │
│  │  - POST /transform         Preview converter chain                 │  │
│  │  - POST /execute           Fire attack (async)                     │  │
│  │  - POST /sessions/{id}/save  Persist to S3                         │  │
│  │  - GET  /insights/{campaign_id}  Load campaign intelligence        │  │
│  │  - WS   /ws/{session_id}   Real-time streaming                     │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ calls entrypoint functions
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Manual Sniping Service                                 │
│  services/manual_sniping/                                                │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────────────────┐  │
│  │ Session Manager│ │ Converter Chain│ │ Attack Executor              │  │
│  │ (In-Memory)    │ │ (PyRIT Bridge) │ │ (HTTP/WS via connectivity)   │  │
│  └────────────────┘ └────────────────┘ └──────────────────────────────┘  │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────────────────┐  │
│  │ Insights Loader│ │ S3 Persistence │ │ WebSocket Manager            │  │
│  │ (Campaign Data)│ │ (On User Save) │ │ (Connection tracking)        │  │
│  └────────────────┘ └────────────────┘ └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Shared Libraries                                   │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────────────────┐  │
│  │ libs/          │ │ libs/          │ │ services/snipers/tools/      │  │
│  │ connectivity/  │ │ persistence/   │ │ pyrit_bridge.py              │  │
│  │ (HTTP/WS)      │ │ s3.py          │ │ converters/                  │  │
│  └────────────────┘ └────────────────┘ └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Attack Execution Flow

```
1. User builds converter chain: [Base64, ROT13, HtmlEntity]
2. User enters payload: "SELECT * FROM users"
3. User clicks "Transform Preview"
   → Frontend calls POST /transform
   → Backend applies chain sequentially
   → Returns: { steps: [{input, output, converter}...], final: "..." }
4. User reviews preview, clicks "Fire"
   → Frontend calls POST /execute with session_id
   → Backend queues attack, returns attack_id immediately
5. Backend executes attack asynchronously
   → Sends progress via WebSocket: { type: "progress", ... }
   → Sends response via WebSocket: { type: "response", ... }
6. Frontend displays streaming response
7. Session accumulates in memory (auto-saved to session state)
8. User clicks "Save to Campaign"
   → Frontend calls POST /sessions/{id}/save
   → Backend persists to S3
   → Updates campaign if linked
```

---

## Implementation Phases

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **1** | Backend Core | 3 days | Models, Session Manager, Converter Chain |
| **2** | Backend API | 2 days | REST endpoints, WebSocket handler |
| **3** | Frontend Core | 3 days | Page layout, Converter Panel, Payload Editor |
| **4** | Frontend Integration | 2 days | WebSocket, API calls, State management |
| **5** | Persistence & Insights | 2 days | S3 save, Campaign loader |
| **6** | Testing & Polish | 2 days | E2E tests, UX refinements |

**Total Estimate**: ~14 days (2-3 weeks with buffer)

---

## Success Criteria

- [ ] User can select and chain converters visually
- [ ] Payload preview updates in real-time as chain changes
- [ ] Attack executes and streams response back immediately
- [ ] Session persists across page refreshes (until browser close)
- [ ] "Save" persists session to S3 with full metadata
- [ ] Campaign insights load and display relevant patterns
- [ ] <500ms response time for transform preview
- [ ] WebSocket reconnects automatically on disconnect

---

## Dependencies

### Existing Code to Reuse
- `services/snipers/tools/pyrit_bridge.py` - ConverterFactory, PayloadTransformer
- `services/snipers/tools/converters/` - Custom converters (Html, Json, Xml)
- `libs/connectivity/` - HTTP/WebSocket clients
- `libs/persistence/s3.py` - S3PersistenceAdapter
- `libs/persistence/sqlite/` - CampaignRepository

### New Code Required

**API Gateway (router + schemas):**
- `services/api_gateway/routers/manual_sniping.py` - REST + WebSocket router
- `services/api_gateway/schemas/manual_sniping.py` - Request/Response models

**Service (business logic):**
- `services/manual_sniping/` - New service directory
- `services/manual_sniping/entrypoint.py` - Public functions for router

**Frontend:**
- `viper-command-center/src/pages/ManualSniping.tsx` - New page
- `viper-command-center/src/features/manual-sniping/` - Feature module

---

## Next Steps

1. **Read**: [01_ARCHITECTURE.md](./01_ARCHITECTURE.md) for detailed service design
2. **Review**: [02_API_SPECIFICATIONS.md](./02_API_SPECIFICATIONS.md) for API contracts
3. **Study**: [03_FRONTEND_DESIGN.md](./03_FRONTEND_DESIGN.md) for UI components
4. **Execute**: [04_IMPLEMENTATION_CHECKLIST.md](./04_IMPLEMENTATION_CHECKLIST.md) for task tracking
