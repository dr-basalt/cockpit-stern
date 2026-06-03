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
        "patterns": ["agenda", "calendrier", "mes events", "mes rendez-vous", "mes rdv", "lis mon agenda", "mon emploi du temps", "cette semaine", "demain", "jeudi", "lundi", "qu'est-ce que j'ai"],
        "tool": "google-calendar",
        "tool_name": "list_events",
        "params_from_llm": True,
    },
    "read_emails": {
        "patterns": ["emails", "mails", "mes emails", "courrier", "inbox", "non lus", "derniers mails", "filtre", "cherche dans mes mails", "mail de"],
        "tool": "gmail",
        "tool_name": "list_emails",
        "params_from_llm": True,
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


GMAIL_PARAMS_PROMPT = """Tu reçois une question utilisateur concernant ses emails.
Génère les paramètres pour l'API Gmail list_emails.

Paramètres disponibles :
- query (string) : filtre Gmail (syntaxe Gmail search). Exemples :
  "is:unread" — non lus
  "from:jean@example.com" — emails de Jean
  "subject:facture" — sujet contient facture
  "after:2026/06/01 before:2026/06/04" — période
  "has:attachment" — avec pièces jointes
  "is:starred" — favoris
  "label:important" — importants
  Tu peux combiner : "from:google is:unread after:2026/06/01"
- max_results (int) : nombre max de résultats (défaut: 10)

Réponds UNIQUEMENT en JSON valide, rien d'autre :
{"query": "...", "max_results": 10}"""

CALENDAR_PARAMS_PROMPT = """Tu reçois une question utilisateur concernant son agenda.
Génère les paramètres pour l'API Google Calendar list_events.

Paramètres disponibles :
- calendar_id (string) : "primary" par défaut
- time_min (string) : date/heure début au format RFC3339 (ex: "2026-06-03T00:00:00+02:00")
- time_max (string) : date/heure fin au format RFC3339
- max_results (int) : nombre max (défaut: 20)
- q (string) : recherche texte dans les events

Aujourd'hui nous sommes le {today}. Timezone: Europe/Paris (+02:00).

Réponds UNIQUEMENT en JSON valide, rien d'autre :
{{"calendar_id": "primary", "time_min": "...", "time_max": "...", "max_results": 20}}"""


async def _build_params_from_llm(tool: str, tool_name: str, user_message: str) -> dict:
    """Use LLM to generate tool params from natural language."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=2)))

    if tool == "gmail":
        system = GMAIL_PARAMS_PROMPT
    elif tool == "google-calendar":
        system = CALENDAR_PARAMS_PROMPT.format(today=now.strftime("%A %d %B %Y"))
    else:
        return {}

    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        # Extract JSON from potential markdown wrapper
        if "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        logger.warning(f"LLM param generation failed: {e}")
        # Fallback defaults
        if tool == "gmail":
            return {"query": "is:unread", "max_results": 10}
        elif tool == "google-calendar":
            return _build_calendar_params()
        return {}


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
            elif intent.get("params_from_llm"):
                params = await _build_params_from_llm(intent["tool"], intent["tool_name"], last_message)

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
