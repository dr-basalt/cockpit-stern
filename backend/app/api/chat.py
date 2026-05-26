import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from app.core.database import get_db, async_session
from app.agents.graph import build_graph
from app.services.inversion import InversionRulesEngine
from app.services.memory import MemoryService
from app.services.profile_store import ProfileStore

logger = logging.getLogger(__name__)
router = APIRouter()

graph = build_graph()
memory_service = MemoryService()
inversion_engine = InversionRulesEngine()


class ChatRequest(BaseModel):
    session_id: str
    profile_id: UUID
    message: str
    energy_level: int | None = None


class ChatResponse(BaseModel):
    session_id: str
    active_agent: str
    message: str
    requires_hitl: bool = False
    hitl_token: str | None = None
    not_self_detected: bool = False
    task_type: str = "production"
    energy_mode: str = "balance"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    store = ProfileStore(db)
    profile = await store.get(request.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Override energy if provided
    energy = request.energy_level or profile.energy_level

    # Build inversion config
    profile.energy_level = energy
    config = inversion_engine.build(profile)

    # Get memory context
    context = await memory_service.get_context(request.profile_id, request.message)

    # Build state
    state = {
        "messages": [HumanMessage(content=request.message)],
        "profile": {
            "hd_type": profile.hd_type,
            "hd_authority": profile.hd_authority,
            "hd_profile": profile.hd_profile,
            "hd_definition": profile.hd_definition,
            "hd_signature": profile.hd_signature,
            "hd_not_self": profile.hd_not_self,
            "clifton_top5": profile.clifton_top5,
            "clifton_bottom5": profile.clifton_bottom5,
            "invariants": profile.invariants,
            "name": profile.name,
        },
        "inversion_config": {
            "clone_system_prompt": config.clone_system_prompt,
            "anti_system_prompt": config.anti_system_prompt,
            "sp_system_prompt": config.sp_system_prompt,
            "formatter_rules": config.formatter_rules,
            "routing_keywords": config.routing_keywords,
            "energy_mode": config.energy_mode,
        },
        "energy_level": energy,
        "task_type": "production",
        "active_agent": "sp",
        "requires_hitl": False,
        "hitl_token": None,
        "not_self_detected": False,
        "session_id": request.session_id,
        "context": context,
    }

    # Run graph
    result = await graph.ainvoke(state)

    # Store interaction
    await memory_service.store_interaction(request.profile_id, {
        "role": "user",
        "content": request.message,
        "agent": result.get("active_agent", "sp"),
        "session_id": request.session_id,
    })

    last_message = result["messages"][-1].content if result["messages"] else ""

    await memory_service.store_interaction(request.profile_id, {
        "role": "assistant",
        "content": last_message,
        "agent": result.get("active_agent", "sp"),
        "session_id": request.session_id,
    })

    return ChatResponse(
        session_id=request.session_id,
        active_agent=result.get("active_agent", "sp"),
        message=last_message,
        requires_hitl=result.get("requires_hitl", False),
        hitl_token=result.get("hitl_token"),
        not_self_detected=result.get("not_self_detected", False),
        task_type=result.get("task_type", "production"),
        energy_mode=config.energy_mode,
    )


async def _build_graph_state(profile, message: str, session_id: str, energy: int | None = None) -> tuple[dict, object]:
    """Shared state builder for both REST and WebSocket."""
    e = energy or profile.energy_level
    profile.energy_level = e
    config = inversion_engine.build(profile)
    context = await memory_service.get_context(profile.id, message)

    state = {
        "messages": [HumanMessage(content=message)],
        "profile": {
            "hd_type": profile.hd_type,
            "hd_authority": profile.hd_authority,
            "hd_profile": profile.hd_profile,
            "hd_definition": profile.hd_definition,
            "hd_signature": profile.hd_signature,
            "hd_not_self": profile.hd_not_self,
            "clifton_top5": profile.clifton_top5,
            "clifton_bottom5": profile.clifton_bottom5,
            "invariants": profile.invariants,
            "name": profile.name,
        },
        "inversion_config": {
            "clone_system_prompt": config.clone_system_prompt,
            "anti_system_prompt": config.anti_system_prompt,
            "sp_system_prompt": config.sp_system_prompt,
            "formatter_rules": config.formatter_rules,
            "routing_keywords": config.routing_keywords,
            "energy_mode": config.energy_mode,
        },
        "energy_level": e,
        "task_type": "production",
        "active_agent": "sp",
        "requires_hitl": False,
        "hitl_token": None,
        "not_self_detected": False,
        "session_id": session_id,
        "context": context,
    }
    return state, config


@router.websocket("/chat/stream")
async def chat_stream(ws: WebSocket):
    """
    WebSocket streaming endpoint.
    Client sends JSON: {"session_id", "profile_id", "message", "energy_level"?}
    Server streams JSON events:
      {"type": "agent", "agent": "sp|clone|anti|real"}
      {"type": "chunk", "content": "...", "agent": "..."}
      {"type": "meta", "task_type": "...", "energy_mode": "...", "not_self_detected": bool, "requires_hitl": bool, "hitl_token": str|null}
      {"type": "done"}
      {"type": "error", "detail": "..."}
    """
    await ws.accept()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            profile_id = data.get("profile_id")
            message = data.get("message", "")
            session_id = data.get("session_id", "ws-default")
            energy_level = data.get("energy_level")

            if not profile_id or not message:
                await ws.send_json({"type": "error", "detail": "profile_id and message required"})
                continue

            # Load profile
            async with async_session() as db:
                store = ProfileStore(db)
                profile = await store.get(UUID(profile_id))
                if not profile:
                    await ws.send_json({"type": "error", "detail": "Profile not found"})
                    continue

                state, config = await _build_graph_state(profile, message, session_id, energy_level)

            # Stream graph execution — collect all, send only final
            last_agent = "sp"
            last_content = ""

            async for event in graph.astream(state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    agent = node_output.get("active_agent")
                    if agent:
                        last_agent = agent

                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        last_content = msg.content if hasattr(msg, "content") else str(msg)

            # Send the routed agent + final formatted message
            await ws.send_json({"type": "agent", "agent": last_agent})
            if last_content:
                await ws.send_json({"type": "chunk", "content": last_content, "agent": last_agent})

            # Send metadata
            await ws.send_json({
                "type": "meta",
                "task_type": state.get("task_type", "production"),
                "energy_mode": config.energy_mode,
                "not_self_detected": state.get("not_self_detected", False),
                "requires_hitl": state.get("requires_hitl", False),
                "hitl_token": state.get("hitl_token"),
            })

            # Store interactions
            await memory_service.store_interaction(UUID(profile_id), {
                "role": "user", "content": message, "agent": last_agent, "session_id": session_id,
            })
            if last_content:
                await memory_service.store_interaction(UUID(profile_id), {
                    "role": "assistant", "content": last_content, "agent": last_agent, "session_id": session_id,
                })

            await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await ws.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
