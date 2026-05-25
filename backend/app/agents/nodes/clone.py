import logging

from langchain_core.messages import AIMessage
import litellm

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

MODEL = "together/deepseek-v3"
FALLBACK_MODEL = "anthropic/claude-haiku-4-5"


async def clone_node(state: AgentState) -> dict:
    """
    Clone — ST-dominant producer. Always proposes 3 options max.
    """
    config = state.get("inversion_config", {})
    system_prompt = config.get("clone_system_prompt", "Tu es un assistant productif.")
    context = state.get("context", "")

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
        logger.warning(f"Clone model failed ({MODEL}), falling back: {e}")
        try:
            response = await litellm.acompletion(model=FALLBACK_MODEL, messages=messages_for_llm, max_tokens=2048)
            content = response.choices[0].message.content
        except Exception as e2:
            logger.error(f"Clone fallback also failed: {e2}")
            content = "Je n'ai pas pu générer de réponse. Réessaie dans un instant."

    return {
        "messages": [AIMessage(content=content)],
        "active_agent": "clone",
    }
