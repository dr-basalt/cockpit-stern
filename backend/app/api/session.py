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


# --- OAuth Connect (Nango proxy) ---

# Aligné sur les providers Nango réellement configurés
INTEGRATIONS = [
    {"key": "github", "name": "GitHub (OAuth)", "icon": "🐙", "category": "Dev", "auth": "oauth2"},
    {"key": "github-pat", "name": "GitHub (PAT)", "icon": "🐙", "category": "Dev", "auth": "api_key"},
    {"key": "google-calendar", "name": "Google Calendar", "icon": "📅", "category": "Google", "auth": "oauth2"},
    {"key": "google-mail", "name": "Gmail", "icon": "📧", "category": "Google", "auth": "oauth2"},
    {"key": "google-drive", "name": "Google Drive", "icon": "📁", "category": "Google", "auth": "oauth2"},
    {"key": "google-docs", "name": "Google Docs", "icon": "📄", "category": "Google", "auth": "oauth2"},
    {"key": "google-sheet", "name": "Google Sheets", "icon": "📊", "category": "Google", "auth": "oauth2"},
    {"key": "slack", "name": "Slack", "icon": "💬", "category": "Communication", "auth": "oauth2"},
    {"key": "notion", "name": "Notion", "icon": "📝", "category": "Productivity", "auth": "oauth2"},
    {"key": "hubspot", "name": "HubSpot", "icon": "🔶", "category": "CRM", "auth": "oauth2"},
    {"key": "linear", "name": "Linear", "icon": "🔷", "category": "Dev", "auth": "oauth2"},
    {"key": "stripe-api-key", "name": "Stripe", "icon": "💳", "category": "Payment", "auth": "api_key"},
]


@router.get("/session/{profile_id}/integrations")
async def list_integrations(profile_id: UUID):
    """List available integrations and connection status."""
    connected = {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{NANGO_URL}/api/v1/connections?env=dev",
                params={"connectionId": str(profile_id)},
            )
            if r.status_code == 200:
                data = r.json()
                for c in data.get("data", data.get("connections", [])):
                    key = c.get("provider_config_key", "")
                    connected[key] = {
                        "connection_id": c.get("connection_id"),
                        "provider": c.get("provider"),
                        "created_at": c.get("created"),
                    }
    except Exception as e:
        logger.warning(f"Nango connections check failed: {e}")

    return {
        "integrations": [
            {
                **integ,
                "connected": integ["key"] in connected,
                "connection": connected.get(integ["key"]),
            }
            for integ in INTEGRATIONS
        ]
    }


class ConnectRequest(BaseModel):
    provider_key: str


@router.post("/session/{profile_id}/connect")
async def create_connect_url(profile_id: UUID, req: ConnectRequest):
    """Create a Nango connect session and return the OAuth URL."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{NANGO_URL}/api/v1/connect/sessions?env=dev",
                headers={"Content-Type": "application/json"},
                json={"end_user": {"id": str(profile_id), "email": f"{str(profile_id)[:8]}@stern-os2.ori3com.cloud"}},
            )
            if r.status_code not in (200, 201):
                return {"error": f"Nango session failed: {r.status_code}", "detail": r.text}

            session_data = r.json()["data"]
            token = session_data["token"]

            oauth_url = f"https://nango-stern-os2.ori3com.cloud/oauth/connect/{req.provider_key}?connect_session_token={token}"
            return {"oauth_url": oauth_url, "session_token": token}
    except Exception as e:
        return {"error": str(e)}


# --- Agent Runtime: Discovery & Connect Link ---

@router.get("/nango/discovery")
async def nango_discovery():
    """Agent runtime endpoint: discover all configured Nango integrations and their status."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Fetch configured integrations from Nango
            r = await client.get(f"{NANGO_URL}/api/v1/integrations?env=dev")
            if r.status_code != 200:
                return {"error": f"Nango API failed: {r.status_code}", "detail": r.text}

            integrations = r.json().get("data", [])

            # Fetch all active connections
            r2 = await client.get(f"{NANGO_URL}/api/v1/connections?env=dev")
            connections = []
            if r2.status_code == 200:
                connections = r2.json().get("data", r2.json().get("connections", []))

            # Build connection index by provider
            conn_by_provider = {}
            for c in connections:
                key = c.get("provider_config_key", "")
                if key not in conn_by_provider:
                    conn_by_provider[key] = []
                conn_by_provider[key].append({
                    "connection_id": c.get("connection_id"),
                    "created": c.get("created"),
                    "provider": c.get("provider"),
                })

            # Enrich integrations with connection status
            result = []
            for integ in integrations:
                provider = integ.get("provider", "")
                unique_key = integ.get("uniqueKey", provider)
                has_creds = integ.get("credentials") is not None
                active_connections = conn_by_provider.get(unique_key, [])

                result.append({
                    "provider": provider,
                    "unique_key": unique_key,
                    "display_name": integ.get("displayName", provider),
                    "auth_mode": integ.get("authMode", "unknown"),
                    "has_credentials": has_creds,
                    "ready": has_creds or integ.get("authMode") in ("API_KEY", "BASIC"),
                    "active_connections": len(active_connections),
                    "connections": active_connections,
                })

            return {
                "total_integrations": len(result),
                "ready": sum(1 for r in result if r["ready"]),
                "needs_oauth_credentials": sum(1 for r in result if not r["ready"]),
                "total_connections": sum(r["active_connections"] for r in result),
                "integrations": result,
            }
    except Exception as e:
        logger.error(f"Nango discovery failed: {e}")
        return {"error": str(e)}


class ConnectLinkRequest(BaseModel):
    profile_id: UUID
    provider_key: str
    notify_email: str | None = None
    notify_message: str | None = None


@router.post("/nango/connect-link")
async def create_connect_link(req: ConnectLinkRequest):
    """Agent runtime endpoint: generate a headless connect link.

    The agent calls this to get an OAuth link it can send to the user
    via email, Slack, or any notification channel.
    The link is valid for 30 minutes.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{NANGO_URL}/api/v1/connect/sessions?env=dev",
                headers={"Content-Type": "application/json"},
                json={
                    "end_user": {
                        "id": str(req.profile_id),
                        "email": req.notify_email or f"{str(req.profile_id)[:8]}@stern-os2.ori3com.cloud",
                    },
                },
            )
            if r.status_code not in (200, 201):
                return {"error": f"Nango session failed: {r.status_code}", "detail": r.text}

            session_data = r.json()["data"]
            token = session_data["token"]
            connect_url = f"https://nango-stern-os2.ori3com.cloud/oauth/connect/{req.provider_key}?connect_session_token={token}"

            return {
                "connect_url": connect_url,
                "session_token": token,
                "provider": req.provider_key,
                "expires_in_minutes": 30,
                "instruction": f"Envoie ce lien a l'utilisateur pour qu'il autorise {req.provider_key}. Le lien expire dans 30 minutes.",
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/nango/connections/{profile_id}")
async def get_user_connections(profile_id: UUID):
    """Agent runtime endpoint: check which integrations a user has connected."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{NANGO_URL}/api/v1/connections?env=dev",
                params={"connectionId": str(profile_id)},
            )
            if r.status_code != 200:
                return {"connections": [], "error": r.text}

            data = r.json()
            connections = data.get("data", data.get("connections", []))
            return {
                "profile_id": str(profile_id),
                "total": len(connections),
                "connections": [
                    {
                        "provider": c.get("provider"),
                        "provider_config_key": c.get("provider_config_key"),
                        "connection_id": c.get("connection_id"),
                        "created": c.get("created"),
                    }
                    for c in connections
                ],
            }
    except Exception as e:
        return {"connections": [], "error": str(e)}


class NangoCredentialsRequest(BaseModel):
    provider_key: str
    client_id: str
    client_secret: str
    scopes: str = ""


@router.put("/nango/integrations/{provider_key}/credentials")
async def update_integration_credentials(provider_key: str, req: NangoCredentialsRequest):
    """Update OAuth credentials for an integration (admin endpoint).

    Used to provide client_id/client_secret for OAuth providers
    that don't work with shared credentials in self-hosted mode.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            body = {
                "credentials": {
                    "type": "OAUTH2",
                    "client_id": req.client_id,
                    "client_secret": req.client_secret,
                },
            }
            if req.scopes:
                body["credentials"]["scopes"] = req.scopes

            r = await client.patch(
                f"{NANGO_URL}/api/v1/integrations/{provider_key}?env=dev",
                headers={"Content-Type": "application/json"},
                json=body,
            )
            if r.status_code not in (200, 201):
                return {"error": f"Failed: {r.status_code}", "detail": r.text}
            return {"status": "ok", "provider": provider_key}
    except Exception as e:
        return {"error": str(e)}
