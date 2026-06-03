import json
import logging

from langchain_core.messages import AIMessage
import litellm

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

MODEL = "openrouter/deepseek/deepseek-chat-v3-0324"
FALLBACK_MODEL = "openrouter/anthropic/claude-haiku-4-5"

# Intent patterns that trigger MCP tool calls or skills
MCP_INTENTS = {
    "morning_brief": {
        "patterns": ["briefing", "brief du jour", "briefing du jour", "morning brief", "mon planning", "ma journée", "qu'est-ce que j'ai aujourd'hui"],
        "skill": "morning_brief",
    },
    "read_calendar": {
        "patterns": ["agenda", "calendrier", "mes events", "mes rendez-vous", "mes rdv", "lis mon agenda", "mon emploi du temps", "cette semaine"],
        "tool": "google-calendar",
        "tool_name": "list_events",
        "params_builder": "_build_calendar_params",
    },
    "read_emails": {
        "patterns": ["emails", "mails", "mes emails", "courrier", "inbox", "non lus", "derniers mails"],
        "tool": "gmail",
        "tool_name": "list_emails",
        "params": {"max_results": 5, "query": "is:unread"},
    },
    "read_drive": {
        "patterns": ["mes fichiers", "google drive", "drive", "documents récents"],
        "tool": "google-drive",
        "tool_name": "list_files",
        "params": {"max_results": 5},
    },
}


def _detect_mcp_intent(message: str) -> dict | None:
    """Detect if user message matches an MCP intent."""
    msg_lower = message.lower()
    for intent_key, intent in MCP_INTENTS.items():
        if any(p in msg_lower for p in intent["patterns"]):
            return {**intent, "intent_key": intent_key}
    return None


def _build_calendar_params() -> dict:
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=2)))
    return {
        "calendar_id": "primary",
        "time_min": now.replace(hour=0, minute=0, second=0).isoformat(),
        "time_max": (now + timedelta(days=7)).replace(hour=0, minute=0, second=0).isoformat(),
        "max_results": 20,
    }


async def clone_node(state: AgentState) -> dict:
    """
    Clone — ST-dominant producer with MCP tools.
    1. Detect MCP intent in user message
    2. If skill → run skill (e.g. morning_brief)
    3. If tool → call MCP tool + LLM synthesize result
    4. Else → standard LLM response
    """
    config = state.get("inversion_config", {})
    system_prompt = config.get("clone_system_prompt", "Tu es un assistant productif.")
    context = state.get("context", "")
    last_message = state["messages"][-1].content if state["messages"] else ""

    # Step 1: Check for MCP intent
    intent = _detect_mcp_intent(last_message)

    if intent:
        # Step 2: Skill execution
        if "skill" in intent:
            from app.services.skills import SKILL_REGISTRY
            skill = SKILL_REGISTRY.get(intent["skill"])
            if skill:
                try:
                    result = await skill["fn"]()
                    content = result.get("brief", json.dumps(result, ensure_ascii=False, indent=2))
                    return {"messages": [AIMessage(content=content)], "active_agent": "clone"}
                except Exception as e:
                    logger.warning(f"Skill {intent['skill']} failed: {e}")

        # Step 3: Direct MCP tool call
        elif "tool" in intent:
            from app.services.mcp_client import MCPClient
            mcp = MCPClient()
            params = intent.get("params", {})
            if intent.get("params_builder") == "_build_calendar_params":
                params = _build_calendar_params()

            result = await mcp.call(intent["tool"], intent["tool_name"], params)

            if result.get("needs_auth"):
                content = f"⚠️ {intent['tool']} n'est pas connecté. Connecte-le depuis la sidebar (bouton +) puis réessaie."
                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

            if result.get("status") == "ok":
                raw = result.get("result", {}).get("content", [{}])
                raw_text = raw[0].get("text", "") if raw else json.dumps(result.get("result", {}))

                # LLM synthesizes the raw MCP data
                synth_messages = [
                    {"role": "system", "content": f"{system_prompt}\n\nTu reçois des données brutes d'un outil ({intent['tool']}). Synthétise-les en français, de façon claire et actionnable. Sois concis."},
                    {"role": "user", "content": f"Question originale : {last_message}\n\nDonnées brutes :\n{raw_text[:3000]}"},
                ]
                try:
                    response = await litellm.acompletion(model=MODEL, messages=synth_messages, max_tokens=1024)
                    content = response.choices[0].message.content
                except Exception:
                    content = raw_text[:2000]

                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}
            else:
                content = f"Erreur MCP ({intent['tool']}): {result.get('error', result.get('detail', '?'))}"
                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

    # Step 4: Standard LLM response (no MCP intent detected)
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
