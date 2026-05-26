import hashlib
import json
import logging
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.design import DesignVersion, DesignHead, UserPreference, RoleLayoutConfig, DesignVersionHistory

logger = logging.getLogger(__name__)


class DesignVersionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def get_active_tokens(self) -> dict:
        r = await self._get_redis()
        cached = await r.get("design:tokens:active")
        if cached:
            return json.loads(cached)

        result = await self.db.execute(select(DesignHead).where(DesignHead.singleton == True))
        head = result.scalar_one_or_none()
        if not head:
            return {}

        result = await self.db.execute(select(DesignVersion).where(DesignVersion.id == head.version_id))
        version = result.scalar_one_or_none()
        if not version:
            return {}

        await r.setex("design:tokens:active", 300, json.dumps(version.tokens))
        return version.tokens

    async def publish_version(self, tokens: dict, description: str, actor: str) -> str:
        version_id = hashlib.sha256(json.dumps(tokens, sort_keys=True).encode()).hexdigest()[:12]

        # Check if version exists
        existing = await self.db.execute(select(DesignVersion).where(DesignVersion.id == version_id))
        if not existing.scalar_one_or_none():
            self.db.add(DesignVersion(id=version_id, tokens=tokens, description=description, created_by=actor))

        # Update HEAD
        result = await self.db.execute(select(DesignHead).where(DesignHead.singleton == True))
        head = result.scalar_one_or_none()
        if head:
            head.version_id = version_id
        else:
            self.db.add(DesignHead(singleton=True, version_id=version_id))

        # Log
        self.db.add(DesignVersionHistory(version_id=version_id, action="publish", actor=actor))
        await self.db.commit()

        r = await self._get_redis()
        await r.delete("design:tokens:active")
        return version_id

    async def rollback(self, version_id: str, actor: str):
        existing = await self.db.execute(select(DesignVersion).where(DesignVersion.id == version_id))
        if not existing.scalar_one_or_none():
            raise ValueError(f"Version {version_id} not found")

        result = await self.db.execute(select(DesignHead).where(DesignHead.singleton == True))
        head = result.scalar_one_or_none()
        if head:
            head.version_id = version_id
        else:
            self.db.add(DesignHead(singleton=True, version_id=version_id))

        self.db.add(DesignVersionHistory(version_id=version_id, action="rollback", actor=actor))
        await self.db.commit()

        r = await self._get_redis()
        await r.delete("design:tokens:active")

    async def list_versions(self) -> list[dict]:
        result = await self.db.execute(select(DesignVersion).order_by(DesignVersion.created_at.desc()))
        versions = result.scalars().all()
        head_result = await self.db.execute(select(DesignHead).where(DesignHead.singleton == True))
        head = head_result.scalar_one_or_none()
        head_id = head.version_id if head else None

        return [
            {"id": v.id, "description": v.description, "created_by": v.created_by,
             "created_at": v.created_at.isoformat() if v.created_at else None,
             "is_head": v.id == head_id}
            for v in versions
        ]


class UserPreferencesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_preferences(self, user_id: UUID) -> dict:
        result = await self.db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        pref = result.scalar_one_or_none()
        return pref.preferences if pref else {}

    async def save_preferences(self, user_id: UUID, preferences: dict):
        result = await self.db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        pref = result.scalar_one_or_none()
        if pref:
            pref.preferences = preferences
        else:
            self.db.add(UserPreference(user_id=user_id, preferences=preferences))
        await self.db.commit()

    async def get_css_vars(self, user_id: UUID, active_tokens: dict) -> str:
        prefs = await self.get_preferences(user_id)
        overrides = {}

        if theme := prefs.get("theme", {}):
            for agent, color in theme.get("agentColors", {}).items():
                if color:
                    overrides[f"--agent-{agent}"] = color
            if scale := theme.get("fontScale"):
                overrides["--font-scale"] = str(scale)

        merged = {**active_tokens, **overrides}
        lines = [f"  {k}: {v};" for k, v in merged.items()]
        return f"[data-user='{user_id}'] {{\n" + "\n".join(lines) + "\n}"
