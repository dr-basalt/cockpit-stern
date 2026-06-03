"""
title: Stern OS2 — Cockpit Agentique
description: Proxy vers le backend Stern OS2 — MCP tools, skills, routing HD Clone/Anti/SP
author: dr-basalt × Claude
version: 1.0.0
licence: MIT
"""

from pydantic import BaseModel, Field
import httpx
import json


class Pipe:
    """Open WebUI Pipe → Stern OS2 backend.

    Transforme OWUI en frontend du cockpit agentique :
    - Le LangGraph (Clone/Anti/SP) route selon HD + énergie
    - Le Clone voit 187 MCP tools et décide lequel appeler
    - Skills exécutables (morning_brief, etc.)
    - Plans multi-step (ReAct) pour demandes complexes
    """

    class Valves(BaseModel):
        STERN_API_URL: str = Field(
            default="https://api-stern-os2.ori3com.cloud",
            description="URL du backend Stern OS2",
        )
        PROFILE_ID: str = Field(
            default="ec34c303-cdbf-496d-9f4c-17b4e0591146",
            description="UUID du profil utilisateur (Human Design + Clifton)",
        )
        ENERGY_LEVEL: int = Field(
            default=5,
            description="Niveau d'énergie sacrale (1-10). >7=brake, 4-6=balance, <3=accelerate",
        )
        SESSION_ID: str = Field(
            default="owui-session",
            description="ID de session pour la continuité conversationnelle",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def pipes(self):
        """Register Stern OS as a model in the OWUI dropdown."""
        return [
            {
                "id": "stern-cockpit",
                "name": "Stern OS — Cockpit Agentique (Clone/Anti/SP + MCP Tools)",
            },
            {
                "id": "stern-morning-brief",
                "name": "Stern OS — Morning Brief (Calendar + Gmail → Priorité du jour)",
            },
        ]

    async def pipe(self, body: dict, __user__: dict = None) -> str:
        """Route OWUI messages vers Stern OS2 backend."""
        model_id = body.get("model", "").split(".")[-1] if "." in body.get("model", "") else body.get("model", "")
        messages = body.get("messages", [])
        last_message = messages[-1].get("content", "") if messages else ""

        if not last_message:
            return "Envoie un message pour interagir avec le cockpit Stern OS."

        # Morning brief shortcut
        if model_id == "stern-morning-brief":
            return await self._run_skill("morning_brief")

        # Standard chat via LangGraph
        return await self._chat(last_message)

    async def _chat(self, message: str) -> str:
        """Call Stern OS2 /api/chat — LangGraph routing."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{self.valves.STERN_API_URL}/api/chat",
                    json={
                        "session_id": self.valves.SESSION_ID,
                        "profile_id": self.valves.PROFILE_ID,
                        "message": message,
                        "energy_level": self.valves.ENERGY_LEVEL,
                    },
                )

                if r.status_code != 200:
                    return f"Erreur Stern OS2: {r.status_code} — {r.text[:200]}"

                data = r.json()
                agent = data.get("active_agent", "?")
                energy_mode = data.get("energy_mode", "?")
                task_type = data.get("task_type", "?")
                response = data.get("message", "")
                not_self = data.get("not_self_detected", False)

                # Build header with agent metadata
                header = f"**[{agent.upper()}]** · {energy_mode} · {task_type}"
                if not_self:
                    header += " · ⚠️ not-self détecté"

                return f"{header}\n\n{response}"

        except httpx.TimeoutException:
            return "⏱️ Stern OS2 a mis trop de temps à répondre (timeout 60s). La requête impliquait peut-être un plan multi-step complexe."
        except Exception as e:
            return f"Erreur de connexion à Stern OS2: {e}"

    async def _run_skill(self, skill_name: str) -> str:
        """Execute a Stern OS2 skill directly."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{self.valves.STERN_API_URL}/api/skills/{skill_name}/run",
                )

                if r.status_code != 200:
                    return f"Erreur skill {skill_name}: {r.status_code}"

                data = r.json()
                brief = data.get("brief", "")
                sources = data.get("sources", {})

                header = f"**[SKILL: {skill_name}]** · Sources: {json.dumps(sources)}"
                return f"{header}\n\n{brief}"

        except Exception as e:
            return f"Erreur skill: {e}"
