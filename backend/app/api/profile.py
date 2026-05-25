from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.profile_store import ProfileStore

router = APIRouter()


class ProfileCreate(BaseModel):
    name: str
    hd_type: str
    hd_authority: str
    hd_profile: str
    hd_definition: str
    hd_cross: str | None = None
    hd_signature: str
    hd_not_self: str
    clifton_top5: list[str]
    clifton_bottom5: list[str]
    clifton_all34: list[str] | None = None
    mantra: str
    invariants: list[str]
    energy_level: int = 5


class ProfileUpdate(BaseModel):
    name: str | None = None
    hd_type: str | None = None
    hd_authority: str | None = None
    hd_profile: str | None = None
    hd_definition: str | None = None
    hd_cross: str | None = None
    hd_signature: str | None = None
    hd_not_self: str | None = None
    clifton_top5: list[str] | None = None
    clifton_bottom5: list[str] | None = None
    clifton_all34: list[str] | None = None
    mantra: str | None = None
    invariants: list[str] | None = None
    energy_level: int | None = None


class ProfileResponse(BaseModel):
    id: UUID
    name: str
    hd_type: str
    hd_authority: str
    hd_profile: str
    hd_definition: str
    hd_cross: str | None
    hd_signature: str
    hd_not_self: str
    clifton_top5: list[str]
    clifton_bottom5: list[str]
    mantra: str
    invariants: list[str]
    energy_level: int
    dominant_domain: str
    clone_persona: dict
    anti_persona: dict

    model_config = {"from_attributes": True}


@router.post("/profile", response_model=ProfileResponse)
async def create_profile(data: ProfileCreate, db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    profile = await store.create(data.model_dump(exclude_none=True))
    return ProfileResponse.model_validate(profile)


@router.get("/profile/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: UUID, db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    profile = await store.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.put("/profile/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: UUID, data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    profile = await store.update(profile_id, data.model_dump(exclude_none=True))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.delete("/profile/{profile_id}")
async def delete_profile(profile_id: UUID, db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    deleted = await store.delete(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "deleted"}


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    profiles = await store.list_all()
    return [ProfileResponse.model_validate(p) for p in profiles]
