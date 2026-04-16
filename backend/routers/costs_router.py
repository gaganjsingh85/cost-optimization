"""Azure cost router."""

import logging

from fastapi import APIRouter, HTTPException, Query

from config import load_config
from services import azure_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/costs", tags=["Azure Costs"])


@router.get("/summary")
async def get_cost_summary(days: int = Query(30, ge=1, le=365)):
    try:
        config = load_config()
        return azure_service.get_cost_summary(config, days=days)
    except Exception as exc:
        logger.error("Error fetching cost summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost summary: {exc}")


@router.get("/breakdown")
async def get_cost_breakdown(days: int = Query(30, ge=1, le=365)):
    try:
        config = load_config()
        cost = azure_service.get_cost_summary(config, days=days)
        rightsizing = azure_service.get_compute_rightsizing(config)
        total_rightsizing_savings = sum(r.get("monthly_savings", 0) for r in rightsizing)
        return {
            "period_days": days,
            "total_cost": cost.get("total_cost", 0),
            "currency": cost.get("currency", "USD"),
            "by_service": cost.get("by_service", []),
            "by_resource_group": cost.get("by_resource_group", []),
            "by_location": cost.get("by_location", []),
            "compute_rightsizing": rightsizing,
            "rightsizing_total_monthly_savings": round(total_rightsizing_savings, 2),
            "rightsizing_total_annual_savings": round(total_rightsizing_savings * 12, 2),
            "data_status": cost.get("data_status"),
            "error": cost.get("error"),
            "error_class": cost.get("error_class"),
        }
    except Exception as exc:
        logger.error("Error fetching cost breakdown: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost breakdown: {exc}")