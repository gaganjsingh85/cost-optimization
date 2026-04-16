"""
Azure Cost Optimizer API - Main Application Entry Point

FastAPI application providing endpoints for:
- Azure cost data (Advisor recommendations, Cost Management, compute rightsizing)
- Microsoft 365 license usage and optimization
- Claude AI-powered FinOps analysis
- Configuration management
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.config_router import router as config_router
from routers.advisor_router import router as advisor_router
from routers.costs_router import router as costs_router
from routers.m365_router import router as m365_router
from routers.analyze_router import router as analyze_router

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Azure Cost Optimizer API",
    version="1.0.0",
    description=(
        "Backend API for the Azure Cost Optimization agent. "
        "Provides Azure cost data, M365 license analysis, and Claude AI-powered "
        "FinOps recommendations."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(config_router)
app.include_router(advisor_router)
app.include_router(costs_router)
app.include_router(m365_router)
app.include_router(analyze_router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["Health"], summary="Health check")
def health():
    """Returns API health status."""
    return {"status": "ok", "service": "azure-cost-optimizer-api", "version": "1.0.0"}


@app.get("/", tags=["Root"], include_in_schema=False)
def root():
    """Redirects to API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ---------------------------------------------------------------------------
# Startup / shutdown events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    """Runs on application startup."""
    from config import load_config
    config = load_config()
    logger.info("Azure Cost Optimizer API starting up...")
    logger.info(
        "Config status - Azure: %s | M365: %s | Anthropic: %s",
        "configured" if config.has_azure_config() else "not configured",
        "configured" if config.has_m365_config() else "not configured",
        "configured" if config.has_anthropic_config() else "not configured",
    )
    logger.info("API is ready. Visit http://localhost:8000/docs for the API documentation.")


@app.on_event("shutdown")
async def on_shutdown():
    """Runs on application shutdown."""
    logger.info("Azure Cost Optimizer API shutting down.")


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
