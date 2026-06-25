from datetime import datetime, timedelta
from typing import Any

from client import apigee_get
from tools.proxies import get_proxy_details
from tools.environments import get_analytics
from tools.debug import list_debug_sessions, create_debug_session, get_debug_transactions


async def get_proxy_errors(
    proxy_name: str, environment: str, revision: str | None = None
) -> dict[str, Any]:
    """
    Compound tool: resolves the proxy revision, reuses or creates a debug session,
    fetches all captured transactions, and returns only the errored ones.
    """
    details = await get_proxy_details(proxy_name, revision)
    resolved_revision = details["selected_revision"]

    session_id: str | None = None
    session_created = False

    try:
        sessions = await list_debug_sessions(environment, proxy_name, resolved_revision)
        if sessions:
            session_id = sessions[-1]
    except RuntimeError:
        sessions = []

    if not session_id:
        new_session = await create_debug_session(environment, proxy_name, resolved_revision)
        session_id = new_session["session_id"]
        session_created = True

    transactions = await get_debug_transactions(environment, proxy_name, resolved_revision, session_id)
    errors = [t for t in transactions if t.get("is_error")]

    return {
        "proxy": proxy_name,
        "environment": environment,
        "revision": resolved_revision,
        "session_id": session_id,
        "session_created": session_created,
        "total_transactions_captured": len(transactions),
        "error_count": len(errors),
        "errors": errors,
        "note": (
            "Debug session just created — send requests through the proxy to capture transactions, "
            "then call this tool again to see errors."
            if session_created
            else f"Reused existing session '{session_id}'. "
                 f"{len(transactions)} transaction(s) captured, {len(errors)} error(s) found."
        ),
    }


async def get_proxy_error_rate(
    proxy_name: str, environment: str, time_range: str | None = None
) -> dict[str, Any]:
    """
    Analytics-based error rate for a single proxy in an environment.
    Returns total calls, error count, error rate %, and average latency.
    """
    data = await get_analytics(environment, proxy=proxy_name, time_range=time_range)
    return {
        "proxy": proxy_name,
        "environment": environment,
        "time_range": data.get("time_range"),
        "total_calls": data.get("total_calls"),
        "error_count": data.get("error_count"),
        "error_rate_pct": data.get("error_rate_pct"),
        "avg_latency_ms": data.get("avg_latency_ms"),
    }


async def get_top_erroring_proxies(
    environment: str, time_range: str | None = None, top_n: int = 10
) -> list[dict[str, Any]]:
    """
    Analytics-based ranking of proxies by error count in an environment.
    Returns the top_n proxies with the highest error counts, sorted descending.
    """
    if time_range is None:
        now = datetime.utcnow()
        fmt = "%m/%d/%Y %H:%M"
        time_range = f"{(now - timedelta(hours=1)).strftime(fmt)}~{now.strftime(fmt)}"

    metrics = ["sum(message_count)", "avg(total_response_time)", "sum(is_error)"]
    data = await apigee_get(
        f"/environments/{environment}/stats/apiproxy",
        params={"select": ",".join(metrics), "timeRange": time_range},
    )

    stats_data: list = data.get("Response", {}).get("stats", {}).get("data", [])
    results = []

    for row in stats_data:
        identifier = row.get("identifier", {})
        values = identifier.get("values", []) if isinstance(identifier, dict) else []
        proxy_name = values[0] if values else ""
        if not proxy_name:
            continue

        aggregates: dict[str, float] = {}
        for metric_item in row.get("metric", []):
            name: str = metric_item.get("name", "")
            nums = []
            for v in metric_item.get("values", []):
                try:
                    nums.append(float(v) if not isinstance(v, dict) else 0.0)
                except (ValueError, TypeError):
                    pass
            if nums:
                aggregates[name] = (
                    sum(nums) / len(nums) if name.startswith("avg") else sum(nums)
                )

        total_calls = int(aggregates.get("sum(message_count)", 0))
        error_count = int(aggregates.get("sum(is_error)", 0))
        results.append({
            "proxy": proxy_name,
            "total_calls": total_calls,
            "error_count": error_count,
            "error_rate_pct": round((error_count / total_calls * 100) if total_calls else 0.0, 2),
            "avg_latency_ms": round(aggregates.get("avg(total_response_time)", 0.0), 2),
        })

    results.sort(key=lambda x: x["error_count"], reverse=True)
    return results[:top_n]
