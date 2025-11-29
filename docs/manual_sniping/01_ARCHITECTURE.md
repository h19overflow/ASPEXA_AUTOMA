# Manual Sniping Service - Architecture Design

> **Document**: 01_ARCHITECTURE.md
> **Status**: Draft
> **Last Updated**: 2025-11-28

---

## Table of Contents
1. [Service Structure](#service-structure)
2. [Data Models](#data-models)
3. [Core Components](#core-components)
4. [Session Management](#session-management)
5. [Converter Integration](#converter-integration)
6. [Execution Pipeline](#execution-pipeline)

---

## Service Structure

**Note**: The API router lives in `services/api_gateway/routers/` following the existing pattern (like `exploit.py`, `scan.py`, etc.). The service logic lives in `services/manual_sniping/`.

```
services/
├── api_gateway/
│   ├── routers/
│   │   ├── manual_sniping.py       # NEW: FastAPI router (REST + WebSocket)
│   │   ├── exploit.py              # Existing
│   │   ├── scan.py                 # Existing
│   │   └── ...
│   ├── schemas/
│   │   ├── manual_sniping.py       # NEW: Request/Response schemas
│   │   └── ...
│   └── main.py                     # Add: include manual_sniping router
│
└── manual_sniping/                 # NEW: Service logic
    ├── __init__.py                 # Package exports
    ├── entrypoint.py               # Public functions called by router
    ├── models/
    │   ├── __init__.py
    │   ├── session.py              # Session, Attempt, AttackResult models
    │   ├── converter.py            # ConverterChain, TransformStep models
    │   ├── target.py               # TargetConfig, AuthConfig models
    │   └── insights.py             # CampaignInsights, VulnerabilityPattern
    ├── core/
    │   ├── __init__.py
    │   ├── session_manager.py      # In-memory session store with TTL
    │   ├── converter_chain.py      # Chain builder and executor
    │   └── websocket_manager.py    # WebSocket connection manager
    ├── execution/
    │   ├── __init__.py
    │   ├── executor.py             # Attack orchestrator
    │   ├── http_executor.py        # HTTP target execution
    │   └── websocket_executor.py   # WebSocket target execution
    ├── persistence/
    │   ├── __init__.py
    │   └── s3_adapter.py           # S3 persistence for sessions
    └── insights/
        ├── __init__.py
        └── campaign_loader.py      # Load campaign intelligence
```

**Line Count Targets** (per CLAUDE.md: max 150 lines/file):
- `session_manager.py`: ~120 lines
- `converter_chain.py`: ~80 lines
- `executor.py`: ~100 lines
- `router.py`: ~140 lines
- `websocket_handler.py`: ~120 lines

---

## Data Models

### Session Models (`models/session.py`)

```python
"""Session state models for Manual Sniping.

Tracks all attempts within a session until user persists to S3.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class SessionStatus(str, Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    SAVED = "saved"
    EXPIRED = "expired"


class AttemptStatus(str, Enum):
    """Individual attack attempt states."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AttackAttempt(BaseModel):
    """Single attack attempt within a session."""
    attempt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Input
    raw_payload: str
    converter_chain: List[str]  # ["Base64Converter", "ROT13Converter"]
    transformed_payload: str

    # Target
    target_url: str
    protocol: str  # "http" or "websocket"
    headers: Dict[str, str] = Field(default_factory=dict)

    # Output
    status: AttemptStatus = AttemptStatus.PENDING
    response_text: Optional[str] = None
    response_status_code: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

    # Metadata
    transform_errors: List[str] = Field(default_factory=list)


class Session(BaseModel):
    """Manual sniping session container.

    Accumulates attempts in memory until user saves to S3.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # State
    status: SessionStatus = SessionStatus.ACTIVE

    # Configuration
    name: Optional[str] = None  # User-provided session name
    campaign_id: Optional[str] = None  # Link to parent campaign

    # Accumulated data
    attempts: List[AttackAttempt] = Field(default_factory=list)

    # Favorites/Presets
    saved_chains: List[List[str]] = Field(default_factory=list)

    # Persistence metadata (populated on save)
    s3_key: Optional[str] = None
    scan_id: Optional[str] = None

    def add_attempt(self, attempt: AttackAttempt) -> None:
        """Add an attempt and update timestamp."""
        self.attempts.append(attempt)
        self.updated_at = datetime.utcnow()

    def get_stats(self) -> Dict[str, Any]:
        """Calculate session statistics."""
        total = len(self.attempts)
        success = sum(1 for a in self.attempts if a.status == AttemptStatus.SUCCESS)
        failed = sum(1 for a in self.attempts if a.status == AttemptStatus.FAILED)
        avg_latency = (
            sum(a.latency_ms for a in self.attempts if a.latency_ms)
            / max(1, sum(1 for a in self.attempts if a.latency_ms))
        )
        return {
            "total_attempts": total,
            "successful": success,
            "failed": failed,
            "success_rate": success / max(1, total),
            "avg_latency_ms": avg_latency,
        }
```

### Converter Models (`models/converter.py`)

```python
"""Converter chain models for payload transformation."""
from typing import List, Optional
from pydantic import BaseModel, Field


class TransformStep(BaseModel):
    """Single step in a transformation chain."""
    converter_name: str
    input_payload: str
    output_payload: str
    success: bool = True
    error: Optional[str] = None


class TransformResult(BaseModel):
    """Complete transformation result with all steps."""
    original_payload: str
    final_payload: str
    steps: List[TransformStep]
    total_converters: int
    successful_converters: int
    errors: List[str] = Field(default_factory=list)


class ConverterInfo(BaseModel):
    """Converter metadata for UI display."""
    name: str
    display_name: str
    description: str
    category: str  # "encoding", "obfuscation", "escape"
    example_input: str
    example_output: str


class ConverterChainConfig(BaseModel):
    """User-defined converter chain configuration."""
    chain_id: Optional[str] = None
    name: Optional[str] = None  # User-friendly name
    converters: List[str]  # Ordered list of converter names
    is_favorite: bool = False
```

### Target Models (`models/target.py`)

```python
"""Target configuration models."""
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field, HttpUrl


class Protocol(str, Enum):
    """Supported target protocols."""
    HTTP = "http"
    WEBSOCKET = "websocket"


class AuthType(str, Enum):
    """Supported authentication types."""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class AuthConfig(BaseModel):
    """Authentication configuration."""
    auth_type: AuthType = AuthType.NONE
    token: Optional[str] = None  # For bearer/api_key
    username: Optional[str] = None  # For basic auth
    password: Optional[str] = None  # For basic auth
    header_name: str = "Authorization"  # Custom header for API key


class TargetConfig(BaseModel):
    """Complete target configuration."""
    url: str
    protocol: Protocol = Protocol.HTTP
    headers: Dict[str, str] = Field(default_factory=dict)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    timeout_seconds: int = 30
    message_field: str = "message"  # JSON key for payload
```

### Insights Models (`models/insights.py`)

```python
"""Campaign insights models for intelligence display."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VulnerabilityPattern(BaseModel):
    """Extracted vulnerability pattern from scans."""
    pattern_id: str
    source: str  # "cartographer", "swarm", "snipers"
    vulnerability_type: str
    description: str
    successful_payloads: List[str] = Field(default_factory=list)
    confidence: float  # 0.0 - 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReconInsights(BaseModel):
    """Intelligence from Cartographer phase."""
    system_prompt_leak: Optional[str] = None
    detected_tools: List[Dict[str, Any]] = Field(default_factory=list)
    infrastructure: Dict[str, Any] = Field(default_factory=dict)
    auth_structure: Dict[str, Any] = Field(default_factory=dict)


class ScanInsights(BaseModel):
    """Intelligence from Swarm/Garak phase."""
    vulnerable_probes: List[str] = Field(default_factory=list)
    successful_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    detector_scores: Dict[str, float] = Field(default_factory=dict)


class ExploitInsights(BaseModel):
    """Intelligence from automated Snipers phase."""
    patterns_found: List[VulnerabilityPattern] = Field(default_factory=list)
    converter_effectiveness: Dict[str, float] = Field(default_factory=dict)


class CampaignInsights(BaseModel):
    """Aggregated campaign intelligence."""
    campaign_id: str
    campaign_name: Optional[str] = None
    recon: Optional[ReconInsights] = None
    scan: Optional[ScanInsights] = None
    exploit: Optional[ExploitInsights] = None
    patterns: List[VulnerabilityPattern] = Field(default_factory=list)
```

---

## Core Components

### Session Manager (`core/session_manager.py`)

```python
"""In-memory session management with TTL cleanup.

Sessions are stored in memory until user explicitly saves to S3.
Implements automatic cleanup of expired sessions.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

from ..models.session import Session, SessionStatus, AttackAttempt

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages in-memory session state with TTL.

    Thread-safe session store with automatic expiration.
    """

    DEFAULT_TTL_HOURS = 24
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(self, ttl_hours: int = DEFAULT_TTL_HOURS):
        self._sessions: Dict[str, Session] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started with %d hour TTL", self._ttl.total_seconds() / 3600)

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session manager stopped")

    def create_session(
        self,
        name: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        session = Session(name=name, campaign_id=campaign_id)
        self._sessions[session.session_id] = session
        logger.info("Created session %s", session.session_id)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        session = self._sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            return session
        return None

    def add_attempt(self, session_id: str, attempt: AttackAttempt) -> bool:
        """Add an attempt to a session."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.add_attempt(attempt)
        return True

    def update_attempt(
        self,
        session_id: str,
        attempt_id: str,
        **updates
    ) -> bool:
        """Update an existing attempt."""
        session = self.get_session(session_id)
        if not session:
            return False

        for attempt in session.attempts:
            if attempt.attempt_id == attempt_id:
                for key, value in updates.items():
                    if hasattr(attempt, key):
                        setattr(attempt, key, value)
                session.updated_at = datetime.utcnow()
                return True
        return False

    def mark_saved(self, session_id: str, s3_key: str, scan_id: str) -> bool:
        """Mark a session as saved to S3."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.status = SessionStatus.SAVED
        session.s3_key = s3_key
        session.scan_id = scan_id
        session.updated_at = datetime.utcnow()
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Deleted session %s", session_id)
            return True
        return False

    def list_sessions(self) -> list[Session]:
        """List all active sessions."""
        return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error: %s", e)

    def _cleanup_expired(self) -> int:
        """Remove sessions past TTL."""
        now = datetime.utcnow()
        expired = [
            sid for sid, s in self._sessions.items()
            if s.status == SessionStatus.ACTIVE
            and (now - s.updated_at) > self._ttl
        ]
        for sid in expired:
            self._sessions[sid].status = SessionStatus.EXPIRED
            del self._sessions[sid]

        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
        return len(expired)
```

### Converter Chain (`core/converter_chain.py`)

```python
"""Converter chain builder and executor.

Reuses PyRIT bridge from automated Snipers service.
"""
from typing import List, Tuple

from services.snipers.tools.pyrit_bridge import ConverterFactory, PayloadTransformer
from ..models.converter import TransformResult, TransformStep, ConverterInfo


# Converter metadata for UI
CONVERTER_CATALOG: List[ConverterInfo] = [
    ConverterInfo(
        name="Base64Converter",
        display_name="Base64",
        description="Encode payload as Base64",
        category="encoding",
        example_input="hello",
        example_output="aGVsbG8=",
    ),
    ConverterInfo(
        name="ROT13Converter",
        display_name="ROT13",
        description="Apply ROT13 cipher (rotate 13 positions)",
        category="obfuscation",
        example_input="hello",
        example_output="uryyb",
    ),
    ConverterInfo(
        name="CaesarConverter",
        display_name="Caesar",
        description="Apply Caesar cipher (configurable shift)",
        category="obfuscation",
        example_input="hello",
        example_output="khoor",
    ),
    ConverterInfo(
        name="UrlConverter",
        display_name="URL Encode",
        description="URL-encode special characters",
        category="encoding",
        example_input="<script>",
        example_output="%3Cscript%3E",
    ),
    ConverterInfo(
        name="TextToHexConverter",
        display_name="Hex",
        description="Convert text to hexadecimal",
        category="encoding",
        example_input="AB",
        example_output="4142",
    ),
    ConverterInfo(
        name="UnicodeConverter",
        display_name="Unicode",
        description="Convert to Unicode escape sequences",
        category="encoding",
        example_input="<",
        example_output="\\u003c",
    ),
    ConverterInfo(
        name="HtmlEntityConverter",
        display_name="HTML Entity",
        description="Encode as HTML entities (4 strategies)",
        category="escape",
        example_input="<div>",
        example_output="&#60;div&#62;",
    ),
    ConverterInfo(
        name="JsonEscapeConverter",
        display_name="JSON Escape",
        description="Escape for JSON strings (3 strategies)",
        category="escape",
        example_input='"test"',
        example_output='\\"test\\"',
    ),
    ConverterInfo(
        name="XmlEscapeConverter",
        display_name="XML Escape",
        description="Escape for XML content (4 strategies)",
        category="escape",
        example_input="<tag>",
        example_output="&lt;tag&gt;",
    ),
]


class ConverterChainExecutor:
    """Executes converter chains with step-by-step tracking.

    Wraps PayloadTransformer to provide detailed transformation steps.
    """

    def __init__(self):
        self._factory = ConverterFactory()
        self._transformer = PayloadTransformer(self._factory)

    def get_available_converters(self) -> List[ConverterInfo]:
        """Return metadata for all available converters."""
        return CONVERTER_CATALOG

    async def transform_with_steps(
        self,
        payload: str,
        converter_names: List[str]
    ) -> TransformResult:
        """Apply converter chain with step-by-step results.

        Args:
            payload: Original payload text
            converter_names: Ordered list of converter names

        Returns:
            TransformResult with each step's input/output
        """
        steps: List[TransformStep] = []
        current = payload
        errors: List[str] = []

        for name in converter_names:
            converter = self._factory.get_converter(name)
            if converter is None:
                error = f"Converter '{name}' not available"
                errors.append(error)
                steps.append(TransformStep(
                    converter_name=name,
                    input_payload=current,
                    output_payload=current,
                    success=False,
                    error=error,
                ))
                continue

            try:
                result = await converter.convert_async(prompt=current)
                output = result.output_text
                steps.append(TransformStep(
                    converter_name=name,
                    input_payload=current,
                    output_payload=output,
                    success=True,
                ))
                current = output
            except Exception as e:
                error = f"Converter '{name}' failed: {str(e)}"
                errors.append(error)
                steps.append(TransformStep(
                    converter_name=name,
                    input_payload=current,
                    output_payload=current,
                    success=False,
                    error=error,
                ))

        return TransformResult(
            original_payload=payload,
            final_payload=current,
            steps=steps,
            total_converters=len(converter_names),
            successful_converters=sum(1 for s in steps if s.success),
            errors=errors,
        )

    def transform_sync(
        self,
        payload: str,
        converter_names: List[str]
    ) -> Tuple[str, List[str]]:
        """Synchronous transform (delegates to PayloadTransformer)."""
        return self._transformer.transform(payload, converter_names)
```

---

## Execution Pipeline

### Attack Executor (`execution/executor.py`)

```python
"""Attack execution orchestrator.

Coordinates converter transformation and target execution.
"""
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import logging

from libs.connectivity import AsyncHttpClient, ConnectionConfig
from ..models.session import AttackAttempt, AttemptStatus
from ..models.target import TargetConfig, Protocol, AuthType
from ..core.converter_chain import ConverterChainExecutor

logger = logging.getLogger(__name__)


class AttackExecutor:
    """Orchestrates attack execution with streaming callbacks.

    Applies converter chain, sends to target, streams response.
    """

    def __init__(self):
        self._converter_chain = ConverterChainExecutor()

    async def execute(
        self,
        raw_payload: str,
        converter_names: list[str],
        target: TargetConfig,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> AttackAttempt:
        """Execute an attack with optional progress callbacks.

        Args:
            raw_payload: Original payload text
            converter_names: Converters to apply
            target: Target configuration
            on_progress: Callback for progress updates

        Returns:
            Completed AttackAttempt
        """
        attempt = AttackAttempt(
            raw_payload=raw_payload,
            converter_chain=converter_names,
            transformed_payload="",
            target_url=target.url,
            protocol=target.protocol.value,
            headers=target.headers.copy(),
        )

        # Step 1: Transform payload
        if on_progress:
            on_progress("transforming", {"converters": converter_names})

        transform_result = await self._converter_chain.transform_with_steps(
            raw_payload, converter_names
        )
        attempt.transformed_payload = transform_result.final_payload
        attempt.transform_errors = transform_result.errors

        if on_progress:
            on_progress("transformed", {
                "final_payload": transform_result.final_payload,
                "steps": len(transform_result.steps),
            })

        # Step 2: Build connection config
        config = self._build_config(target)

        # Step 3: Execute based on protocol
        attempt.status = AttemptStatus.EXECUTING
        if on_progress:
            on_progress("executing", {"url": target.url})

        try:
            if target.protocol == Protocol.HTTP:
                await self._execute_http(attempt, config, on_progress)
            else:
                await self._execute_websocket(attempt, config, on_progress)

        except Exception as e:
            attempt.status = AttemptStatus.FAILED
            attempt.error_message = str(e)
            logger.error("Attack failed: %s", e)
            if on_progress:
                on_progress("error", {"message": str(e)})

        return attempt

    def _build_config(self, target: TargetConfig) -> ConnectionConfig:
        """Build connection config from target config."""
        headers = target.headers.copy()

        # Apply authentication
        if target.auth.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {target.auth.token}"
        elif target.auth.auth_type == AuthType.API_KEY:
            headers[target.auth.header_name] = target.auth.token
        elif target.auth.auth_type == AuthType.BASIC:
            import base64
            creds = f"{target.auth.username}:{target.auth.password}"
            encoded = base64.b64encode(creds.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return ConnectionConfig(
            endpoint_url=target.url,
            headers=headers,
            timeout=target.timeout_seconds,
            message_field=target.message_field,
        )

    async def _execute_http(
        self,
        attempt: AttackAttempt,
        config: ConnectionConfig,
        on_progress: Optional[Callable],
    ) -> None:
        """Execute HTTP attack."""
        start = datetime.utcnow()

        async with AsyncHttpClient(config) as client:
            response = await client.send(attempt.transformed_payload)

        attempt.latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        attempt.response_text = response.text
        attempt.response_status_code = response.status_code
        attempt.response_headers = dict(response.raw.get("headers", {}))
        attempt.status = AttemptStatus.SUCCESS

        if on_progress:
            on_progress("response", {
                "text": response.text,
                "status_code": response.status_code,
                "latency_ms": attempt.latency_ms,
            })

    async def _execute_websocket(
        self,
        attempt: AttackAttempt,
        config: ConnectionConfig,
        on_progress: Optional[Callable],
    ) -> None:
        """Execute WebSocket attack."""
        import websockets

        start = datetime.utcnow()

        async with websockets.connect(
            config.endpoint_url,
            extra_headers=config.headers,
        ) as ws:
            await ws.send(attempt.transformed_payload)
            response = await asyncio.wait_for(
                ws.recv(),
                timeout=config.timeout
            )

        attempt.latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        attempt.response_text = response
        attempt.status = AttemptStatus.SUCCESS

        if on_progress:
            on_progress("response", {
                "text": response,
                "latency_ms": attempt.latency_ms,
            })
```

---

## Persistence Integration

### S3 Adapter (`persistence/s3_adapter.py`)

```python
"""S3 persistence for Manual Sniping sessions.

Reuses libs/persistence/s3.py for storage operations.
"""
from typing import Optional
import logging

from libs.persistence.s3 import S3PersistenceAdapter
from libs.persistence.contracts import AuditPhase
from libs.persistence.scan_models import ScanType
from libs.persistence.sqlite.campaign_repository import CampaignRepository

from ..models.session import Session

logger = logging.getLogger(__name__)


class ManualSnipingS3Adapter:
    """Persists Manual Sniping sessions to S3."""

    def __init__(self, s3_adapter: Optional[S3PersistenceAdapter] = None):
        self._s3 = s3_adapter or S3PersistenceAdapter(
            bucket_name="aspexa-automa-audit-lake"
        )
        self._campaign_repo = CampaignRepository()

    async def save_session(
        self,
        session: Session,
    ) -> tuple[str, str]:
        """Persist session to S3.

        Args:
            session: Session to persist

        Returns:
            Tuple of (s3_key, scan_id)
        """
        # Generate scan_id from session
        scan_id = f"manual-snipe-{session.session_id[:8]}"

        # Build artifact data
        data = session.model_dump(mode="json")
        data["type"] = "manual_sniping_session"
        data["stats"] = session.get_stats()

        # Determine audit_id (use campaign_id if linked, else session_id)
        audit_id = session.campaign_id or session.session_id

        # Save to S3
        metadata = await self._s3.save_artifact(
            audit_id=audit_id,
            phase=AuditPhase.EXPLOIT,  # Manual sniping is exploitation
            filename=f"{scan_id}.json",
            data=data,
        )

        # Update campaign if linked
        if session.campaign_id:
            try:
                campaign = self._campaign_repo.get(session.campaign_id)
                if campaign:
                    campaign.manual_snipe_scan_id = scan_id
                    self._campaign_repo.update(campaign)
                    logger.info(
                        "Updated campaign %s with manual snipe scan %s",
                        session.campaign_id, scan_id
                    )
            except Exception as e:
                logger.warning("Could not update campaign: %s", e)

        logger.info("Saved session %s to S3: %s", session.session_id, metadata.s3_key)
        return metadata.s3_key, scan_id

    async def load_session(
        self,
        audit_id: str,
        scan_id: str,
    ) -> Optional[Session]:
        """Load a previously saved session from S3."""
        try:
            data = await self._s3.load_artifact(
                audit_id=audit_id,
                phase=AuditPhase.EXPLOIT,
                filename=f"{scan_id}.json",
            )
            return Session.model_validate(data)
        except Exception as e:
            logger.error("Failed to load session %s: %s", scan_id, e)
            return None
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **In-memory sessions** | Fast access, no DB overhead for transient data |
| **TTL cleanup** | Prevents memory leaks from abandoned sessions |
| **Reuse PyRIT bridge** | DRY - converters already implemented |
| **Step-by-step transform** | User needs to see each transformation |
| **Async execution** | Non-blocking during network I/O |
| **Progress callbacks** | Enable WebSocket streaming to frontend |
| **Optional campaign link** | Works standalone or integrated |
| **S3 on explicit save** | User controls when to persist |

---

## Next Document

Continue to [02_API_SPECIFICATIONS.md](./02_API_SPECIFICATIONS.md) for REST and WebSocket API details.
