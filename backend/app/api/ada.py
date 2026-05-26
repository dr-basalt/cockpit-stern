import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.spawner import SubAgentSpawner, SubAgentTemplate, SpawnedAgent
from app.services.mcp_client import MCPClient, AGENT_TOOL_PERMISSIONS
from app.agents.nodes.conformance import ConformanceAgent
from app.services.profile_store import ProfileStore

logger = logging.getLogger(__name__)
router = APIRouter()

spawner = SubAgentSpawner()
mcp = MCPClient()
conformance = ConformanceAgent()


# --- DISCOVERY ---

@router.get("/agents")
async def list_agents():
    agents = spawner.list_agents()
    return [{"id": a.id, "role": a.role, "profession": a.profession, "status": a.status,
             "okr_id": a.okr_id, "execution_mode": a.execution_mode, "model_tier": a.model_tier}
            for a in agents]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = spawner.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"id": agent.id, "role": agent.role, "profession": agent.profession,
            "system_prompt": agent.system_prompt, "tools": agent.tools,
            "okr_id": agent.okr_id, "execution_mode": agent.execution_mode,
            "model_tier": agent.model_tier, "status": agent.status, "created_at": agent.created_at}


@router.get("/agents/{agent_id}/skills")
async def get_agent_skills(agent_id: str):
    agent = spawner.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    tools = await mcp.discover_tools("", agent.role)
    perms = AGENT_TOOL_PERMISSIONS.get(agent.role, AGENT_TOOL_PERMISSIONS.get("clone", {}))
    return {"agent_id": agent_id, "access": perms.get("access"), "tools": tools}


@router.get("/tools")
async def list_tools():
    tools = await mcp.discover_tools("")
    return {"tools": tools}


# --- SCRUDX AGENTS ---

class SpawnRequest(BaseModel):
    profile_id: UUID
    role: str
    profession: str
    ddd_context: str = "general"
    tools: list[str] = []
    okr_parent_id: str = ""
    execution_mode: str = "mitl"
    model_tier: str = "pro"


@router.post("/agents/spawn")
async def spawn_agent(req: SpawnRequest, db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    profile = await store.get(req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    template = SubAgentTemplate(
        role=req.role, profession=req.profession, ddd_context=req.ddd_context,
        tools=req.tools, okr_parent_id=req.okr_parent_id,
        execution_mode=req.execution_mode, model_tier=req.model_tier,
    )
    agent = await spawner.spawn(template, profile)
    return {"id": agent.id, "role": agent.role, "status": agent.status}


class TaskRequest(BaseModel):
    task: str
    mode: str = "mitl"
    dry_run: bool = False
    okr_check: bool = True


@router.post("/agents/{agent_id}/task")
async def agent_task(agent_id: str, req: TaskRequest):
    agent = spawner.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent_id,
        "task": req.task,
        "mode": req.mode,
        "dry_run": req.dry_run,
        "status": "queued",
        "message": f"Task queued for {agent.role} in {req.mode} mode",
    }


@router.post("/agents/{agent_id}/dryrun")
async def agent_dryrun(agent_id: str, req: TaskRequest):
    agent = spawner.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    diff = await mcp._dry_run(agent.tools[0] if agent.tools else "unknown", {"task": req.task}, None)
    return {"agent_id": agent_id, "diff": diff}


# --- CONFORMANCE ---

@router.get("/conformance")
async def get_conformance():
    report = await conformance.run_full_check()
    return {
        "surface": report.surface, "structure": report.structure,
        "substance": report.substance, "overall": report.overall,
        "issues": report.issues, "timestamp": report.timestamp.isoformat(),
    }


@router.post("/conformance/check")
async def check_conformance(profile_id: UUID | None = None):
    report = await conformance.run_full_check(profile_id)
    return {
        "surface": report.surface, "structure": report.structure,
        "substance": report.substance, "overall": report.overall,
        "issues_count": len(report.issues), "issues": report.issues,
    }


@router.post("/conformance/fix")
async def fix_conformance(profile_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    report = await conformance.run_full_check(profile_id)
    fixed = await conformance.fix_issues(report)
    return {"fixed": fixed, "remaining": len(report.issues) - fixed}


# --- OKR ---

@router.get("/okr")
async def list_okrs(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.okr import OKR
    result = await db.execute(select(OKR).order_by(OKR.level, OKR.created_at))
    okrs = result.scalars().all()
    return [{"id": str(o.id), "title": o.title, "level": o.level, "status": o.status,
             "parent_id": str(o.parent_id) if o.parent_id else None,
             "alignment_score": o.alignment_score} for o in okrs]


class OKRCreate(BaseModel):
    profile_id: UUID
    title: str
    why: str
    key_results: list[str]
    parent_id: UUID | None = None
    level: int = 0


@router.post("/okr/spawn")
async def spawn_okr(req: OKRCreate, db: AsyncSession = Depends(get_db)):
    from app.models.okr import OKR
    okr = OKR(
        profile_id=req.profile_id, parent_id=req.parent_id, title=req.title,
        why=req.why, key_results=req.key_results, level=req.level,
    )
    db.add(okr)
    await db.commit()
    await db.refresh(okr)
    return {"id": str(okr.id), "title": okr.title, "level": okr.level}


@router.get("/okr/alignment/{agent_id}")
async def okr_alignment(agent_id: str):
    agent = spawner.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "okr_id": agent.okr_id, "alignment_score": 0.85}
