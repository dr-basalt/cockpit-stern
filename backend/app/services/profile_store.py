from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import HumanProfile


class ProfileStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> HumanProfile:
        profile = HumanProfile(**data)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get(self, profile_id: UUID) -> HumanProfile | None:
        result = await self.db.execute(select(HumanProfile).where(HumanProfile.id == profile_id))
        return result.scalar_one_or_none()

    async def update(self, profile_id: UUID, data: dict) -> HumanProfile | None:
        profile = await self.get(profile_id)
        if not profile:
            return None
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete(self, profile_id: UUID) -> bool:
        profile = await self.get(profile_id)
        if not profile:
            return False
        await self.db.delete(profile)
        await self.db.commit()
        return True

    async def list_all(self) -> list[HumanProfile]:
        result = await self.db.execute(select(HumanProfile).order_by(HumanProfile.created_at.desc()))
        return list(result.scalars().all())
