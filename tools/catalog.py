from datetime import datetime
from typing import Any

from client import apigee_get


def _ms_to_iso(ms_str: str | int | None) -> str:
    """Convert an Apigee epoch-milliseconds timestamp to an ISO 8601 string."""
    if ms_str is None:
        return ""
    try:
        return datetime.utcfromtimestamp(int(ms_str) / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return str(ms_str)


async def list_api_products() -> list[dict[str, Any]]:
    """Return all API products with name, display name, environments, quota, and proxies."""
    data = await apigee_get("/apiproducts", params={"expand": "true"})
    products = data.get("apiProduct", [])
    result = []
    for p in products:
        quota = None
        if p.get("quota"):
            quota = f"{p['quota']} per {p.get('quotaInterval', '?')} {p.get('quotaTimeUnit', '')}"
        result.append(
            {
                "name": p.get("name", ""),
                "display_name": p.get("displayName", ""),
                "environments": p.get("environments", []),
                "proxies": p.get("proxies", []),
                "quota": quota,
                "approval_type": p.get("approvalType", ""),
            }
        )
    return result


async def list_developers(count: int = 100) -> list[dict[str, Any]]:
    """Return registered developers with email, name, status, and creation date."""
    data = await apigee_get("/developers", params={"count": count})
    developers = data.get("developer", [])
    result = []
    for dev in developers:
        result.append(
            {
                "email": dev.get("email", ""),
                "first_name": dev.get("firstName", ""),
                "last_name": dev.get("lastName", ""),
                "status": dev.get("status", ""),
                "created_at": _ms_to_iso(dev.get("createdAt")),
            }
        )
    return result


async def list_apps(
    developer_email: str | None = None,
    count: int = 100,
) -> list[dict[str, Any]]:
    """
    Return developer apps with name, status, credentialed products, and creation date.

    If `developer_email` is given, only that developer's apps are returned.
    Otherwise all apps in the org are returned (up to `count`).
    """
    if developer_email:
        data = await apigee_get(
            f"/developers/{developer_email}/apps", params={"expand": "true"}
        )
        apps = data.get("app", [])
    else:
        data = await apigee_get("/apps", params={"expand": "true", "count": count})
        apps = data.get("app", [])

    result = []
    for app in apps:
        # Collect all API products across all credentials
        products: list[str] = []
        for cred in app.get("credentials", []):
            for ap in cred.get("apiProducts", []):
                pname = ap.get("apiproduct", "") if isinstance(ap, dict) else str(ap)
                if pname and pname not in products:
                    products.append(pname)

        result.append(
            {
                "name": app.get("name", ""),
                "developer_email": app.get("developerId", developer_email or ""),
                "status": app.get("status", ""),
                "api_products": products,
                "created_at": _ms_to_iso(app.get("createdAt")),
            }
        )
    return result
