import json
import logging
from datetime import datetime, timezone, timedelta

from langchain_core.messages import AIMessage
import litellm

from app.agents.state import AgentState
from app.services.mcp_client import MCPClient, OBOT_MCP_SERVERS
from app.services.skills import SKILL_REGISTRY

logger = logging.getLogger(__name__)

MODEL = "openrouter/deepseek/deepseek-chat-v3-0324"
FALLBACK_MODEL = "openrouter/anthropic/claude-haiku-4-5"

# Cached tool catalog — loaded once, refreshed on demand
_tool_catalog_cache: dict | None = None


async def _get_tool_catalog() -> str:
    """Build a text description of all available MCP tools for the LLM.

    This is the GENERIC approach: the LLM sees ALL tools and decides.
    No hardcoded intents. POEO × POAIG.
    """
    global _tool_catalog_cache
    if _tool_catalog_cache:
        return _tool_catalog_cache

    mcp = MCPClient()
    lines = []
    lines.append("OUTILS DISPONIBLES (MCP servers connectés) :")
    lines.append("")

    for key, info in OBOT_MCP_SERVERS.items():
        tools = await mcp.list_server_tools(info["catalog_id"])
        if not tools:
            continue
        lines.append(f"## {info['name']} (server: {key})")
        for t in tools:
            params_str = ", ".join(f"{k}: {v}" for k, v in t.get("params", {}).items())
            lines.append(f"  - {t['name']}({params_str}) — {t.get('description', '')[:80]}")
        lines.append("")

    lines.append("## Skills composites")
    for name, skill in SKILL_REGISTRY.items():
        lines.append(f"  - SKILL:{name} — {skill['description']}")

    catalog = "\n".join(lines)
    _tool_catalog_cache = catalog
    return catalog


ROUTER_SYSTEM = """Tu es le Clone, agent productif du cockpit Stern OS.
Ton utilisateur est un solopreneur Generator 4/1 (Human Design).

Tu as accès à des OUTILS (MCP tools) et des SKILLS (compositions d'outils).
Quand l'utilisateur demande quelque chose que tu peux résoudre avec un outil,
tu dois répondre en JSON avec l'appel d'outil.

RÈGLES :
- Si la demande peut être résolue par un outil → appelle l'outil
- Si la demande nécessite plusieurs outils → appelle SKILL:morning_brief ou enchaîne
- Si la demande est une conversation normale → réponds normalement (pas de JSON)
- Aujourd'hui : {today} (timezone Europe/Paris, +02:00)

FORMAT D'APPEL D'OUTIL — réponds UNIQUEMENT ce JSON si tu veux appeler un outil :
{{"tool_call": {{"server": "nom-du-server", "tool": "nom_du_tool", "params": {{...}}}}}}

FORMAT D'APPEL DE SKILL :
{{"skill_call": "nom_du_skill"}}

Si tu ne veux PAS appeler d'outil, réponds normalement en texte libre.
Ne mets JAMAIS de JSON dans une réponse texte libre.

{tool_catalog}"""


async def clone_node(state: AgentState) -> dict:
    """Clone — POAIG: l'IA décide quels outils appeler.

    Pas d'intents hardcodés. Le LLM voit le catalog de tools
    et décide s'il doit appeler un outil ou répondre normalement.
    La structure émerge (POEO), l'IA est l'agent (POAIG).
    """
    config = state.get("inversion_config", {})
    user_system_prompt = config.get("clone_system_prompt", "")
    context = state.get("context", "")
    last_message = state["messages"][-1].content if state["messages"] else ""
    now = datetime.now(timezone(timedelta(hours=2)))

    # Build tool catalog (cached after first call)
    tool_catalog = await _get_tool_catalog()

    # Step 1: Ask LLM — tool call or text response?
    router_prompt = ROUTER_SYSTEM.format(
        today=now.strftime("%A %d %B %Y, %Hh%M"),
        tool_catalog=tool_catalog,
    )

    messages_for_router = [{"role": "system", "content": router_prompt}]
    if user_system_prompt:
        messages_for_router.append({"role": "system", "content": f"Personnalité:\n{user_system_prompt}"})
    if context:
        messages_for_router.append({"role": "system", "content": f"Contexte mémoire:\n{context}"})
    for msg in state["messages"]:
        role = "user" if msg.type == "human" else "assistant"
        messages_for_router.append({"role": role, "content": msg.content})

    try:
        response = await litellm.acompletion(model=MODEL, messages=messages_for_router, max_tokens=2048)
        raw_content = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Clone router failed ({MODEL}), fallback: {e}")
        try:
            response = await litellm.acompletion(model=FALLBACK_MODEL, messages=messages_for_router, max_tokens=2048)
            raw_content = response.choices[0].message.content
        except Exception as e2:
            logger.error(f"Clone fallback also failed: {e2}")
            return {"messages": [AIMessage(content="Erreur de connexion. Réessaie.")], "active_agent": "clone"}

    # Step 2: Parse — is it a tool call or a text response?
    stripped = raw_content.strip()

    # Try to extract JSON (might be wrapped in markdown)
    json_str = stripped
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str and "{" in json_str:
        json_str = json_str.split("```")[1].split("```")[0]

    try:
        parsed = json.loads(json_str.strip())

        # Skill call
        if "skill_call" in parsed:
            skill_name = parsed["skill_call"]
            skill = SKILL_REGISTRY.get(skill_name)
            if skill:
                result = await skill["fn"]()
                content = result.get("brief", json.dumps(result, ensure_ascii=False, indent=2))
                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

        # Tool call
        if "tool_call" in parsed:
            tc = parsed["tool_call"]
            server = tc.get("server", "")
            tool_name = tc.get("tool", "")
            params = tc.get("params", {})

            mcp = MCPClient()
            result = await mcp.call(server, tool_name, params)

            if result.get("needs_auth"):
                content = f"⚠️ **{server}** n'est pas connecté. Connecte-le depuis la sidebar (bouton +) puis réessaie."
                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

            if result.get("status") == "ok":
                raw = result.get("result", {}).get("content", [{}])
                raw_text = raw[0].get("text", "") if raw else json.dumps(result.get("result", {}), ensure_ascii=False)

                # Synthesize
                synth_messages = [
                    {"role": "system", "content": f"Tu es le Clone, agent productif. Synthétise ces données en français, de façon claire et actionnable. Sois concis. Aujourd'hui: {now.strftime('%A %d %B %Y')}."},
                    {"role": "user", "content": f"Question: {last_message}\n\nDonnées brutes ({server}.{tool_name}):\n{raw_text[:3000]}"},
                ]
                try:
                    r2 = await litellm.acompletion(model=MODEL, messages=synth_messages, max_tokens=1024)
                    content = r2.choices[0].message.content
                except Exception:
                    content = raw_text[:2000]
                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}
            else:
                content = f"Erreur {server}.{tool_name}: {result.get('error', '?')}"
                return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # Not JSON → it's a text response, use as-is

    # Step 3: Text response (LLM decided no tool was needed)
    return {
        "messages": [AIMessage(content=raw_content)],
        "active_agent": "clone",
    }
