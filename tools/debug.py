from typing import Any

from client import apigee_get, apigee_post


async def list_debug_sessions(environment: str, proxy_name: str, revision: str) -> list[str]:
    data = await apigee_get(
        f"/environments/{environment}/apis/{proxy_name}/revisions/{revision}/debugsessions"
    )
    sessions = data.get("sessions", data) if isinstance(data, dict) else data
    if not isinstance(sessions, list):
        return []
    return [s.get("id", s) if isinstance(s, dict) else s for s in sessions]


async def create_debug_session(
    environment: str,
    proxy_name: str,
    revision: str,
    timeout_seconds: int = 300,
    count: int = 20,
) -> dict[str, Any]:
    result = await apigee_post(
        f"/environments/{environment}/apis/{proxy_name}/revisions/{revision}/debugsessions",
        body={"count": count, "timeout": timeout_seconds},
    )
    return {
        "session_id": result.get("id", result.get("name", "")),
        "proxy": proxy_name,
        "revision": revision,
        "environment": environment,
        "timeout_seconds": timeout_seconds,
        "max_transactions": count,
        "note": "Session active — transactions are captured as live traffic flows through the proxy.",
    }


async def get_debug_transactions(
    environment: str, proxy_name: str, revision: str, session_id: str
) -> list[dict[str, Any]]:
    data = await apigee_get(
        f"/environments/{environment}/apis/{proxy_name}/revisions/{revision}/debugsessions/{session_id}/data"
    )
    transaction_ids = data if isinstance(data, list) else data.get("transactions", [])
    results = []
    for txn in transaction_ids[:50]:
        txn_id = txn.get("id", txn) if isinstance(txn, dict) else txn
        try:
            txn_data = await apigee_get(
                f"/environments/{environment}/apis/{proxy_name}/revisions/{revision}"
                f"/debugsessions/{session_id}/data/{txn_id}"
            )
            results.append(_summarize_transaction(txn_id, txn_data))
        except RuntimeError:
            results.append({"id": txn_id, "error": "could not fetch transaction"})
    return results


def _extract_variables(data: dict) -> dict[str, str]:
    """Recursively collect all {name, value} pairs from Apigee debug transaction data."""
    variables: dict[str, str] = {}

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "name" in obj and "value" in obj and isinstance(obj["name"], str):
                variables[obj["name"]] = str(obj.get("value", ""))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return variables


def _summarize_transaction(txn_id: str, data: dict) -> dict[str, Any]:
    variables = _extract_variables(data)
    status_code = variables.get("response.status.code", variables.get("status.code", ""))
    fault_name = variables.get("fault.name", "")
    is_error = bool(fault_name) or (status_code[:1] in ("4", "5") if status_code else False)
    return {
        "id": txn_id,
        "completed": data.get("completed", False),
        "is_error": is_error,
        "status_code": status_code,
        "request_uri": variables.get("request.uri", variables.get("request.path", "")),
        "fault_name": fault_name,
        "fault_type": variables.get("fault.type", ""),
        "error_message": variables.get("fault.string", variables.get("error.message", "")),
    }
