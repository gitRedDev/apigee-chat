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
                "to a single proxy and/or supply custom metrics. "
                "Use this when the user asks about traffic, latency, error rates, "
                "or API usage in a given environment."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "description": "Name of the Apigee environment (e.g. 'prod').",
                    },
                    "proxy": {
                        "type": "string",
                        "description": "Filter analytics to this proxy name. Optional.",
                    },
                    "time_range": {
                        "type": "string",
                        "description": (
                            "Time window in Apigee format: "
                            "'MM/DD/YYYY HH:MM~MM/DD/YYYY HH:MM'. "
                            "Defaults to the last hour if omitted."
                        ),
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Apigee metric expressions to retrieve. "
                            "Defaults to message_count, total_response_time, is_error."
                        ),
                    },
                },
                "required": ["environment"],
            },
        ),
        Tool(
            name="list_proxies",
            description=(
                "List all API proxies in the Apigee organization along with "
                "their latest revision number. Use this to get an overview of "
                "which proxies exist before drilling into details."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_deployed_proxies",
            description=(
                "Show which API proxies are currently deployed in a specific "
                "environment, including their active revision and deployment state "
                "(deployed / error / undeployed). Use this to check what is "
                "live in prod (or any environment)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "description": "Name of the Apigee environment to inspect.",
                    }
                },
                "required": ["environment"],
            },
        ),
        Tool(
            name="get_proxy_details",
            description=(
                "Get full details for a named API proxy: all revisions, the latest "
                "revision, which environments it is deployed to, and creation / "
                "modification timestamps. Optionally pin to a specific revision. "
                "Use this when the user asks about a specific proxy's history, "
                "deployment status, or configuration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proxy_name": {
                        "type": "string",
                        "description": "Exact name of the API proxy.",
                    },
                    "revision": {
                        "type": "string",
                        "description": "Revision number to inspect. Defaults to latest.",
                    },
                },
                "required": ["proxy_name"],
            },
        ),
        Tool(
            name="list_api_products",
            description=(
                "List all API products in the Apigee organization with their display "
                "name, which environments they are published to, which proxies they "
                "bundle, and any quota limits. Use this to understand what is exposed "
                "to external developers via the developer portal."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_developers",
            description=(
                "List registered developers in the Apigee organization with email, "
                "name, status (active/inactive), and registration date. "
                "Use this when the user asks who has signed up or to find a "
                "specific developer's details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of developers to return. Default 100.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_apps",
            description=(
                "List developer applications registered in Apigee. Each app entry "
                "includes its name, status, which API products it has credentials "
                "for, and creation date. Scope to a single developer by supplying "
                "their email address, or omit to list all apps in the org."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "developer_email": {
                        "type": "string",
                        "description": "Return only apps belonging to this developer. Optional.",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum apps to return when listing all. Default 100.",
                    },
                },
                "required": [],
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
        case "list_environments":
            return await apigee_tools.list_environments()

        case "get_analytics":
            return await apigee_tools.get_analytics(
                environment=args["environment"],
                proxy=args.get("proxy"),
                time_range=args.get("time_range"),
                metrics=args.get("metrics"),
            )

        case "list_proxies":
            return await apigee_tools.list_proxies()

        case "get_deployed_proxies":
            return await apigee_tools.get_deployed_proxies(
                environment=args["environment"]
            )

        case "get_proxy_details":
            return await apigee_tools.get_proxy_details(
                proxy_name=args["proxy_name"],
                revision=args.get("revision"),
            )

        case "list_api_products":
            return await apigee_tools.list_api_products()

        case "list_developers":
            return await apigee_tools.list_developers(
                count=args.get("count", 100)
            )

        case "list_apps":
            return await apigee_tools.list_apps(
                developer_email=args.get("developer_email"),
                count=args.get("count", 100),
            )

        case _:
            raise ValueError(f"Unknown tool: {name}")


# ── entry point ─────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
