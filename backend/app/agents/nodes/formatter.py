import logging

from langchain_core.messages import AIMessage
import litellm

from app.agents.state import AgentState
from app.services.inversion import FORMATTER_RULES

logger = logging.getLogger(__name__)

MODEL = "openrouter/google/gemini-2.0-flash-001"
FALLBACK_MODEL = "openrouter/anthropic/claude-haiku-4-5"


async def formatter_node(state: AgentState) -> dict:
    """
    Post-processing: reformats any agent output according to HD type rules.
    """
    hd_type = state.get("profile", {}).get("hd_type", "Generator")
    format_rule = FORMATTER_RULES.get(hd_type, FORMATTER_RULES["Generator"])
    active_agent = state.get("active_agent", "clone")

    last_msg = state["messages"][-1].content if state["messages"] else ""

    system_prompt = (
        f"Tu es le formateur de sortie du Cockpit Stern.\n"
        f"L'agent actif est: {active_agent}\n"
        f"Le type HD de l'utilisateur est: {hd_type}\n\n"
        f"RÈGLE DE FORMATAGE:\n{format_rule}\n\n"
        f"Reformate le message suivant selon cette règle.\n"
        f"Garde le contenu intact. Change uniquement la FORME.\n"
        f"Si le message est déjà bien formaté, retourne-le tel quel.\n"
    )

    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Message à formater:\n\n{last_msg}"},
    ]

    try:
        response = await litellm.acompletion(model=MODEL, messages=messages_for_llm, max_tokens=2048)
        content = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Formatter model failed, falling back: {e}")
        try:
            response = await litellm.acompletion(model=FALLBACK_MODEL, messages=messages_for_llm, max_tokens=2048)
            content = response.choices[0].message.content
        except Exception:
            content = last_msg  # passthrough if both fail

    return {
        "messages": [AIMessage(content=content)],
    }
