"""
Claude AI service for the Azure Cost Optimizer.
Uses Anthropic SDK (claude-sonnet-4-6) to analyze cost data and generate
actionable FinOps recommendations.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a senior FinOps (Cloud Financial Operations) expert and Microsoft cloud consultant with 15+ years of experience optimizing Azure and Microsoft 365 spending for enterprise organizations.

Your role is to analyze cloud cost data and deliver clear, actionable, quantified recommendations that help organizations reduce spend while maintaining operational excellence.

Guidelines:
- Always lead with the most impactful savings opportunities ranked by potential dollar value
- Be specific and actionable — give exact resource names, sizes, or actions wherever possible
- Quantify savings in both monthly and annual USD values
- Prioritize quick wins (low effort, high savings) prominently
- Use clear business language that both technical and non-technical stakeholders can understand
- Format monetary values consistently as USD: $X,XXX.XX or $X.XX/month
- When data is marked as sample data, acknowledge this and explain what real data would reveal
- Structure your response with clear headings and bullet points for executive readability
- Consider Azure Reserved Instances, Savings Plans, and right-sizing as primary levers
- For M365, focus on license reclamation, downgrade opportunities, and inactive user cleanup
- Always include risk considerations and recommended validation steps before taking action

Your analysis should follow this structure:
1. Executive Summary (2-3 sentences with total savings potential)
2. Top Savings Opportunities (ranked, with specific actions)
3. Quick Wins (can be implemented this week with minimal risk)
4. Medium-term Optimizations (1-3 months)
5. Risk Considerations
6. Recommended Next Steps
"""

# ---------------------------------------------------------------------------
# Helper: build Anthropic client
# ---------------------------------------------------------------------------

def _get_client(config):
    """Returns an Anthropic client using the configured API key."""
    import anthropic
    return anthropic.Anthropic(api_key=config.anthropic_api_key)


def _call_claude(config, user_message: str) -> str:
    """
    Sends a message to Claude and returns the response text.
    Raises on API errors.
    """
    client = _get_client(config)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )
    return message.content[0].text


def _parse_savings_from_text(text: str) -> float:
    """
    Attempts to extract a total savings figure from analysis text.
    Returns 0.0 if not found.
    """
    import re
    # Look for patterns like $12,345.67/month or $12,345/month (annual)
    patterns = [
        r"\$([0-9,]+\.?[0-9]*)\s*/\s*month",
        r"\$([0-9,]+\.?[0-9]*)\s*per\s*month",
        r"total.*?\$([0-9,]+\.?[0-9]*)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                # Take the largest value found (likely the total)
                values = [float(m.replace(",", "")) for m in matches]
                return max(values)
            except ValueError:
                continue
    return 0.0


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def analyze_azure_costs(config, advisor_data: list[dict], cost_data: dict) -> dict:
    """
    Analyzes Azure Advisor recommendations and cost summary using Claude.

    Returns:
        dict with keys:
            - executive_summary: str
            - top_savings_opportunities: list of dicts
            - quick_wins: list of dicts
            - total_potential_savings: float
            - analysis_text: str (full markdown analysis)
    """
    if not config.has_anthropic_config():
        return _fallback_azure_analysis(advisor_data, cost_data)

    is_sample = cost_data.get("sample_data", False) or (
        advisor_data and advisor_data[0].get("sample_data", False)
    )

    # Calculate total annual savings from advisor recommendations
    total_annual_savings = sum(
        rec.get("potential_annual_savings", 0.0) for rec in advisor_data
    )
    cost_recs = [r for r in advisor_data if r.get("category") == "Cost"]

    # Build a concise data summary to send to Claude
    cost_breakdown = json.dumps(
        {
            "total_cost_last_30_days": cost_data.get("total_cost"),
            "currency": cost_data.get("currency", "USD"),
            "period_days": cost_data.get("period_days", 30),
            "top_services_by_cost": cost_data.get("by_service", [])[:8],
            "top_resource_groups_by_cost": cost_data.get("by_resource_group", [])[:5],
            "top_locations_by_cost": cost_data.get("by_location", [])[:5],
        },
        indent=2,
    )

    advisor_summary = json.dumps(
        [
            {
                "category": r.get("category"),
                "impact": r.get("impact"),
                "impacted_value": r.get("impacted_value"),
                "short_description": r.get("short_description"),
                "potential_annual_savings": r.get("potential_annual_savings", 0),
                "resource_group": r.get("resource_group"),
            }
            for r in advisor_data[:20]  # Limit to top 20 for token efficiency
        ],
        indent=2,
    )

    sample_note = (
        "\n\nNOTE: This analysis is based on SAMPLE/DEMO DATA. "
        "Please configure real Azure credentials to get actual recommendations."
        if is_sample
        else ""
    )

    user_message = f"""Please analyze the following Azure cost and advisor recommendation data and provide comprehensive FinOps recommendations.{sample_note}

## Azure Cost Summary (Last {cost_data.get('period_days', 30)} Days)
```json
{cost_breakdown}
```

## Azure Advisor Recommendations ({len(advisor_data)} total, {len(cost_recs)} cost-related)
Total Advisor-identified potential annual savings: ${total_annual_savings:,.2f}

```json
{advisor_summary}
```

Please provide:
1. An executive summary (2-3 sentences)
2. Top 5 savings opportunities with specific actions and estimated monthly savings
3. Quick wins (implementable this week)
4. Total potential monthly savings estimate
5. Risk considerations and validation steps

Format your response clearly with markdown headings."""

    try:
        analysis_text = _call_claude(config, user_message)
        total_monthly_savings = _parse_savings_from_text(analysis_text)
        if total_monthly_savings == 0:
            total_monthly_savings = total_annual_savings / 12

        # Extract structured data from the analysis
        opportunities = _extract_opportunities_from_advisor(advisor_data)
        quick_wins = _extract_quick_wins(advisor_data)

        # Build executive summary (first paragraph of analysis)
        lines = analysis_text.strip().split("\n")
        exec_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                exec_lines.append(stripped)
                if len(exec_lines) >= 3:
                    break
        executive_summary = " ".join(exec_lines)[:500]

        return {
            "executive_summary": executive_summary,
            "top_savings_opportunities": opportunities,
            "quick_wins": quick_wins,
            "total_potential_savings": round(total_monthly_savings, 2),
            "analysis_text": analysis_text,
            "is_sample_data": is_sample,
        }
    except Exception as exc:
        logger.error("Claude Azure analysis failed: %s", exc)
        return _fallback_azure_analysis(advisor_data, cost_data)


def analyze_m365(config, license_data: dict) -> dict:
    """
    Analyzes M365 license usage data using Claude.

    Returns:
        dict with keys:
            - executive_summary: str
            - license_recommendations: list of dicts
            - total_potential_savings: float
            - analysis_text: str (full markdown analysis)
    """
    if not config.has_anthropic_config():
        return _fallback_m365_analysis(license_data)

    is_sample = license_data.get("sample_data", False)
    total_spend = license_data.get("total_monthly_spend_estimate", 0)
    potential_savings = license_data.get("potential_savings", 0)

    license_summary = json.dumps(
        {
            "total_monthly_spend_estimate": total_spend,
            "total_annual_spend_estimate": license_data.get("total_annual_spend_estimate", total_spend * 12),
            "inactive_users": license_data.get("inactive_users", 0),
            "potential_savings_from_unused_licenses": potential_savings,
            "licenses": [
                {
                    "friendly_name": lic.get("friendly_name"),
                    "consumed_units": lic.get("consumed_units"),
                    "enabled_units": lic.get("enabled_units"),
                    "unused_units": lic.get("unused_units"),
                    "unit_cost_estimate": lic.get("unit_cost_estimate"),
                    "unused_cost_estimate": lic.get("unused_cost_estimate"),
                }
                for lic in license_data.get("licenses", [])
            ],
            "existing_recommendations": license_data.get("recommendations", []),
        },
        indent=2,
    )

    sample_note = (
        "\n\nNOTE: This analysis is based on SAMPLE/DEMO DATA. "
        "Please configure real M365 credentials to get actual recommendations."
        if is_sample
        else ""
    )

    user_message = f"""Please analyze the following Microsoft 365 license usage data and provide comprehensive cost optimization recommendations.{sample_note}

## M365 License Summary
```json
{license_summary}
```

Please provide:
1. An executive summary (2-3 sentences covering total spend and savings potential)
2. License-specific recommendations with current count, recommended count, and monthly savings
3. Actions for inactive users
4. Estimated total monthly savings
5. Implementation steps and risks

Format your response clearly with markdown headings."""

    try:
        analysis_text = _call_claude(config, user_message)
        total_monthly_savings = _parse_savings_from_text(analysis_text)
        if total_monthly_savings == 0:
            total_monthly_savings = potential_savings

        license_recs = _build_license_recommendations(license_data)

        lines = analysis_text.strip().split("\n")
        exec_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                exec_lines.append(stripped)
                if len(exec_lines) >= 3:
                    break
        executive_summary = " ".join(exec_lines)[:500]

        return {
            "executive_summary": executive_summary,
            "license_recommendations": license_recs,
            "total_potential_savings": round(total_monthly_savings, 2),
            "analysis_text": analysis_text,
            "is_sample_data": is_sample,
        }
    except Exception as exc:
        logger.error("Claude M365 analysis failed: %s", exc)
        return _fallback_m365_analysis(license_data)


def full_analysis(config, azure_data: dict, m365_data: dict) -> dict:
    """
    Comprehensive analysis combining Azure and M365 cost data.

    azure_data should contain: advisor_recommendations, cost_summary
    m365_data should contain: license_summary

    Returns consolidated analysis dict.
    """
    if not config.has_anthropic_config():
        azure_analysis = _fallback_azure_analysis(
            azure_data.get("advisor_recommendations", []),
            azure_data.get("cost_summary", {}),
        )
        m365_analysis = _fallback_m365_analysis(m365_data.get("license_summary", {}))
        return _merge_analyses(azure_analysis, m365_analysis)

    advisor_data = azure_data.get("advisor_recommendations", [])
    cost_data = azure_data.get("cost_summary", {})
    license_data = m365_data.get("license_summary", {})

    is_sample = (
        cost_data.get("sample_data", False)
        or license_data.get("sample_data", False)
        or (advisor_data and advisor_data[0].get("sample_data", False))
    )

    azure_total_cost = cost_data.get("total_cost", 0)
    m365_total_cost = license_data.get("total_monthly_spend_estimate", 0)
    azure_advisor_savings = sum(r.get("potential_annual_savings", 0) for r in advisor_data) / 12
    m365_potential_savings = license_data.get("potential_savings", 0)

    combined_message = f"""Please provide a COMPREHENSIVE cloud cost optimization analysis covering both Azure Infrastructure and Microsoft 365 licensing.{' NOTE: Based on SAMPLE/DEMO DATA.' if is_sample else ''}

## AZURE INFRASTRUCTURE
**Monthly Spend:** ${azure_total_cost:,.2f}
**Advisor-Identified Monthly Savings:** ${azure_advisor_savings:,.2f}

**Top Cost Services:**
{json.dumps(cost_data.get('by_service', [])[:6], indent=2)}

**Key Advisor Recommendations:**
{json.dumps([{'category': r['category'], 'impact': r['impact'], 'description': r['short_description'], 'annual_savings': r.get('potential_annual_savings', 0)} for r in advisor_data[:10]], indent=2)}

## MICROSOFT 365 LICENSING
**Monthly Spend:** ${m365_total_cost:,.2f}
**Potential Monthly Savings:** ${m365_potential_savings:,.2f}
**Inactive Users:** {license_data.get('inactive_users', 0)}

**License Breakdown:**
{json.dumps([{'name': l['friendly_name'], 'consumed': l['consumed_units'], 'total': l['enabled_units'], 'unused': l['unused_units'], 'monthly_cost': l['consumed_units'] * l['unit_cost_estimate']} for l in license_data.get('licenses', [])], indent=2)}

## REQUEST
Please provide:
1. **Executive Summary** - Combined cloud spend, total savings potential across Azure + M365
2. **Priority Matrix** - Top 10 actions ranked by ROI (savings vs effort)
3. **Azure Quick Wins** - Top 3 immediate actions
4. **M365 Quick Wins** - Top 3 immediate actions
5. **30-60-90 Day Roadmap** - Phased implementation plan
6. **Total Potential Savings** - Monthly and annual figures
7. **KPIs to Track** - Metrics to monitor optimization progress

Format with clear markdown headings and quantified recommendations."""

    try:
        analysis_text = _call_claude(config, combined_message)
        total_savings = azure_advisor_savings + m365_potential_savings
        total_savings_parsed = _parse_savings_from_text(analysis_text)
        if total_savings_parsed > total_savings:
            total_savings = total_savings_parsed

        azure_analysis = analyze_azure_costs(config, advisor_data, cost_data)
        m365_analysis = analyze_m365(config, license_data)

        lines = analysis_text.strip().split("\n")
        exec_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                exec_lines.append(stripped)
                if len(exec_lines) >= 3:
                    break
        executive_summary = " ".join(exec_lines)[:600]

        return {
            "executive_summary": executive_summary,
            "azure": azure_analysis,
            "m365": m365_analysis,
            "combined_analysis_text": analysis_text,
            "total_azure_monthly_spend": round(azure_total_cost, 2),
            "total_m365_monthly_spend": round(m365_total_cost, 2),
            "total_monthly_spend": round(azure_total_cost + m365_total_cost, 2),
            "total_potential_monthly_savings": round(total_savings, 2),
            "total_potential_annual_savings": round(total_savings * 12, 2),
            "is_sample_data": is_sample,
        }
    except Exception as exc:
        logger.error("Claude full analysis failed: %s", exc)
        azure_analysis = _fallback_azure_analysis(advisor_data, cost_data)
        m365_analysis = _fallback_m365_analysis(license_data)
        return _merge_analyses(azure_analysis, m365_analysis)


# ---------------------------------------------------------------------------
# Fallback / helper functions
# ---------------------------------------------------------------------------

def _extract_opportunities_from_advisor(advisor_data: list[dict]) -> list[dict]:
    """Extracts top savings opportunities from advisor data."""
    cost_recs = [r for r in advisor_data if r.get("category") == "Cost"]
    cost_recs_sorted = sorted(
        cost_recs, key=lambda x: x.get("potential_annual_savings", 0), reverse=True
    )
    results = []
    for rec in cost_recs_sorted[:5]:
        annual = rec.get("potential_annual_savings", 0)
        monthly = annual / 12
        results.append({
            "title": rec.get("short_description", "Cost optimization opportunity"),
            "description": (
                f"Resource: {rec.get('impacted_value', 'N/A')} "
                f"(Resource Group: {rec.get('resource_group', 'N/A')})"
            ),
            "estimated_monthly_savings": round(monthly, 2),
            "priority": rec.get("impact", "Medium"),
            "action_required": rec.get("short_description", "Review and implement recommendation"),
        })
    return results


def _extract_quick_wins(advisor_data: list[dict]) -> list[dict]:
    """Extracts quick-win actions from advisor recommendations."""
    quick_win_keywords = ["delete", "shutdown", "deallocate", "idle", "unused", "unattached"]
    quick_wins = []
    for rec in advisor_data:
        desc = rec.get("short_description", "").lower()
        if any(kw in desc for kw in quick_win_keywords):
            annual = rec.get("potential_annual_savings", 0)
            quick_wins.append({
                "action": rec.get("short_description", ""),
                "savings": f"${annual / 12:,.2f}/month",
                "effort": "Low",
            })
    # Add a few general quick wins if list is short
    if len(quick_wins) < 3:
        quick_wins.append({
            "action": "Review and delete unattached managed disks",
            "savings": "Varies",
            "effort": "Low",
        })
        quick_wins.append({
            "action": "Set up Azure Cost Alerts and budgets for each resource group",
            "savings": "Prevents overruns",
            "effort": "Low",
        })
    return quick_wins[:5]


def _build_license_recommendations(license_data: dict) -> list[dict]:
    """Builds structured license recommendations from license summary."""
    results = []
    for lic in license_data.get("licenses", []):
        if lic.get("unused_units", 0) > 0:
            results.append({
                "license_name": lic.get("friendly_name", lic.get("sku_part_number", "")),
                "current_count": lic.get("enabled_units", 0),
                "recommended_count": lic.get("consumed_units", 0),
                "monthly_savings": lic.get("unused_cost_estimate", 0),
                "action": (
                    f"Remove {lic['unused_units']} unassigned licenses. "
                    f"Reduce from {lic['enabled_units']} to {lic['consumed_units']}."
                ),
            })
    return sorted(results, key=lambda x: x["monthly_savings"], reverse=True)


def _fallback_azure_analysis(advisor_data: list[dict], cost_data: dict) -> dict:
    """Returns a structured fallback analysis when Claude is not available."""
    total_annual = sum(r.get("potential_annual_savings", 0) for r in advisor_data)
    total_monthly = total_annual / 12
    opportunities = _extract_opportunities_from_advisor(advisor_data)
    quick_wins = _extract_quick_wins(advisor_data)

    total_cost = cost_data.get("total_cost", 0)
    top_service = (cost_data.get("by_service") or [{}])[0]

    analysis_text = f"""## Azure Cost Analysis

### Executive Summary
Your Azure subscription is spending **${total_cost:,.2f}/month** (last 30 days). Azure Advisor has identified **${total_monthly:,.2f}/month** (${total_annual:,.2f}/year) in potential savings across {len(advisor_data)} recommendations.

### Top Savings Opportunities
{chr(10).join(f"- **{o['title']}**: ${o['estimated_monthly_savings']:,.2f}/month" for o in opportunities)}

### Highest Cost Service
{top_service.get('service_name', 'N/A')}: ${top_service.get('cost', 0):,.2f}/month

### Quick Wins
{chr(10).join(f"- {qw['action']} (Est. savings: {qw['savings']})" for qw in quick_wins)}

### Note
Configure your Anthropic API key to receive detailed AI-powered analysis and personalized recommendations.
"""

    return {
        "executive_summary": (
            f"Azure spend is ${total_cost:,.2f}/month with ${total_monthly:,.2f}/month "
            f"in identified savings opportunities from {len(advisor_data)} Advisor recommendations."
        ),
        "top_savings_opportunities": opportunities,
        "quick_wins": quick_wins,
        "total_potential_savings": round(total_monthly, 2),
        "analysis_text": analysis_text,
        "is_sample_data": cost_data.get("sample_data", False),
    }


def _fallback_m365_analysis(license_data: dict) -> dict:
    """Returns a structured fallback analysis when Claude is not available."""
    potential = license_data.get("potential_savings", 0)
    total_spend = license_data.get("total_monthly_spend_estimate", 0)
    inactive = license_data.get("inactive_users", 0)
    license_recs = _build_license_recommendations(license_data)

    analysis_text = f"""## Microsoft 365 License Analysis

### Executive Summary
Your M365 environment is spending **${total_spend:,.2f}/month** on licenses with approximately **${potential:,.2f}/month** in potential savings from {len(license_data.get('licenses', []))} license types analyzed.

### License Optimization Opportunities
{chr(10).join(f"- **{r['license_name']}**: Remove {r['current_count'] - r['recommended_count']} unused seats — save ${r['monthly_savings']:,.2f}/month" for r in license_recs)}

### Inactive Users
{inactive} users show no activity in the last 30 days across Teams and Exchange. Reviewing their license assignments could yield significant additional savings.

### Note
Configure your Anthropic API key to receive detailed AI-powered analysis and personalized recommendations.
"""

    return {
        "executive_summary": (
            f"M365 spend is ${total_spend:,.2f}/month with ${potential:,.2f}/month "
            f"in potential savings from unused licenses and {inactive} inactive users."
        ),
        "license_recommendations": license_recs,
        "total_potential_savings": round(potential, 2),
        "analysis_text": analysis_text,
        "is_sample_data": license_data.get("sample_data", False),
    }


def _merge_analyses(azure_analysis: dict, m365_analysis: dict) -> dict:
    """Merges Azure and M365 fallback analyses into a combined result."""
    azure_savings = azure_analysis.get("total_potential_savings", 0)
    m365_savings = m365_analysis.get("total_potential_savings", 0)
    total = azure_savings + m365_savings

    return {
        "executive_summary": (
            f"Combined cloud optimization potential: ${total:,.2f}/month "
            f"(Azure: ${azure_savings:,.2f}, M365: ${m365_savings:,.2f})."
        ),
        "azure": azure_analysis,
        "m365": m365_analysis,
        "combined_analysis_text": (
            azure_analysis.get("analysis_text", "") + "\n\n---\n\n" +
            m365_analysis.get("analysis_text", "")
        ),
        "total_potential_monthly_savings": round(total, 2),
        "total_potential_annual_savings": round(total * 12, 2),
        "is_sample_data": azure_analysis.get("is_sample_data", False) or m365_analysis.get("is_sample_data", False),
    }
