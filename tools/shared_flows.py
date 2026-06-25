from typing import Any

from client import apigee_get


async def list_shared_flows() -> list[dict[str, Any]]:
    data = await apigee_get("/sharedflows")
    flows = data if isinstance(data, list) else data.get("sharedFlows", [])
    result = []
    for flow in flows:
        name = flow.get("name", flow) if isinstance(flow, dict) else flow
        revisions: list[str] = flow.get("revision", []) if isinstance(flow, dict) else []
        latest = str(max(int(r) for r in revisions)) if revisions else "unknown"
        result.append({"name": name, "latest_revision": latest})
    return result


async def get_shared_flow_details(name: str, revision: str | None = None) -> dict[str, Any]:
    meta = await apigee_get(f"/sharedflows/{name}")
    all_revisions = sorted(meta.get("revision", []), key=lambda r: int(r))
    if revision is None:
        revision = all_revisions[-1] if all_revisions else "1"
    rev_meta = await apigee_get(f"/sharedflows/{name}/revisions/{revision}")
    dep_data = await apigee_get(f"/sharedflows/{name}/revisions/{revision}/deployments")
    dep_envs = [d.get("environment", "") for d in dep_data.get("deployments", [])]
    return {
        "name": name,
        "all_revisions": all_revisions,
        "latest_revision": all_revisions[-1] if all_revisions else revision,
        "selected_revision": revision,
        "deployed_environments": dep_envs,
        "created_at": rev_meta.get("createdAt", ""),
        "last_modified_at": rev_meta.get("lastModifiedAt", ""),
        "description": rev_meta.get("description", ""),
    }
