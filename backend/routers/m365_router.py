"""M365 router."""

import logging

from fastapi import APIRouter, HTTPException

from config import load_config
from services import m365_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/m365", tags=["Microsoft 365"])


@router.get("/licenses")
async def get_licenses():
    try:
        config = load_config()
        summary = m365_service.get_license_summary(config)
        licenses = summary.get("licenses", [])
        total_monthly = sum(
            l.get("consumed_units", 0) * l.get("unit_cost_estimate", 0) for l in licenses
        )
        total_unused_cost = sum(l.get("unused_cost_estimate", 0) for l in licenses)
        total_unused_units = sum(l.get("unused_units", 0) for l in licenses)
        return {
            "total_license_types": len(licenses),
            "total_monthly_cost_estimate": round(total_monthly, 2),
            "total_unused_cost_estimate": round(total_unused_cost, 2),
            "total_unused_units": total_unused_units,
            "licenses": licenses,
            "data_status": summary.get("data_status"),
            "error": summary.get("error"),
            "error_class": summary.get("error_class"),
        }
    except Exception as exc:
        logger.error("Error fetching M365 licenses: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch M365 licenses: {exc}")


@router.get("/usage")
async def get_usage():
    try:
        config = load_config()
        return m365_service.get_m365_app_usage(config)
    except Exception as exc:
        logger.error("Error fetching M365 usage: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch M365 usage: {exc}")


@router.get("/summary")
async def get_summary():
    try:
        config = load_config()
        return m365_service.get_license_summary(config)
    except Exception as exc:
        logger.error("Error fetching M365 summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch M365 summary: {exc}")