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

INTEGRATIONS = [
    {"key": "github-stern", "name": "GitHub", "icon": "🐙", "category": "Dev"},
    {"key": "notion-stern", "name": "Notion", "icon": "📝", "category": "Productivity"},
    {"key": "slack-stern", "name": "Slack", "icon": "💬", "category": "Communication"},
    {"key": "gcal-stern", "name": "Google Calendar", "icon": "📅", "category": "Google"},
    {"key": "gmail-stern", "name": "Gmail", "icon": "📧", "category": "Google"},
    {"key": "gdrive-stern", "name": "Google Drive", "icon": "📁", "category": "Google"},
    {"key": "gdocs-stern", "name": "Google Docs", "icon": "📄", "category": "Google"},
    {"key": "gsheets-stern", "name": "Google Sheets", "icon": "📊", "category": "Google"},
    {"key": "gmeet-stern", "name": "Google Meet", "icon": "🎥", "category": "Google"},
    {"key": "facebook-stern", "name": "Facebook", "icon": "📘", "category": "Meta"},
    {"key": "instagram-stern", "name": "Instagram", "icon": "📸", "category": "Meta"},
    {"key": "meta-ads-stern", "name": "Meta Ads", "icon": "📢", "category": "Meta"},
    {"key": "whatsapp-stern", "name": "WhatsApp", "icon": "💚", "category": "Meta"},
]


@router.get("/session/{profile_id}/integrations")
async def list_integrations(profile_id: UUID):
    """List available integrations and connection status."""
    connected = set()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{NANGO_URL}/api/v1/connections?env=prod",
                headers={"Authorization": f"Bearer {NANGO_SECRET}"},
                params={"connectionId": str(profile_id)},
            )
            if r.status_code == 200:
                data = r.json()
                for c in data.get("data", data.get("connections", [])):
                    connected.add(c.get("provider_config_key", ""))
    except Exception as e:
        logger.warning(f"Nango connections check failed: {e}")

    return {
        "integrations": [
            {**integ, "connected": integ["key"] in connected}
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
                f"{NANGO_URL}/api/v1/connect/sessions?env=prod",
                headers={
                    "Authorization": f"Bearer {NANGO_SECRET}",
                    "Content-Type": "application/json",
                },
                json={"end_user": {"id": str(profile_id), "email": f"{profile_id}@cockpit-stern"}},
            )
            if r.status_code != 200:
                return {"error": f"Nango session failed: {r.status_code}", "detail": r.text}

            session_data = r.json()["data"]
            token = session_data["token"]

            oauth_url = f"https://nango-stern-os2.ori3com.cloud/oauth/connect/{req.provider_key}?connect_session_token={token}"
            return {"oauth_url": oauth_url, "session_token": token}
    except Exception as e:
        return {"error": str(e)}
