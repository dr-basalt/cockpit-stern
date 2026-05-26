import logging

from langchain_core.messages import AIMessage

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

HD_FOOTERS = {
    "Generator": "",  # Le Clone gère déjà le format oui/non dans son output
    "Manifesting Generator": "",
    "Projector": "",
    "Manifestor": "",
    "Reflector": "",
}


async def formatter_node(state: AgentState) -> dict:
    """
    Post-processing léger — PAS de réécriture LLM.
    Ajoute un footer adapté au HD type si l'agent actif est clone ou anti.
    Le contenu original est TOUJOURS préservé intact.
    """
    hd_type = state.get("profile", {}).get("hd_type", "Generator")
    active_agent = state.get("active_agent", "clone")
    last_msg = state["messages"][-1].content if state["messages"] else ""

    # SP et real : pas de footer, le message est déjà adapté à l'autorité
    if active_agent in ("sp", "real"):
        return {"messages": [AIMessage(content=last_msg)]}

    # Clone et anti : ajoute un footer HD type (pas de réécriture)
    footer = HD_FOOTERS.get(hd_type, "")
    content = last_msg + footer

    return {"messages": [AIMessage(content=content)]}
