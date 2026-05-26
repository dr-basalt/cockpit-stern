import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AGENT_TOOL_PERMISSIONS = {
    "clone": {"access": "read_write", "tools": ["notion", "github", "calendar", "search", "file", "email_draft"]},
    "anti": {"access": "read_only", "tools": ["notion_read", "calendar_read", "okr_read"]},
    "sp": {"access": "notify_only", "tools": ["notification", "message_draft"]},
    "real": {"access": "none", "tools": []},
}


class MCPClient:
    """Adapter between LangGraph nodes and Obot MCP gateway + Nango token store."""

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
        perms = AGENT_TOOL_PERMISSIONS.get(agent, AGENT_TOOL_PERMISSIONS["clone"])
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.obot}/api/v1/tools")
                if r.status_code == 200:
                    all_tools = r.json()
                    return [t for t in all_tools if t.get("name") in perms["tools"]]
        except Exception as e:
            logger.warning(f"Obot unavailable, returning mock tools: {e}")
        return [{"name": t, "available": False, "mock": True} for t in perms["tools"]]

    async def _get_token(self, profile_id: str, tool_name: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self.nango}/connection/{profile_id}",
                    headers={"Authorization": f"Bearer {self.nango_secret}"},
                    params={"provider_config_key": tool_name},
                )
                if r.status_code == 200:
                    return r.json().get("credentials", {}).get("access_token")
        except Exception as e:
            logger.debug(f"Nango token fetch failed: {e}")
        return None

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
