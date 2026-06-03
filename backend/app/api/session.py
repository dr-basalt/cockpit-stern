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

# In-memory store for pending OAuth flows and completed tokens
_pending_oauth: dict[str, dict] = {}
_oauth_tokens: dict[str, dict] = {}


INTEGRATION_META = {
    "google-calendar": {"icon": "📅", "category": "Google"},
    "gmail": {"icon": "📧", "category": "Google"},
    "google-drive": {"icon": "📁", "category": "Google"},
    "google-docs": {"icon": "📄", "category": "Google"},
    "google-sheets": {"icon": "📊", "category": "Google"},
    "slack": {"icon": "💬", "category": "Communication"},
    "notion": {"icon": "📝", "category": "Productivity"},
    "hubspot": {"icon": "🔶", "category": "CRM"},
    "linear": {"icon": "🔷", "category": "Dev"},
    "stripe": {"icon": "💳", "category": "Payment"},
    "todoist": {"icon": "✅", "category": "Productivity"},
    "outlook": {"icon": "📮", "category": "Microsoft"},
}


@router.get("/session/{profile_id}/integrations")
async def list_integrations(profile_id: UUID):
    """List available MCP integrations via Obot (OAuth handled by Obot shared apps)."""
    tools = await mcp.discover_tools(str(profile_id))
    return {
        "integrations": [
            {
                "key": t["name"],
                "name": t["display_name"],
                "icon": INTEGRATION_META.get(t["name"], {}).get("icon", "🔌"),
                "category": INTEGRATION_META.get(t["name"], {}).get("category", "Other"),
                "connected": t["name"] in _oauth_tokens,
                "active": t["active"],
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


@router.get("/mcp/introspect")
async def mcp_introspect():
    """MCP Introspector — fait émerger le DDD depuis les MCP tools.

    Introspects all connected MCP servers, extracts entities + SCRUDX,
    detects cross-BC relations, identifies gaps, suggests compositions/skills.
    """
    from app.services.mcp_introspector import introspect_tools

    # Fetch tools from all active MCP servers
    tools_by_server: dict[str, list[dict]] = {}
    for key, info in OBOT_MCP_SERVERS.items():
        tools = await mcp.list_server_tools(info["catalog_id"])
        if tools:
            tools_by_server[key] = tools

    if not tools_by_server:
        return {"error": "No MCP servers with tools available"}

    return introspect_tools(tools_by_server)


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
    """Generate a direct OAuth URL via the remote MCP server (*.obot.ai).

    This bypasses the local Obot instance entirely — the remote MCP server
    handles OAuth with its own shared Google/Slack/etc apps.
    The user opens this URL in their browser → authorizes → callback comes back here.
    """
    import secrets
    import hashlib
    import base64

    info = OBOT_MCP_SERVERS.get(tool_key)
    if not info or "auth_server" not in info:
        return {"error": f"Unknown or unsupported tool: {tool_key}"}

    auth_server = info["auth_server"]
    callback_url = "https://api-stern-os2.ori3com.cloud/mcp/callback"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Step 1: Get authorization server metadata
            r = await client.get(f"{auth_server}/.well-known/oauth-authorization-server")
            if r.status_code != 200:
                return {"error": f"Auth server metadata failed: {r.status_code}", "detail": r.text}
            auth_meta = r.json()

            # Step 2: Dynamic client registration (RFC 7591)
            reg_endpoint = auth_meta.get("registration_endpoint")
            if not reg_endpoint:
                return {"error": "No registration endpoint in auth metadata"}

            r2 = await client.post(reg_endpoint, json={
                "redirect_uris": [callback_url],
                "client_name": "Stern OS2",
                "token_endpoint_auth_method": "client_secret_post",
            })
            if r2.status_code not in (200, 201):
                return {"error": f"Client registration failed: {r2.status_code}", "detail": r2.text}
            reg = r2.json()

            # Step 3: Build PKCE challenge
            code_verifier = secrets.token_urlsafe(32)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()

            # Step 4: Build authorization URL
            scopes = " ".join(auth_meta.get("scopes_supported", ["profile"]))
            state_data = f"{tool_key}:{code_verifier}"
            # Encode state so we can recover tool_key + verifier on callback
            state = base64.urlsafe_b64encode(state_data.encode()).decode()

            auth_url = (
                f"{auth_meta['authorization_endpoint']}"
                f"?response_type=code"
                f"&client_id={reg['client_id']}"
                f"&redirect_uri={callback_url}"
                f"&state={state}"
                f"&code_challenge={code_challenge}"
                f"&code_challenge_method=S256"
                f"&scope={scopes}"
            )

            # Store client credentials in memory for callback exchange
            # In production, use Redis or DB
            _pending_oauth[state] = {
                "tool_key": tool_key,
                "client_id": reg["client_id"],
                "client_secret": reg["client_secret"],
                "code_verifier": code_verifier,
                "token_endpoint": auth_meta["token_endpoint"],
                "redirect_uri": callback_url,
            }

            return {
                "connect_url": auth_url,
                "provider": tool_key,
                "display_name": info["name"],
                "instruction": f"Ouvre ce lien pour connecter {info['name']}. L'OAuth est geree par le MCP server distant (zero app a creer).",
            }
    except Exception as e:
        logger.error(f"OAuth connect failed for {tool_key}: {e}")
        return {"error": str(e)}


class ToolCallRequest(BaseModel):
    tool_name: str
    params: dict = {}
    dry_run: bool = False


@router.post("/obot/call/{tool_key}")
async def call_tool(tool_key: str, req: ToolCallRequest):
    """Agent runtime: execute a tool on an Obot MCP server."""
    result = await mcp.call(tool_key, req.tool_name, req.params, req.dry_run)
    return result
