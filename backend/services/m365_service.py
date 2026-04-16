"""
M365 / Microsoft Graph service for Azure Cost Optimizer.

Changes:
- All expensive calls are cached (TTLs: license summary 5min, activity 10min).
- On auth failure we return empty + data_status, not fake sample data.
"""

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from services.cache import get_cache

logger = logging.getLogger(__name__)

_TTL_LICENSES = 300   # 5 min
_TTL_ACTIVITY = 600   # 10 min
_TTL_TOKEN = 3300     # ~55 min (tokens last 60, refresh a bit early)


# ---------------------------------------------------------------------------
# SKU friendly name + unit cost mapping
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
    "AAD_PREMIUM": "Microsoft Entra ID P1",
    "AAD_PREMIUM_P2": "Microsoft Entra ID P2",
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

SKU_UNIT_COST: dict[str, float] = {
    "ENTERPRISEPREMIUM": 57.00, "ENTERPRISEPACK": 36.00, "SPE_E5": 57.00,
    "SPE_E3": 36.00, "SPE_F1": 8.00, "DESKLESSPACK": 2.25,
    "TEAMS_EXPLORATORY": 0.00, "TEAMS_FREE": 0.00,
    "ATP_ENTERPRISE": 5.00, "EXCHANGE_S_ENTERPRISE": 8.00,
    "EXCHANGE_S_STANDARD": 4.00, "POWER_BI_PRO": 10.00,
    "POWER_BI_PREMIUM_PER_USER": 20.00, "PROJECTPREMIUM": 55.00,
    "PROJECTPROFESSIONAL": 30.00, "VISIOCLIENT": 28.00,
    "VISIOONLINE_PLAN1": 5.00, "INTUNE_A": 8.00,
    "EMS": 9.00, "EMSPREMIUM": 15.40,
    "AAD_PREMIUM": 6.00, "AAD_PREMIUM_P2": 9.00,
    "OFFICE_BUSINESS_PREMIUM": 22.00, "OFFICE_BUSINESS": 8.25,
    "OFFICESUBSCRIPTION": 12.00, "O365_BUSINESS_PREMIUM": 12.50,
    "O365_BUSINESS_ESSENTIALS": 6.00, "WIN10_PRO_ENT_SUB": 7.00,
    "WIN_ENT_E5": 13.20, "MCOEV": 8.00,
}

_SAMPLE_LICENSE_SUMMARY = {
    "total_monthly_spend_estimate": 0.0,
    "total_annual_spend_estimate": 0.0,
    "licenses": [],
    "inactive_users": 0,
    "potential_savings": 0.0,
    "recommendations": [],
    "sample_data": True,
    "data_status": "sample",
    "message": "No M365 credentials configured. Go to Settings to connect.",
}


def _classify_token_error(msg: str) -> str:
    if "AADSTS700016" in msg:
        return "auth_app_not_in_tenant"
    if "AADSTS7000215" in msg or "Invalid client secret" in msg:
        return "auth_invalid_secret"
    if "AADSTS50034" in msg or "tenant" in msg.lower():
        return "auth_tenant_not_found"
    if "AADSTS65001" in msg:
        return "auth_consent_required"
    return "auth_unknown"


# ---------------------------------------------------------------------------
# Token with caching
# ---------------------------------------------------------------------------

def _get_token_with_error(config) -> tuple[Optional[str], Optional[str]]:
    """Returns (token, error_description). Cached."""
    if not config.has_m365_config():
        return None, "No M365 credentials configured."

    cache = get_cache()
    cache_key = f"m365_token:{config.m365_tenant_id}:{config.m365_client_id}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached, None

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
            token = result["access_token"]
            cache.set(cache_key, token, ttl=_TTL_TOKEN)
            return token, None
        error = result.get("error_description", result.get("error", "Unknown error"))
        return None, error
    except Exception as exc:
        return None, str(exc)


def get_token(config) -> Optional[str]:
    token, _ = _get_token_with_error(config)
    return token


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _graph_get(token: str, url: str, params: Optional[dict] = None) -> Optional[dict]:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as exc:
        logger.error("Graph API HTTP error for %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.error("Graph API request failed for %s: %s", url, exc)
        return None


def _graph_get_csv(token: str, url: str) -> Optional[list[dict]]:
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/plain"}
    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code in (401, 403):
            logger.warning("Graph CSV access denied (%d) for %s", response.status_code, url)
            return None
        response.raise_for_status()
        content = response.text
        if not content.strip():
            return []
        reader = csv.DictReader(io.StringIO(content))
        return [dict(row) for row in reader]
    except Exception as exc:
        logger.error("Graph CSV request failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_subscribed_licenses(config) -> list[dict]:
    return get_license_summary(config).get("licenses", [])


def get_m365_app_usage(config) -> dict:
    cache = get_cache()
    cache_key = f"m365_app_usage:{config.m365_tenant_id}"

    def _fetch() -> dict:
        token = get_token(config)
        if not token:
            return {"sample_data": False, "data_status": "auth_error"}

        url = "https://graph.microsoft.com/v1.0/reports/getM365AppUserCounts(period='D30')"
        rows = _graph_get_csv(token, url)
        if rows is None or not rows:
            return {"sample_data": False, "data_status": "empty"}

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
            "data_status": "live",
        }

    return cache.get_or_compute(cache_key, _fetch, ttl=_TTL_ACTIVITY)


def _fetch_mailbox_and_teams(config) -> tuple[list, list]:
    """Returns (mailbox_rows, teams_rows) - cached together."""
    cache = get_cache()
    cache_key = f"m365_activity:{config.m365_tenant_id}"

    def _fetch():
        token = get_token(config)
        if not token:
            return ([], [])
        mb_url = "https://graph.microsoft.com/v1.0/reports/getMailboxUsageDetail(period='D30')"
        tm_url = "https://graph.microsoft.com/v1.0/reports/getTeamsUserActivityUserDetail(period='D30')"
        mb = _graph_get_csv(token, mb_url) or []
        tm = _graph_get_csv(token, tm_url) or []
        mb_clean = [
            {
                "user_principal_name": r.get("User Principal Name", ""),
                "is_deleted": r.get("Is Deleted", "False").lower() == "true",
                "last_activity_date": r.get("Last Activity Date", ""),
            }
            for r in mb
        ]
        tm_clean = [
            {
                "user_principal_name": r.get("User Principal Name", ""),
                "is_deleted": r.get("Is Deleted", "False").lower() == "true",
                "last_activity_date": r.get("Last Activity Date", ""),
            }
            for r in tm
        ]
        return (mb_clean, tm_clean)

    return cache.get_or_compute(cache_key, _fetch, ttl=_TTL_ACTIVITY)


def _count_inactive_users(mailbox_rows: list, teams_rows: list) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    active = set()
    for row in mailbox_rows + teams_rows:
        d = row.get("last_activity_date", "")
        if d:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    active.add(row.get("user_principal_name", "").lower())
            except ValueError:
                pass
    all_upns = set()
    for row in mailbox_rows:
        upn = row.get("user_principal_name", "").lower()
        if upn and not row.get("is_deleted", False):
            all_upns.add(upn)
    return len(all_upns - active)


def get_license_summary(config) -> dict:
    """
    Full M365 license summary. Cached 5 minutes.
    Return shape:
      { total_monthly_spend_estimate, total_annual_spend_estimate,
        licenses, inactive_users, potential_savings, recommendations,
        data_status, error?, error_class? }
    """
    if not config.has_m365_config():
        return _SAMPLE_LICENSE_SUMMARY

    cache = get_cache()
    cache_key = f"m365_license_summary:{config.m365_tenant_id}"

    def _fetch() -> dict:
        token, token_err = _get_token_with_error(config)
        if not token:
            ec = _classify_token_error(token_err or "")
            return {
                "total_monthly_spend_estimate": 0.0,
                "total_annual_spend_estimate": 0.0,
                "licenses": [],
                "inactive_users": 0,
                "potential_savings": 0.0,
                "recommendations": [],
                "sample_data": False,
                "data_status": "auth_error",
                "error": token_err,
                "error_class": ec,
            }

        data = _graph_get(token, "https://graph.microsoft.com/v1.0/subscribedSkus")
        if data is None:
            return {
                "total_monthly_spend_estimate": 0.0,
                "total_annual_spend_estimate": 0.0,
                "licenses": [],
                "inactive_users": 0,
                "potential_savings": 0.0,
                "recommendations": [],
                "sample_data": False,
                "data_status": "api_error",
                "error": "Failed to fetch /subscribedSkus - check Organization.Read.All permission.",
            }

        skus = data.get("value", [])
        licenses = []
        for sku in skus:
            sku_part = sku.get("skuPartNumber", "")
            friendly = SKU_FRIENDLY_NAMES.get(sku_part, sku_part or "Unknown license")
            unit_cost = SKU_UNIT_COST.get(sku_part, 0.0)
            consumed = int(sku.get("consumedUnits", 0))
            prepaid = sku.get("prepaidUnits", {})
            enabled = int(prepaid.get("enabled", 0))
            suspended = int(prepaid.get("suspended", 0))
            warning = int(prepaid.get("warning", 0))
            unused = max(0, enabled - consumed)
            licenses.append({
                "sku_id": sku.get("skuId", ""),
                "sku_part_number": sku_part,
                "friendly_name": friendly,
                "consumed_units": consumed,
                "enabled_units": enabled,
                "suspended_units": suspended,
                "warning_units": warning,
                "unit_cost_estimate": unit_cost,
                "unused_units": unused,
                "unused_cost_estimate": round(unused * unit_cost, 2),
                "sample_data": False,
            })

        total_monthly = sum(l["consumed_units"] * l["unit_cost_estimate"] for l in licenses)
        total_unused = sum(l["unused_cost_estimate"] for l in licenses)

        mailbox_rows, teams_rows = _fetch_mailbox_and_teams(config)
        inactive_users = _count_inactive_users(mailbox_rows, teams_rows) if (mailbox_rows or teams_rows) else 0

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
            total_consumed = sum(l["consumed_units"] for l in licenses if l["consumed_units"] > 0)
            avg_cost = (total_monthly / total_consumed) if total_consumed > 0 else 36.0
            inactive_savings = round(inactive_users * avg_cost, 2)
            recommendations.append({
                "title": f"Audit {inactive_users} inactive users",
                "description": (
                    f"{inactive_users} users have shown no activity in Teams or Exchange "
                    "in the last 30 days. They may not need full enterprise licenses."
                ),
                "monthly_savings": inactive_savings,
                "priority": "High" if inactive_savings > 500 else "Medium",
                "action": "Review and downgrade or remove licenses for inactive users",
            })
            total_unused += inactive_savings

        return {
            "total_monthly_spend_estimate": round(total_monthly, 2),
            "total_annual_spend_estimate": round(total_monthly * 12, 2),
            "licenses": licenses,
            "inactive_users": inactive_users,
            "potential_savings": round(total_unused, 2),
            "recommendations": recommendations,
            "sample_data": False,
            "data_status": "live" if licenses else "empty",
        }

    return cache.get_or_compute(cache_key, _fetch, ttl=_TTL_LICENSES)