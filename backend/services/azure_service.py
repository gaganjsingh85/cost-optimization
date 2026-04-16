"""
Azure service layer for Azure Cost Optimizer.
Fetches Azure Advisor recommendations, cost data, and compute rightsizing info.
Falls back to sample data when credentials are invalid or API calls fail.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample / demo data used as fallback when real API calls fail
# ---------------------------------------------------------------------------

_SAMPLE_ADVISOR_RECOMMENDATIONS = [
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-001",
        "name": "rec-001",
        "category": "Cost",
        "impact": "High",
        "impacted_field": "Microsoft.Compute/virtualMachines",
        "impacted_value": "vm-prod-001",
        "short_description": "Right-size or shut down underutilized virtual machines",
        "extended_properties": {
            "savingsAmount": "147.20",
            "savingsCurrency": "USD",
            "annualSavingsAmount": "1766.40",
        },
        "potential_annual_savings": 1766.40,
        "resource_group": "rg-production",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-002",
        "name": "rec-002",
        "category": "Cost",
        "impact": "High",
        "impacted_field": "Microsoft.Sql/servers/databases",
        "impacted_value": "sql-analytics-db",
        "short_description": "Buy reserved capacity for Azure SQL Database to save money over pay-as-you-go costs",
        "extended_properties": {
            "savingsAmount": "312.50",
            "savingsCurrency": "USD",
            "annualSavingsAmount": "3750.00",
        },
        "potential_annual_savings": 3750.00,
        "resource_group": "rg-data",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-003",
        "name": "rec-003",
        "category": "Cost",
        "impact": "Medium",
        "impacted_field": "Microsoft.Storage/storageAccounts",
        "impacted_value": "storagedevlogs",
        "short_description": "Use Azure Blob Storage access tiers to reduce storage costs",
        "extended_properties": {
            "savingsAmount": "28.60",
            "savingsCurrency": "USD",
            "annualSavingsAmount": "343.20",
        },
        "potential_annual_savings": 343.20,
        "resource_group": "rg-dev",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-004",
        "name": "rec-004",
        "category": "Security",
        "impact": "High",
        "impacted_field": "Microsoft.Compute/virtualMachines",
        "impacted_value": "vm-legacy-001",
        "short_description": "Enable Microsoft Defender for servers",
        "extended_properties": {},
        "potential_annual_savings": 0.0,
        "resource_group": "rg-legacy",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-005",
        "name": "rec-005",
        "category": "HighAvailability",
        "impact": "Medium",
        "impacted_field": "Microsoft.Compute/virtualMachines",
        "impacted_value": "vm-prod-002",
        "short_description": "Enable virtual machine replication to protect your applications from regional outage",
        "extended_properties": {},
        "potential_annual_savings": 0.0,
        "resource_group": "rg-production",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-006",
        "name": "rec-006",
        "category": "Performance",
        "impact": "Low",
        "impacted_field": "Microsoft.Sql/servers/databases",
        "impacted_value": "sql-main-db",
        "short_description": "Add indexes to improve query performance",
        "extended_properties": {},
        "potential_annual_savings": 0.0,
        "resource_group": "rg-data",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-007",
        "name": "rec-007",
        "category": "Cost",
        "impact": "Medium",
        "impacted_field": "Microsoft.Compute/virtualMachines",
        "impacted_value": "vm-dev-003",
        "short_description": "Delete or deallocate idle virtual machines",
        "extended_properties": {
            "savingsAmount": "65.00",
            "savingsCurrency": "USD",
            "annualSavingsAmount": "780.00",
        },
        "potential_annual_savings": 780.00,
        "resource_group": "rg-dev",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
    {
        "id": "/subscriptions/demo-sub/providers/Microsoft.Advisor/recommendations/rec-008",
        "name": "rec-008",
        "category": "OperationalExcellence",
        "impact": "Low",
        "impacted_field": "Microsoft.Resources/subscriptions/resourceGroups",
        "impacted_value": "rg-temp-old",
        "short_description": "Delete unused resource groups to reduce management overhead",
        "extended_properties": {},
        "potential_annual_savings": 0.0,
        "resource_group": "rg-temp-old",
        "subscription_id": "demo-subscription-id",
        "sample_data": True,
    },
]

_SAMPLE_COST_SUMMARY = {
    "total_cost": 8432.75,
    "currency": "USD",
    "period_days": 30,
    "by_service": [
        {"service_name": "Virtual Machines", "cost": 3245.60},
        {"service_name": "Azure SQL Database", "cost": 1876.20},
        {"service_name": "Azure Kubernetes Service", "cost": 1123.45},
        {"service_name": "Storage Accounts", "cost": 654.30},
        {"service_name": "Azure Functions", "cost": 412.85},
        {"service_name": "Cognitive Services", "cost": 387.20},
        {"service_name": "Virtual Network", "cost": 298.15},
        {"service_name": "Azure Monitor", "cost": 215.00},
        {"service_name": "Other", "cost": 220.00},
    ],
    "by_resource_group": [
        {"resource_group": "rg-production", "cost": 4512.30},
        {"resource_group": "rg-data", "cost": 1987.65},
        {"resource_group": "rg-dev", "cost": 1234.80},
        {"resource_group": "rg-staging", "cost": 498.00},
        {"resource_group": "rg-legacy", "cost": 200.00},
    ],
    "by_location": [
        {"location": "East US", "cost": 4123.40},
        {"location": "West Europe", "cost": 2876.55},
        {"location": "Southeast Asia", "cost": 1432.80},
    ],
    "daily_trend": [
        {"date": (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"),
         "cost": round(250 + (i % 7) * 30 + (i % 3) * 15, 2)}
        for i in range(30, 0, -1)
    ],
    "sample_data": True,
}

_SAMPLE_COMPUTE_RIGHTSIZING = [
    {
        "vm_name": "vm-prod-001",
        "resource_group": "rg-production",
        "location": "East US",
        "current_size": "Standard_D4s_v3",
        "current_cost_monthly": 147.20,
        "recommended_size": "Standard_D2s_v3",
        "recommended_cost_monthly": 73.60,
        "monthly_savings": 73.60,
        "annual_savings": 883.20,
        "cpu_utilization_avg": "12%",
        "memory_utilization_avg": "18%",
        "reason": "CPU and memory utilization below 20% for 30 days. Downsize recommended.",
        "tags": {"environment": "production", "owner": "team-api"},
        "sample_data": True,
    },
    {
        "vm_name": "vm-dev-003",
        "resource_group": "rg-dev",
        "location": "East US",
        "current_size": "Standard_D4s_v3",
        "current_cost_monthly": 147.20,
        "recommended_size": "Deallocate",
        "recommended_cost_monthly": 0.0,
        "monthly_savings": 147.20,
        "annual_savings": 1766.40,
        "cpu_utilization_avg": "2%",
        "memory_utilization_avg": "5%",
        "reason": "VM appears idle for 30 days. Consider deallocation or deletion.",
        "tags": {"environment": "dev", "owner": "team-infra"},
        "sample_data": True,
    },
    {
        "vm_name": "vm-analytics-01",
        "resource_group": "rg-data",
        "location": "West Europe",
        "current_size": "Standard_E8s_v3",
        "current_cost_monthly": 485.60,
        "recommended_size": "Standard_E4s_v3",
        "recommended_cost_monthly": 242.80,
        "monthly_savings": 242.80,
        "annual_savings": 2913.60,
        "cpu_utilization_avg": "22%",
        "memory_utilization_avg": "35%",
        "reason": "Memory optimized VM with low CPU. Evaluate if smaller size meets workload needs.",
        "tags": {"environment": "production", "owner": "team-data"},
        "sample_data": True,
    },
]

_SAMPLE_SUBSCRIPTION = {
    "subscription_id": "demo-subscription-id",
    "display_name": "Demo Subscription (Sample Data)",
    "state": "Enabled",
    "tenant_id": "demo-tenant-id",
    "sample_data": True,
}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely converts a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_savings(extended_properties: dict) -> float:
    """Extracts potential annual savings from extended_properties dict."""
    if not extended_properties:
        return 0.0
    for key in ("annualSavingsAmount", "annualSavings", "savingsAmount"):
        val = extended_properties.get(key)
        if val is not None:
            return _safe_float(val)
    return 0.0


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_credential(config):
    """
    Returns an Azure ClientSecretCredential from the provided config.
    Raises ImportError-safe wrapper if azure-identity is unavailable.
    """
    from azure.identity import ClientSecretCredential

    return ClientSecretCredential(
        tenant_id=config.azure_tenant_id,
        client_id=config.azure_client_id,
        client_secret=config.azure_client_secret,
    )


def get_advisor_recommendations(config) -> list[dict]:
    """
    Fetches ALL Azure Advisor recommendations across all categories.
    Returns list of recommendation dicts.
    Falls back to sample data on any error.
    """
    if not config.has_azure_config():
        logger.info("No Azure config present - returning sample advisor recommendations.")
        return _SAMPLE_ADVISOR_RECOMMENDATIONS

    try:
        from azure.mgmt.advisor import AdvisorManagementClient

        credential = get_credential(config)
        client = AdvisorManagementClient(credential, config.azure_subscription_id)

        recommendations = []
        for rec in client.recommendations.list():
            try:
                props = rec.properties if hasattr(rec, "properties") else {}
                extended = {}
                if hasattr(props, "extended_properties") and props.extended_properties:
                    extended = dict(props.extended_properties)
                elif isinstance(props, dict):
                    extended = props.get("extended_properties", {})

                short_desc = ""
                if hasattr(props, "short_description"):
                    sd = props.short_description
                    if hasattr(sd, "solution"):
                        short_desc = sd.solution or (sd.problem if hasattr(sd, "problem") else "")
                    elif isinstance(sd, dict):
                        short_desc = sd.get("solution", sd.get("problem", ""))

                category = ""
                if hasattr(props, "category"):
                    category = str(props.category) if props.category else ""

                impact = ""
                if hasattr(props, "impact"):
                    impact = str(props.impact) if props.impact else ""

                impacted_field = ""
                impacted_value = ""
                if hasattr(props, "impacted_field"):
                    impacted_field = props.impacted_field or ""
                if hasattr(props, "impacted_value"):
                    impacted_value = props.impacted_value or ""

                resource_id = rec.id or ""
                resource_group = ""
                parts = resource_id.split("/")
                if "resourceGroups" in parts:
                    idx = parts.index("resourceGroups")
                    if idx + 1 < len(parts):
                        resource_group = parts[idx + 1]

                recommendations.append({
                    "id": resource_id,
                    "name": rec.name or "",
                    "category": category,
                    "impact": impact,
                    "impacted_field": impacted_field,
                    "impacted_value": impacted_value,
                    "short_description": short_desc,
                    "extended_properties": extended,
                    "potential_annual_savings": _extract_savings(extended),
                    "resource_group": resource_group,
                    "subscription_id": config.azure_subscription_id,
                    "sample_data": False,
                })
            except Exception as inner_exc:
                logger.warning("Skipping recommendation due to parse error: %s", inner_exc)
                continue

        logger.info("Retrieved %d advisor recommendations.", len(recommendations))
        return recommendations

    except Exception as exc:
        logger.error("Failed to fetch advisor recommendations: %s", exc)
        return _SAMPLE_ADVISOR_RECOMMENDATIONS


def get_cost_summary(config, days: int = 30) -> dict:
    """
    Fetches actual cost data for the last N days using Azure Cost Management.
    Returns aggregated cost summary dict.
    Falls back to sample data on any error.
    """
    if not config.has_azure_config():
        logger.info("No Azure config present - returning sample cost summary.")
        result = dict(_SAMPLE_COST_SUMMARY)
        result["period_days"] = days
        return result

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

        # Query total cost by service name
        def _run_query(grouping_name: str, grouping_type: str = "Dimension") -> list:
            query = QueryDefinition(
                type="ActualCost",
                timeframe="Custom",
                time_period=QueryTimePeriod(
                    from_property=start_date,
                    to=end_date,
                ),
                dataset=QueryDataset(
                    granularity="None",
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="Cost",
                            function="Sum",
                        )
                    },
                    grouping=[
                        QueryGrouping(
                            type=grouping_type,
                            name=grouping_name,
                        )
                    ],
                ),
            )
            result = client.query.usage(scope=scope, parameters=query)
            rows = result.rows or []
            columns = [c.name.lower() for c in (result.columns or [])]
            items = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                items.append(row_dict)
            return items

        # Query total
        total_query = QueryDefinition(
            type="ActualCost",
            timeframe="Custom",
            time_period=QueryTimePeriod(
                from_property=start_date,
                to=end_date,
            ),
            dataset=QueryDataset(
                granularity="None",
                aggregation={
                    "totalCost": QueryAggregation(name="Cost", function="Sum")
                },
            ),
        )
        total_result = client.query.usage(scope=scope, parameters=total_query)
        total_cost = 0.0
        currency = "USD"
        if total_result.rows:
            total_cost = _safe_float(total_result.rows[0][0])
        if total_result.columns and len(total_result.columns) > 1:
            # currency column is usually index 1
            if total_result.rows:
                currency = str(total_result.rows[0][1]) if len(total_result.rows[0]) > 1 else "USD"

        # By service
        service_rows = _run_query("ServiceName")
        by_service = [
            {"service_name": str(r.get("servicename", r.get("ServiceName", "Unknown"))),
             "cost": _safe_float(r.get("totalcost", r.get("cost", 0)))}
            for r in service_rows
        ]
        by_service.sort(key=lambda x: x["cost"], reverse=True)

        # By resource group
        rg_rows = _run_query("ResourceGroupName")
        by_resource_group = [
            {"resource_group": str(r.get("resourcegroupname", r.get("ResourceGroupName", "Unknown"))),
             "cost": _safe_float(r.get("totalcost", r.get("cost", 0)))}
            for r in rg_rows
        ]
        by_resource_group.sort(key=lambda x: x["cost"], reverse=True)

        # By location
        loc_rows = _run_query("ResourceLocation")
        by_location = [
            {"location": str(r.get("resourcelocation", r.get("ResourceLocation", "Unknown"))),
             "cost": _safe_float(r.get("totalcost", r.get("cost", 0)))}
            for r in loc_rows
        ]
        by_location.sort(key=lambda x: x["cost"], reverse=True)

        # Daily trend
        daily_query = QueryDefinition(
            type="ActualCost",
            timeframe="Custom",
            time_period=QueryTimePeriod(
                from_property=start_date,
                to=end_date,
            ),
            dataset=QueryDataset(
                granularity="Daily",
                aggregation={
                    "totalCost": QueryAggregation(name="Cost", function="Sum")
                },
            ),
        )
        daily_result = client.query.usage(scope=scope, parameters=daily_query)
        daily_trend = []
        if daily_result.rows:
            date_col_idx = None
            cost_col_idx = None
            if daily_result.columns:
                for i, col in enumerate(daily_result.columns):
                    name_lower = col.name.lower()
                    if "date" in name_lower or "usagedate" in name_lower:
                        date_col_idx = i
                    elif "cost" in name_lower or "pretaxcost" in name_lower:
                        cost_col_idx = i
            for row in daily_result.rows:
                date_val = str(row[date_col_idx]) if date_col_idx is not None else ""
                cost_val = _safe_float(row[cost_col_idx]) if cost_col_idx is not None else 0.0
                # Date may be integer like 20240101 or string
                if date_val.isdigit() and len(date_val) == 8:
                    date_val = f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]}"
                daily_trend.append({"date": date_val, "cost": cost_val})
        daily_trend.sort(key=lambda x: x["date"])

        return {
            "total_cost": round(total_cost, 2),
            "currency": currency,
            "period_days": days,
            "by_service": by_service,
            "by_resource_group": by_resource_group,
            "by_location": by_location,
            "daily_trend": daily_trend,
            "sample_data": False,
        }

    except Exception as exc:
        logger.error("Failed to fetch cost summary: %s", exc)
        result = dict(_SAMPLE_COST_SUMMARY)
        result["period_days"] = days
        return result


def get_compute_rightsizing(config) -> list[dict]:
    """
    Lists VMs and returns rightsizing recommendations based on size and tags.
    Falls back to sample data on any error.
    """
    if not config.has_azure_config():
        logger.info("No Azure config present - returning sample compute rightsizing data.")
        return _SAMPLE_COMPUTE_RIGHTSIZING

    try:
        from azure.mgmt.compute import ComputeManagementClient

        credential = get_credential(config)
        compute_client = ComputeManagementClient(credential, config.azure_subscription_id)

        # Size-to-monthly-cost estimates (USD, approximate East US pricing)
        size_cost_map = {
            "Standard_B1s": 7.59, "Standard_B1ms": 15.19, "Standard_B2s": 30.37,
            "Standard_B2ms": 60.74, "Standard_B4ms": 121.47, "Standard_B8ms": 242.94,
            "Standard_D1_v2": 52.56, "Standard_D2_v2": 105.12, "Standard_D4_v2": 210.24,
            "Standard_D2s_v3": 73.00, "Standard_D4s_v3": 146.00, "Standard_D8s_v3": 292.00,
            "Standard_D16s_v3": 584.00, "Standard_D32s_v3": 1168.00,
            "Standard_D2as_v4": 70.08, "Standard_D4as_v4": 140.16, "Standard_D8as_v4": 280.32,
            "Standard_E2s_v3": 101.18, "Standard_E4s_v3": 202.36, "Standard_E8s_v3": 404.72,
            "Standard_F2s_v2": 61.78, "Standard_F4s_v2": 123.56, "Standard_F8s_v2": 247.12,
        }

        # Downsize map: current -> recommended smaller size
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

        recommendations = []
        vms = list(compute_client.virtual_machines.list_all())

        for vm in vms:
            try:
                vm_size = ""
                if vm.hardware_profile and vm.hardware_profile.vm_size:
                    vm_size = str(vm.hardware_profile.vm_size)

                resource_id = vm.id or ""
                resource_group = ""
                parts = resource_id.split("/")
                if "resourceGroups" in parts:
                    idx = parts.index("resourceGroups")
                    if idx + 1 < len(parts):
                        resource_group = parts[idx + 1]

                location = vm.location or "unknown"
                tags = dict(vm.tags) if vm.tags else {}
                current_cost = size_cost_map.get(vm_size, 0.0)
                recommended_size = downsize_map.get(vm_size)

                if not recommended_size:
                    continue

                recommended_cost = size_cost_map.get(recommended_size, current_cost * 0.5)
                monthly_savings = current_cost - recommended_cost
                annual_savings = monthly_savings * 12

                if monthly_savings <= 0:
                    continue

                recommendations.append({
                    "vm_name": vm.name or "",
                    "resource_group": resource_group,
                    "location": location,
                    "current_size": vm_size,
                    "current_cost_monthly": round(current_cost, 2),
                    "recommended_size": recommended_size,
                    "recommended_cost_monthly": round(recommended_cost, 2),
                    "monthly_savings": round(monthly_savings, 2),
                    "annual_savings": round(annual_savings, 2),
                    "cpu_utilization_avg": "N/A (metrics require Azure Monitor integration)",
                    "memory_utilization_avg": "N/A",
                    "reason": (
                        f"VM is running {vm_size}. Based on size analysis, downsizing to "
                        f"{recommended_size} could save ${monthly_savings:.2f}/month. "
                        "Verify CPU/memory utilization before acting."
                    ),
                    "tags": tags,
                    "sample_data": False,
                })
            except Exception as inner_exc:
                logger.warning("Skipping VM due to parse error: %s", inner_exc)
                continue

        logger.info("Generated %d compute rightsizing recommendations.", len(recommendations))
        if not recommendations:
            logger.info("No rightsizing candidates found - returning sample data.")
            return _SAMPLE_COMPUTE_RIGHTSIZING

        return sorted(recommendations, key=lambda x: x["annual_savings"], reverse=True)

    except Exception as exc:
        logger.error("Failed to fetch compute rightsizing data: %s", exc)
        return _SAMPLE_COMPUTE_RIGHTSIZING
    
def get_subscription_info(config) -> dict:
    """
    Fetches the Azure subscription display name, ID, state, and tenant ID.
    Falls back to sample data when credentials are missing or the call fails.
    """
    if not config.has_azure_config():
        logger.info("No Azure config present - returning sample subscription info.")
        return _SAMPLE_SUBSCRIPTION
 
    try:
        from azure.mgmt.subscription import SubscriptionClient
 
        credential = get_credential(config)
        client = SubscriptionClient(credential)
        sub = client.subscriptions.get(config.azure_subscription_id)
 
        return {
            "subscription_id": sub.subscription_id or config.azure_subscription_id,
            "display_name": sub.display_name or "Unnamed Subscription",
            "state": str(sub.state) if sub.state else "Unknown",
            "tenant_id": sub.tenant_id or config.azure_tenant_id,
            "sample_data": False,
        }
    except Exception as exc:
        logger.error("Failed to fetch subscription info: %s", exc)
        return {
            "subscription_id": config.azure_subscription_id or "unknown",
            "display_name": "Unable to fetch subscription name",
            "state": "Unknown",
            "tenant_id": config.azure_tenant_id or "unknown",
            "sample_data": False,
            "error": str(exc),
        }