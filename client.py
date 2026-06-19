import os
from typing import Any

import httpx

from auth import get_access_token

_BASE_URL = "https://apigee.googleapis.com/v1"


def _org() -> str:
    org = os.environ.get("APIGEE_ORG", "").strip()
    if not org:
        raise RuntimeError("APIGEE_ORG environment variable is not set")
    return org


async def apigee_get(path: str, params: dict[str, Any] | None = None) -> dict | list:
    """
    Perform an authenticated GET against the Apigee Management API.

    `path` should start with '/' and is relative to /organizations/{org}.
    Raises RuntimeError with status code + body on 4xx/5xx.
    """
    token = await get_access_token()
    org = _org()
    url = f"{_BASE_URL}/organizations/{org}{path}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params or {})

    if response.is_error:
        raise RuntimeError(
            f"Apigee API error {response.status_code} for {url}: {response.text}"
        )

    return response.json()
