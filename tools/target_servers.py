from typing import Any

from client import apigee_get, apigee_post, apigee_put, apigee_delete


async def list_target_servers(environment: str) -> list[str]:
    data = await apigee_get(f"/environments/{environment}/targetservers")
    return data if isinstance(data, list) else []


async def get_target_server(environment: str, name: str) -> dict[str, Any]:
    data = await apigee_get(f"/environments/{environment}/targetservers/{name}")
    ssl_info = data.get("sSLInfo", {}) or {}
    return {
        "name": data.get("name", ""),
        "host": data.get("host", ""),
        "port": data.get("port", 0),
        "enabled": data.get("isEnabled", True),
        "ssl_enabled": ssl_info.get("enabled", False),
        "protocol": data.get("protocol", "HTTP"),
    }


async def upsert_target_server(
    environment: str, name: str, host: str, port: int, ssl_enabled: bool = False
) -> dict[str, Any]:
    body = {
        "name": name,
        "host": host,
        "port": port,
        "isEnabled": True,
        "sSLInfo": {"enabled": ssl_enabled},
    }
    try:
        await apigee_get(f"/environments/{environment}/targetservers/{name}")
        await apigee_put(f"/environments/{environment}/targetservers/{name}", body=body)
        return {"action": "updated", "name": name, "host": host, "port": port}
    except RuntimeError as exc:
        if "404" not in str(exc) and "NOT_FOUND" not in str(exc):
            raise
        await apigee_post(f"/environments/{environment}/targetservers", body=body)
        return {"action": "created", "name": name, "host": host, "port": port}


async def delete_target_server(environment: str, name: str) -> dict[str, Any]:
    await apigee_delete(f"/environments/{environment}/targetservers/{name}")
    return {"action": "deleted", "environment": environment, "name": name}
