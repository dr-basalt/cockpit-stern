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
Aujourd'hui : {today} (timezone Europe/Paris, +02:00)

ÉTAPE 1 — CLASSIFIER l'intention de l'utilisateur.
Réponds en JSON selon le type :

TYPE "chat" — conversation, question de culture, réflexion :
{{"type": "chat"}}

TYPE "action" — 1 seul outil suffit :
{{"type": "action", "tool_call": {{"server": "nom", "tool": "nom_tool", "params": {{...}}}}}}

TYPE "skill" — composition connue :
{{"type": "skill", "skill_call": "nom_du_skill"}}

TYPE "plan" — demande complexe nécessitant PLUSIEURS outils en séquence :
{{"type": "plan", "goal": "le but final en 1 phrase", "steps": [
  {{"step": 1, "description": "ce que fait cette étape", "server": "nom", "tool": "nom_tool", "params": {{...}}, "depends_on": []}},
  {{"step": 2, "description": "...", "server": "nom", "tool": "nom_tool", "params": {{...}}, "depends_on": [1]}},
  ...
]}}

RÈGLES DE DÉCOMPOSITION (pour type "plan") :
- Identifier le BUT (backward chaining : que veut l'user ?)
- Décomposer en étapes ATOMIQUES (1 tool call par step)
- Ordonner par DÉPENDANCE (RCE : exécuter les feuilles d'abord)
- Chaque step qui dépend du résultat d'un step précédent → depends_on: [N]
- Les steps sans dépendance PEUVENT s'exécuter en parallèle
- Privilégier le CHEMIN LE PLUS COURT (efficience)
- Ne pas inventer de tools qui n'existent pas dans le catalog

Réponds UNIQUEMENT en JSON. Pas de texte avant ou après.

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

    # Also try to find JSON embedded in text
    if "{" in json_str and "tool_call" in json_str:
        start = json_str.index("{")
        # Find matching closing brace
        depth = 0
        for i in range(start, len(json_str)):
            if json_str[i] == "{":
                depth += 1
            elif json_str[i] == "}":
                depth -= 1
                if depth == 0:
                    json_str = json_str[start:i + 1]
                    break
    elif "{" in json_str and "skill_call" in json_str:
        start = json_str.index("{")
        depth = 0
        for i in range(start, len(json_str)):
            if json_str[i] == "{":
                depth += 1
            elif json_str[i] == "}":
                depth -= 1
                if depth == 0:
                    json_str = json_str[start:i + 1]
                    break

    try:
        parsed = json.loads(json_str.strip())
        intent_type = parsed.get("type", "")

        # Chat — no tool needed, ask LLM for a normal response
        if intent_type == "chat":
            raise json.JSONDecodeError("chat", "", 0)  # fall through to text response below

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

        # Plan — multi-step pipeline execution
        if intent_type == "plan" and "steps" in parsed:
            mcp = MCPClient()
            step_results = {}
            steps = parsed["steps"]
            goal = parsed.get("goal", "")

            for step in sorted(steps, key=lambda s: s.get("step", 0)):
                step_num = step.get("step", 0)
                deps = step.get("depends_on", [])

                # Inject results from dependencies into params
                params = step.get("params", {})
                for dep in deps:
                    if dep in step_results and isinstance(step_results[dep], str):
                        params["_context_from_step_" + str(dep)] = step_results[dep][:500]

                result = await mcp.call(
                    step.get("server", ""),
                    step.get("tool", ""),
                    params,
                )

                if result.get("status") == "ok":
                    raw = result.get("result", {}).get("content", [{}])
                    step_results[step_num] = raw[0].get("text", "") if raw else json.dumps(result.get("result", {}))
                elif result.get("needs_auth"):
                    step_results[step_num] = f"[{step.get('server')} non connecté]"
                else:
                    step_results[step_num] = f"[Erreur: {result.get('error', '?')}]"

            # Synthesize all step results
            all_results = "\n\n".join(
                f"## Étape {k} — {steps[k-1].get('description', '')}\n{v[:800]}"
                for k, v in sorted(step_results.items())
            )

            synth_messages = [
                {"role": "system", "content": f"Tu es le Clone. L'utilisateur a demandé : \"{last_message}\"\nBut identifié : {goal}\n\nTu as exécuté un plan en {len(steps)} étapes. Synthétise les résultats en une réponse claire, actionnable et concise en français. Aujourd'hui: {now.strftime('%A %d %B %Y')}."},
                {"role": "user", "content": all_results[:4000]},
            ]
            try:
                r2 = await litellm.acompletion(model=MODEL, messages=synth_messages, max_tokens=1024)
                content = r2.choices[0].message.content
            except Exception:
                content = all_results[:2000]

            return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # Not JSON or chat type → text response

    # Step 3: Text response (LLM decided no tool was needed, or type=chat)
    # Re-ask LLM without the tool catalog for a clean conversational response
    chat_messages = [{"role": "system", "content": user_system_prompt or "Tu es un assistant productif bienveillant. Réponds en français."}]
    if context:
        chat_messages.append({"role": "system", "content": f"Contexte mémoire:\n{context}"})
    for msg in state["messages"]:
        role = "user" if msg.type == "human" else "assistant"
        chat_messages.append({"role": role, "content": msg.content})

    try:
        response = await litellm.acompletion(model=MODEL, messages=chat_messages, max_tokens=2048)
        content = response.choices[0].message.content
    except Exception:
        try:
            response = await litellm.acompletion(model=FALLBACK_MODEL, messages=chat_messages, max_tokens=2048)
            content = response.choices[0].message.content
        except Exception:
            content = "Erreur de connexion. Réessaie."

    return {
        "messages": [AIMessage(content=content)],
        "active_agent": "clone",
    }
