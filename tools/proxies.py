from typing import Any

from client import apigee_get


async def list_proxies() -> list[dict[str, Any]]:
    """Return all API proxies in the org, each with its latest revision number."""
    data = await apigee_get("/apis")
    proxies = data if isinstance(data, list) else data.get("proxies", [])
    result = []
    for proxy in proxies:
        name = proxy.get("name", proxy) if isinstance(proxy, dict) else proxy
        revisions: list[str] = proxy.get("revision", []) if isinstance(proxy, dict) else []
        latest = str(max(int(r) for r in revisions)) if revisions else "unknown"
        result.append({"name": name, "latest_revision": latest})
    return result


async def get_deployed_proxies(environment: str) -> list[dict[str, Any]]:
    """
    Return all proxies currently deployed in the given environment,
    with their revision and deployment state.
    """
    data = await apigee_get(f"/environments/{environment}/deployments")
    deployments = data.get("deployments", [])
    result = []
    for dep in deployments:
        result.append(
            {
                "proxy": dep.get("apiProxy", ""),
                "revision": dep.get("revision", ""),
                "state": dep.get("state", ""),
                "environment": dep.get("environment", environment),
            }
        )
    return result


async def get_proxy_details(
    proxy_name: str, revision: str | None = None
) -> dict[str, Any]:
    """
    Return full details for a proxy: all revisions, latest revision, deployed
    environments, and creation/modification timestamps.

    If `revision` is omitted the latest revision is selected automatically.
    """
    proxy_meta = await apigee_get(f"/apis/{proxy_name}")
    all_revisions: list[str] = proxy_meta.get("revision", [])
    sorted_revisions = sorted(all_revisions, key=lambda r: int(r))

    if revision is None:
        revision = sorted_revisions[-1] if sorted_revisions else "1"

    rev_meta = await apigee_get(f"/apis/{proxy_name}/revisions/{revision}")
    dep_data = await apigee_get(f"/apis/{proxy_name}/revisions/{revision}/deployments")
    dep_envs = [d.get("environment", "") for d in dep_data.get("deployments", [])]

    return {
        "name": proxy_name,
        "all_revisions": sorted_revisions,
        "latest_revision": sorted_revisions[-1] if sorted_revisions else revision,
        "selected_revision": revision,
        "deployed_environments": dep_envs,
        "created_at": rev_meta.get("createdAt", ""),
        "last_modified_at": rev_meta.get("lastModifiedAt", ""),
        "description": rev_meta.get("description", ""),
        "type": rev_meta.get("type", ""),
    }
