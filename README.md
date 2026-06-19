# apigee-mcp

An MCP server that exposes Apigee X / GCP Management API operations as tools
for Claude (and any other MCP-compatible LLM client).

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | `python3 --version` |
| gcloud CLI | [Install guide](https://cloud.google.com/sdk/docs/install) |
| Apigee X org | Your GCP project must have Apigee X provisioned |

Authenticate with Application Default Credentials once:

```bash
gcloud auth application-default login
```

## Installation

```bash
cd apigee-mcp
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set APIGEE_ORG=<your-gcp-project-id>
```

## Running the server

```bash
python server.py
```

The server communicates over stdio (standard MCP transport). You will not see
any output on startup unless `APIGEE_ORG` is missing, in which case it exits
with a descriptive error.

## Claude Desktop configuration

Add the block below to your `claude_desktop_config.json`
(usually at `~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS, or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "apigee": {
      "command": "/absolute/path/to/apigee-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/apigee-mcp/server.py"],
      "env": {
        "APIGEE_ORG": "my-gcp-project-id"
      }
    }
  }
}
```

Replace the paths and project ID with your own values. Restart Claude Desktop
after saving the file.

## VS Code configuration

Create `.vscode/mcp.json` in your workspace (or add to your user settings):

```json
{
  "servers": {
    "apigee": {
      "type": "stdio",
      "command": "/absolute/path/to/apigee-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/apigee-mcp/server.py"],
      "env": {
        "APIGEE_ORG": "my-gcp-project-id"
      }
    }
  }
}
```

## Available tools

| Tool | What it answers |
|---|---|
| `list_environments` | What environments exist in my org? |
| `get_analytics` | How much traffic / what latency / how many errors in env X? |
| `list_proxies` | What API proxies exist, and what revision is each on? |
| `get_deployed_proxies` | What is currently deployed in prod? |
| `get_proxy_details` | Full history and deployment status for proxy X |
| `list_api_products` | What products are published, with which proxies and quotas? |
| `list_developers` | Who has registered as a developer? |
| `list_apps` | What apps exist, what products do they use? |

## Example questions to ask Claude

- "List all environments in my Apigee org."
- "Show me the error rate for the `payments-proxy` in prod over the last 24 hours."
- "Which revision of `orders-api` is deployed to staging?"
- "What API products bundle the `inventory-proxy`?"
- "List all developers who registered in 2024."
- "Which apps does developer `alice@example.com` have, and what products do they use?"

## Using a service account instead of ADC

1. Create a service account in GCP with the **Apigee Organization Admin** role
   (or a more restrictive read-only role if preferred).
2. Download the JSON key file.
3. Set the environment variable before running the server:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
python server.py
```

`google.auth.default()` automatically picks up `GOOGLE_APPLICATION_CREDENTIALS`,
so no code changes are needed.

## Quick token test (no ADC setup)

```bash
export APIGEE_ACCESS_TOKEN=$(gcloud auth print-access-token)
export APIGEE_ORG=my-gcp-project-id
python server.py
```

When `APIGEE_ACCESS_TOKEN` is set it takes priority over ADC. The token expires
after ~1 hour; restart the server or unset the variable to fall back to ADC.
