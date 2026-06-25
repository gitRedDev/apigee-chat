from typing import Any

from client import apigee_get, apigee_post


async def list_caches(environment: str) -> list[dict[str, Any]]:
    data = await apigee_get(f"/environments/{environment}/caches")
    caches = data if isinstance(data, list) else data.get("cache", [])
    result = []
    for c in caches:
        name = c.get("name", c) if isinstance(c, dict) else c
        result.append({
            "name": name,
            "description": c.get("description", "") if isinstance(c, dict) else "",
            "expiry_settings": c.get("expirySettings", {}) if isinstance(c, dict) else {},
        })
    return result


async def clear_cache(environment: str, cache_name: str) -> dict[str, Any]:
    await apigee_post(
        f"/environments/{environment}/caches/{cache_name}/entries",
        params={"action": "clear"},
    )
    return {"action": "cleared", "environment": environment, "cache": cache_name}
