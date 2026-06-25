from typing import Any

from client import apigee_get, apigee_post, apigee_put, apigee_delete


async def list_kvms(environment: str) -> list[str]:
    data = await apigee_get(f"/environments/{environment}/keyvaluemaps")
    return data if isinstance(data, list) else data.get("keyValueMap", [])


async def get_kvm_entries(environment: str, kvm_name: str) -> list[dict[str, Any]]:
    data = await apigee_get(
        f"/environments/{environment}/keyvaluemaps/{kvm_name}/entries",
        params={"count": 200},
    )
    entries = data.get("keyValueEntry", []) if isinstance(data, dict) else data
    return [{"key": e.get("name", ""), "value": e.get("value", "")} for e in entries]


async def upsert_kvm_entry(
    environment: str, kvm_name: str, key: str, value: str
) -> dict[str, Any]:
    body = {"name": key, "value": value}
    try:
        await apigee_get(f"/environments/{environment}/keyvaluemaps/{kvm_name}/entries/{key}")
        await apigee_put(f"/environments/{environment}/keyvaluemaps/{kvm_name}/entries/{key}", body=body)
        return {"action": "updated", "kvm": kvm_name, "key": key}
    except RuntimeError as exc:
        if "404" not in str(exc) and "NOT_FOUND" not in str(exc):
            raise
        await apigee_post(f"/environments/{environment}/keyvaluemaps/{kvm_name}/entries", body=body)
        return {"action": "created", "kvm": kvm_name, "key": key}


async def delete_kvm_entry(environment: str, kvm_name: str, key: str) -> dict[str, Any]:
    await apigee_delete(f"/environments/{environment}/keyvaluemaps/{kvm_name}/entries/{key}")
    return {"action": "deleted", "kvm": kvm_name, "key": key}
