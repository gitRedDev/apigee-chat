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


async def _request(method: str, path: str, body: dict | None = None, params: dict[str, Any] | None = None) -> dict | list:
    token = await get_access_token()
    org = _org()
    url = f"{_BASE_URL}/organizations/{org}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await getattr(client, method)(url, headers=headers, json=body, params=params or {})
    if response.is_error:
        raise RuntimeError(f"Apigee API error {response.status_code} for {url}: {response.text}")
    if not response.content:
        return {}
    return response.json()


async def apigee_post(path: str, body: dict | None = None, params: dict[str, Any] | None = None) -> dict | list:
    return await _request("post", path, body=body or {}, params=params)


async def apigee_put(path: str, body: dict | None = None) -> dict | list:
    return await _request("put", path, body=body or {})


async def apigee_delete(path: str) -> dict | list:
    token = await get_access_token()
    org = _org()
    url = f"{_BASE_URL}/organizations/{org}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(url, headers=headers)
    if response.is_error:
        raise RuntimeError(f"Apigee API error {response.status_code} for {url}: {response.text}")
    if not response.content:
        return {}
    return response.json()


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
