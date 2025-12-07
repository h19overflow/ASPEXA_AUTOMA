"""API Gateway - HTTP entry point for all services.

Provides REST endpoints as an alternative to event-driven consumers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api_gateway.routers import recon, scan, campaigns, scans
from services.api_gateway.routers.snipers import (
    phase1_router,
    phase2_router,
    phase3_router,
    attack_router,
)

app = FastAPI(
    title="Aspexa Automa API",
    description="HTTP gateway for reconnaissance, scanning, and exploitation services",
    version="1.0.0",
)

# CORS middleware for frontend access
# Note: allow_credentials=True cannot be used with allow_origins=["*"]
# For development, we use wildcard origins without credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=False,  # Cannot use True with wildcard origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Scan-Id"],  # Expose the scan ID header for SSE
)

# Service execution endpoints
app.include_router(recon.router, prefix="/api")
app.include_router(scan.router, prefix="/api")

# Snipers composable attack endpoints
app.include_router(phase1_router, prefix="/api/snipers")
app.include_router(phase2_router, prefix="/api/snipers")
app.include_router(phase3_router, prefix="/api/snipers")
app.include_router(attack_router, prefix="/api/snipers")

# Persistence endpoints
app.include_router(campaigns.router, prefix="/api")
app.include_router(scans.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Service health check."""
    return {"status": "healthy", "service": "api_gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)