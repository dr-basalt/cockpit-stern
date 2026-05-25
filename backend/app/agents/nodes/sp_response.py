import logging

from langchain_core.messages import AIMessage
import litellm

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

MODEL = "together/deepseek-v3"
FALLBACK_MODEL = "anthropic/claude-haiku-4-5"


async def sp_response_node(state: AgentState) -> dict:
    """
    SP direct response — sacral stimulus or flow state.
    Never prescribes. Generates questions or options only.
    """
    config = state.get("inversion_config", {})
    system_prompt = config.get("sp_system_prompt", "Tu es un sparring partner bienveillant.")
    context = state.get("context", "")
    not_self = state.get("not_self_detected", False)

    if not_self:
        not_self_signal = state.get("profile", {}).get("hd_not_self", "Frustration")
        system_prompt += (
            f"\n\n⚠️ ALERTE NOT-SELF DÉTECTÉE: {not_self_signal}\n"
            f"L'utilisateur montre des signes de {not_self_signal}.\n"
            f"Priorité absolue: reconnaître ce signal, ralentir, recentrer sur l'autorité.\n"
        )

    messages_for_llm = [{"role": "system", "content": system_prompt}]

    if context:
        messages_for_llm.append({"role": "system", "content": f"Contexte mémoire:\n{context}"})

    for msg in state["messages"]:
        role = "user" if msg.type == "human" else "assistant"
        messages_for_llm.append({"role": role, "content": msg.content})

    try:
        response = await litellm.acompletion(model=MODEL, messages=messages_for_llm, max_tokens=2048)
        content = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"SP model failed, falling back: {e}")
        try:
            response = await litellm.acompletion(model=FALLBACK_MODEL, messages=messages_for_llm, max_tokens=2048)
            content = response.choices[0].message.content
        except Exception:
            content = "Je suis là. Prends un instant. Qu'est-ce que tu ressens maintenant?"

    return {
        "messages": [AIMessage(content=content)],
        "active_agent": "sp",
    }
