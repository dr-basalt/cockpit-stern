import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Obot MCP catalog IDs + remote public URLs (*.obot.ai handle OAuth)
OBOT_MCP_SERVERS = {
    "google-calendar": {"catalog_id": "default-google-calendar-cd16928d", "name": "Google Calendar", "remote_url": "https://google-calendar-mcp.obot.ai/mcp/", "auth_server": "https://google-calendar-mcp.obot.ai"},
    "gmail": {"catalog_id": "default-gmail-8a99d8be", "name": "Gmail", "remote_url": "https://gmail-mcp.obot.ai/mcp", "auth_server": "https://gmail-mcp.obot.ai"},
    "google-drive": {"catalog_id": "default-google-drive-4d983c77", "name": "Google Drive", "remote_url": "https://google-drive-mcp.obot.ai/mcp/", "auth_server": "https://google-drive-mcp.obot.ai"},
    "google-docs": {"catalog_id": "default-google-docs-2e59f122", "name": "Google Docs", "remote_url": "https://google-docs-mcp.obot.ai/mcp/", "auth_server": "https://google-docs-mcp.obot.ai"},
    "google-sheets": {"catalog_id": "default-google-sheets-68166c0a", "name": "Google Sheets", "remote_url": "https://google-sheets-mcp.obot.ai/mcp/", "auth_server": "https://google-sheets-mcp.obot.ai"},
    "slack": {"catalog_id": "default-slack-b73781ab", "name": "Slack", "remote_url": "https://slack-mcp.obot.ai/mcp", "auth_server": "https://slack-mcp.obot.ai"},
    "notion": {"catalog_id": "default-notion-ae1c5d40", "name": "Notion", "remote_url": "https://mcp.notion.com/mcp", "auth_server": "https://mcp.notion.com"},
    "hubspot": {"catalog_id": "default-hubspot-d7fcd7e1", "name": "HubSpot", "remote_url": "https://hubspot-mcp.obot.ai/mcp", "auth_server": "https://hubspot-mcp.obot.ai"},
    "linear": {"catalog_id": "default-linear-2ad8f8d8", "name": "Linear", "remote_url": "https://mcp.linear.app/mcp", "auth_server": "https://mcp.linear.app"},
    "stripe": {"catalog_id": "default-stripe-eab4c1f7", "name": "Stripe", "remote_url": "https://mcp.stripe.com", "auth_server": "https://mcp.stripe.com"},
    "todoist": {"catalog_id": "default-todoist-77d6d2c9", "name": "Todoist", "remote_url": "https://ai.todoist.net/mcp", "auth_server": "https://ai.todoist.net"},
    "outlook": {"catalog_id": "default-outlook-841b850d", "name": "Outlook", "remote_url": "https://outlook-mcp.obot.ai/mcp", "auth_server": "https://outlook-mcp.obot.ai"},
}

AGENT_TOOL_PERMISSIONS = {
    "clone": {"access": "read_write", "tools": ["google-calendar", "gmail", "google-drive", "google-docs", "google-sheets", "slack", "notion", "hubspot", "linear", "stripe", "todoist"]},
    "anti": {"access": "read_only", "tools": ["google-calendar", "notion", "hubspot", "linear", "todoist"]},
    "sp": {"access": "notify_only", "tools": ["slack", "gmail"]},
    "real": {"access": "none", "tools": []},
}


class MCPClient:
    """Adapter between LangGraph agents and Obot MCP gateway.

    Obot manages OAuth (shared apps from obot.ai) + MCP tool execution.
    No need for separate OAuth apps — Obot's catalog servers handle auth.
    """

    def __init__(self, obot_url: str = ""):
        self.obot = obot_url or getattr(settings, "OBOT_URL", "http://obot:8080")

    # --- Discovery ---

    async def discover_tools(self, profile_id: str = "", agent: str = "clone") -> list[dict]:
        """Discover available MCP tools from Obot, filtered by agent permissions."""
        perms = AGENT_TOOL_PERMISSIONS.get(agent, AGENT_TOOL_PERMISSIONS["clone"])
        tools = []

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.obot}/api/mcp-servers")
                if r.status_code == 200:
                    servers = r.json().get("items", [])
                    active_catalogs = {s.get("catalogEntryID", ""): s for s in servers}

                    for key, info in OBOT_MCP_SERVERS.items():
                        server = active_catalogs.get(info["catalog_id"])
                        is_active = server is not None
                        is_configured = server.get("configured", False) if server else False
                        is_permitted = key in perms["tools"]

                        tools.append({
                            "name": key,
                            "display_name": info["name"],
                            "catalog_id": info["catalog_id"],
                            "active": is_active,
                            "configured": is_configured,
                            "permitted": is_permitted,
                            "access": perms["access"] if is_permitted else "none",
                            "connect_url": server.get("connectURL", "") if server else "",
                        })

                    return tools
        except Exception as e:
            logger.warning(f"Obot discovery failed: {e}")

        # Fallback: return static list
        return [
            {
                "name": key,
                "display_name": info["name"],
                "active": False,
                "configured": False,
                "permitted": key in perms["tools"],
                "access": perms["access"] if key in perms["tools"] else "none",
            }
            for key, info in OBOT_MCP_SERVERS.items()
        ]

    async def list_server_tools(self, catalog_id: str) -> list[dict]:
        """List available tools (functions) for a specific MCP server."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.obot}/api/mcp-servers")
                if r.status_code == 200:
                    servers = r.json().get("items", [])
                    for s in servers:
                        if s.get("catalogEntryID") == catalog_id:
                            previews = s.get("manifest", {}).get("toolPreview", [])
                            return [
                                {"name": t["name"], "description": t.get("description", ""), "params": t.get("params", {})}
                                for t in previews
                            ]
        except Exception as e:
            logger.warning(f"Obot tool list failed: {e}")
        return []

    # --- OAuth Connect ---

    async def get_connect_url(self, tool_key: str) -> str | None:
        """Get the OAuth connect URL for a tool. User opens this in browser to authorize."""
        info = OBOT_MCP_SERVERS.get(tool_key)
        if not info:
            return None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.obot}/api/mcp-servers")
                if r.status_code == 200:
                    servers = r.json().get("items", [])
                    for s in servers:
                        if s.get("catalogEntryID") == info["catalog_id"]:
                            connect = s.get("connectURL", "")
                            if connect:
                                # Convert internal URL to external
                                return connect.replace(
                                    "http://localhost:8080",
                                    "https://api-stern-os2.ori3com.cloud/obot-proxy"
                                )
        except Exception as e:
            logger.warning(f"Obot connect URL failed: {e}")
        return None

    # --- Tool Execution via MCP ---

    async def call(self, tool_key: str, tool_name: str, params: dict, dry_run: bool = False) -> dict:
        """Execute a tool on an Obot MCP server.

        Args:
            tool_key: The high-level key (e.g. "google-calendar")
            tool_name: The specific tool function (e.g. "list_events")
            params: Parameters for the tool
            dry_run: If True, return what would happen without executing
        """
        if dry_run:
            return self._dry_run(tool_key, tool_name, params)

        info = OBOT_MCP_SERVERS.get(tool_key)
        if not info:
            return {"error": f"Unknown tool: {tool_key}", "available_tools": list(OBOT_MCP_SERVERS.keys())}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Call the MCP server via Obot's connect endpoint
                connect_path = f"/mcp-connect/{info['catalog_id']}"
                r = await client.post(
                    f"{self.obot}{connect_path}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": params},
                        "id": 1,
                    },
                    headers={"Content-Type": "application/json"},
                )
                if r.status_code < 400:
                    return {"status": "ok", "tool": tool_name, "server": tool_key, "result": r.json()}
                return {"status": "error", "code": r.status_code, "detail": r.text}
        except Exception as e:
            logger.warning(f"MCP call failed: {e}")
            return {"error": str(e), "tool": tool_name, "server": tool_key}

    def _dry_run(self, tool_key: str, tool_name: str, params: dict) -> dict:
        return {
            "action": tool_name,
            "server": tool_key,
            "params": params,
            "risk_level": "low" if "list" in tool_name or "get" in tool_name else "medium",
            "dry_run": True,
        }
