import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.design_api import DesignVersionService, UserPreferencesService

logger = logging.getLogger(__name__)
router = APIRouter()


# --- VERSIONS ---

@router.get("/versions")
async def list_versions(db: AsyncSession = Depends(get_db)):
    svc = DesignVersionService(db)
    return await svc.list_versions()


@router.get("/versions/{version_id}")
async def get_version(version_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.design import DesignVersion
    result = await db.execute(select(DesignVersion).where(DesignVersion.id == version_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"id": v.id, "tokens": v.tokens, "description": v.description,
            "created_by": v.created_by, "created_at": v.created_at.isoformat() if v.created_at else None}


class PublishRequest(BaseModel):
    tokens: dict
    description: str = ""
    actor: str = "system"


@router.post("/versions")
async def publish_version(req: PublishRequest, db: AsyncSession = Depends(get_db)):
    svc = DesignVersionService(db)
    version_id = await svc.publish_version(req.tokens, req.description, req.actor)
    return {"version_id": version_id}


@router.post("/versions/rollback/{version_id}")
async def rollback_version(version_id: str, db: AsyncSession = Depends(get_db)):
    svc = DesignVersionService(db)
    try:
        await svc.rollback(version_id, "user")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok", "head": version_id}


# --- TOKENS ---

@router.get("/tokens")
async def get_active_tokens(db: AsyncSession = Depends(get_db)):
    svc = DesignVersionService(db)
    return await svc.get_active_tokens()


# --- USER PREFERENCES ---

@router.get("/user/{user_id}/preferences")
async def get_user_prefs(user_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = UserPreferencesService(db)
    return await svc.get_preferences(user_id)


class PrefsUpdate(BaseModel):
    preferences: dict


@router.put("/user/{user_id}/preferences")
async def update_user_prefs(user_id: UUID, req: PrefsUpdate, db: AsyncSession = Depends(get_db)):
    svc = UserPreferencesService(db)
    await svc.save_preferences(user_id, req.preferences)
    return {"status": "ok"}


@router.get("/user/{user_id}/css-vars")
async def get_user_css_vars(user_id: UUID, db: AsyncSession = Depends(get_db)):
    design_svc = DesignVersionService(db)
    pref_svc = UserPreferencesService(db)
    tokens = await design_svc.get_active_tokens()
    css = await pref_svc.get_css_vars(user_id, tokens)
    return css


# --- RBAC ---

@router.get("/rbac/{role}")
async def get_rbac(role: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.design import RoleLayoutConfig
    result = await db.execute(select(RoleLayoutConfig).where(RoleLayoutConfig.role == role))
    config = result.scalar_one_or_none()
    return config.config if config else {}


class RBACUpdate(BaseModel):
    config: dict


@router.put("/rbac/{role}")
async def update_rbac(role: str, req: RBACUpdate, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.design import RoleLayoutConfig
    result = await db.execute(select(RoleLayoutConfig).where(RoleLayoutConfig.role == role))
    existing = result.scalar_one_or_none()
    if existing:
        existing.config = req.config
    else:
        db.add(RoleLayoutConfig(role=role, config=req.config))
    await db.commit()
    return {"status": "ok"}


# --- NLP ---

class NLPIntentRequest(BaseModel):
    text: str


@router.post("/nlp/intent")
async def nlp_intent(req: NLPIntentRequest):
    """Analyze NLP text → design intent (token changes)."""
    import re
    text = req.text.lower()
    elements = []

    color_match = re.search(r"(sp|clone|anti|réel|real).*(#[0-9a-fA-F]{3,6}|violet|purple|bleu|blue|rouge|red|vert|green)", text)
    if color_match:
        agent = color_match.group(1).replace("réel", "real")
        color_name = color_match.group(2)
        color_map = {"violet": "#7B3FE8", "purple": "#7B3FE8", "bleu": "#4A8FE8", "blue": "#4A8FE8",
                      "rouge": "#E05A2B", "red": "#E05A2B", "vert": "#1BB68A", "green": "#1BB68A"}
        value = color_map.get(color_name, color_name)
        elements.append({"token": f"--agent-{agent}", "value": value, "confidence": 0.9})

    if "sombre" in text or "dark" in text:
        elements.append({"token": "--bg-void", "value": "#07070D", "confidence": 0.85})
    if "clair" in text or "light" in text:
        elements.append({"token": "--bg-void", "value": "#F5F5FA", "confidence": 0.85})

    return {"intent": "theme_override" if elements else "unknown", "elements": elements, "raw_text": req.text}


@router.post("/penpot/sync")
async def penpot_sync():
    """Trigger Penpot → tokens → new version pipeline."""
    return {"status": "mock", "message": "Penpot MCP sync not yet configured. Set up .mcp.json with Penpot endpoint."}
