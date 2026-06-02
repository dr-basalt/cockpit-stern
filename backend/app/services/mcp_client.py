import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AGENT_TOOL_PERMISSIONS = {
    "clone": {"access": "read_write", "tools": ["notion", "github", "google-calendar", "google-mail", "google-drive", "slack", "hubspot", "stripe-api-key", "linear"]},
    "anti": {"access": "read_only", "tools": ["notion", "google-calendar", "hubspot", "linear"]},
    "sp": {"access": "notify_only", "tools": ["slack", "google-mail"]},
    "real": {"access": "none", "tools": []},
}


class MCPClient:
    """Adapter between LangGraph nodes and Nango (auth + proxy) + Obot (MCP gateway)."""

    def __init__(self, obot_url: str = "", nango_url: str = "", nango_secret: str = ""):
        self.obot = obot_url or getattr(settings, "OBOT_URL", "http://obot:8080")
        self.nango = nango_url or getattr(settings, "NANGO_URL", "http://nango:3003")
        self.nango_secret = nango_secret or getattr(settings, "NANGO_SECRET_KEY", "")

    async def call(self, tool_name: str, profile_id: str, params: dict, dry_run: bool = False) -> dict:
        token = await self._get_token(profile_id, tool_name)
        if dry_run:
            return await self._dry_run(tool_name, params, token)
        return await self._execute(tool_name, params, token)

    async def discover_tools(self, profile_id: str, agent: str = "clone") -> list[dict]:
        """Discover available tools: merge Nango integrations + agent permissions."""
        perms = AGENT_TOOL_PERMISSIONS.get(agent, AGENT_TOOL_PERMISSIONS["clone"])
        tools = []

        # Fetch Nango integrations to see what's actually configured
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.nango}/api/v1/integrations?env=dev")
                if r.status_code == 200:
                    integrations = r.json().get("data", [])
                    for integ in integrations:
                        provider = integ.get("provider", "")
                        unique_key = integ.get("uniqueKey", provider)
                        if unique_key in perms["tools"]:
                            # Check if user has active connection
                            connected = False
                            if profile_id:
                                connected = await self._check_connection(profile_id, unique_key)
                            tools.append({
                                "name": unique_key,
                                "provider": provider,
                                "display_name": integ.get("displayName", provider),
                                "available": connected,
                                "access": perms["access"],
                                "mock": False,
                            })
                    # Add tools from permissions that aren't in Nango
                    nango_keys = {t["name"] for t in tools}
                    for t in perms["tools"]:
                        if t not in nango_keys:
                            tools.append({"name": t, "available": False, "mock": True, "access": perms["access"]})
                    return tools
        except Exception as e:
            logger.warning(f"Nango discovery failed: {e}")

        return [{"name": t, "available": False, "mock": True, "access": perms["access"]} for t in perms["tools"]]

    async def _check_connection(self, profile_id: str, provider_key: str) -> bool:
        """Check if a user has an active connection for a provider."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self.nango}/api/v1/connections?env=dev",
                    params={"connectionId": profile_id},
                )
                if r.status_code == 200:
                    connections = r.json().get("data", r.json().get("connections", []))
                    return any(c.get("provider_config_key") == provider_key for c in connections)
        except Exception:
            pass
        return False

    async def _get_token(self, profile_id: str, tool_name: str) -> str | None:
        """Fetch OAuth token from Nango for a specific connection."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self.nango}/api/v1/connections/{profile_id}?env=dev",
                    params={"provider_config_key": tool_name},
                )
                if r.status_code == 200:
                    return r.json().get("credentials", {}).get("access_token")
        except Exception as e:
            logger.debug(f"Nango token fetch failed: {e}")
        return None

    async def nango_proxy(self, profile_id: str, provider_key: str, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Use Nango's proxy to call external APIs with managed credentials.

        This is the key capability: the agent doesn't need tokens — Nango injects
        them automatically via its proxy.
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {
                    "Connection-Id": profile_id,
                    "Provider-Config-Key": provider_key,
                }
                r = await client.request(
                    method=method,
                    url=f"{self.nango}/proxy{endpoint}",
                    headers=headers,
                    json=data,
                )
                if r.status_code < 400:
                    return {"status": "ok", "data": r.json()}
                return {"status": "error", "code": r.status_code, "detail": r.text}
        except Exception as e:
            logger.warning(f"Nango proxy call failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _execute(self, tool_name: str, params: dict, token: str | None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.obot}/api/v1/tools/{tool_name}/execute",
                    json={"params": params, "token": token},
                )
                return r.json()
        except Exception as e:
            logger.warning(f"MCP execute failed: {e}")
            return {"error": str(e), "mock": True, "tool": tool_name, "params": params}

    async def _dry_run(self, tool_name: str, params: dict, token: str | None) -> dict:
        return {
            "action": tool_name,
            "target": params.get("target", "unknown"),
            "content_before": None,
            "content_after": params.get("content", ""),
            "risk_level": "low" if tool_name.endswith("_read") else "medium",
            "dry_run": True,
        }
