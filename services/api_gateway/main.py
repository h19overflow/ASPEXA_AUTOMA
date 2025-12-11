"""API Gateway - HTTP entry point for all services.

Provides REST endpoints as an alternative to event-driven consumers.
Includes Clerk-based authentication for protected endpoints.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from services.api_gateway.routers import recon, scan, campaigns, scans
from services.api_gateway.routers.snipers import (
    phase1_router,
    phase2_router,
    phase3_router,
    attack_router,
)
from services.api_gateway.auth import require_friend

app = FastAPI(
    title="Aspexa Automa API",
    description="HTTP gateway for reconnaissance, scanning, and exploitation services",
    version="1.0.0",
)

# CORS middleware for frontend access
# Note: Updated to support Clerk authentication with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Viper Command Center (dev)
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # Alternative dev port
        "http://192.168.0.4:8080",  # Local network access
        "http://192.168.0.4:5173",  # Local network Vite
    ],
    allow_credentials=True,  # Required for Clerk auth cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Scan-Id"],  # Expose the scan ID header for SSE
)

# Protected service execution endpoints (friends only)
app.include_router(
    recon.router,
    prefix="/api",
    dependencies=[Depends(require_friend)],
)
app.include_router(
    scan.router,
    prefix="/api",
    dependencies=[Depends(require_friend)],
)

# Protected snipers endpoints (friends only)
app.include_router(
    phase1_router,
    prefix="/api/snipers",
    dependencies=[Depends(require_friend)],
)
app.include_router(
    phase2_router,
    prefix="/api/snipers",
    dependencies=[Depends(require_friend)],
)
app.include_router(
    phase3_router,
    prefix="/api/snipers",
    dependencies=[Depends(require_friend)],
)
app.include_router(
    attack_router,
    prefix="/api/snipers",
    dependencies=[Depends(require_friend)],
)

# Protected persistence endpoints (friends only)
app.include_router(
    campaigns.router,
    prefix="/api",
    dependencies=[Depends(require_friend)],
)
app.include_router(
    scans.router,
    prefix="/api",
    dependencies=[Depends(require_friend)],
)


@app.get("/health")
async def health_check():
    """Service health check (public endpoint)."""
    return {"status": "healthy", "service": "api_gateway"}


@app.get("/api/auth/status")
async def auth_status():
    """Check if authentication is configured (public endpoint)."""
    from libs.config import get_settings

    settings = get_settings()
    return {
        "auth_configured": settings.clerk_secret_key is not None,
        "auth_provider": "clerk",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
