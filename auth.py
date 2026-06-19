import os
import asyncio
from functools import lru_cache

import google.auth
import google.auth.transport.requests
from google.oauth2 import credentials as oauth2_credentials

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# Module-level cache for ADC credentials so we reuse the same object across calls
_adc_credentials: google.auth.credentials.Credentials | None = None


async def get_access_token() -> str:
    """
    Return a valid Bearer token for Apigee API calls.

    Priority:
    1. APIGEE_ACCESS_TOKEN env var — returned as-is (useful for quick testing).
    2. Application Default Credentials (ADC) — refreshed automatically when expired.
    """
    raw_token = os.environ.get("APIGEE_ACCESS_TOKEN", "").strip()
    if raw_token:
        return raw_token

    return await asyncio.to_thread(_get_adc_token)


def _get_adc_token() -> str:
    global _adc_credentials

    if _adc_credentials is None:
        _adc_credentials, _ = google.auth.default(scopes=_SCOPES)

    if not _adc_credentials.valid:
        request = google.auth.transport.requests.Request()
        _adc_credentials.refresh(request)

    return _adc_credentials.token
