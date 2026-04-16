"""
Costs router for Azure Cost Optimizer API.
Returns Azure cost summaries and breakdowns.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from config import load_config
from services import azure_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/costs", tags=["Azure Costs"])


@router.get("/summary", summary="Get Azure cost summary")
async def get_cost_summary(
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days to look back for cost data (1-365)",
    )
):
    """
    Returns actual Azure cost data for the last N days including:
    - Total cost and currency
    - Costs broken down by service, resource group, and location
    - Daily cost trend
    Returns sample data if Azure credentials are not configured.
    """
    try:
        config = load_config()
        summary = azure_service.get_cost_summary(config, days=days)
        return summary
    except Exception as exc:
        logger.error("Error fetching cost summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost summary: {exc}")


@router.get("/breakdown", summary="Get Azure cost breakdown")
async def get_cost_breakdown(
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days to look back for cost data (1-365)",
    )
):
    """
    Returns detailed Azure cost breakdown by service and resource group.
    Also includes compute rightsizing recommendations.
    Returns sample data if Azure credentials are not configured.
    """
    try:
        config = load_config()
        cost_summary = azure_service.get_cost_summary(config, days=days)
        rightsizing = azure_service.get_compute_rightsizing(config)

        total_rightsizing_savings = sum(
            r.get("monthly_savings", 0) for r in rightsizing
        )

        return {
            "period_days": days,
            "total_cost": cost_summary.get("total_cost", 0),
            "currency": cost_summary.get("currency", "USD"),
            "by_service": cost_summary.get("by_service", []),
            "by_resource_group": cost_summary.get("by_resource_group", []),
            "by_location": cost_summary.get("by_location", []),
            "compute_rightsizing": rightsizing,
            "rightsizing_total_monthly_savings": round(total_rightsizing_savings, 2),
            "rightsizing_total_annual_savings": round(total_rightsizing_savings * 12, 2),
            "sample_data": cost_summary.get("sample_data", False),
        }
    except Exception as exc:
        logger.error("Error fetching cost breakdown: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost breakdown: {exc}")
