"""Azure Advisor router."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from config import load_config
from services import azure_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advisor", tags=["Azure Advisor"])

VALID_CATEGORIES = {"Cost", "Security", "HighAvailability", "Performance", "OperationalExcellence"}


@router.get("/recommendations")
async def get_recommendations(
    category: Optional[str] = Query(None),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Valid: {', '.join(sorted(VALID_CATEGORIES))}",
        )

    try:
        config = load_config()
        result = azure_service.get_advisor_recommendations_with_status(config)
        recs = result["recommendations"]
        if category:
            recs = [r for r in recs if r.get("category") == category]

        return {
            "total": len(recs),
            "category_filter": category,
            "recommendations": recs,
            "data_status": result.get("data_status"),
            "error": result.get("error"),
            "error_class": result.get("error_class"),
        }
    except Exception as exc:
        logger.error("Error fetching advisor recommendations: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch recommendations: {exc}")


@router.get("/summary")
async def get_summary():
    try:
        config = load_config()
        result = azure_service.get_advisor_recommendations_with_status(config)
        recs = result["recommendations"]

        category_counts: dict[str, int] = {}
        category_savings: dict[str, float] = {}
        total_annual = 0.0
        impact_counts: dict[str, int] = {}

        for rec in recs:
            cat = rec.get("category", "Unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1
            annual = rec.get("potential_annual_savings", 0.0)
            category_savings[cat] = category_savings.get(cat, 0.0) + annual
            total_annual += annual
            impact = rec.get("impact", "Unknown")
            impact_counts[impact] = impact_counts.get(impact, 0) + 1

        categories = [
            {
                "category": cat,
                "count": category_counts[cat],
                "total_annual_savings": round(category_savings.get(cat, 0.0), 2),
                "total_monthly_savings": round(category_savings.get(cat, 0.0) / 12, 2),
            }
            for cat in sorted(category_counts.keys())
        ]

        return {
            "total_recommendations": len(recs),
            "total_annual_savings": round(total_annual, 2),
            "total_monthly_savings": round(total_annual / 12, 2),
            "by_category": categories,
            "by_impact": [{"impact": i, "count": c} for i, c in sorted(impact_counts.items())],
            "data_status": result.get("data_status"),
            "error": result.get("error"),
            "error_class": result.get("error_class"),
        }
    except Exception as exc:
        logger.error("Error building advisor summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to build summary: {exc}")