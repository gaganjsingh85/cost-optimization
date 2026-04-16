"""AI analysis router - triggers Claude analysis of cost data."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import load_config
from services import azure_service, m365_service, claude_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["AI Analysis"])


class AnalysisRequest(BaseModel):
    days: Optional[int] = 30


@router.post("/azure")
async def analyze_azure(request: AnalysisRequest = None):
    days = (request.days if request else None) or 30
    try:
        config = load_config()
        advisor_data = azure_service.get_advisor_recommendations(config)
        cost_data = azure_service.get_cost_summary(config, days=days)
        return claude_service.analyze_azure_costs(config, advisor_data, cost_data)
    except Exception as exc:
        logger.error("Azure analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Azure analysis failed: {exc}")


@router.post("/m365")
async def analyze_m365(request: AnalysisRequest = None):
    try:
        config = load_config()
        license_data = m365_service.get_license_summary(config)
        return claude_service.analyze_m365(config, license_data)
    except Exception as exc:
        logger.error("M365 analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"M365 analysis failed: {exc}")


@router.post("/full")
async def full_analysis(request: AnalysisRequest = None):
    days = (request.days if request else None) or 30
    try:
        config = load_config()
        advisor_data = azure_service.get_advisor_recommendations(config)
        cost_data = azure_service.get_cost_summary(config, days=days)
        compute_rightsizing = azure_service.get_compute_rightsizing(config)
        license_data = m365_service.get_license_summary(config)

        azure_data = {
            "advisor_recommendations": advisor_data,
            "cost_summary": cost_data,
            "compute_rightsizing": compute_rightsizing,
        }
        m365_data = {"license_summary": license_data}

        analysis = claude_service.full_analysis(config, azure_data, m365_data)
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