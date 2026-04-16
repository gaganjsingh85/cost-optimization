"""
Chat service for the Azure Cost Optimizer.

Powers the floating "Chat with Me" agent. Uses Claude with tool use so the
model can fetch live Azure/M365 data on demand rather than preloading
everything into every turn.
"""

import json
import logging
from typing import Any

from services import azure_service, m365_service

logger = logging.getLogger(__name__)


_CHAT_SYSTEM_PROMPT = """You are a FinOps (Cloud Financial Operations) assistant embedded in an Azure Cost Optimizer dashboard. You help users understand their Azure and Microsoft 365 cloud spend and identify savings opportunities.

You have access to tools that fetch LIVE data from the user's Azure subscription and Microsoft 365 tenant. Use these tools when, and ONLY when, the user asks a question that requires their actual data (e.g. "what's my top cost service", "how many unused licenses do I have", "what would I save by right-sizing"). For general FinOps knowledge questions (e.g. "what are reserved instances"), answer directly without calling tools.

Guidelines:
- Be concise. Short, direct answers work best in a chat panel.
- Quantify savings in USD with both monthly and annual figures when relevant.
- When you use tool data, cite specific resource names, SKUs, or counts.
- If a tool returns sample data (marked with "sample_data": true), tell the user the numbers are from demo data and that they should configure real credentials in Settings for accurate figures.
- If the user asks about a recommendation, explain the business rationale, the risk, and a validation step before acting.
- Use markdown formatting (bold, bullet points) sparingly and only where it genuinely aids readability.
- Do not call the same tool more than once per turn unless the user's question genuinely needs different parameters.
"""


# ---------------------------------------------------------------------------
# Tool definitions exposed to Claude
# ---------------------------------------------------------------------------

CHAT_TOOLS = [
    {
        "name": "get_azure_cost_summary",
        "description": (
            "Get the user's Azure cost summary for a given time window. Returns "
            "total cost, cost broken down by service, resource group, and location, "
            "plus a daily cost trend. Use this when the user asks about Azure spend, "
            "top services, or cost trends."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (1-365). Default 30.",
                    "minimum": 1,
                    "maximum": 365,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_azure_advisor_recommendations",
        "description": (
            "Get Azure Advisor recommendations across Cost, Security, High "
            "Availability, Performance, and Operational Excellence categories. "
            "Use this when the user asks what Azure could save, what Advisor "
            "suggests, or about specific optimization opportunities."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "Cost",
                        "Security",
                        "HighAvailability",
                        "Performance",
                        "OperationalExcellence",
                    ],
                    "description": "Optional category filter.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_azure_compute_rightsizing",
        "description": (
            "Get VM right-sizing recommendations with current size, recommended "
            "size, and projected monthly savings. Use this when the user asks "
            "about specific VMs, right-sizing, or underutilized compute."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_m365_license_summary",
        "description": (
            "Get the user's Microsoft 365 license summary including total monthly "
            "spend, per-SKU usage (consumed vs enabled), unused licenses with "
            "estimated cost, inactive-user count, and prioritized recommendations. "
            "Use this for any M365 licensing, user activity, or savings question."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_azure_subscription_info",
        "description": (
            "Get the display name, ID, and state of the currently configured Azure "
            "subscription. Use when the user asks which subscription they're "
            "looking at."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def _truncate_for_model(data: Any, max_chars: int = 12000) -> str:
    """JSON-dump a tool result and truncate if it's too large for the context."""
    text = json.dumps(data, default=str, indent=2)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated for length]"


def _run_tool(config, tool_name: str, tool_input: dict) -> str:
    """Dispatches a tool call to the appropriate service function."""
    try:
        if tool_name == "get_azure_cost_summary":
            days = tool_input.get("days", 30)
            data = azure_service.get_cost_summary(config, days=days)
            # Trim daily_trend to keep the payload small
            if "daily_trend" in data and len(data["daily_trend"]) > 14:
                data = dict(data)
                data["daily_trend"] = data["daily_trend"][-14:]
            return _truncate_for_model(data)

        if tool_name == "get_azure_advisor_recommendations":
            category = tool_input.get("category")
            recs = azure_service.get_advisor_recommendations(config)
            if category:
                recs = [r for r in recs if r.get("category") == category]
            # Slim each recommendation down
            slim = [
                {
                    "name": r.get("name"),
                    "category": r.get("category"),
                    "impact": r.get("impact"),
                    "resource": r.get("impacted_value"),
                    "resource_group": r.get("resource_group"),
                    "description": r.get("short_description"),
                    "potential_annual_savings": r.get("potential_annual_savings", 0),
                    "sample_data": r.get("sample_data", False),
                }
                for r in recs
            ]
            return _truncate_for_model({
                "count": len(slim),
                "recommendations": slim,
            })

        if tool_name == "get_azure_compute_rightsizing":
            data = azure_service.get_compute_rightsizing(config)
            return _truncate_for_model({
                "count": len(data),
                "recommendations": data,
            })

        if tool_name == "get_m365_license_summary":
            data = m365_service.get_license_summary(config)
            return _truncate_for_model(data)

        if tool_name == "get_azure_subscription_info":
            data = azure_service.get_subscription_info(config)
            return _truncate_for_model(data)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as exc:
        logger.error("Tool %s failed: %s", tool_name, exc)
        return json.dumps({"error": f"Tool {tool_name} failed: {exc}"})


# ---------------------------------------------------------------------------
# Public chat entry point
# ---------------------------------------------------------------------------

def chat(config, user_message: str, history: list[dict]) -> dict:
    """
    Runs one conversational turn.

    Args:
        config: loaded Config instance
        user_message: the new message from the user
        history: prior conversation as a list of {"role": "user"|"assistant", "content": str}

    Returns:
        {
            "reply": str,               # final assistant text
            "tools_used": list[str],    # names of tools Claude invoked this turn
            "error": str | None,
        }
    """
    if not config.has_anthropic_config():
        return {
            "reply": (
                "I need an Anthropic API key to chat. Please add one in Settings "
                "under *AI Analysis (Anthropic Claude)*, then try again."
            ),
            "tools_used": [],
            "error": "no_anthropic_key",
        }

    try:
        import anthropic
    except ImportError:
        return {
            "reply": "The anthropic SDK is not installed on the server.",
            "tools_used": [],
            "error": "missing_sdk",
        }

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    # Build the message list for the API call
    messages: list[dict] = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    tools_used: list[str] = []
    max_iterations = 5  # Safety cap on tool-use loop

    try:
        for _ in range(max_iterations):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=_CHAT_SYSTEM_PROMPT,
                tools=CHAT_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                # Append the assistant message (including tool_use blocks) verbatim
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tools_used.append(block.name)
                        result_text = _run_tool(config, block.name, block.input or {})
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        })

                messages.append({"role": "user", "content": tool_results})
                continue  # loop again so Claude can respond to tool results

            # Regular end_turn or stop - collect text
            reply_parts = [
                block.text for block in response.content
                if getattr(block, "type", None) == "text"
            ]
            reply_text = "\n".join(reply_parts).strip() or "(no response)"
            return {
                "reply": reply_text,
                "tools_used": tools_used,
                "error": None,
            }

        return {
            "reply": (
                "I got stuck in a tool-use loop. Please try rephrasing your question."
            ),
            "tools_used": tools_used,
            "error": "max_iterations",
        }

    except Exception as exc:
        logger.error("Chat call failed: %s", exc)
        return {
            "reply": f"Sorry, I hit an error talking to Claude: {exc}",
            "tools_used": tools_used,
            "error": str(exc),
        }