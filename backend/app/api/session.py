import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)
router = APIRouter()
memory_service = MemoryService()

NANGO_URL = getattr(settings, "NANGO_URL", "http://nango:3003")
NANGO_SECRET = getattr(settings, "NANGO_SECRET_KEY", "")


class EnergyUpdate(BaseModel):
    energy_level: int


@router.post("/session/{profile_id}/energy")
async def update_energy(profile_id: UUID, data: EnergyUpdate):
    await memory_service.set_energy(profile_id, data.energy_level)
    return {"status": "ok", "energy_level": data.energy_level}


@router.get("/session/{profile_id}/energy")
async def get_energy(profile_id: UUID):
    energy = await memory_service.get_energy(profile_id)
    return {"energy_level": energy or 5}


@router.get("/session/{profile_id}/decisions")
async def get_decisions(profile_id: UUID):
    decisions = await memory_service.get_decision_history(profile_id)
    return {"decisions": decisions}


# --- Obot MCP Gateway: Discovery, Connect, Tools ---

from app.services.mcp_client import MCPClient, OBOT_MCP_SERVERS

OBOT_URL = getattr(settings, "OBOT_URL", "http://obot:8080")
mcp = MCPClient()


@router.get("/session/{profile_id}/integrations")
async def list_integrations(profile_id: UUID):
    """List available MCP integrations via Obot (OAuth handled by Obot shared apps)."""
    tools = await mcp.discover_tools(str(profile_id))
    return {
        "integrations": [
            {
                "key": t["name"],
                "name": t["display_name"],
                "active": t["active"],
                "configured": t["configured"],
                "connect_url": t.get("connect_url", "").replace("http://localhost:8080", "https://obot-stern-os2.ori3com.cloud"),
            }
            for t in tools
        ]
    }


class ConnectRequest(BaseModel):
    provider_key: str


@router.post("/session/{profile_id}/connect")
async def create_connect_url(profile_id: UUID, req: ConnectRequest):
    """Get OAuth connect URL via Obot MCP. User opens this in browser."""
    url = await mcp.get_connect_url(req.provider_key)
    if url:
        return {"oauth_url": url, "provider": req.provider_key}
    return {"error": f"No connect URL for {req.provider_key}"}


@router.get("/obot/discovery")
async def obot_discovery():
    """Agent runtime: discover all Obot MCP servers with tools and connect status."""
    tools = await mcp.discover_tools()
    active = [t for t in tools if t["active"]]
    return {
        "total_servers": len(OBOT_MCP_SERVERS),
        "active": len(active),
        "configured": sum(1 for t in active if t["configured"]),
        "servers": tools,
    }


@router.get("/obot/servers/{tool_key}/tools")
async def list_server_tools(tool_key: str):
    """Agent runtime: list available tool functions for a specific MCP server."""
    info = OBOT_MCP_SERVERS.get(tool_key)
    if not info:
        return {"error": f"Unknown server: {tool_key}", "available": list(OBOT_MCP_SERVERS.keys())}
    tools = await mcp.list_server_tools(info["catalog_id"])
    return {"server": tool_key, "display_name": info["name"], "tools": tools}


@router.get("/obot/connect/{tool_key}")
async def get_connect_link(tool_key: str):
    """Agent runtime: get OAuth connect URL for a tool. Send to user via email/slack."""
    url = await mcp.get_connect_url(tool_key)
    if url:
        return {
            "connect_url": url,
            "provider": tool_key,
            "instruction": f"Ouvre ce lien pour connecter {OBOT_MCP_SERVERS.get(tool_key, {}).get('name', tool_key)}. L'OAuth est geree par Obot (pas d'app a creer).",
        }
    return {"error": f"No connect URL for {tool_key}"}


class ToolCallRequest(BaseModel):
    tool_name: str
    params: dict = {}
    dry_run: bool = False


@router.post("/obot/call/{tool_key}")
async def call_tool(tool_key: str, req: ToolCallRequest):
    """Agent runtime: execute a tool on an Obot MCP server."""
    result = await mcp.call(tool_key, req.tool_name, req.params, req.dry_run)
    return result
