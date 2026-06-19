from datetime import datetime, timedelta
from typing import Any

from client import apigee_get


async def list_environments() -> list[str]:
    """Return the list of environment names in the Apigee org."""
    data = await apigee_get("/environments")
    # API returns either a list of strings or {"environments": [...]}
    if isinstance(data, list):
        return data
    return data.get("environments", [])


async def get_analytics(
    environment: str,
    proxy: str | None = None,
    time_range: str | None = None,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """
    Fetch traffic analytics for an environment, optionally filtered to a single proxy.

    Returns a human-readable summary: total calls, average latency, error count,
    and error rate — parsed out of the raw Apigee stats response.
    """
    if metrics is None:
        metrics = ["sum(message_count)", "avg(total_response_time)", "sum(is_error)"]

    if time_range is None:
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        fmt = "%m/%d/%Y %H:%M"
        time_range = f"{one_hour_ago.strftime(fmt)}~{now.strftime(fmt)}"

    params: dict[str, Any] = {
        "select": ",".join(metrics),
        "timeRange": time_range,
    }
    if proxy:
        params["filter"] = f"(apiproxy eq '{proxy}')"

    data = await apigee_get(f"/environments/{environment}/stats/apiproxy", params=params)
    return _parse_analytics(data, environment, proxy, time_range, metrics)


def _parse_analytics(
    raw: dict,
    environment: str,
    proxy: str | None,
    time_range: str,
    metrics: list[str],
) -> dict[str, Any]:
    """
    Flatten the deeply nested Apigee stats envelope into a readable dict.

    Apigee wraps results as:
      { "Response": { "stats": { "data": [ { "metric": [...] } ] } } }
    Each metric item has a name and a list of values across time buckets.
    We sum/average across buckets to produce single aggregate numbers.
    """
    result: dict[str, Any] = {
        "environment": environment,
        "time_range": time_range,
        "filter_proxy": proxy,
    }

    try:
        stats_data: list = (
            raw.get("Response", {})
            .get("stats", {})
            .get("data", [])
        )
    except AttributeError:
        result["raw"] = raw
        return result

    # Collect aggregate values keyed by metric name
    aggregates: dict[str, float] = {}
    for row in stats_data:
        for metric_item in row.get("metric", []):
            name: str = metric_item.get("name", "")
            values: list = metric_item.get("values", [])
            # values are strings like "1234.0" or dicts — coerce to float, skip None/"null"
            nums = []
            for v in values:
                try:
                    nums.append(float(v) if not isinstance(v, dict) else 0.0)
                except (ValueError, TypeError):
                    pass
            if nums:
                aggregates[name] = sum(nums) if not name.startswith("avg") else (sum(nums) / len(nums))

    total_calls = int(aggregates.get("sum(message_count)", 0))
    avg_latency_ms = round(aggregates.get("avg(total_response_time)", 0.0), 2)
    error_count = int(aggregates.get("sum(is_error)", 0))
    error_rate_pct = round((error_count / total_calls * 100) if total_calls > 0 else 0.0, 2)

    result.update(
        {
            "total_calls": total_calls,
            "avg_latency_ms": avg_latency_ms,
            "error_count": error_count,
            "error_rate_pct": error_rate_pct,
            "metrics_requested": metrics,
            "raw_aggregates": aggregates,
        }
    )
    return result
