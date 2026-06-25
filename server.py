"""
Apigee MCP Server — exposes Apigee Management API operations as MCP tools.

Run with:  python server.py
"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import tools as apigee_tools

load_dotenv()

# ── startup validation ──────────────────────────────────────────────────────────
if not os.environ.get("APIGEE_ORG", "").strip():
    print(
        "ERROR: APIGEE_ORG environment variable is not set.\n"
        "Set it to your GCP project ID (which is also your Apigee org name).\n"
        "Example:  APIGEE_ORG=my-gcp-project  python server.py",
        file=sys.stderr,
    )
    sys.exit(1)

app = Server("apigee-mcp")


# ── tool registry ───────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ── environments ──────────────────────────────────────────────────────
        Tool(
            name="list_environments",
            description=(
                "List all environments defined in the Apigee organization "
                "(e.g. 'dev', 'staging', 'prod'). Use this to discover which "
                "environments exist before querying environment-specific data."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_analytics",
            description=(
                "Retrieve traffic analytics for a specific Apigee environment. "
                "Returns total API calls, average latency (ms), error count, and "
                "error rate for the requested time window. Optionally filter results "
                "to a single proxy and/or supply custom metrics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment (e.g. 'prod')."},
                    "proxy": {"type": "string", "description": "Filter analytics to this proxy name. Optional."},
                    "time_range": {
                        "type": "string",
                        "description": "Time window: 'MM/DD/YYYY HH:MM~MM/DD/YYYY HH:MM'. Defaults to last hour.",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Apigee metric expressions. Defaults to message_count, total_response_time, is_error.",
                    },
                },
                "required": ["environment"],
            },
        ),
        # ── proxies ───────────────────────────────────────────────────────────
        Tool(
            name="list_proxies",
            description="List all API proxies in the org with their latest revision number.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_deployed_proxies",
            description=(
                "Show which API proxies are currently deployed in a specific environment, "
                "including their active revision and deployment state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment to inspect."},
                },
                "required": ["environment"],
            },
        ),
        Tool(
            name="get_proxy_details",
            description=(
                "Get full details for a named API proxy: all revisions, latest revision, "
                "deployed environments, and creation/modification timestamps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proxy_name": {"type": "string", "description": "Exact name of the API proxy."},
                    "revision": {"type": "string", "description": "Revision to inspect. Defaults to latest."},
                },
                "required": ["proxy_name"],
            },
        ),
        Tool(
            name="list_proxy_policies",
            description=(
                "List all policy names attached to a proxy revision. "
                "Use this to audit which policies (auth, quotas, transforms, etc.) are in place."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proxy_name": {"type": "string", "description": "Exact name of the API proxy."},
                    "revision": {"type": "string", "description": "Revision to inspect. Defaults to latest."},
                },
                "required": ["proxy_name"],
            },
        ),
        # ── catalog ───────────────────────────────────────────────────────────
        Tool(
            name="list_api_products",
            description=(
                "List all API products with display name, environments, bundled proxies, and quota limits."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_developers",
            description="List registered developers with email, name, status, and registration date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Maximum number of developers to return. Default 100."},
                },
                "required": [],
            },
        ),
        Tool(
            name="list_apps",
            description=(
                "List developer applications with name, status, credentialed API products, and creation date. "
                "Scope to a single developer by supplying their email, or omit to list all apps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "developer_email": {"type": "string", "description": "Return only apps for this developer. Optional."},
                    "count": {"type": "integer", "description": "Maximum apps to return. Default 100."},
                },
                "required": [],
            },
        ),
        # ── KVMs ─────────────────────────────────────────────────────────────
        Tool(
            name="list_kvms",
            description=(
                "List all Key-Value Maps (KVMs) in an environment. "
                "KVMs store configuration and runtime data used by proxy policies."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                },
                "required": ["environment"],
            },
        ),
        Tool(
            name="get_kvm_entries",
            description=(
                "Retrieve all entries (key-value pairs) from a specific KVM in an environment. "
                "Values for encrypted KVMs will be masked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "kvm_name": {"type": "string", "description": "Name of the Key-Value Map."},
                },
                "required": ["environment", "kvm_name"],
            },
        ),
        Tool(
            name="upsert_kvm_entry",
            description=(
                "Create or update a single entry in a KVM. "
                "If the key already exists it is updated; otherwise it is created."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "kvm_name": {"type": "string", "description": "Name of the Key-Value Map."},
                    "key": {"type": "string", "description": "Entry key name."},
                    "value": {"type": "string", "description": "Entry value."},
                },
                "required": ["environment", "kvm_name", "key", "value"],
            },
        ),
        Tool(
            name="delete_kvm_entry",
            description="Delete a single entry from a KVM by key name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "kvm_name": {"type": "string", "description": "Name of the Key-Value Map."},
                    "key": {"type": "string", "description": "Entry key to delete."},
                },
                "required": ["environment", "kvm_name", "key"],
            },
        ),
        # ── target servers ────────────────────────────────────────────────────
        Tool(
            name="list_target_servers",
            description=(
                "List all target servers defined in an environment. "
                "Target servers abstract backend host/port so proxies can reference them by name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                },
                "required": ["environment"],
            },
        ),
        Tool(
            name="get_target_server",
            description="Get host, port, SSL config, and enabled state for a specific target server.",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "name": {"type": "string", "description": "Target server name."},
                },
                "required": ["environment", "name"],
            },
        ),
        Tool(
            name="upsert_target_server",
            description=(
                "Create or update a target server in an environment. "
                "If a server with the given name already exists it is updated; otherwise created."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "name": {"type": "string", "description": "Target server name."},
                    "host": {"type": "string", "description": "Backend hostname or IP."},
                    "port": {"type": "integer", "description": "Backend port number."},
                    "ssl_enabled": {"type": "boolean", "description": "Whether TLS is enabled. Default false."},
                },
                "required": ["environment", "name", "host", "port"],
            },
        ),
        Tool(
            name="delete_target_server",
            description="Delete a target server from an environment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "name": {"type": "string", "description": "Target server name to delete."},
                },
                "required": ["environment", "name"],
            },
        ),
        # ── shared flows ──────────────────────────────────────────────────────
        Tool(
            name="list_shared_flows",
            description=(
                "List all shared flows in the org with their latest revision. "
                "Shared flows are reusable policy chains attached to multiple proxies."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_shared_flow_details",
            description=(
                "Get revision history, deployed environments, and timestamps for a shared flow."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Shared flow name."},
                    "revision": {"type": "string", "description": "Revision to inspect. Defaults to latest."},
                },
                "required": ["name"],
            },
        ),
        # ── caches ────────────────────────────────────────────────────────────
        Tool(
            name="list_caches",
            description="List all caches in an environment with their expiry settings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                },
                "required": ["environment"],
            },
        ),
        Tool(
            name="clear_cache",
            description=(
                "Flush all entries in a named cache for an environment. "
                "Use this when stale cached responses need to be invalidated immediately."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "cache_name": {"type": "string", "description": "Name of the cache to clear."},
                },
                "required": ["environment", "cache_name"],
            },
        ),
        # ── debug / trace ─────────────────────────────────────────────────────
        Tool(
            name="create_debug_session",
            description=(
                "Start a debug (trace) session on a specific proxy revision in an environment. "
                "The session captures the next N live transactions for inspection. "
                "Use get_debug_transactions to retrieve captured data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "proxy_name": {"type": "string", "description": "Name of the API proxy to trace."},
                    "revision": {"type": "string", "description": "Proxy revision to trace."},
                    "timeout_seconds": {"type": "integer", "description": "Session lifetime in seconds. Default 300."},
                    "count": {"type": "integer", "description": "Max transactions to capture. Default 20."},
                },
                "required": ["environment", "proxy_name", "revision"],
            },
        ),
        Tool(
            name="get_debug_transactions",
            description=(
                "Retrieve and summarize all transactions captured in a debug session. "
                "Each entry includes status code, request URI, fault name, and error flag."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "proxy_name": {"type": "string", "description": "Name of the API proxy."},
                    "revision": {"type": "string", "description": "Proxy revision the session belongs to."},
                    "session_id": {"type": "string", "description": "Debug session ID returned by create_debug_session."},
                },
                "required": ["environment", "proxy_name", "revision", "session_id"],
            },
        ),
        # ── diagnostics (compound) ────────────────────────────────────────────
        Tool(
            name="get_proxy_errors",
            description=(
                "Compound diagnostic tool: given a proxy and environment, this tool resolves "
                "the active revision, reuses an existing debug session or creates one if none exists, "
                "fetches all captured transactions, and returns only the errored ones with fault details. "
                "If a new session was just created, send traffic through the proxy then call this again."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proxy_name": {"type": "string", "description": "Name of the API proxy to diagnose."},
                    "environment": {"type": "string", "description": "Environment where the proxy is deployed."},
                    "revision": {"type": "string", "description": "Proxy revision to target. Defaults to latest."},
                },
                "required": ["proxy_name", "environment"],
            },
        ),
        Tool(
            name="get_proxy_error_rate",
            description=(
                "Analytics-based error summary for a single proxy: total calls, error count, "
                "error rate %, and average latency. Unlike get_proxy_errors this uses historical "
                "analytics data — no debug session needed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proxy_name": {"type": "string", "description": "Name of the API proxy."},
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "time_range": {
                        "type": "string",
                        "description": "Time window: 'MM/DD/YYYY HH:MM~MM/DD/YYYY HH:MM'. Defaults to last hour.",
                    },
                },
                "required": ["proxy_name", "environment"],
            },
        ),
        Tool(
            name="get_top_erroring_proxies",
            description=(
                "Rank all proxies in an environment by error count over the given time window. "
                "Returns the top N proxies with total calls, error count, error rate %, and avg latency. "
                "Use this to quickly identify which proxies are causing the most problems."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "description": "Name of the Apigee environment."},
                    "time_range": {
                        "type": "string",
                        "description": "Time window: 'MM/DD/YYYY HH:MM~MM/DD/YYYY HH:MM'. Defaults to last hour.",
                    },
                    "top_n": {"type": "integer", "description": "How many proxies to return. Default 10."},
                },
                "required": ["environment"],
            },
        ),
    ]


# ── tool dispatch ───────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
        text = json.dumps(result, indent=2, default=str)
    except Exception as exc:
        text = f"Error: {exc}"

    return [TextContent(type="text", text=text)]


async def _dispatch(name: str, args: dict):
    match name:
        # environments
        case "list_environments":
            return await apigee_tools.list_environments()
        case "get_analytics":
            return await apigee_tools.get_analytics(
                environment=args["environment"],
                proxy=args.get("proxy"),
                time_range=args.get("time_range"),
                metrics=args.get("metrics"),
            )
        # proxies
        case "list_proxies":
            return await apigee_tools.list_proxies()
        case "get_deployed_proxies":
            return await apigee_tools.get_deployed_proxies(environment=args["environment"])
        case "get_proxy_details":
            return await apigee_tools.get_proxy_details(
                proxy_name=args["proxy_name"],
                revision=args.get("revision"),
            )
        case "list_proxy_policies":
            return await apigee_tools.list_proxy_policies(
                proxy_name=args["proxy_name"],
                revision=args.get("revision"),
            )
        # catalog
        case "list_api_products":
            return await apigee_tools.list_api_products()
        case "list_developers":
            return await apigee_tools.list_developers(count=args.get("count", 100))
        case "list_apps":
            return await apigee_tools.list_apps(
                developer_email=args.get("developer_email"),
                count=args.get("count", 100),
            )
        # kvms
        case "list_kvms":
            return await apigee_tools.list_kvms(environment=args["environment"])
        case "get_kvm_entries":
            return await apigee_tools.get_kvm_entries(
                environment=args["environment"],
                kvm_name=args["kvm_name"],
            )
        case "upsert_kvm_entry":
            return await apigee_tools.upsert_kvm_entry(
                environment=args["environment"],
                kvm_name=args["kvm_name"],
                key=args["key"],
                value=args["value"],
            )
        case "delete_kvm_entry":
            return await apigee_tools.delete_kvm_entry(
                environment=args["environment"],
                kvm_name=args["kvm_name"],
                key=args["key"],
            )
        # target servers
        case "list_target_servers":
            return await apigee_tools.list_target_servers(environment=args["environment"])
        case "get_target_server":
            return await apigee_tools.get_target_server(
                environment=args["environment"],
                name=args["name"],
            )
        case "upsert_target_server":
            return await apigee_tools.upsert_target_server(
                environment=args["environment"],
                name=args["name"],
                host=args["host"],
                port=args["port"],
                ssl_enabled=args.get("ssl_enabled", False),
            )
        case "delete_target_server":
            return await apigee_tools.delete_target_server(
                environment=args["environment"],
                name=args["name"],
            )
        # shared flows
        case "list_shared_flows":
            return await apigee_tools.list_shared_flows()
        case "get_shared_flow_details":
            return await apigee_tools.get_shared_flow_details(
                name=args["name"],
                revision=args.get("revision"),
            )
        # caches
        case "list_caches":
            return await apigee_tools.list_caches(environment=args["environment"])
        case "clear_cache":
            return await apigee_tools.clear_cache(
                environment=args["environment"],
                cache_name=args["cache_name"],
            )
        # debug
        case "create_debug_session":
            return await apigee_tools.create_debug_session(
                environment=args["environment"],
                proxy_name=args["proxy_name"],
                revision=args["revision"],
                timeout_seconds=args.get("timeout_seconds", 300),
                count=args.get("count", 20),
            )
        case "get_debug_transactions":
            return await apigee_tools.get_debug_transactions(
                environment=args["environment"],
                proxy_name=args["proxy_name"],
                revision=args["revision"],
                session_id=args["session_id"],
            )
        # diagnostics
        case "get_proxy_errors":
            return await apigee_tools.get_proxy_errors(
                proxy_name=args["proxy_name"],
                environment=args["environment"],
                revision=args.get("revision"),
            )
        case "get_proxy_error_rate":
            return await apigee_tools.get_proxy_error_rate(
                proxy_name=args["proxy_name"],
                environment=args["environment"],
                time_range=args.get("time_range"),
            )
        case "get_top_erroring_proxies":
            return await apigee_tools.get_top_erroring_proxies(
                environment=args["environment"],
                time_range=args.get("time_range"),
                top_n=args.get("top_n", 10),
            )
        case _:
            raise ValueError(f"Unknown tool: {name}")


# ── entry point ─────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
