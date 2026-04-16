"""
Config router. Handles read/write/delete of credentials.

GET /api/config/        -> plaintext non-secrets + boolean flags for secrets
GET /api/config/status  -> boolean flags only
POST /api/config/       -> merges partial payload; empty-string = keep existing
DELETE /api/config/     -> deletes config file
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import load_config, delete_config_file, Config
from services.cache import get_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Configuration"])


class ConfigUpdateRequest(BaseModel):
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    m365_tenant_id: Optional[str] = None
    m365_client_id: Optional[str] = None
    m365_client_secret: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class ConfigReadResponse(BaseModel):
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    m365_tenant_id: Optional[str] = None
    m365_client_id: Optional[str] = None
    azure_client_secret_set: bool = False
    m365_client_secret_set: bool = False
    anthropic_api_key_set: bool = False
    has_azure: bool = False
    has_m365: bool = False
    has_anthropic: bool = False


class ConfigStatusResponse(BaseModel):
    has_azure: bool
    has_m365: bool
    has_anthropic: bool


@router.get("/", response_model=ConfigReadResponse)
async def get_config():
    config = load_config()
    return ConfigReadResponse(
        azure_tenant_id=config.azure_tenant_id,
        azure_client_id=config.azure_client_id,
        azure_subscription_id=config.azure_subscription_id,
        m365_tenant_id=config.m365_tenant_id,
        m365_client_id=config.m365_client_id,
        azure_client_secret_set=bool(config.azure_client_secret),
        m365_client_secret_set=bool(config.m365_client_secret),
        anthropic_api_key_set=bool(config.anthropic_api_key),
        has_azure=config.has_azure_config(),
        has_m365=config.has_m365_config(),
        has_anthropic=config.has_anthropic_config(),
    )


@router.get("/status", response_model=ConfigStatusResponse)
async def get_config_status():
    config = load_config()
    return ConfigStatusResponse(
        has_azure=config.has_azure_config(),
        has_m365=config.has_m365_config(),
        has_anthropic=config.has_anthropic_config(),
    )


@router.post("/")
async def save_config(request: ConfigUpdateRequest):
    try:
        existing = load_config()

        def _merge(new_val, existing_val):
            if new_val is None or new_val == "":
                return existing_val
            return new_val

        updated = Config(
            azure_tenant_id=_merge(request.azure_tenant_id, existing.azure_tenant_id),
            azure_client_id=_merge(request.azure_client_id, existing.azure_client_id),
            azure_client_secret=_merge(request.azure_client_secret, existing.azure_client_secret),
            azure_subscription_id=_merge(request.azure_subscription_id, existing.azure_subscription_id),
            m365_tenant_id=_merge(request.m365_tenant_id, existing.m365_tenant_id),
            m365_client_id=_merge(request.m365_client_id, existing.m365_client_id),
            m365_client_secret=_merge(request.m365_client_secret, existing.m365_client_secret),
            anthropic_api_key=_merge(request.anthropic_api_key, existing.anthropic_api_key),
        )
        updated.save_to_file()

        # Credentials may have changed - blow away caches so next request refreshes
        cache = get_cache()
        for prefix in ("advisor:", "cost_summary:", "rightsizing:", "subscription:",
                       "m365_token:", "m365_license_summary:", "m365_activity:",
                       "m365_app_usage:"):
            cache.invalidate_prefix(prefix)

        return {
            "success": True,
            "message": "Configuration saved successfully.",
            "has_azure": updated.has_azure_config(),
            "has_m365": updated.has_m365_config(),
            "has_anthropic": updated.has_anthropic_config(),
        }
    except Exception as exc:
        logger.error("Failed to save config: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {exc}")


@router.delete("/")
async def delete_config():
    try:
        deleted = delete_config_file()
        cache = get_cache()
        for prefix in ("advisor:", "cost_summary:", "rightsizing:", "subscription:",
                       "m365_token:", "m365_license_summary:", "m365_activity:",
                       "m365_app_usage:"):
            cache.invalidate_prefix(prefix)
        return {
            "success": True,
            "message": "Configuration file deleted." if deleted else "No config file found.",
        }
    except Exception as exc:
        logger.error("Failed to delete config: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {exc}")