"""
M365 router for Azure Cost Optimizer API.
Returns Microsoft 365 license usage and cost optimization data.
"""

import logging

from fastapi import APIRouter, HTTPException

from config import load_config
from services import m365_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/m365", tags=["Microsoft 365"])


@router.get("/licenses", summary="Get M365 subscribed licenses")
async def get_licenses():
    """
    Returns all subscribed Microsoft 365 SKUs with usage details including:
    - Friendly license name
    - Consumed vs. enabled (licensed) units
    - Unit cost estimate and total unused cost
    Returns sample data if M365 credentials are not configured or Graph API access is denied.
    """
    try:
        config = load_config()
        licenses = m365_service.get_subscribed_licenses(config)

        total_monthly_cost = sum(
            lic["consumed_units"] * lic["unit_cost_estimate"] for lic in licenses
        )
        total_unused_cost = sum(lic["unused_cost_estimate"] for lic in licenses)
        total_unused_units = sum(lic["unused_units"] for lic in licenses)

        return {
            "total_license_types": len(licenses),
            "total_monthly_cost_estimate": round(total_monthly_cost, 2),
            "total_unused_cost_estimate": round(total_unused_cost, 2),
            "total_unused_units": total_unused_units,
            "licenses": licenses,
            "sample_data": any(lic.get("sample_data") for lic in licenses),
        }
    except Exception as exc:
        logger.error("Error fetching M365 licenses: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch M365 licenses: {exc}")


@router.get("/usage", summary="Get M365 app usage summary")
async def get_usage():
    """
    Returns Microsoft 365 application usage statistics for the last 30 days including:
    - Active user counts per application (Word, Excel, Teams, etc.)
    Returns sample data if M365 credentials are not configured.
    """
    try:
        config = load_config()
        usage = m365_service.get_m365_app_usage(config)
        return usage
    except Exception as exc:
        logger.error("Error fetching M365 app usage: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch M365 app usage: {exc}")


@router.get("/summary", summary="Get full M365 license summary with recommendations")
async def get_summary():
    """
    Returns a comprehensive M365 license summary including:
    - Total monthly and annual spend estimates
    - License details with unused units and cost
    - Count of inactive users (no activity in 30 days)
    - Potential savings from license reclamation
    - Specific recommendations ranked by savings impact
    Returns sample data if M365 credentials are not configured.
    """
    try:
        config = load_config()
        summary = m365_service.get_license_summary(config)
        return summary
    except Exception as exc:
        logger.error("Error fetching M365 summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch M365 summary: {exc}")
