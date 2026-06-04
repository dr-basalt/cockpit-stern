import json
import logging
from datetime import datetime, timezone, timedelta

from langchain_core.messages import AIMessage
import httpx
import litellm

from app.agents.state import AgentState
from app.services.mcp_client import MCPClient, OBOT_MCP_SERVERS
from app.services.skills import SKILL_REGISTRY

logger = logging.getLogger(__name__)

MODEL_FAST = "openrouter/anthropic/claude-haiku-4-5"  # Fast path: chat conversationnel (~1-2s)
MODEL_TOOL = "openrouter/deepseek/deepseek-chat-v3-0324"  # Tool path: classification + synthesis (meilleur JSON)
MODEL_FALLBACK = "openrouter/anthropic/claude-haiku-4-5"

# Cached tool catalog — loaded once per process, with TTL
_tool_catalog_cache: str | None = None
_tool_catalog_ts: float = 0
CATALOG_TTL = 300  # refresh every 5 min


async def _get_tool_catalog() -> str:
    """Build a text description of all available MCP tools for the LLM.

    This is the GENERIC approach: the LLM sees ALL tools and decides.
    No hardcoded intents. POEO × POAIG.
    """
    import time
    global _tool_catalog_cache, _tool_catalog_ts
    if _tool_catalog_cache and (time.time() - _tool_catalog_ts) < CATALOG_TTL:
        return _tool_catalog_cache

    mcp = MCPClient()
    lines = []
    lines.append("OUTILS DISPONIBLES (MCP servers connectés) :")
    lines.append("")

    for key, info in OBOT_MCP_SERVERS.items():
        tools = await mcp.list_server_tools(info["catalog_id"])
        if not tools:
            continue
        lines.append(f"## {info['name']} (server: \"{key}\")")
        for t in tools:
            params = t.get("params", {})
            if params:
                params_entries = []
                for k, v in params.items():
                    params_entries.append(f'"{k}": "<{v}>"')
                params_json = "{" + ", ".join(params_entries) + "}"
            else:
                params_json = "{}"
            lines.append(f"  - tool: \"{t['name']}\", params: {params_json}")
            lines.append(f"    {t.get('description', '')[:100]}")
        lines.append("")

    lines.append("## Skills composites")
    for name, skill in SKILL_REGISTRY.items():
        lines.append(f"  - SKILL:{name} — {skill['description']}")

    catalog = "\n".join(lines)
    _tool_catalog_cache = catalog
    _tool_catalog_ts = time.time()
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


async def _generate_connect_url(tool_key: str) -> str | None:
    """Generate OAuth connect URL for a tool (dynamic client registration + PKCE)."""
    import secrets
    import hashlib
    import base64

    info = OBOT_MCP_SERVERS.get(tool_key, {})
    auth_server = info.get("auth_server")
    if not auth_server:
        return None

    callback_url = "https://api-stern-os2.ori3com.cloud/mcp/callback"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{auth_server}/.well-known/oauth-authorization-server")
            if r.status_code != 200:
                return None
            auth_meta = r.json()

            reg_endpoint = auth_meta.get("registration_endpoint")
            if not reg_endpoint:
                return None

            r2 = await client.post(reg_endpoint, json={
                "redirect_uris": [callback_url],
                "client_name": "Stern OS2",
                "token_endpoint_auth_method": "client_secret_post",
            })
            if r2.status_code not in (200, 201):
                return None
            reg = r2.json()

            code_verifier = secrets.token_urlsafe(32)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()

            state_data = f"{tool_key}:{code_verifier}"
            state = base64.urlsafe_b64encode(state_data.encode()).decode()

            scopes = " ".join(auth_meta.get("scopes_supported", ["profile"]))

            # Store pending OAuth for callback
            from app.api.session import _pending_oauth
            _pending_oauth[state] = {
                "tool_key": tool_key,
                "client_id": reg["client_id"],
                "client_secret": reg["client_secret"],
                "code_verifier": code_verifier,
                "token_endpoint": auth_meta["token_endpoint"],
                "redirect_uri": callback_url,
            }

            return (
                f"{auth_meta['authorization_endpoint']}"
                f"?response_type=code"
                f"&client_id={reg['client_id']}"
                f"&redirect_uri={callback_url}"
                f"&state={state}"
                f"&code_challenge={code_challenge}"
                f"&code_challenge_method=S256"
                f"&scope={scopes}"
            )
    except Exception as e:
        logger.warning(f"Failed to generate connect URL for {tool_key}: {e}")
        return None


# Keywords that hint at tool/data usage — if NONE present, skip catalog (fast path)
TOOL_HINTS = [
    "mail", "email", "gmail", "inbox", "courrier",
    "agenda", "calendrier", "event", "rdv", "rendez-vous", "meeting", "demain", "semaine",
    "fichier", "drive", "document", "doc", "sheet",
    "notion", "page", "base de données",
    "slack", "message", "channel",
    "linear", "issue", "ticket", "bug",
    "stripe", "paiement", "facture", "invoice",
    "todoist", "tâche", "task", "todo",
    "outlook",
    "briefing", "brief", "morning",
    "crée", "envoie", "supprime", "modifie", "planifie", "organise",
    "connecte", "connecter",
    "lis", "montre", "affiche", "cherche", "filtre", "trouve",
]


def _needs_tools(message: str) -> bool:
    """Fast pre-filter: does this message likely need MCP tools?"""
    msg = message.lower()
    return any(hint in msg for hint in TOOL_HINTS)


async def clone_node(state: AgentState) -> dict:
    """Clone — POAIG: l'IA décide quels outils appeler.

    FAST PATH: si le message est conversationnel (pas de tool hints),
    on skippe le catalog et on répond directement via LLM.
    TOOL PATH: sinon, on charge le catalog et le LLM classifie.
    """
    config = state.get("inversion_config", {})
    user_system_prompt = config.get("clone_system_prompt", "")
    context = state.get("context", "")
    last_message = state["messages"][-1].content if state["messages"] else ""
    now = datetime.now(timezone(timedelta(hours=2)))

    # FAST PATH — conversational, no tools needed
    if not _needs_tools(last_message):
        chat_messages = [{"role": "system", "content": user_system_prompt or "Tu es le Clone, agent productif du cockpit Stern OS. Réponds en français, sois concis et bienveillant. Ton utilisateur est un Generator 4/1 (Human Design)."}]
        if context:
            chat_messages.append({"role": "system", "content": f"Contexte mémoire:\n{context}"})
        for msg in state["messages"]:
            role = "user" if msg.type == "human" else "assistant"
            chat_messages.append({"role": role, "content": msg.content})

        try:
            response = await litellm.acompletion(model=MODEL_FAST, messages=chat_messages, max_tokens=1024)
            content = response.choices[0].message.content
        except Exception:
            try:
                response = await litellm.acompletion(model=MODEL_FALLBACK, messages=chat_messages, max_tokens=1024)
                content = response.choices[0].message.content
            except Exception:
                content = "Erreur de connexion. Réessaie."
        return {"messages": [AIMessage(content=content)], "active_agent": "clone"}

    # TOOL PATH — load catalog, classify intent
    tool_catalog = await _get_tool_catalog()

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
        response = await litellm.acompletion(model=MODEL_TOOL, messages=messages_for_router, max_tokens=2048)
        raw_content = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Clone router failed ({MODEL_TOOL}), fallback: {e}")
        try:
            response = await litellm.acompletion(model=MODEL_FALLBACK, messages=messages_for_router, max_tokens=2048)
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
                # Try to generate a direct OAuth link
                from app.services.mcp_client import OBOT_MCP_SERVERS
                info = OBOT_MCP_SERVERS.get(server, {})
                display = info.get("name", server)
                connect_url = await _generate_connect_url(server)
                if connect_url:
                    content = f"⚠️ **{display}** n'est pas encore connecté.\n\n**[Clique ici pour connecter {display}]({connect_url})**\n\nUne fois autorisé, réessaie ta demande."
                else:
                    content = f"⚠️ **{display}** n'est pas connecté et le lien OAuth n'a pas pu être généré."
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
                    r2 = await litellm.acompletion(model=MODEL_FAST, messages=synth_messages, max_tokens=1024)
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
                r2 = await litellm.acompletion(model=MODEL_FAST, messages=synth_messages, max_tokens=1024)
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
        response = await litellm.acompletion(model=MODEL_FAST, messages=chat_messages, max_tokens=2048)
        content = response.choices[0].message.content
    except Exception:
        try:
            response = await litellm.acompletion(model=MODEL_FALLBACK, messages=chat_messages, max_tokens=2048)
            content = response.choices[0].message.content
        except Exception:
            content = "Erreur de connexion. Réessaie."

    return {
        "messages": [AIMessage(content=content)],
        "active_agent": "clone",
    }
