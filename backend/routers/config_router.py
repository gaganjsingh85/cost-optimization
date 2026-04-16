"""
Config router for Azure Cost Optimizer API.
Handles reading, writing, and deleting configuration.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import load_config, delete_config_file, Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Configuration"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ConfigUpdateRequest(BaseModel):
    azure_tenant_id: Optional[str] = Field(None, description="Azure tenant ID")
    azure_client_id: Optional[str] = Field(None, description="Azure client (application) ID")
    azure_client_secret: Optional[str] = Field(None, description="Azure client secret")
    azure_subscription_id: Optional[str] = Field(None, description="Azure subscription ID")
    m365_tenant_id: Optional[str] = Field(None, description="M365 / Entra tenant ID")
    m365_client_id: Optional[str] = Field(None, description="M365 application client ID")
    m365_client_secret: Optional[str] = Field(None, description="M365 application client secret")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")


class ConfigStatusResponse(BaseModel):
    has_azure: bool
    has_m365: bool
    has_anthropic: bool
    azure_tenant_id_hint: Optional[str] = None
    azure_client_id_hint: Optional[str] = None
    azure_subscription_id_hint: Optional[str] = None
    m365_tenant_id_hint: Optional[str] = None
    m365_client_id_hint: Optional[str] = None
    anthropic_api_key_hint: Optional[str] = None


def _mask_value(value: Optional[str], show_last: int = 8) -> Optional[str]:
    """Returns last N chars of a value with leading asterisks, or None."""
    if not value:
        return None
    if len(value) <= show_last:
        return "*" * len(value)
    return "*" * (len(value) - show_last) + value[-show_last:]


def _mask_secret(value: Optional[str]) -> Optional[str]:
    """Returns '*****' if value is present, None otherwise."""
    if not value:
        return None
    return "*****"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=ConfigStatusResponse, summary="Get current config status")
async def get_config_status():
    """
    Returns the current configuration status with masked sensitive values.
    Tenant IDs and client IDs show the last 8 characters.
    Secrets are fully masked.
    """
    config = load_config()
    return ConfigStatusResponse(
        has_azure=config.has_azure_config(),
        has_m365=config.has_m365_config(),
        has_anthropic=config.has_anthropic_config(),
        azure_tenant_id_hint=_mask_value(config.azure_tenant_id, show_last=8),
        azure_client_id_hint=_mask_value(config.azure_client_id, show_last=8),
        azure_subscription_id_hint=_mask_value(config.azure_subscription_id, show_last=8),
        m365_tenant_id_hint=_mask_value(config.m365_tenant_id, show_last=8),
        m365_client_id_hint=_mask_value(config.m365_client_id, show_last=8),
        anthropic_api_key_hint=_mask_secret(config.anthropic_api_key),
    )


@router.post("/", summary="Save configuration")
async def save_config(request: ConfigUpdateRequest):
    """
    Accepts a full or partial configuration payload.
    Merges with existing config and saves to config.json.
    Returns success confirmation.
    """
    try:
        # Load existing config to merge with new values
        existing = load_config()

        # Build updated config, preferring new values over existing
        updated = Config(
            azure_tenant_id=request.azure_tenant_id or existing.azure_tenant_id,
            azure_client_id=request.azure_client_id or existing.azure_client_id,
            azure_client_secret=request.azure_client_secret or existing.azure_client_secret,
            azure_subscription_id=request.azure_subscription_id or existing.azure_subscription_id,
            m365_tenant_id=request.m365_tenant_id or existing.m365_tenant_id,
            m365_client_id=request.m365_client_id or existing.m365_client_id,
            m365_client_secret=request.m365_client_secret or existing.m365_client_secret,
            anthropic_api_key=request.anthropic_api_key or existing.anthropic_api_key,
        )

        updated.save_to_file()

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


@router.delete("/", summary="Delete saved configuration")
async def delete_config():
    """
    Deletes the config.json file.
    After deletion, the app will fall back to environment variables.
    """
    try:
        deleted = delete_config_file()
        if deleted:
            return {"success": True, "message": "Configuration file deleted successfully."}
        return {"success": True, "message": "No configuration file found - nothing to delete."}
    except Exception as exc:
        logger.error("Failed to delete config: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {exc}")
