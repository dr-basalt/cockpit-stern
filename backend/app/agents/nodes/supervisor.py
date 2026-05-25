import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


async def supervisor_node(state: AgentState) -> dict:
    """
    Profile-aware router. Decides which agent handles the request.
    Returns the active_agent field for conditional edge routing.
    """
    task_type = state.get("task_type", "production")
    requires_hitl = state.get("requires_hitl", False)

    if requires_hitl:
        logger.info("Supervisor → HITL (real)")
        return {"active_agent": "real"}

    route_map = {
        "production": "clone",
        "challenge": "anti",
        "sacral_stimulus": "sp",
        "flow": "sp",
        "irreversible_decision": "real",
    }

    agent = route_map.get(task_type, "clone")
    logger.info(f"Supervisor → {agent} (task_type={task_type})")
    return {"active_agent": agent}
