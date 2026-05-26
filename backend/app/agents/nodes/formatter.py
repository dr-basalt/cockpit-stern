import logging

from langchain_core.messages import AIMessage

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

HD_FOOTERS = {
    "Generator": "\n\n---\n_Ton sacral répond à quoi ? Oui ou Non._",
    "Manifesting Generator": "\n\n---\n_Tu peux avancer sur plusieurs en parallèle. Qu'est-ce qui t'attire ?_",
    "Projector": "\n\n---\n_Si tu étais invité à choisir, laquelle te reconnaît le plus ?_",
    "Manifestor": "",  # Pas de question — le Manifestor initie seul
    "Reflector": "\n\n---\n_Laisse cette idée reposer. Dans quelques jours, est-ce que ça résonne encore ?_",
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
