"""
Azure subscription router.
Returns basic subscription info (ID, display name) for the UI header.
"""

import logging

from fastapi import APIRouter, HTTPException

from config import load_config
from services import azure_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/azure", tags=["Azure"])


@router.get("/subscription", summary="Get Azure subscription info")
async def get_subscription():
    """
    Returns the configured Azure subscription's display name, ID, state,
    and tenant ID. Falls back to sample data if Azure credentials are not
    configured.
    """
    try:
        config = load_config()
        return azure_service.get_subscription_info(config)
    except Exception as exc:
        logger.error("Error fetching subscription info: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch subscription info: {exc}"
        )