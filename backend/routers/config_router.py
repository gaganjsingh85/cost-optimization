"""
Config router for Azure Cost Optimizer API.
Handles reading, writing, and deleting configuration.

GET /api/config/         -> returns non-secret fields in plaintext + boolean flags for secrets
GET /api/config/status   -> returns only boolean flags (legacy / header use)
POST /api/config/        -> merges a partial payload into the saved config
DELETE /api/config/      -> deletes the saved config file
"""

import logging
from typing import Optional

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


class ConfigReadResponse(BaseModel):
    """Plaintext response for non-secret fields; booleans for secrets."""
    # Non-secrets (plaintext)
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    m365_tenant_id: Optional[str] = None
    m365_client_id: Optional[str] = None

    # Secrets (boolean presence only)
    azure_client_secret_set: bool = False
    m365_client_secret_set: bool = False
    anthropic_api_key_set: bool = False

    # Overall flags
    has_azure: bool = False
    has_m365: bool = False
    has_anthropic: bool = False


class ConfigStatusResponse(BaseModel):
    has_azure: bool
    has_m365: bool
    has_anthropic: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=ConfigReadResponse, summary="Get current config")
async def get_config():
    """
    Returns the current non-secret configuration fields in plaintext so the
    Settings UI can populate its form. Secret fields are returned as boolean
    flags only (*_set) to indicate whether they have a value.
    """
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


@router.get("/status", response_model=ConfigStatusResponse, summary="Get config presence flags only")
async def get_config_status():
    """Returns only boolean flags - lightweight check for Layout/header."""
    config = load_config()
    return ConfigStatusResponse(
        has_azure=config.has_azure_config(),
        has_m365=config.has_m365_config(),
        has_anthropic=config.has_anthropic_config(),
    )


@router.post("/", summary="Save configuration")
async def save_config(request: ConfigUpdateRequest):
    """
    Accepts a full or partial configuration payload.
    Merges with existing config and saves to config.json.
    Empty-string values are treated as "no change" so the UI can safely send
    a blank secret field when the user hasn't typed anything new.
    """
    try:
        existing = load_config()

        def _merge(new_val: Optional[str], existing_val: Optional[str]) -> Optional[str]:
            # Treat None or empty string as "keep existing"
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
    """Deletes config.json. After deletion the app falls back to environment variables."""
    try:
        deleted = delete_config_file()
        if deleted:
            return {"success": True, "message": "Configuration file deleted successfully."}
        return {"success": True, "message": "No configuration file found - nothing to delete."}
    except Exception as exc:
        logger.error("Failed to delete config: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {exc}")