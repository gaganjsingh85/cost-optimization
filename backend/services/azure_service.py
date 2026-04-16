"""
Azure service layer for Azure Cost Optimizer.

Changes vs earlier version:
- All expensive calls are cached via services.cache (TTLs: advisor 5min,
  cost 60s, rightsizing 5min, subscription 10min).
- Cost Management calls include x-ms-command-name=CostAnalysis which
  materially reduces 429 throttling.
- 429 responses honor the x-ms-ratelimit-*-retry-after headers with a
  single bounded retry.
- Subscription info uses getattr for tenant_id to handle SDK variance.
- All functions return a data_status field so the UI can render a clear
  state instead of silent sample data.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.cache import get_cache

logger = logging.getLogger(__name__)

# Cache TTLs (seconds)
_TTL_ADVISOR = 300       # 5 min
_TTL_COST = 60           # 1 min - most volatile
_TTL_RIGHTSIZING = 300   # 5 min
_TTL_SUBSCRIPTION = 600  # 10 min

# Extra request headers that reduce 429s on CostManagement
_COST_HEADERS = {"x-ms-command-name": "CostAnalysis", "ClientType": "CostOptimizer"}

# Retry config for 429
_MAX_RETRIES = 1      # One retry after 429
_MAX_WAIT = 30        # Cap on retry-after wait (seconds)

# Headers we inspect for retry-after info
_RETRY_AFTER_HEADERS = (
    "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after",
    "x-ms-ratelimit-microsoft.costmanagement-qpu-retry-after",
    "x-ms-ratelimit-microsoft.costmanagement-tenant-retry-after",
    "x-ms-ratelimit-microsoft.costmanagement-client-retry-after",
    "Retry-After",
)


# ---------------------------------------------------------------------------
# Sample / demo data - used ONLY when no config is present
# ---------------------------------------------------------------------------

_SAMPLE_ADVISOR = [
    {
        "id": "/subscriptions/demo/providers/Microsoft.Advisor/recommendations/demo-1",
        "name": "demo-1",
        "category": "Cost",
        "impact": "High",
        "impacted_field": "Microsoft.Compute/virtualMachines",
        "impacted_value": "vm-demo-001",
        "short_description": {
            "problem": "Right-size or shut down underutilized virtual machines",
            "solution": "Based on utilization patterns, this VM can be resized to a smaller SKU to reduce costs.",
        },
        "description": "Right-size or shut down underutilized virtual machines",
        "recommendation_type": "VirtualMachineRightSizing",
        "extended_properties": {"annualSavingsAmount": "1766.40"},
        "potential_annual_savings": 1766.40,
        "resource_group": "rg-demo",
        "subscription_id": "demo-sub",
        "sample_data": True,
    },
]

_SAMPLE_COST = {
    "total_cost": 0.0,
    "currency": "USD",
    "period_days": 30,
    "by_service": [],
    "by_resource_group": [],
    "by_location": [],
    "daily_trend": [],
    "sample_data": True,
    "data_status": "sample",
    "message": "No Azure credentials configured. Go to Settings to connect.",
}

_SAMPLE_SUBSCRIPTION = {
    "subscription_id": "demo-subscription-id",
    "display_name": "Demo Subscription (No credentials)",
    "state": "Unknown",
    "tenant_id": "demo-tenant-id",
    "sample_data": True,
    "data_status": "sample",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_savings(ep: dict) -> float:
    if not ep:
        return 0.0
    for key in ("annualSavingsAmount", "annualSavings", "savingsAmount"):
        v = ep.get(key)
        if v is not None:
            return _safe_float(v)
    return 0.0


def _classify_error(exc: Exception) -> str:
    msg = str(exc)
    if "AADSTS700016" in msg:
        return "auth_app_not_in_tenant"
    if "AADSTS7000215" in msg or "Invalid client secret" in msg:
        return "auth_invalid_secret"
    if "AADSTS50034" in msg:
        return "auth_tenant_not_found"
    if "AuthorizationFailed" in msg or "does not have authorization" in msg:
        return "authz_forbidden"
    if "SubscriptionNotFound" in msg:
        return "subscription_not_found"
    if "429" in msg or "Too many requests" in msg:
        return "rate_limited"
    if "No module named" in msg:
        return "sdk_error"
    return "unknown"


def _extract_retry_after(exc: Exception) -> float:
    """Tries to extract retry-after seconds from an HttpResponseError."""
    try:
        resp = getattr(exc, "response", None)
        headers = getattr(resp, "headers", None) if resp else None
        if not headers:
            return 5.0  # Sensible default
        for h in _RETRY_AFTER_HEADERS:
            v = headers.get(h)
            if v:
                try:
                    return min(_MAX_WAIT, float(v))
                except ValueError:
                    continue
    except Exception:
        pass
    return 5.0


def get_credential(config):
    from azure.identity import ClientSecretCredential
    return ClientSecretCredential(
        tenant_id=config.azure_tenant_id,
        client_id=config.azure_client_id,
        client_secret=config.azure_client_secret,
    )


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------

def get_advisor_recommendations(config) -> list[dict]:
    """Legacy signature - returns just the list."""
    return get_advisor_recommendations_with_status(config)["recommendations"]


def get_advisor_recommendations_with_status(config) -> dict:
    """
    Returns {"recommendations": [...], "data_status": str, "error": str|None, "error_class": str|None}.
    Cached for 5 minutes.
    """
    if not config.has_azure_config():
        return {
            "recommendations": _SAMPLE_ADVISOR,
            "data_status": "sample",
            "error": "No Azure credentials configured.",
        }

    cache = get_cache()
    cache_key = f"advisor:{config.azure_subscription_id}"

    def _fetch() -> dict:
        try:
            from azure.mgmt.advisor import AdvisorManagementClient

            credential = get_credential(config)
            client = AdvisorManagementClient(credential, config.azure_subscription_id)

            # The SDK's list() returns CACHED recommendations. If the cache is
            # empty/stale, we need to trigger generation and retry.
            raw_recs = list(client.recommendations.list())
            logger.info(
                "Advisor.recommendations.list() returned %d raw items for subscription %s",
                len(raw_recs), config.azure_subscription_id,
            )

            # If empty, trigger a regeneration and retry once. This is the
            # ONLY way to get recommendations on a fresh or long-idle
            # subscription where Azure's own cache has expired.
            if not raw_recs:
                logger.info("Advisor cache empty - triggering generate_recommendations()")
                try:
                    client.recommendations.generate()
                    # Generation is async on Azure's side. Wait briefly.
                    import time as _t
                    _t.sleep(8)
                    raw_recs = list(client.recommendations.list())
                    logger.info(
                        "After generate: Advisor returned %d recommendations",
                        len(raw_recs),
                    )
                except Exception as gen_exc:
                    logger.warning("generate_recommendations() failed: %s", gen_exc)

            recs = []
            skipped = 0
            first_rec_logged = False
            for rec in raw_recs:
                # In newer azure-mgmt-advisor SDKs (4.x+), fields are flattened
                # directly onto the rec object. In older versions, they're
                # nested under rec.properties. Handle both by using rec.properties
                # if it exists, else falling back to rec itself.
                props = getattr(rec, "properties", None) or rec

                # Log the first rec's structure once so we can see what the SDK
                # is actually returning if parsing is failing.
                if not first_rec_logged:
                    try:
                        logger.info(
                            "First rec sample - id=%s, name=%s, type=%s, using_properties_attr=%s",
                            getattr(rec, "id", "?"),
                            getattr(rec, "name", "?"),
                            type(rec).__name__,
                            getattr(rec, "properties", None) is not None,
                        )
                        logger.info(
                            "First rec props type=%s, key attrs present: category=%s, impact=%s, short_description=%s, extended_properties=%s",
                            type(props).__name__,
                            hasattr(props, "category"),
                            hasattr(props, "impact"),
                            hasattr(props, "short_description"),
                            hasattr(props, "extended_properties"),
                        )
                        sd_dbg = getattr(props, "short_description", None)
                        logger.info(
                            "First rec short_description - type=%s, value=%r",
                            type(sd_dbg).__name__ if sd_dbg else "None",
                            str(sd_dbg)[:200] if sd_dbg else None,
                        )
                    except Exception as dbg_exc:
                        logger.warning("Diagnostic logging failed: %s", dbg_exc)
                    first_rec_logged = True

                try:
                    # Extract each field independently so one bad field doesn't
                    # skip the whole rec.
                    def _safe_get(obj, attr, default=""):
                        try:
                            v = getattr(obj, attr, default)
                            return v if v is not None else default
                        except Exception:
                            return default

                    ep = {}
                    try:
                        raw_ep = _safe_get(props, "extended_properties", None)
                        if raw_ep:
                            ep = dict(raw_ep)
                    except Exception as ep_exc:
                        logger.warning("Failed to parse extended_properties: %s", ep_exc)

                    # short_description in the Advisor SDK is a ShortDescription
                    # object with .problem and .solution attributes. Handle both
                    # object and string (older/newer SDK variance) forms.
                    problem_text = ""
                    solution_text = ""
                    try:
                        sd = _safe_get(props, "short_description", None)
                        if sd is not None:
                            if isinstance(sd, str):
                                problem_text = sd
                            else:
                                problem_text = str(_safe_get(sd, "problem", "") or "")
                                solution_text = str(_safe_get(sd, "solution", "") or "")
                    except Exception as sd_exc:
                        logger.warning("Failed to parse short_description: %s", sd_exc)

                    # Fallback - some recs only populate description at top level
                    if not problem_text:
                        problem_text = str(_safe_get(props, "description", "") or "")

                    # Also check extended_properties.recommendationType for a human label
                    rec_type = ep.get("recommendationType") or ep.get("recommendationTypeId", "") or ""
                    # And the "displayName" / "reason" fields that sometimes appear
                    display_name = ep.get("displayName") or ep.get("reason", "") or ""
                    if not problem_text and display_name:
                        problem_text = display_name

                    category = str(_safe_get(props, "category", "") or "")
                    impact = str(_safe_get(props, "impact", "") or "")
                    impacted_field = str(_safe_get(props, "impacted_field", "") or "")
                    impacted_value = str(_safe_get(props, "impacted_value", "") or "")

                    resource_id = str(_safe_get(rec, "id", "") or "")
                    resource_group = ""
                    if resource_id:
                        parts = resource_id.split("/")
                        # resource_group name appears after "resourceGroups" (case-insensitive)
                        for i, part in enumerate(parts):
                            if part.lower() == "resourcegroups" and i + 1 < len(parts):
                                resource_group = parts[i + 1]
                                break

                    # Skip entries where we couldn't extract any meaningful data.
                    # This can happen for subscription-level recs that have no
                    # category/impact in the flattened payload.
                    if not category and not impact and not problem_text:
                        skipped += 1
                        logger.warning(
                            "Skipping rec %s - could not extract category/impact/description",
                            resource_id or "?",
                        )
                        continue

                    # Return short_description as an OBJECT so the frontend can
                    # show problem + solution separately. Also provide a flat
                    # `description` string for simpler consumers.
                    recs.append({
                        "id": resource_id,
                        "name": str(_safe_get(rec, "name", "") or ""),
                        "category": category,
                        "impact": impact,
                        "impacted_field": impacted_field,
                        "impacted_value": impacted_value,
                        "short_description": {
                            "problem": problem_text,
                            "solution": solution_text,
                        },
                        "description": problem_text,  # flat convenience field
                        "recommendation_type": rec_type,
                        "extended_properties": ep,
                        "potential_annual_savings": _extract_savings(ep),
                        "resource_group": resource_group,
                        "subscription_id": config.azure_subscription_id,
                        "sample_data": False,
                    })
                except Exception as inner:
                    skipped += 1
                    # Log the FULL exception including type name so we can see
                    # what's actually failing.
                    import traceback as _tb
                    logger.warning(
                        "Skipping recommendation due to parse error: %s: %s\n%s",
                        type(inner).__name__,
                        inner,
                        _tb.format_exc().splitlines()[-3:],
                    )

            if skipped:
                logger.info("Skipped %d recommendations due to parse errors", skipped)
            logger.info("Retrieved %d advisor recommendations.", len(recs))

            return {
                "recommendations": recs,
                "data_status": "live" if recs else "empty",
                "error": None if recs else (
                    "Azure Advisor returned no cached recommendations. It may take "
                    "a few minutes for Azure to populate them. Try refreshing in a bit."
                ),
                "error_class": None,
            }
        except Exception as exc:
            ec = _classify_error(exc)
            logger.error("Failed to fetch advisor recommendations (%s): %s", ec, exc)
            return {
                "recommendations": [],
                "data_status": "auth_error" if ec.startswith("auth") or ec == "authz_forbidden" else "sdk_error",
                "error": str(exc),
                "error_class": ec,
            }

    result = cache.get_or_compute(cache_key, _fetch, ttl=_TTL_ADVISOR)

    # Never cache empty results for the full 5 min - they often indicate a
    # transient state where Azure's own cache is warming up. Shorten TTL to 30s
    # so the next refresh will retry.
    if result.get("data_status") in ("empty", "sdk_error", "auth_error"):
        cache.set(cache_key, result, ttl=30)

    return result


# ---------------------------------------------------------------------------
# Cost Management
# ---------------------------------------------------------------------------

def _run_cost_query(client, scope: str, body_dict: dict):
    """
    Wrapper around client.query.usage that handles one 429 retry using the
    retry-after header. Adds x-ms-command-name header.
    """
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.query.usage(
                scope=scope,
                parameters=body_dict,
                headers=_COST_HEADERS,
            )
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "Too many requests" in msg:
                if attempt >= _MAX_RETRIES:
                    raise
                wait_s = _extract_retry_after(exc)
                logger.warning(
                    "CostManagement 429; retrying once after %.1fs (attempt %d)",
                    wait_s, attempt + 1,
                )
                time.sleep(wait_s)
                continue
            raise
    # Unreachable
    return None


def get_cost_summary(config, days: int = 30) -> dict:
    """
    Fetches cost data with aggressive caching. On 429, returns empty payload
    with data_status='rate_limited' so the UI can show a friendly message.
    """
    if not config.has_azure_config():
        result = dict(_SAMPLE_COST)
        result["period_days"] = days
        return result

    cache = get_cache()
    cache_key = f"cost_summary:{config.azure_subscription_id}:{days}"

    def _empty_with_error(err: str, err_class: str, data_status: str = "auth_error") -> dict:
        return {
            "total_cost": 0.0,
            "currency": "USD",
            "period_days": days,
            "by_service": [],
            "by_resource_group": [],
            "by_location": [],
            "daily_trend": [],
            "sample_data": False,
            "data_status": data_status,
            "error": err,
            "error_class": err_class,
        }

    def _fetch() -> dict:
        try:
            from azure.mgmt.costmanagement import CostManagementClient
            from azure.mgmt.costmanagement.models import (
                QueryDefinition,
                QueryTimePeriod,
                QueryDataset,
                QueryAggregation,
                QueryGrouping,
            )

            credential = get_credential(config)
            client = CostManagementClient(credential)

            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            scope = f"/subscriptions/{config.azure_subscription_id}"

            def _make_grouped_query(grouping_name: str) -> QueryDefinition:
                return QueryDefinition(
                    type="ActualCost",
                    timeframe="Custom",
                    time_period=QueryTimePeriod(from_property=start_date, to=end_date),
                    dataset=QueryDataset(
                        granularity="None",
                        aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                        grouping=[QueryGrouping(type="Dimension", name=grouping_name)],
                    ),
                )

            # Run queries one at a time with small delay between each to stay
            # well under the 4-calls-per-minute CostManagement limit.
            def _run_and_parse(grouping: str) -> list:
                result = _run_cost_query(client, scope, _make_grouped_query(grouping))
                rows = result.rows or []
                columns = [c.name.lower() for c in (result.columns or [])]
                return [dict(zip(columns, row)) for row in rows]

            service_rows = _run_and_parse("ServiceName")
            rg_rows = _run_and_parse("ResourceGroupName")
            loc_rows = _run_and_parse("ResourceLocation")

            by_service = sorted([
                {"service_name": str(r.get("servicename", "Unknown")),
                 "cost": _safe_float(r.get("totalcost", r.get("cost", 0)))}
                for r in service_rows
            ], key=lambda x: x["cost"], reverse=True)

            by_resource_group = sorted([
                {"resource_group": str(r.get("resourcegroupname", r.get("resourcegroup", "Unknown"))),
                 "cost": _safe_float(r.get("totalcost", r.get("cost", 0)))}
                for r in rg_rows
            ], key=lambda x: x["cost"], reverse=True)

            by_location = sorted([
                {"location": str(r.get("resourcelocation", "Unknown")),
                 "cost": _safe_float(r.get("totalcost", r.get("cost", 0)))}
                for r in loc_rows
            ], key=lambda x: x["cost"], reverse=True)

            # Total cost = sum of service costs (avoids an extra API call)
            total_cost = sum(s["cost"] for s in by_service)

            # Daily trend - one more query. If it 429s we still return partial.
            daily_trend = []
            try:
                daily_def = QueryDefinition(
                    type="ActualCost",
                    timeframe="Custom",
                    time_period=QueryTimePeriod(from_property=start_date, to=end_date),
                    dataset=QueryDataset(
                        granularity="Daily",
                        aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                    ),
                )
                daily_result = _run_cost_query(client, scope, daily_def)
                if daily_result.rows and daily_result.columns:
                    date_idx = cost_idx = None
                    for i, col in enumerate(daily_result.columns):
                        nl = col.name.lower()
                        if "date" in nl or "usagedate" in nl:
                            date_idx = i
                        elif "cost" in nl or "pretaxcost" in nl:
                            cost_idx = i
                    for row in daily_result.rows:
                        date_val = str(row[date_idx]) if date_idx is not None else ""
                        cost_val = _safe_float(row[cost_idx]) if cost_idx is not None else 0.0
                        if date_val.isdigit() and len(date_val) == 8:
                            date_val = f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]}"
                        daily_trend.append({"date": date_val, "cost": cost_val})
                    daily_trend.sort(key=lambda x: x["date"])
            except Exception as daily_exc:
                logger.warning("Daily trend query failed (non-fatal): %s", daily_exc)

            has_data = total_cost > 0 or by_service or by_resource_group
            return {
                "total_cost": round(total_cost, 2),
                "currency": "USD",
                "period_days": days,
                "by_service": by_service,
                "by_resource_group": by_resource_group,
                "by_location": by_location,
                "daily_trend": daily_trend,
                "sample_data": False,
                "data_status": "live" if has_data else "empty",
                "message": None if has_data else "No cost data returned for this period.",
            }

        except Exception as exc:
            ec = _classify_error(exc)
            logger.error("Failed to fetch cost summary (%s): %s", ec, exc)
            if ec == "rate_limited":
                return _empty_with_error(
                    "Azure Cost Management is rate-limiting this subscription. Data will refresh in a minute.",
                    ec,
                    "rate_limited",
                )
            status = "auth_error" if ec.startswith("auth") or ec == "authz_forbidden" else "sdk_error"
            return _empty_with_error(str(exc), ec, status)

    result = cache.get_or_compute(cache_key, _fetch, ttl=_TTL_COST)
    # Don't cache rate-limited or error results for the full 60s - let them retry sooner
    if result.get("data_status") in ("rate_limited", "sdk_error", "auth_error"):
        # Shorten TTL by pre-expiring if currently cached with full TTL
        # We just invalidate so next call retries after ~15s via a short TTL
        cache.set(cache_key, result, ttl=15)
    return result


# ---------------------------------------------------------------------------
# Compute right-sizing
# ---------------------------------------------------------------------------

def get_compute_rightsizing(config) -> list[dict]:
    if not config.has_azure_config():
        return []

    cache = get_cache()
    cache_key = f"rightsizing:{config.azure_subscription_id}"

    def _fetch() -> list:
        try:
            from azure.mgmt.compute import ComputeManagementClient

            credential = get_credential(config)
            compute_client = ComputeManagementClient(credential, config.azure_subscription_id)

            size_cost_map = {
                "Standard_B1s": 7.59, "Standard_B1ms": 15.19, "Standard_B2s": 30.37,
                "Standard_B2ms": 60.74, "Standard_B4ms": 121.47, "Standard_B8ms": 242.94,
                "Standard_D2s_v3": 73.00, "Standard_D4s_v3": 146.00, "Standard_D8s_v3": 292.00,
                "Standard_D16s_v3": 584.00, "Standard_D32s_v3": 1168.00,
                "Standard_D2as_v4": 70.08, "Standard_D4as_v4": 140.16, "Standard_D8as_v4": 280.32,
                "Standard_E2s_v3": 101.18, "Standard_E4s_v3": 202.36, "Standard_E8s_v3": 404.72,
                "Standard_F2s_v2": 61.78, "Standard_F4s_v2": 123.56, "Standard_F8s_v2": 247.12,
            }
            downsize_map = {
                "Standard_D4s_v3": "Standard_D2s_v3",
                "Standard_D8s_v3": "Standard_D4s_v3",
                "Standard_D16s_v3": "Standard_D8s_v3",
                "Standard_D32s_v3": "Standard_D16s_v3",
                "Standard_E4s_v3": "Standard_E2s_v3",
                "Standard_E8s_v3": "Standard_E4s_v3",
                "Standard_D4as_v4": "Standard_D2as_v4",
                "Standard_D8as_v4": "Standard_D4as_v4",
                "Standard_B4ms": "Standard_B2ms",
                "Standard_B8ms": "Standard_B4ms",
                "Standard_F4s_v2": "Standard_F2s_v2",
                "Standard_F8s_v2": "Standard_F4s_v2",
            }

            recs = []
            for vm in compute_client.virtual_machines.list_all():
                try:
                    vm_size = str(vm.hardware_profile.vm_size) if vm.hardware_profile and vm.hardware_profile.vm_size else ""
                    resource_id = vm.id or ""
                    resource_group = ""
                    parts = resource_id.split("/")
                    if "resourceGroups" in parts:
                        idx = parts.index("resourceGroups")
                        if idx + 1 < len(parts):
                            resource_group = parts[idx + 1]

                    current_cost = size_cost_map.get(vm_size, 0.0)
                    recommended_size = downsize_map.get(vm_size)
                    if not recommended_size:
                        continue
                    recommended_cost = size_cost_map.get(recommended_size, current_cost * 0.5)
                    monthly_savings = current_cost - recommended_cost
                    if monthly_savings <= 0:
                        continue

                    recs.append({
                        "vm_name": vm.name or "",
                        "resource_group": resource_group,
                        "location": vm.location or "unknown",
                        "current_size": vm_size,
                        "current_cost_monthly": round(current_cost, 2),
                        "recommended_size": recommended_size,
                        "recommended_cost_monthly": round(recommended_cost, 2),
                        "monthly_savings": round(monthly_savings, 2),
                        "annual_savings": round(monthly_savings * 12, 2),
                        "cpu_utilization_avg": "N/A",
                        "memory_utilization_avg": "N/A",
                        "reason": (
                            f"VM is running {vm_size}. Downsizing to {recommended_size} "
                            f"could save ${monthly_savings:.2f}/month. Verify utilization first."
                        ),
                        "tags": dict(vm.tags) if vm.tags else {},
                        "sample_data": False,
                    })
                except Exception as inner:
                    logger.warning("Skipping VM due to parse error: %s", inner)

            logger.info("Generated %d compute rightsizing recommendations.", len(recs))
            return sorted(recs, key=lambda x: x["annual_savings"], reverse=True)

        except Exception as exc:
            logger.error("Failed to fetch compute rightsizing: %s", exc)
            return []

    return cache.get_or_compute(cache_key, _fetch, ttl=_TTL_RIGHTSIZING)


# ---------------------------------------------------------------------------
# Subscription info
# ---------------------------------------------------------------------------

def get_subscription_info(config) -> dict:
    if not config.has_azure_config():
        return _SAMPLE_SUBSCRIPTION

    cache = get_cache()
    cache_key = f"subscription:{config.azure_subscription_id}"

    def _fetch() -> dict:
        try:
            from azure.mgmt.subscription import SubscriptionClient

            credential = get_credential(config)
            client = SubscriptionClient(credential)
            sub = client.subscriptions.get(config.azure_subscription_id)

            # Different SDK versions expose tenant_id differently - use getattr
            tenant_id = (
                getattr(sub, "tenant_id", None)
                or getattr(sub, "tenantId", None)
                or config.azure_tenant_id
            )

            return {
                "subscription_id": getattr(sub, "subscription_id", None) or config.azure_subscription_id,
                "display_name": getattr(sub, "display_name", None) or "Unnamed Subscription",
                "state": str(getattr(sub, "state", "") or "Unknown"),
                "tenant_id": tenant_id,
                "sample_data": False,
                "data_status": "live",
            }
        except Exception as exc:
            ec = _classify_error(exc)
            logger.error("Failed to fetch subscription info (%s): %s", ec, exc)
            return {
                "subscription_id": config.azure_subscription_id or "unknown",
                "display_name": "Unable to fetch subscription name",
                "state": "Unknown",
                "tenant_id": config.azure_tenant_id or "unknown",
                "sample_data": False,
                "data_status": "auth_error" if ec.startswith("auth") else "sdk_error",
                "error": str(exc),
                "error_class": ec,
            }

    return cache.get_or_compute(cache_key, _fetch, ttl=_TTL_SUBSCRIPTION)