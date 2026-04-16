"""Claude AI service for cost analysis."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior FinOps (Cloud Financial Operations) expert and Microsoft cloud consultant with 15+ years of experience optimizing Azure and Microsoft 365 spending for enterprise organizations.

Your role is to analyze cloud cost data and deliver clear, actionable, quantified recommendations that help organizations reduce spend while maintaining operational excellence.

Guidelines:
- Always lead with the most impactful savings opportunities ranked by potential dollar value
- Be specific and actionable - give exact resource names, sizes, or actions wherever possible
- Quantify savings in both monthly and annual USD values
- Prioritize quick wins (low effort, high savings) prominently
- Use clear business language that both technical and non-technical stakeholders can understand
- Format monetary values consistently as USD: $X,XXX.XX or $X.XX/month
- When data is marked as sample data, acknowledge this and explain what real data would reveal
- Structure your response with clear headings and bullet points for executive readability
- Consider Azure Reserved Instances, Savings Plans, and right-sizing as primary levers
- For M365, focus on license reclamation, downgrade opportunities, and inactive user cleanup
- Always include risk considerations and recommended validation steps before taking action
"""


def _make_client(config):
    import anthropic
    try:
        return anthropic.Anthropic(api_key=config.anthropic_api_key)
    except TypeError as exc:
        if "proxies" in str(exc):
            raise RuntimeError(
                "Incompatible anthropic/httpx versions. Run `pip install --upgrade anthropic`."
            ) from exc
        raise


def _call_claude(config, user_message: str) -> str:
    client = _make_client(config)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


def _parse_savings(text: str) -> float:
    import re
    patterns = [
        r"\$([0-9,]+\.?[0-9]*)\s*/\s*month",
        r"\$([0-9,]+\.?[0-9]*)\s*per\s*month",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                values = [float(m.replace(",", "")) for m in matches]
                return max(values)
            except ValueError:
                continue
    return 0.0


# ---------------------------------------------------------------------------
# Fallback helpers
# ---------------------------------------------------------------------------

def _desc_text(rec: dict) -> str:
    """Normalize short_description into a single string for prompts/fallbacks.
    Handles both the new object form {problem, solution} and the legacy string form."""
    sd = rec.get("short_description")
    if isinstance(sd, dict):
        return (sd.get("problem") or sd.get("solution") or "").strip()
    if isinstance(sd, str):
        return sd.strip()
    return (rec.get("description") or "").strip()


def _extract_opportunities(advisor_data: list[dict]) -> list[dict]:
    cost_recs = sorted(
        [r for r in advisor_data if r.get("category") == "Cost"],
        key=lambda x: x.get("potential_annual_savings", 0),
        reverse=True,
    )
    return [
        {
            "title": _desc_text(r) or "Cost opportunity",
            "description": f"Resource: {r.get('impacted_value', 'N/A')} (RG: {r.get('resource_group', 'N/A')})",
            "estimated_monthly_savings": round(r.get("potential_annual_savings", 0) / 12, 2),
            "priority": r.get("impact", "Medium"),
            "action_required": _desc_text(r) or "Review and implement",
        }
        for r in cost_recs[:5]
    ]


def _extract_quick_wins(advisor_data: list[dict]) -> list[dict]:
    keywords = ["delete", "shutdown", "deallocate", "idle", "unused", "unattached"]
    wins = []
    for rec in advisor_data:
        desc = _desc_text(rec).lower()
        if any(kw in desc for kw in keywords):
            annual = rec.get("potential_annual_savings", 0)
            wins.append({
                "action": _desc_text(rec),
                "savings": f"${annual / 12:,.2f}/month",
                "effort": "Low",
            })
    if len(wins) < 3:
        wins.append({"action": "Review and delete unattached managed disks", "savings": "Varies", "effort": "Low"})
        wins.append({"action": "Set up Cost Alerts and budgets per resource group", "savings": "Prevents overruns", "effort": "Low"})
    return wins[:5]


def _build_license_recs(license_data: dict) -> list[dict]:
    results = []
    for lic in license_data.get("licenses", []):
        if lic.get("unused_units", 0) > 0:
            results.append({
                "license_name": lic.get("friendly_name", lic.get("sku_part_number", "")),
                "current_count": lic.get("enabled_units", 0),
                "recommended_count": lic.get("consumed_units", 0),
                "monthly_savings": lic.get("unused_cost_estimate", 0),
                "action": f"Remove {lic['unused_units']} unused licenses.",
            })
    return sorted(results, key=lambda x: x["monthly_savings"], reverse=True)


def _fallback_azure(advisor_data: list[dict], cost_data: dict) -> dict:
    total_annual = sum(r.get("potential_annual_savings", 0) for r in advisor_data)
    total_monthly = total_annual / 12
    opportunities = _extract_opportunities(advisor_data)
    quick_wins = _extract_quick_wins(advisor_data)
    total_cost = cost_data.get("total_cost", 0)
    top_service = (cost_data.get("by_service") or [{}])[0]

    text = f"""## Azure Cost Analysis

### Executive Summary
Azure spend: **${total_cost:,.2f}/month** (last 30 days). Azure Advisor has identified **${total_monthly:,.2f}/month** (${total_annual:,.2f}/year) in potential savings across {len(advisor_data)} recommendations.

### Top Savings Opportunities
{chr(10).join(f"- **{o['title']}**: ${o['estimated_monthly_savings']:,.2f}/month" for o in opportunities)}

### Highest Cost Service
{top_service.get('service_name', 'N/A')}: ${top_service.get('cost', 0):,.2f}/month

### Quick Wins
{chr(10).join(f"- {qw['action']} (Est. {qw['savings']})" for qw in quick_wins)}

Configure your Anthropic API key to receive detailed AI-powered analysis.
"""

    return {
        "executive_summary": f"Azure spend is ${total_cost:,.2f}/month with ${total_monthly:,.2f}/month in identified savings.",
        "top_savings_opportunities": opportunities,
        "quick_wins": quick_wins,
        "total_potential_savings": round(total_monthly, 2),
        "analysis_text": text,
        "is_sample_data": cost_data.get("sample_data", False),
    }


def _fallback_m365(license_data: dict) -> dict:
    potential = license_data.get("potential_savings", 0)
    total_spend = license_data.get("total_monthly_spend_estimate", 0)
    inactive = license_data.get("inactive_users", 0)
    license_recs = _build_license_recs(license_data)

    text = f"""## M365 License Analysis

### Executive Summary
M365 spend: **${total_spend:,.2f}/month** with **${potential:,.2f}/month** in potential savings across {len(license_data.get('licenses', []))} license types.

### License Optimization Opportunities
{chr(10).join(f"- **{r['license_name']}**: Remove {r['current_count'] - r['recommended_count']} unused seats - save ${r['monthly_savings']:,.2f}/month" for r in license_recs)}

### Inactive Users
{inactive} users show no activity in 30 days.

Configure your Anthropic API key for AI-powered analysis.
"""

    return {
        "executive_summary": f"M365 spend is ${total_spend:,.2f}/month with ${potential:,.2f}/month potential savings.",
        "license_recommendations": license_recs,
        "total_potential_savings": round(potential, 2),
        "analysis_text": text,
        "is_sample_data": license_data.get("sample_data", False),
    }


def _merge_analyses(azure_a: dict, m365_a: dict) -> dict:
    az = azure_a.get("total_potential_savings", 0)
    m3 = m365_a.get("total_potential_savings", 0)
    total = az + m3
    return {
        "executive_summary": f"Combined savings potential: ${total:,.2f}/month (Azure ${az:,.2f}, M365 ${m3:,.2f}).",
        "azure": azure_a,
        "m365": m365_a,
        "combined_analysis_text": azure_a.get("analysis_text", "") + "\n\n---\n\n" + m365_a.get("analysis_text", ""),
        "total_potential_monthly_savings": round(total, 2),
        "total_potential_annual_savings": round(total * 12, 2),
        "is_sample_data": azure_a.get("is_sample_data", False) or m365_a.get("is_sample_data", False),
    }


# ---------------------------------------------------------------------------
# Public analysis functions
# ---------------------------------------------------------------------------

def analyze_azure_costs(config, advisor_data, cost_data) -> dict:
    if not config.has_anthropic_config():
        return _fallback_azure(advisor_data, cost_data)

    total_annual = sum(r.get("potential_annual_savings", 0) for r in advisor_data)

    cost_breakdown = json.dumps({
        "total_cost_last_30_days": cost_data.get("total_cost"),
        "currency": cost_data.get("currency", "USD"),
        "top_services_by_cost": cost_data.get("by_service", [])[:8],
        "top_resource_groups_by_cost": cost_data.get("by_resource_group", [])[:5],
        "top_locations_by_cost": cost_data.get("by_location", [])[:5],
    }, indent=2)

    advisor_summary = json.dumps([
        {
            "category": r.get("category"),
            "impact": r.get("impact"),
            "impacted_value": r.get("impacted_value"),
            "short_description": _desc_text(r),
            "potential_annual_savings": r.get("potential_annual_savings", 0),
            "resource_group": r.get("resource_group"),
        }
        for r in advisor_data[:20]
    ], indent=2)

    user_message = f"""Analyze this Azure cost and advisor recommendation data:

## Cost Summary
```json
{cost_breakdown}
```

## Advisor Recommendations ({len(advisor_data)} total)
Total potential annual savings: ${total_annual:,.2f}

```json
{advisor_summary}
```

Provide: executive summary, top 5 savings opportunities with specific actions, quick wins, total monthly savings estimate, risks. Use markdown headings."""

    try:
        text = _call_claude(config, user_message)
        monthly = _parse_savings(text) or (total_annual / 12)
        lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.strip().startswith("#")][:3]
        return {
            "executive_summary": " ".join(lines)[:500],
            "top_savings_opportunities": _extract_opportunities(advisor_data),
            "quick_wins": _extract_quick_wins(advisor_data),
            "total_potential_savings": round(monthly, 2),
            "analysis_text": text,
            "is_sample_data": cost_data.get("sample_data", False),
        }
    except Exception as exc:
        logger.error("Claude Azure analysis failed: %s", exc)
        return _fallback_azure(advisor_data, cost_data)


def analyze_m365(config, license_data) -> dict:
    if not config.has_anthropic_config():
        return _fallback_m365(license_data)

    summary_json = json.dumps({
        "total_monthly_spend_estimate": license_data.get("total_monthly_spend_estimate", 0),
        "inactive_users": license_data.get("inactive_users", 0),
        "potential_savings": license_data.get("potential_savings", 0),
        "licenses": [
            {
                "name": l.get("friendly_name"),
                "consumed": l.get("consumed_units"),
                "enabled": l.get("enabled_units"),
                "unused": l.get("unused_units"),
                "unit_cost": l.get("unit_cost_estimate"),
                "unused_cost": l.get("unused_cost_estimate"),
            }
            for l in license_data.get("licenses", [])
        ],
    }, indent=2)

    user_message = f"""Analyze this Microsoft 365 license data:

```json
{summary_json}
```

Provide: executive summary, per-license recommendations with current/recommended counts and monthly savings, inactive-user actions, total monthly savings. Use markdown headings."""

    try:
        text = _call_claude(config, user_message)
        monthly = _parse_savings(text) or license_data.get("potential_savings", 0)
        lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.strip().startswith("#")][:3]
        return {
            "executive_summary": " ".join(lines)[:500],
            "license_recommendations": _build_license_recs(license_data),
            "total_potential_savings": round(monthly, 2),
            "analysis_text": text,
            "is_sample_data": license_data.get("sample_data", False),
        }
    except Exception as exc:
        logger.error("Claude M365 analysis failed: %s", exc)
        return _fallback_m365(license_data)


def full_analysis(config, azure_data, m365_data) -> dict:
    if not config.has_anthropic_config():
        return _merge_analyses(
            _fallback_azure(azure_data.get("advisor_recommendations", []), azure_data.get("cost_summary", {})),
            _fallback_m365(m365_data.get("license_summary", {})),
        )

    # Delegate to the individual analyses (which call Claude) and merge
    advisor = azure_data.get("advisor_recommendations", [])
    cost = azure_data.get("cost_summary", {})
    licenses = m365_data.get("license_summary", {})

    azure_a = analyze_azure_costs(config, advisor, cost)
    m365_a = analyze_m365(config, licenses)
    return _merge_analyses(azure_a, m365_a)