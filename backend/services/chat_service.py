"""Chat service - Claude conversational agent with tool use."""

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
- If a tool returns a data_status of "auth_error" or "rate_limited", explain the issue plainly and suggest what to fix.
- Use markdown formatting (bold, bullet points) sparingly and only where it genuinely aids readability.
- Do not call the same tool more than once per turn unless the user's question genuinely needs different parameters.
"""

CHAT_TOOLS = [
    {
        "name": "get_azure_cost_summary",
        "description": "Get Azure cost summary for a given period. Use for Azure spend, top services, cost trends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "minimum": 1, "maximum": 365, "description": "Days to look back (default 30)."}
            },
            "required": [],
        },
    },
    {
        "name": "get_azure_advisor_recommendations",
        "description": "Get Azure Advisor recommendations across all categories. Use for savings opportunities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["Cost", "Security", "HighAvailability", "Performance", "OperationalExcellence"]}
            },
            "required": [],
        },
    },
    {
        "name": "get_azure_compute_rightsizing",
        "description": "Get VM right-sizing recommendations with projected monthly savings.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_m365_license_summary",
        "description": "Get M365 license summary (per-SKU, unused, inactive users, recommendations).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_azure_subscription_info",
        "description": "Get the display name, ID, and state of the configured Azure subscription.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def _make_client(api_key: str):
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "The 'anthropic' package is not installed. Run `pip install anthropic`."
        ) from exc

    try:
        return anthropic.Anthropic(api_key=api_key)
    except TypeError as exc:
        if "proxies" in str(exc):
            raise RuntimeError(
                "Incompatible anthropic/httpx versions. Run `pip install --upgrade anthropic`."
            ) from exc
        raise


def _truncate(data: Any, max_chars: int = 12000) -> str:
    text = json.dumps(data, default=str, indent=2)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated for length]"


def _run_tool(config, name: str, tool_input: dict) -> str:
    try:
        if name == "get_azure_cost_summary":
            days = tool_input.get("days", 30)
            data = azure_service.get_cost_summary(config, days=days)
            if "daily_trend" in data and len(data["daily_trend"]) > 14:
                data = dict(data)
                data["daily_trend"] = data["daily_trend"][-14:]
            return _truncate(data)

        if name == "get_azure_advisor_recommendations":
            category = tool_input.get("category")
            recs = azure_service.get_advisor_recommendations(config)
            if category:
                recs = [r for r in recs if r.get("category") == category]
            slim = [
                {
                    "name": r.get("name"),
                    "category": r.get("category"),
                    "impact": r.get("impact"),
                    "resource": r.get("impacted_value"),
                    "resource_group": r.get("resource_group"),
                    "description": (r.get("short_description") or {}).get("problem")
                        if isinstance(r.get("short_description"), dict)
                        else r.get("description") or r.get("short_description"),
                    "solution": (r.get("short_description") or {}).get("solution")
                        if isinstance(r.get("short_description"), dict)
                        else None,
                    "potential_annual_savings": r.get("potential_annual_savings", 0),
                    "sample_data": r.get("sample_data", False),
                }
                for r in recs
            ]
            return _truncate({"count": len(slim), "recommendations": slim})

        if name == "get_azure_compute_rightsizing":
            data = azure_service.get_compute_rightsizing(config)
            return _truncate({"count": len(data), "recommendations": data})

        if name == "get_m365_license_summary":
            return _truncate(m365_service.get_license_summary(config))

        if name == "get_azure_subscription_info":
            return _truncate(azure_service.get_subscription_info(config))

        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc)
        return json.dumps({"error": f"Tool {name} failed: {exc}"})


def chat(config, user_message: str, history: list[dict]) -> dict:
    if not config.has_anthropic_config():
        return {
            "reply": (
                "I need an Anthropic API key to chat. Please add one in Settings under "
                "*AI Analysis (Anthropic Claude)*, then try again."
            ),
            "tools_used": [],
            "error": "no_anthropic_key",
        }

    try:
        client = _make_client(config.anthropic_api_key)
    except RuntimeError as exc:
        logger.error("Failed to init Anthropic client: %s", exc)
        return {"reply": f"Sorry, I can't start the chat: {exc}", "tools_used": [], "error": "client_init_failed"}

    messages: list[dict] = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    tools_used: list[str] = []
    MAX_ITERATIONS = 5

    try:
        for _ in range(MAX_ITERATIONS):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=_CHAT_SYSTEM_PROMPT,
                tools=CHAT_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
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
                continue

            reply_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            reply_text = "\n".join(reply_parts).strip() or "(no response)"
            return {"reply": reply_text, "tools_used": tools_used, "error": None}

        return {
            "reply": "I got stuck in a tool-use loop. Please rephrase your question.",
            "tools_used": tools_used,
            "error": "max_iterations",
        }
    except Exception as exc:
        logger.error("Chat call failed: %s", exc)
        return {"reply": f"Sorry, I hit an error talking to Claude: {exc}", "tools_used": tools_used, "error": str(exc)}