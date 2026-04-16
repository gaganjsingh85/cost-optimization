"""
Azure Cost Optimizer API - Main Entry Point
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
from routers.subscription_router import router as subscription_router
from routers.chat_router import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Quiet Azure SDK HTTP logging - it's extremely noisy
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("msal").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Azure Cost Optimizer API",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(advisor_router)
app.include_router(costs_router)
app.include_router(m365_router)
app.include_router(analyze_router)
app.include_router(subscription_router)
app.include_router(chat_router)


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "azure-cost-optimizer-api", "version": "1.2.0"}


@app.get("/", include_in_schema=False)
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def on_startup():
    from config import load_config
    config = load_config()
    logger.info("Azure Cost Optimizer API starting up...")
    logger.info(
        "Config - Azure: %s | M365: %s | Anthropic: %s",
        "configured" if config.has_azure_config() else "not configured",
        "configured" if config.has_m365_config() else "not configured",
        "configured" if config.has_anthropic_config() else "not configured",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")