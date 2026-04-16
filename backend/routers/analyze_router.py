"""
Analysis router for Azure Cost Optimizer API.
Triggers Claude AI analysis of Azure and M365 cost data.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import load_config
from services import azure_service, m365_service, claude_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["AI Analysis"])


# ---------------------------------------------------------------------------
# Request models (optional overrides)
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    """Optional request body to pass pre-fetched data or override defaults."""
    days: Optional[int] = 30


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/azure", summary="Analyze Azure costs with Claude AI")
async def analyze_azure(request: AnalysisRequest = None):
    """
    Fetches Azure Advisor recommendations and cost data, then sends them to
    Claude AI for analysis. Returns structured FinOps recommendations.

    If Anthropic API key is not configured, returns a structured fallback analysis
    based on the raw data without AI commentary.
    """
    days = (request.days if request else None) or 30

    try:
        config = load_config()

        # Fetch data in parallel (synchronous wrappers but keeping consistent API)
        advisor_data = azure_service.get_advisor_recommendations(config)
        cost_data = azure_service.get_cost_summary(config, days=days)

        # Run Claude analysis
        analysis = claude_service.analyze_azure_costs(config, advisor_data, cost_data)
        return analysis

    except Exception as exc:
        logger.error("Azure analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Azure analysis failed: {exc}")


@router.post("/m365", summary="Analyze M365 licenses with Claude AI")
async def analyze_m365(request: AnalysisRequest = None):
    """
    Fetches M365 license usage data and sends it to Claude AI for analysis.
    Returns structured license optimization recommendations.

    If Anthropic API key is not configured, returns a structured fallback analysis
    based on the raw data without AI commentary.
    """
    try:
        config = load_config()

        # Fetch M365 license summary
        license_data = m365_service.get_license_summary(config)

        # Run Claude analysis
        analysis = claude_service.analyze_m365(config, license_data)
        return analysis

    except Exception as exc:
        logger.error("M365 analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"M365 analysis failed: {exc}")


@router.post("/full", summary="Run full combined Azure + M365 analysis with Claude AI")
async def full_analysis(request: AnalysisRequest = None):
    """
    Fetches all Azure and M365 data, then runs a comprehensive Claude AI analysis
    covering both infrastructure and licensing costs.

    Returns a combined report with:
    - Executive summary across all cloud spend
    - Priority matrix of optimization opportunities
    - Azure and M365 specific recommendations
    - 30-60-90 day implementation roadmap
    - Total potential savings (monthly and annual)

    If Anthropic API key is not configured, returns structured fallback analysis.
    """
    days = (request.days if request else None) or 30

    try:
        config = load_config()

        # Fetch all data
        advisor_data = azure_service.get_advisor_recommendations(config)
        cost_data = azure_service.get_cost_summary(config, days=days)
        compute_rightsizing = azure_service.get_compute_rightsizing(config)
        license_data = m365_service.get_license_summary(config)

        # Bundle data for analysis
        azure_data = {
            "advisor_recommendations": advisor_data,
            "cost_summary": cost_data,
            "compute_rightsizing": compute_rightsizing,
        }
        m365_data = {
            "license_summary": license_data,
        }

        # Run comprehensive Claude analysis
        analysis = claude_service.full_analysis(config, azure_data, m365_data)

        # Enrich with raw data references
        analysis["raw"] = {
            "advisor_recommendations_count": len(advisor_data),
            "cost_period_days": days,
            "m365_license_types": len(license_data.get("licenses", [])),
            "compute_rightsizing_count": len(compute_rightsizing),
        }

        return analysis

    except Exception as exc:
        logger.error("Full analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Full analysis failed: {exc}")
