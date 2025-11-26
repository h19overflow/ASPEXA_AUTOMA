"""API Gateway - HTTP entry point for all services.

Provides REST endpoints as an alternative to event-driven consumers.
"""
from fastapi import FastAPI

from services.api_gateway.routers import recon, scan, exploit, campaigns, scans

app = FastAPI(
    title="Aspexa Automa API",
    description="HTTP gateway for reconnaissance, scanning, and exploitation services",
    version="1.0.0",
)

# Service execution endpoints
app.include_router(recon.router)
app.include_router(scan.router)
app.include_router(exploit.router)

# Persistence endpoints
app.include_router(campaigns.router)
app.include_router(scans.router)


@app.get("/health")
async def health_check():
    """Service health check."""
    return {"status": "healthy", "service": "api_gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)