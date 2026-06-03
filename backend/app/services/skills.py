"""Skill Engine — compositions de MCP tools exécutables.

Un Skill = une chaîne de tool calls cross-BC + LLM synthesis optionnel.
Chaque skill est SCRUD-able et exécutable.
"""
import logging
from datetime import datetime, timezone, timedelta

import httpx
import litellm

from app.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)
mcp = MCPClient()

LLM_MODEL = "openrouter/deepseek/deepseek-chat-v3-0324"
LLM_FALLBACK = "openrouter/anthropic/claude-haiku-4-5"


async def _llm_synthesize(system: str, user: str) -> str:
    """Call LLM to synthesize data into a human-readable brief."""
    try:
        r = await litellm.acompletion(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=1024,
        )
        return r.choices[0].message.content
    except Exception:
        try:
            r = await litellm.acompletion(
                model=LLM_FALLBACK,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=1024,
            )
            return r.choices[0].message.content
        except Exception as e:
            return f"[Erreur LLM: {e}]"


async def skill_morning_brief() -> dict:
    """Morning Brief — AGGREGATE : Calendar.today + Gmail.unread → priorité du jour.

    Retourne un briefing structuré.
    """
    now = datetime.now(timezone(timedelta(hours=2)))  # Europe/Paris
    today_start = now.replace(hour=0, minute=0, second=0).isoformat()
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()

    # Step 1: Fetch today's events
    cal_result = await mcp.call("google-calendar", "list_events", {
        "calendar_id": "primary",
        "time_min": today_start,
        "time_max": tomorrow_start,
        "max_results": 20,
    })

    events_raw = ""
    if cal_result.get("status") == "ok":
        content = cal_result.get("result", {}).get("content", [])
        if content:
            events_raw = content[0].get("text", "Aucun event")
    elif cal_result.get("needs_auth"):
        events_raw = "[Google Calendar non connecté]"
    else:
        events_raw = f"[Erreur Calendar: {cal_result.get('error', '?')}]"

    # Step 2: Fetch unread emails
    gmail_result = await mcp.call("gmail", "list_emails", {
        "max_results": 10,
        "query": "is:unread",
    })

    emails_raw = ""
    if gmail_result.get("status") == "ok":
        content = gmail_result.get("result", {}).get("content", [])
        if content:
            emails_raw = content[0].get("text", "Aucun email")
    elif gmail_result.get("needs_auth"):
        emails_raw = "[Gmail non connecté]"
    else:
        emails_raw = f"[Erreur Gmail: {gmail_result.get('error', '?')}]"

    # Step 3: LLM synthesizes
    system = """Tu es l'agent Coach du cockpit Stern OS. Tu produis un briefing matinal concis.
Ton utilisateur est un solopreneur Generator 4/1 (Human Design) qui a tendance à se disperser.
Ton rôle : réduire la dispersion cognitive, montrer UNE priorité claire, motiver.

Structure du brief :
1. PRIORITÉ DU JOUR (1 seule chose à faire en premier)
2. AGENDA (résumé des events du jour, en bullet points)
3. EMAILS URGENTS (les 3 emails les plus importants à traiter)
4. ÉNERGIE (un mot d'encouragement aligné avec l'autorité sacrale)

Sois concis, direct, pas de fluff. Langue : français."""

    user = f"""Voici les données du jour ({now.strftime('%A %d %B %Y')}) :

## Events du jour
{events_raw}

## Emails non lus
{emails_raw}

Génère le briefing matinal."""

    brief = await _llm_synthesize(system, user)

    return {
        "skill": "morning_brief",
        "date": now.strftime("%Y-%m-%d"),
        "brief": brief,
        "sources": {
            "calendar": cal_result.get("status", "error"),
            "gmail": gmail_result.get("status", "error"),
        },
    }


# Registry of executable skills
SKILL_REGISTRY = {
    "morning_brief": {
        "fn": skill_morning_brief,
        "pattern": "AGGREGATE",
        "tools": ["google-calendar.list_events", "gmail.list_emails"],
        "description": "Briefing du matin : agenda + emails → priorité du jour",
    },
}
