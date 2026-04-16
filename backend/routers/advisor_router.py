"""
Azure Advisor router for Azure Cost Optimizer API.
Returns Azure Advisor recommendations and summaries.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from config import load_config
from services import azure_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advisor", tags=["Azure Advisor"])

# Valid Advisor categories
VALID_CATEGORIES = {
    "Cost", "Security", "HighAvailability", "Performance", "OperationalExcellence"
}


@router.get("/recommendations", summary="Get Azure Advisor recommendations")
async def get_recommendations(
    category: Optional[str] = Query(
        None,
        description="Filter by category: Cost, Security, HighAvailability, Performance, OperationalExcellence",
    )
):
    """
    Returns Azure Advisor recommendations across all categories.
    Optionally filter by category using the `category` query parameter.
    Returns sample data if Azure credentials are not configured.
    """
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Valid options: {', '.join(sorted(VALID_CATEGORIES))}",
        )

    try:
        config = load_config()
        recommendations = azure_service.get_advisor_recommendations(config)

        if category:
            recommendations = [r for r in recommendations if r.get("category") == category]

        return {
            "total": len(recommendations),
            "category_filter": category,
            "recommendations": recommendations,
        }
    except Exception as exc:
        logger.error("Error fetching advisor recommendations: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch recommendations: {exc}")


@router.get("/summary", summary="Get Advisor recommendations summary")
async def get_summary():
    """
    Returns a summary of Azure Advisor recommendations grouped by category,
    including counts per category and total potential annual/monthly savings.
    """
    try:
        config = load_config()
        recommendations = azure_service.get_advisor_recommendations(config)

        # Build category summary
        category_counts: dict[str, int] = {}
        category_savings: dict[str, float] = {}
        total_annual_savings = 0.0
        impact_counts: dict[str, int] = {}

        for rec in recommendations:
            cat = rec.get("category", "Unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            annual_savings = rec.get("potential_annual_savings", 0.0)
            category_savings[cat] = category_savings.get(cat, 0.0) + annual_savings
            total_annual_savings += annual_savings

            impact = rec.get("impact", "Unknown")
            impact_counts[impact] = impact_counts.get(impact, 0) + 1

        categories = []
        for cat in sorted(category_counts.keys()):
            categories.append({
                "category": cat,
                "count": category_counts[cat],
                "total_annual_savings": round(category_savings.get(cat, 0.0), 2),
                "total_monthly_savings": round(category_savings.get(cat, 0.0) / 12, 2),
            })

        is_sample = any(r.get("sample_data") for r in recommendations)

        return {
            "total_recommendations": len(recommendations),
            "total_annual_savings": round(total_annual_savings, 2),
            "total_monthly_savings": round(total_annual_savings / 12, 2),
            "by_category": categories,
            "by_impact": [
                {"impact": impact, "count": count}
                for impact, count in sorted(impact_counts.items())
            ],
            "sample_data": is_sample,
        }
    except Exception as exc:
        logger.error("Error building advisor summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to build summary: {exc}")
