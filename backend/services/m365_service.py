"""
M365 / Microsoft Graph API service for the Azure Cost Optimizer.
Fetches license usage, mailbox activity, Teams usage, and SharePoint data.
Falls back to sample data when credentials are invalid or Graph API calls fail.
"""

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SKU friendly name mapping
# ---------------------------------------------------------------------------

SKU_FRIENDLY_NAMES: dict[str, str] = {
    "ENTERPRISEPREMIUM": "Microsoft 365 E5",
    "ENTERPRISEPACK": "Microsoft 365 E3",
    "SPE_E5": "Microsoft 365 E5",
    "SPE_E3": "Microsoft 365 E3",
    "SPE_F1": "Microsoft 365 F3",
    "DESKLESSPACK": "Microsoft 365 F1",
    "TEAMS_EXPLORATORY": "Microsoft Teams Exploratory",
    "TEAMS_FREE": "Microsoft Teams Free",
    "ATP_ENTERPRISE": "Microsoft Defender for Office 365 (Plan 2)",
    "EXCHANGE_S_ENTERPRISE": "Exchange Online (Plan 2)",
    "EXCHANGE_S_STANDARD": "Exchange Online (Plan 1)",
    "POWER_BI_PRO": "Power BI Pro",
    "POWER_BI_PREMIUM_PER_USER": "Power BI Premium Per User",
    "PBI_PREMIUM_PER_USER_ADDON": "Power BI Premium Per User Add-On",
    "FLOW_FREE": "Power Automate Free",
    "POWERFLOW_P1": "Power Automate Plan 1",
    "POWERFLOW_P2": "Power Automate Plan 2",
    "PROJECTPREMIUM": "Project Plan 5",
    "PROJECTPROFESSIONAL": "Project Plan 3",
    "VISIOCLIENT": "Visio Plan 2",
    "VISIOONLINE_PLAN1": "Visio Plan 1",
    "MCOEV": "Microsoft Teams Phone Standard",
    "MCOPSTN1": "Microsoft 365 Domestic Calling Plan",
    "INTUNE_A": "Microsoft Intune",
    "EMS": "Enterprise Mobility + Security E3",
    "EMSPREMIUM": "Enterprise Mobility + Security E5",
    "AAD_PREMIUM": "Azure Active Directory Premium P1",
    "AAD_PREMIUM_P2": "Azure Active Directory Premium P2",
    "RIGHTSMANAGEMENT": "Azure Information Protection Plan 1",
    "INFORMATION_PROTECTION_COMPLIANCE": "Microsoft 365 E5 Compliance",
    "WIN10_PRO_ENT_SUB": "Windows 10/11 Enterprise E3",
    "WIN_ENT_E5": "Windows 10/11 Enterprise E5",
    "OFFICE_BUSINESS_PREMIUM": "Microsoft 365 Business Premium",
    "OFFICE_BUSINESS": "Microsoft 365 Apps for Business",
    "OFFICESUBSCRIPTION": "Microsoft 365 Apps for Enterprise",
    "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Standard",
    "O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
    "STANDARD_MULTITENANT_HOSTING": "SharePoint Syntex",
    "DEVELOPERPACK": "Microsoft 365 E3 Developer",
    "DEVELOPERPACK_E5": "Microsoft 365 E5 Developer",
}

# Monthly per-user cost estimates in USD (list price, approximate)
SKU_UNIT_COST: dict[str, float] = {
    "ENTERPRISEPREMIUM": 57.00,
    "ENTERPRISEPACK": 36.00,
    "SPE_E5": 57.00,
    "SPE_E3": 36.00,
    "SPE_F1": 8.00,
    "DESKLESSPACK": 2.25,
    "TEAMS_EXPLORATORY": 0.00,
    "TEAMS_FREE": 0.00,
    "ATP_ENTERPRISE": 5.00,
    "EXCHANGE_S_ENTERPRISE": 8.00,
    "EXCHANGE_S_STANDARD": 4.00,
    "POWER_BI_PRO": 10.00,
    "POWER_BI_PREMIUM_PER_USER": 20.00,
    "PROJECTPREMIUM": 55.00,
    "PROJECTPROFESSIONAL": 30.00,
    "VISIOCLIENT": 28.00,
    "VISIOONLINE_PLAN1": 5.00,
    "INTUNE_A": 8.00,
    "EMS": 9.00,
    "EMSPREMIUM": 15.40,
    "AAD_PREMIUM": 6.00,
    "AAD_PREMIUM_P2": 9.00,
    "OFFICE_BUSINESS_PREMIUM": 22.00,
    "OFFICE_BUSINESS": 8.25,
    "OFFICESUBSCRIPTION": 12.00,
    "O365_BUSINESS_PREMIUM": 12.50,
    "O365_BUSINESS_ESSENTIALS": 6.00,
    "WIN10_PRO_ENT_SUB": 7.00,
    "WIN_ENT_E5": 13.20,
    "MCOEV": 8.00,
}

# ---------------------------------------------------------------------------
# Sample / demo data
# ---------------------------------------------------------------------------

_SAMPLE_LICENSES = [
    {
        "sku_id": "c7df2760-2c81-4ef7-b578-5b5392b571df",
        "sku_part_number": "ENTERPRISEPREMIUM",
        "friendly_name": "Microsoft 365 E5",
        "consumed_units": 82,
        "enabled_units": 100,
        "suspended_units": 0,
        "warning_units": 2,
        "unit_cost_estimate": 57.00,
        "unused_units": 18,
        "unused_cost_estimate": 1026.00,
        "sample_data": True,
    },
    {
        "sku_id": "6fd2c87f-b296-42f0-b197-1e91e994b900",
        "sku_part_number": "ENTERPRISEPACK",
        "friendly_name": "Microsoft 365 E3",
        "consumed_units": 145,
        "enabled_units": 150,
        "suspended_units": 0,
        "warning_units": 0,
        "unit_cost_estimate": 36.00,
        "unused_units": 5,
        "unused_cost_estimate": 180.00,
        "sample_data": True,
    },
    {
        "sku_id": "f30db892-07e9-47e9-837c-80727f46fd3d",
        "sku_part_number": "POWER_BI_PRO",
        "friendly_name": "Power BI Pro",
        "consumed_units": 28,
        "enabled_units": 50,
        "suspended_units": 0,
        "warning_units": 0,
        "unit_cost_estimate": 10.00,
        "unused_units": 22,
        "unused_cost_estimate": 220.00,
        "sample_data": True,
    },
    {
        "sku_id": "1f2f344a-700d-42c9-9427-5cea1d5d7ba6",
        "sku_part_number": "PROJECTPROFESSIONAL",
        "friendly_name": "Project Plan 3",
        "consumed_units": 8,
        "enabled_units": 15,
        "suspended_units": 0,
        "warning_units": 0,
        "unit_cost_estimate": 30.00,
        "unused_units": 7,
        "unused_cost_estimate": 210.00,
        "sample_data": True,
    },
]

_SAMPLE_LICENSE_SUMMARY = {
    "total_monthly_spend_estimate": 12_054.00,
    "total_annual_spend_estimate": 144_648.00,
    "licenses": _SAMPLE_LICENSES,
    "inactive_users": 34,
    "potential_savings": 2_418.00,
    "recommendations": [
        {
            "title": "Remove 18 unused Microsoft 365 E5 licenses",
            "description": (
                "18 out of 100 E5 licenses are unassigned. "
                "Consider reducing your license count by at least 15 to save ~$855/month."
            ),
            "monthly_savings": 855.00,
            "priority": "High",
            "action": "Reduce E5 license count from 100 to 85",
        },
        {
            "title": "Downgrade 22 unused Power BI Pro licenses",
            "description": (
                "22 Power BI Pro licenses are unassigned. "
                "Review if all assigned users are actively using Power BI."
            ),
            "monthly_savings": 220.00,
            "priority": "Medium",
            "action": "Remove 22 unassigned Power BI Pro licenses",
        },
        {
            "title": "Reclaim 7 unused Project Plan 3 licenses",
            "description": (
                "7 out of 15 Project licenses are unassigned. "
                "Reduce to 8 to match actual usage."
            ),
            "monthly_savings": 210.00,
            "priority": "Medium",
            "action": "Reduce Project Plan 3 license count from 15 to 8",
        },
        {
            "title": "Audit 34 inactive users",
            "description": (
                "34 users have shown no activity in Teams or Exchange in the last 30 days. "
                "Verify if they still require full licenses."
            ),
            "monthly_savings": 1_188.00,
            "priority": "High",
            "action": "Review and optionally downgrade or remove licenses for inactive users",
        },
    ],
    "sample_data": True,
}

_SAMPLE_APP_USAGE = {
    "period": "D30",
    "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    "word_active": 142,
    "excel_active": 138,
    "powerpoint_active": 97,
    "outlook_active": 215,
    "onenote_active": 64,
    "teams_active": 198,
    "sharepoint_active": 176,
    "onedrive_active": 189,
    "yammer_active": 12,
    "skype_active": 8,
    "total_licensed_users": 245,
    "sample_data": True,
}

# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------

def get_token(config) -> Optional[str]:
    """
    Acquires a Microsoft Graph API access token using MSAL client credentials flow.
    Returns the access token string, or None on failure.
    """
    if not config.has_m365_config():
        logger.info("No M365 config present - cannot acquire token.")
        return None

    try:
        import msal

        authority = f"https://login.microsoftonline.com/{config.m365_tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=config.m365_client_id,
            client_credential=config.m365_client_secret,
            authority=authority,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            return result["access_token"]
        error = result.get("error_description", result.get("error", "Unknown error"))
        logger.error("MSAL token acquisition failed: %s", error)
        return None
    except Exception as exc:
        logger.error("Failed to acquire M365 token: %s", exc)
        return None


def _graph_get(token: str, url: str, params: Optional[dict] = None) -> Optional[dict]:
    """Makes an authenticated GET request to the Microsoft Graph API."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_exc:
        logger.error("Graph API HTTP error for %s: %s", url, http_exc)
        return None
    except Exception as exc:
        logger.error("Graph API request failed for %s: %s", url, exc)
        return None


def _graph_get_csv(token: str, url: str) -> Optional[list[dict]]:
    """
    Makes an authenticated GET request to the Microsoft Graph API expecting CSV content.
    Returns parsed list of dicts, or None on failure.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/plain"}
    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code in (401, 403):
            logger.warning("Graph API access denied (403/401) for %s - insufficient scopes.", url)
            return None
        response.raise_for_status()
        content = response.text
        if not content.strip():
            return []
        reader = csv.DictReader(io.StringIO(content))
        return [dict(row) for row in reader]
    except Exception as exc:
        logger.error("Graph API CSV request failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_subscribed_licenses(config) -> list[dict]:
    """
    Fetches subscribed SKUs from Microsoft Graph /subscribedSkus.
    Returns list of license dicts with usage and cost estimates.
    """
    token = get_token(config)
    if not token:
        logger.info("No M365 token - returning sample license data.")
        return _SAMPLE_LICENSES

    data = _graph_get(token, "https://graph.microsoft.com/v1.0/subscribedSkus")
    if data is None:
        return _SAMPLE_LICENSES

    skus = data.get("value", [])
    results = []

    for sku in skus:
        sku_part = sku.get("skuPartNumber", "")
        friendly = SKU_FRIENDLY_NAMES.get(sku_part, sku_part)
        unit_cost = SKU_UNIT_COST.get(sku_part, 0.0)

        consumed = int(sku.get("consumedUnits", 0))
        prepaid = sku.get("prepaidUnits", {})
        enabled = int(prepaid.get("enabled", 0))
        suspended = int(prepaid.get("suspended", 0))
        warning = int(prepaid.get("warning", 0))
        unused = max(0, enabled - consumed)
        unused_cost = round(unused * unit_cost, 2)

        results.append({
            "sku_id": sku.get("skuId", ""),
            "sku_part_number": sku_part,
            "friendly_name": friendly,
            "consumed_units": consumed,
            "enabled_units": enabled,
            "suspended_units": suspended,
            "warning_units": warning,
            "unit_cost_estimate": unit_cost,
            "unused_units": unused,
            "unused_cost_estimate": unused_cost,
            "sample_data": False,
        })

    return results


def get_m365_app_usage(config) -> dict:
    """
    Fetches M365 app user counts for the last 30 days.
    Returns usage summary dict.
    """
    token = get_token(config)
    if not token:
        return _SAMPLE_APP_USAGE

    url = "https://graph.microsoft.com/v1.0/reports/getM365AppUserCounts(period='D30')"
    rows = _graph_get_csv(token, url)
    if rows is None:
        return _SAMPLE_APP_USAGE

    # The report returns daily rows; take the most recent
    if not rows:
        return _SAMPLE_APP_USAGE

    # Sort by report date descending and take latest
    rows_sorted = sorted(rows, key=lambda r: r.get("Report Date", ""), reverse=True)
    latest = rows_sorted[0] if rows_sorted else {}

    def _int(val):
        try:
            return int(val) if val else 0
        except (ValueError, TypeError):
            return 0

    return {
        "period": "D30",
        "report_date": latest.get("Report Date", ""),
        "word_active": _int(latest.get("Word")),
        "excel_active": _int(latest.get("Excel")),
        "powerpoint_active": _int(latest.get("PowerPoint")),
        "outlook_active": _int(latest.get("Outlook")),
        "onenote_active": _int(latest.get("OneNote")),
        "teams_active": _int(latest.get("Teams")),
        "sharepoint_active": _int(latest.get("SharePoint")),
        "onedrive_active": _int(latest.get("OneDrive")),
        "yammer_active": _int(latest.get("Yammer")),
        "skype_active": _int(latest.get("Skype For Business")),
        "total_licensed_users": _int(latest.get("Report Period")),
        "sample_data": False,
    }


def get_mailbox_usage(config) -> list[dict]:
    """
    Fetches mailbox usage detail report for the last 30 days.
    Returns list of mailbox dicts with storage and last activity date.
    """
    token = get_token(config)
    if not token:
        return []

    url = "https://graph.microsoft.com/v1.0/reports/getMailboxUsageDetail(period='D30')"
    rows = _graph_get_csv(token, url)
    if rows is None:
        return []

    results = []
    for row in rows:
        results.append({
            "user_principal_name": row.get("User Principal Name", ""),
            "display_name": row.get("Display Name", ""),
            "is_deleted": row.get("Is Deleted", "False").lower() == "true",
            "item_count": int(row.get("Item Count", 0) or 0),
            "storage_used_bytes": int(row.get("Storage Used (Byte)", 0) or 0),
            "last_activity_date": row.get("Last Activity Date", ""),
            "report_period": row.get("Report Period", "30"),
        })
    return results


def get_teams_usage(config) -> list[dict]:
    """
    Fetches Teams user activity detail for the last 30 days.
    Returns list of per-user Teams usage dicts.
    """
    token = get_token(config)
    if not token:
        return []

    url = "https://graph.microsoft.com/v1.0/reports/getTeamsUserActivityUserDetail(period='D30')"
    rows = _graph_get_csv(token, url)
    if rows is None:
        return []

    results = []
    for row in rows:
        results.append({
            "user_principal_name": row.get("User Principal Name", ""),
            "display_name": row.get("Display Name", ""),
            "is_deleted": row.get("Is Deleted", "False").lower() == "true",
            "last_activity_date": row.get("Last Activity Date", ""),
            "team_chat_message_count": int(row.get("Team Chat Message Count", 0) or 0),
            "private_chat_message_count": int(row.get("Private Chat Message Count", 0) or 0),
            "call_count": int(row.get("Call Count", 0) or 0),
            "meeting_count": int(row.get("Meetings Attended Count", 0) or 0),
            "meetings_organized_count": int(row.get("Meetings Organized Count", 0) or 0),
            "report_period": row.get("Report Period", "30"),
        })
    return results


def get_sharepoint_usage(config) -> list[dict]:
    """
    Fetches SharePoint site usage detail for the last 30 days.
    Returns list of per-site usage dicts.
    """
    token = get_token(config)
    if not token:
        return []

    url = "https://graph.microsoft.com/v1.0/reports/getSharePointSiteUsageDetail(period='D30')"
    rows = _graph_get_csv(token, url)
    if rows is None:
        return []

    results = []
    for row in rows:
        results.append({
            "site_url": row.get("Site URL", ""),
            "owner_display_name": row.get("Owner Display Name", ""),
            "is_deleted": row.get("Is Deleted", "False").lower() == "true",
            "last_activity_date": row.get("Last Activity Date", ""),
            "file_count": int(row.get("File Count", 0) or 0),
            "active_file_count": int(row.get("Active File Count", 0) or 0),
            "storage_used_bytes": int(row.get("Storage Used (Byte)", 0) or 0),
            "storage_allocated_bytes": int(row.get("Storage Allocated (Byte)", 0) or 0),
            "page_view_count": int(row.get("Page View Count", 0) or 0),
            "visited_page_count": int(row.get("Visited Page Count", 0) or 0),
        })
    return results


def _count_inactive_users(mailbox_rows: list[dict], teams_rows: list[dict]) -> int:
    """
    Counts users with no activity in the last 30 days across Teams and Exchange.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    active_upns: set[str] = set()

    for row in mailbox_rows:
        date_str = row.get("last_activity_date", "")
        if date_str:
            try:
                activity_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if activity_date >= cutoff:
                    active_upns.add(row.get("user_principal_name", "").lower())
            except ValueError:
                pass

    for row in teams_rows:
        date_str = row.get("last_activity_date", "")
        if date_str:
            try:
                activity_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if activity_date >= cutoff:
                    active_upns.add(row.get("user_principal_name", "").lower())
            except ValueError:
                pass

    all_upns: set[str] = set()
    for row in mailbox_rows:
        upn = row.get("user_principal_name", "").lower()
        if upn and not row.get("is_deleted", False):
            all_upns.add(upn)

    inactive_count = len(all_upns - active_upns)
    return inactive_count


def get_license_summary(config) -> dict:
    """
    Orchestrates all M365 data calls and returns a comprehensive summary dict with:
    - total_monthly_spend_estimate
    - licenses: list of license details
    - inactive_users: count of users with no activity in 30 days
    - potential_savings: estimated savings from unused licenses
    - recommendations: list of specific recommendations
    """
    if not config.has_m365_config():
        logger.info("No M365 config - returning sample license summary.")
        return _SAMPLE_LICENSE_SUMMARY

    # Fetch all data
    licenses = get_subscribed_licenses(config)
    mailbox_rows = get_mailbox_usage(config)
    teams_rows = get_teams_usage(config)

    is_sample = any(lic.get("sample_data") for lic in licenses) if licenses else True

    # Calculate totals
    total_monthly = sum(
        lic["consumed_units"] * lic["unit_cost_estimate"]
        for lic in licenses
    )
    total_unused_cost = sum(lic["unused_cost_estimate"] for lic in licenses)

    # Count inactive users (only if real data)
    if mailbox_rows or teams_rows:
        inactive_users = _count_inactive_users(mailbox_rows, teams_rows)
    else:
        inactive_users = 0

    # Build recommendations
    recommendations = []

    for lic in sorted(licenses, key=lambda x: x["unused_cost_estimate"], reverse=True):
        if lic["unused_units"] > 0 and lic["unused_cost_estimate"] > 0:
            savings = lic["unused_cost_estimate"]
            recommendations.append({
                "title": f"Remove {lic['unused_units']} unused {lic['friendly_name']} licenses",
                "description": (
                    f"{lic['unused_units']} out of {lic['enabled_units']} "
                    f"{lic['friendly_name']} licenses are unassigned. "
                    f"Reducing the license count could save ${savings:.2f}/month."
                ),
                "monthly_savings": round(savings, 2),
                "priority": "High" if savings > 500 else "Medium",
                "action": (
                    f"Reduce {lic['friendly_name']} license count from "
                    f"{lic['enabled_units']} to {lic['consumed_units']}"
                ),
            })

    if inactive_users > 0:
        # Estimate average cost per user using consumed/cost data
        total_consumed = sum(lic["consumed_units"] for lic in licenses if lic["consumed_units"] > 0)
        avg_cost_per_user = (total_monthly / total_consumed) if total_consumed > 0 else 36.0
        inactive_savings = round(inactive_users * avg_cost_per_user, 2)
        recommendations.append({
            "title": f"Audit {inactive_users} inactive users",
            "description": (
                f"{inactive_users} users have shown no activity in Teams or Exchange "
                f"in the last 30 days. These users may not need full enterprise licenses."
            ),
            "monthly_savings": inactive_savings,
            "priority": "High" if inactive_savings > 500 else "Medium",
            "action": "Review and downgrade or remove licenses for inactive users",
        })
        total_unused_cost += inactive_savings

    return {
        "total_monthly_spend_estimate": round(total_monthly, 2),
        "total_annual_spend_estimate": round(total_monthly * 12, 2),
        "licenses": licenses,
        "inactive_users": inactive_users,
        "potential_savings": round(total_unused_cost, 2),
        "recommendations": recommendations,
        "sample_data": is_sample,
    }
