from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.memory import MemoryService

router = APIRouter()
memory_service = MemoryService()


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
