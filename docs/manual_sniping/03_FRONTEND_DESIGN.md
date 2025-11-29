# Manual Sniping Service - Frontend Design

> **Document**: 03_FRONTEND_DESIGN.md
> **Status**: Draft
> **Last Updated**: 2025-11-28

---

## Table of Contents
1. [Page Layout](#page-layout)
2. [Component Architecture](#component-architecture)
3. [State Management](#state-management)
4. [API Integration](#api-integration)
5. [WebSocket Integration](#websocket-integration)
6. [Component Specifications](#component-specifications)

---

## Page Layout

### Three-Panel Design

```
┌────────────────────────────────────────────────────────────────────────────┐
│  TopBar                                                        [Save] [?]  │
├────────────────┬───────────────────────────────┬───────────────────────────┤
│                │                               │                           │
│   Converter    │       Payload Editor          │     Response Panel        │
│    Panel       │                               │                           │
│                │  ┌─────────────────────────┐  │  ┌─────────────────────┐  │
│  [Converters]  │  │ Raw Payload             │  │  │ Real-time Response  │  │
│                │  │                         │  │  │                     │  │
│  ┌──────────┐  │  │ SELECT * FROM users...  │  │  │ Streaming...        │  │
│  │ Base64   │  │  │                         │  │  │                     │  │
│  │ ROT13    │  │  └─────────────────────────┘  │  └─────────────────────┘  │
│  │ URL      │  │                               │                           │
│  │ ...      │  │  ┌─────────────────────────┐  │  ┌─────────────────────┐  │
│  └──────────┘  │  │ Preview (step-by-step)  │  │  │ Session History     │  │
│                │  │                         │  │  │                     │  │
│  [Chain]       │  │ Step 1: Base64 → ...    │  │  │ Attempt #1 ✓        │  │
│  ┌──────────┐  │  │ Step 2: ROT13 → ...     │  │  │ Attempt #2 ✗        │  │
│  │ 1.Base64 │  │  │                         │  │  │ Attempt #3 ⏳       │  │
│  │ 2.ROT13  │  │  └─────────────────────────┘  │  │                     │  │
│  └──────────┘  │                               │  └─────────────────────┘  │
│                │  ┌─────────────────────────┐  │                           │
│  [Target]      │  │ Target Configuration    │  │  ┌─────────────────────┐  │
│  URL: [____]   │  │ URL | Headers | Auth    │  │  │ Campaign Insights   │  │
│  Protocol: ▼   │  └─────────────────────────┘  │  │                     │  │
│                │                               │  │ 🎯 SQL Injection    │  │
│                │        [🔥 FIRE]              │  │ 🎯 Prompt Leak      │  │
│                │                               │  │                     │  │
└────────────────┴───────────────────────────────┴───────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `>= 1280px` | Three columns (20% / 50% / 30%) |
| `1024-1279px` | Three columns (25% / 45% / 30%) |
| `768-1023px` | Two columns (stacked converter + payload, response below) |
| `< 768px` | Single column (tabs for panels) |

---

## Component Architecture

### File Structure

```
viper-command-center/src/
├── pages/
│   └── ManualSniping.tsx           # Main page component
├── features/
│   └── manual-sniping/
│       ├── index.ts                # Feature exports
│       ├── types/
│       │   └── index.ts            # TypeScript interfaces
│       ├── api/
│       │   ├── client.ts           # REST API client
│       │   └── websocket.ts        # WebSocket manager
│       ├── stores/
│       │   └── session-store.ts    # Zustand session state
│       ├── hooks/
│       │   ├── use-payload-transform.ts
│       │   └── use-websocket-stream.ts
│       └── components/
│           ├── converter-panel/
│           │   ├── ConverterPanel.tsx
│           │   ├── ConverterList.tsx
│           │   ├── ConverterChain.tsx
│           │   └── ChainItem.tsx
│           ├── payload-editor/
│           │   ├── PayloadEditor.tsx
│           │   ├── RawPayloadInput.tsx
│           │   ├── TransformPreview.tsx
│           │   └── TargetConfig.tsx
│           ├── response-panel/
│           │   ├── ResponsePanel.tsx
│           │   ├── LiveResponse.tsx
│           │   ├── SessionHistory.tsx
│           │   └── AttemptCard.tsx
│           └── insights-sidebar/
│               ├── InsightsSidebar.tsx
│               ├── PatternCard.tsx
│               └── QuickInsert.tsx
```

### Component Hierarchy

```
ManualSnipingPage
├── TopBar (existing)
├── ResizablePanelGroup
│   ├── ConverterPanel
│   │   ├── ConverterList
│   │   │   └── ConverterItem (x9)
│   │   ├── ConverterChain
│   │   │   └── ChainItem (draggable)
│   │   └── TargetQuickConfig
│   │
│   ├── PayloadEditor
│   │   ├── Tabs
│   │   │   ├── RawPayloadInput
│   │   │   ├── TransformPreview
│   │   │   └── TargetConfig
│   │   └── FireButton
│   │
│   └── ResponsePanel
│       ├── LiveResponse
│       ├── SessionHistory
│       │   └── AttemptCard (x N)
│       └── InsightsSidebar (collapsible)
│           └── PatternCard (x N)
```

---

## State Management

### Session Store (Zustand)

```typescript
// stores/session-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Attempt {
  attemptId: string;
  timestamp: Date;
  rawPayload: string;
  converterChain: string[];
  transformedPayload: string;
  targetUrl: string;
  status: 'pending' | 'executing' | 'success' | 'failed' | 'timeout';
  responseText?: string;
  responseStatusCode?: number;
  latencyMs?: number;
  error?: string;
}

interface Session {
  sessionId: string;
  name?: string;
  campaignId?: string;
  status: 'active' | 'saved' | 'expired';
  createdAt: Date;
  attempts: Attempt[];
  savedChains: string[][];
}

interface SessionState {
  // Current session
  session: Session | null;

  // UI state
  selectedConverters: string[];
  rawPayload: string;
  targetUrl: string;
  targetProtocol: 'http' | 'websocket';
  targetHeaders: Record<string, string>;
  authConfig: {
    type: 'none' | 'bearer' | 'api_key' | 'basic';
    token?: string;
    username?: string;
    password?: string;
  };

  // Transform preview
  transformResult: TransformResult | null;
  isTransforming: boolean;

  // Execution state
  isExecuting: boolean;
  currentAttemptId: string | null;
  liveResponse: string;

  // Actions
  createSession: (name?: string, campaignId?: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;

  addConverter: (name: string) => void;
  removeConverter: (index: number) => void;
  reorderConverters: (from: number, to: number) => void;
  clearChain: () => void;

  setPayload: (payload: string) => void;
  setTarget: (url: string, protocol?: string) => void;
  setAuth: (config: SessionState['authConfig']) => void;

  transform: () => Promise<void>;
  execute: () => Promise<void>;
  saveSession: (name?: string) => Promise<void>;

  appendLiveResponse: (text: string) => void;
  updateAttempt: (attemptId: string, updates: Partial<Attempt>) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      // Initial state
      session: null,
      selectedConverters: [],
      rawPayload: '',
      targetUrl: '',
      targetProtocol: 'http',
      targetHeaders: {},
      authConfig: { type: 'none' },
      transformResult: null,
      isTransforming: false,
      isExecuting: false,
      currentAttemptId: null,
      liveResponse: '',

      // Actions
      createSession: async (name, campaignId) => {
        const response = await apiClient.createSession({ name, campaignId });
        set({ session: response });
      },

      addConverter: (name) => {
        set((state) => ({
          selectedConverters: [...state.selectedConverters, name],
        }));
      },

      removeConverter: (index) => {
        set((state) => ({
          selectedConverters: state.selectedConverters.filter((_, i) => i !== index),
        }));
      },

      reorderConverters: (from, to) => {
        set((state) => {
          const converters = [...state.selectedConverters];
          const [removed] = converters.splice(from, 1);
          converters.splice(to, 0, removed);
          return { selectedConverters: converters };
        });
      },

      setPayload: (payload) => set({ rawPayload: payload }),

      transform: async () => {
        const { rawPayload, selectedConverters } = get();
        if (!rawPayload || selectedConverters.length === 0) return;

        set({ isTransforming: true });
        try {
          const result = await apiClient.transform({
            payload: rawPayload,
            converters: selectedConverters,
          });
          set({ transformResult: result });
        } finally {
          set({ isTransforming: false });
        }
      },

      execute: async () => {
        const state = get();
        if (!state.session || !state.rawPayload || !state.targetUrl) return;

        set({ isExecuting: true, liveResponse: '' });
        try {
          const response = await apiClient.execute({
            sessionId: state.session.sessionId,
            payload: state.rawPayload,
            converters: state.selectedConverters,
            target: {
              url: state.targetUrl,
              protocol: state.targetProtocol,
              headers: state.targetHeaders,
              auth: state.authConfig,
            },
          });
          set({ currentAttemptId: response.attemptId });
        } catch (error) {
          set({ isExecuting: false });
          throw error;
        }
      },

      appendLiveResponse: (text) => {
        set((state) => ({
          liveResponse: state.liveResponse + text,
        }));
      },

      updateAttempt: (attemptId, updates) => {
        set((state) => {
          if (!state.session) return state;
          return {
            session: {
              ...state.session,
              attempts: state.session.attempts.map((a) =>
                a.attemptId === attemptId ? { ...a, ...updates } : a
              ),
            },
            isExecuting: updates.status !== 'executing' ? false : state.isExecuting,
          };
        });
      },

      saveSession: async (name) => {
        const { session } = get();
        if (!session) return;

        const response = await apiClient.saveSession(session.sessionId, { name });
        set((state) => ({
          session: state.session ? {
            ...state.session,
            status: 'saved',
            s3Key: response.s3Key,
            scanId: response.scanId,
          } : null,
        }));
      },
    }),
    {
      name: 'manual-sniping-session',
      partialize: (state) => ({
        // Only persist these fields
        selectedConverters: state.selectedConverters,
        rawPayload: state.rawPayload,
        targetUrl: state.targetUrl,
        targetProtocol: state.targetProtocol,
        targetHeaders: state.targetHeaders,
        authConfig: state.authConfig,
      }),
    }
  )
);
```

### React Query Integration

```typescript
// hooks/use-payload-transform.ts
import { useQuery } from '@tanstack/react-query';
import { useSessionStore } from '../stores/session-store';
import { apiClient } from '../api/client';

export function usePayloadTransform() {
  const { rawPayload, selectedConverters } = useSessionStore();

  return useQuery({
    queryKey: ['transform', rawPayload, selectedConverters],
    queryFn: () => apiClient.transform({
      payload: rawPayload,
      converters: selectedConverters,
    }),
    enabled: rawPayload.length > 0 && selectedConverters.length > 0,
    staleTime: 1000 * 60, // Cache for 1 minute
    refetchOnWindowFocus: false,
  });
}
```

---

## API Integration

### REST Client

```typescript
// api/client.ts
import axios from 'axios';
import type {
  CreateSessionRequest,
  Session,
  TransformRequest,
  TransformResult,
  ExecuteRequest,
  ExecuteResponse,
  SaveSessionRequest,
  SaveSessionResponse,
  ConverterInfo,
  CampaignInsights,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiClient = {
  // Sessions
  createSession: async (data: CreateSessionRequest): Promise<Session> => {
    const response = await api.post('/api/manual-sniping/sessions', data);
    return response.data;
  },

  getSession: async (sessionId: string): Promise<Session> => {
    const response = await api.get(`/api/manual-sniping/sessions/${sessionId}`);
    return response.data;
  },

  listSessions: async (): Promise<{ sessions: Session[]; total: number }> => {
    const response = await api.get('/api/manual-sniping/sessions');
    return response.data;
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/manual-sniping/sessions/${sessionId}`);
  },

  // Transform
  transform: async (data: TransformRequest): Promise<TransformResult> => {
    const response = await api.post('/api/manual-sniping/transform', data);
    return response.data;
  },

  // Execute
  execute: async (data: ExecuteRequest): Promise<ExecuteResponse> => {
    const response = await api.post('/api/manual-sniping/execute', data);
    return response.data;
  },

  // Save
  saveSession: async (sessionId: string, data: SaveSessionRequest): Promise<SaveSessionResponse> => {
    const response = await api.post(`/api/manual-sniping/sessions/${sessionId}/save`, data);
    return response.data;
  },

  // Converters
  getConverters: async (): Promise<{ converters: ConverterInfo[]; categories: string[] }> => {
    const response = await api.get('/api/manual-sniping/converters');
    return response.data;
  },

  // Insights
  getInsights: async (campaignId: string): Promise<CampaignInsights> => {
    const response = await api.get(`/api/manual-sniping/insights/${campaignId}`);
    return response.data;
  },
};
```

---

## WebSocket Integration

### WebSocket Manager

```typescript
// api/websocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { useSessionStore } from '../stores/session-store';

type WSMessage =
  | { type: 'connected'; sessionId: string }
  | { type: 'progress'; attemptId: string; stage: string; data: Record<string, unknown> }
  | { type: 'response'; attemptId: string; data: { text: string; statusCode: number; latencyMs: number } }
  | { type: 'error'; attemptId: string; data: { message: string; code: string } };

export function useWebSocketStream(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const { appendLiveResponse, updateAttempt } = useSessionStore();

  const connect = useCallback(() => {
    if (!sessionId) return;

    const wsUrl = `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'}/api/manual-sniping/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      const message: WSMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'connected':
          console.log('Session connected:', message.sessionId);
          break;

        case 'progress':
          if (message.stage === 'executing') {
            appendLiveResponse(`Connecting to ${message.data.url}...\n`);
          } else if (message.stage === 'transformed') {
            appendLiveResponse(`Payload transformed (${message.data.steps} steps)\n`);
          }
          break;

        case 'response':
          updateAttempt(message.attemptId, {
            status: 'success',
            responseText: message.data.text,
            responseStatusCode: message.data.statusCode,
            latencyMs: message.data.latencyMs,
          });
          appendLiveResponse(`\n${message.data.text}`);
          break;

        case 'error':
          updateAttempt(message.attemptId, {
            status: 'failed',
            error: message.data.message,
          });
          appendLiveResponse(`\n❌ Error: ${message.data.message}`);
          break;
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Attempt reconnection
      if (reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++;
        setTimeout(connect, 1000 * reconnectAttempts.current);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [sessionId, appendLiveResponse, updateAttempt]);

  // Connect on mount / session change
  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  // Ping to keep alive
  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    reconnect: connect,
  };
}
```

---

## Component Specifications

### ConverterPanel

```tsx
// components/converter-panel/ConverterPanel.tsx
import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Trash2, GripVertical, Plus } from 'lucide-react';
import { DndContext, closestCenter, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useSessionStore } from '../../stores/session-store';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

const CATEGORY_COLORS = {
  encoding: 'bg-blue-500',
  obfuscation: 'bg-purple-500',
  escape: 'bg-green-500',
};

export function ConverterPanel() {
  const { selectedConverters, addConverter, removeConverter, reorderConverters } = useSessionStore();

  const { data: converterData } = useQuery({
    queryKey: ['converters'],
    queryFn: apiClient.getConverters,
  });

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = selectedConverters.indexOf(active.id as string);
      const newIndex = selectedConverters.indexOf(over.id as string);
      reorderConverters(oldIndex, newIndex);
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Converters</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden">
        {/* Available Converters */}
        <div className="flex-1 min-h-0">
          <p className="text-xs text-muted-foreground mb-2">Available</p>
          <ScrollArea className="h-[200px]">
            <div className="space-y-1">
              {converterData?.converters.map((converter) => (
                <div
                  key={converter.name}
                  className="flex items-center justify-between p-2 rounded hover:bg-muted cursor-pointer"
                  onClick={() => addConverter(converter.name)}
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className={`${CATEGORY_COLORS[converter.category]} text-white text-xs`}
                    >
                      {converter.category}
                    </Badge>
                    <span className="text-sm">{converter.displayName}</span>
                  </div>
                  <Plus className="h-4 w-4 text-muted-foreground" />
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Converter Chain */}
        <div className="flex-1 min-h-0">
          <p className="text-xs text-muted-foreground mb-2">
            Chain ({selectedConverters.length})
          </p>
          <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={selectedConverters} strategy={verticalListSortingStrategy}>
              <ScrollArea className="h-[200px]">
                <div className="space-y-1">
                  {selectedConverters.map((name, index) => (
                    <ChainItem
                      key={`${name}-${index}`}
                      id={name}
                      name={name}
                      index={index}
                      onRemove={() => removeConverter(index)}
                    />
                  ))}
                </div>
              </ScrollArea>
            </SortableContext>
          </DndContext>

          {selectedConverters.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">
              Click converters above to add to chain
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ChainItem({ id, name, index, onRemove }: {
  id: string;
  name: string;
  index: number;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 p-2 bg-muted rounded"
    >
      <button {...attributes} {...listeners} className="cursor-grab">
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </button>
      <span className="text-xs text-muted-foreground">{index + 1}.</span>
      <span className="flex-1 text-sm">{name.replace('Converter', '')}</span>
      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onRemove}>
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
}
```

### PayloadEditor

```tsx
// components/payload-editor/PayloadEditor.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Flame, Eye } from 'lucide-react';
import { useSessionStore } from '../../stores/session-store';
import { usePayloadTransform } from '../../hooks/use-payload-transform';
import { TransformPreview } from './TransformPreview';
import { TargetConfig } from './TargetConfig';

export function PayloadEditor() {
  const {
    rawPayload,
    setPayload,
    selectedConverters,
    isExecuting,
    execute,
  } = useSessionStore();

  const { data: transformResult, isLoading: isTransforming } = usePayloadTransform();

  const canFire = rawPayload.length > 0 && !isExecuting;

  return (
    <Card className="h-full flex flex-col">
      <CardContent className="flex-1 flex flex-col p-4 gap-4">
        <Tabs defaultValue="payload" className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="payload">Payload</TabsTrigger>
            <TabsTrigger value="preview" className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              Preview
              {isTransforming && <Loader2 className="h-3 w-3 animate-spin" />}
            </TabsTrigger>
            <TabsTrigger value="target">Target</TabsTrigger>
          </TabsList>

          <TabsContent value="payload" className="flex-1 mt-4">
            <Textarea
              placeholder="Enter your payload here...&#10;&#10;Example: SELECT * FROM users WHERE id='{{input}}'"
              value={rawPayload}
              onChange={(e) => setPayload(e.target.value)}
              className="h-full min-h-[300px] font-mono text-sm resize-none"
            />
          </TabsContent>

          <TabsContent value="preview" className="flex-1 mt-4 overflow-hidden">
            <TransformPreview
              result={transformResult}
              isLoading={isTransforming}
              converterCount={selectedConverters.length}
            />
          </TabsContent>

          <TabsContent value="target" className="flex-1 mt-4 overflow-auto">
            <TargetConfig />
          </TabsContent>
        </Tabs>

        {/* Fire Button */}
        <Button
          size="lg"
          className="w-full bg-red-600 hover:bg-red-700 text-white"
          disabled={!canFire}
          onClick={execute}
        >
          {isExecuting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <Flame className="mr-2 h-5 w-5" />
              FIRE
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
```

### ResponsePanel

```tsx
// components/response-panel/ResponsePanel.tsx
import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Terminal,
  History,
  Lightbulb,
  Save,
  Download,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';
import { useSessionStore } from '../../stores/session-store';
import { SessionHistory } from './SessionHistory';
import { InsightsSidebar } from '../insights-sidebar/InsightsSidebar';

export function ResponsePanel() {
  const {
    session,
    liveResponse,
    isExecuting,
    saveSession,
  } = useSessionStore();

  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveSession();
    } finally {
      setIsSaving(false);
    }
  };

  const stats = session?.attempts.length ? {
    total: session.attempts.length,
    success: session.attempts.filter(a => a.status === 'success').length,
    failed: session.attempts.filter(a => a.status === 'failed').length,
  } : null;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">Response</CardTitle>
        <div className="flex items-center gap-2">
          {stats && (
            <div className="flex items-center gap-1 text-xs">
              <Badge variant="outline" className="gap-1">
                <CheckCircle2 className="h-3 w-3 text-green-500" />
                {stats.success}
              </Badge>
              <Badge variant="outline" className="gap-1">
                <XCircle className="h-3 w-3 text-red-500" />
                {stats.failed}
              </Badge>
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleSave}
            disabled={!session || session.status === 'saved' || isSaving}
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col overflow-hidden p-4 pt-0">
        <Tabs defaultValue="live" className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="live" className="flex items-center gap-1">
              <Terminal className="h-3 w-3" />
              Live
              {isExecuting && <Loader2 className="h-3 w-3 animate-spin" />}
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-1">
              <History className="h-3 w-3" />
              History
            </TabsTrigger>
            <TabsTrigger value="insights" className="flex items-center gap-1">
              <Lightbulb className="h-3 w-3" />
              Insights
            </TabsTrigger>
          </TabsList>

          <TabsContent value="live" className="flex-1 mt-4">
            <ScrollArea className="h-full">
              <pre className="font-mono text-sm whitespace-pre-wrap p-4 bg-muted rounded-lg min-h-[200px]">
                {liveResponse || (
                  <span className="text-muted-foreground">
                    Response will appear here after firing...
                  </span>
                )}
              </pre>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="history" className="flex-1 mt-4 overflow-hidden">
            <SessionHistory />
          </TabsContent>

          <TabsContent value="insights" className="flex-1 mt-4 overflow-hidden">
            <InsightsSidebar />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
```

---

## Main Page Component

```tsx
// pages/ManualSniping.tsx
import { useEffect } from 'react';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { TopBar } from '@/components/TopBar';
import { ConverterPanel } from '@/features/manual-sniping/components/converter-panel/ConverterPanel';
import { PayloadEditor } from '@/features/manual-sniping/components/payload-editor/PayloadEditor';
import { ResponsePanel } from '@/features/manual-sniping/components/response-panel/ResponsePanel';
import { useSessionStore } from '@/features/manual-sniping/stores/session-store';
import { useWebSocketStream } from '@/features/manual-sniping/api/websocket';
import { useToast } from '@/components/ui/use-toast';

export default function ManualSnipingPage() {
  const { session, createSession } = useSessionStore();
  const { toast } = useToast();

  // Create session on mount if none exists
  useEffect(() => {
    if (!session) {
      createSession().catch((error) => {
        toast({
          title: 'Failed to create session',
          description: error.message,
          variant: 'destructive',
        });
      });
    }
  }, [session, createSession, toast]);

  // Connect WebSocket
  useWebSocketStream(session?.sessionId ?? null);

  return (
    <div className="h-screen flex flex-col bg-background">
      <TopBar />

      <main className="flex-1 overflow-hidden p-4">
        <ResizablePanelGroup direction="horizontal" className="h-full rounded-lg border">
          {/* Left Panel - Converters */}
          <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
            <ConverterPanel />
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Center Panel - Payload Editor */}
          <ResizablePanel defaultSize={50} minSize={30}>
            <PayloadEditor />
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right Panel - Response */}
          <ResizablePanel defaultSize={30} minSize={20}>
            <ResponsePanel />
          </ResizablePanel>
        </ResizablePanelGroup>
      </main>
    </div>
  );
}
```

---

## Next Document

Continue to [04_IMPLEMENTATION_CHECKLIST.md](./04_IMPLEMENTATION_CHECKLIST.md) for phase-by-phase implementation tasks.
