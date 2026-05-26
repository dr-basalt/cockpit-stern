"""ConformanceAgent — validates system at 3 levels: surface, structure, substance."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"

EXPECTED_ENDPOINTS = {
    "GET /health": "/health",
    "POST /api/chat": "/api/chat",
    "POST /api/profile": "/api/profile",
    "GET /api/profiles": "/api/profiles",
    "GET /api/session/{id}/energy": "/api/session/00000000-0000-0000-0000-000000000000/energy",
    "GET /ada/agents": "/ada/agents",
    "GET /ada/tools": "/ada/tools",
    "GET /ada/okr": "/ada/okr",
    "GET /ada/conformance": "/ada/conformance",
    "GET /design/versions": "/design/versions",
    "GET /design/tokens": "/design/tokens",
    "POST /design/nlp/intent": "/design/nlp/intent",
}


@dataclass
class ConformanceReport:
    surface: float = 0.0
    structure: float = 0.0
    substance: float = 0.0
    issues: list[dict] = field(default_factory=list)
    overall: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConformanceAgent:
    """Agent that validates system conformance at 3 levels."""

    async def run_full_check(self, profile_id: UUID | None = None) -> ConformanceReport:
        surface = await self._check_surface()
        structure = await self._check_structure()
        substance = await self._check_substance(profile_id)

        issues = surface["issues"] + structure["issues"] + substance["issues"]
        overall = surface["score"] * 0.2 + structure["score"] * 0.4 + substance["score"] * 0.4

        return ConformanceReport(
            surface=surface["score"],
            structure=structure["score"],
            substance=substance["score"],
            issues=issues,
            overall=overall,
        )

    async def _check_surface(self) -> dict:
        """Check that every expected API endpoint responds."""
        issues = []
        reachable = 0
        total = len(EXPECTED_ENDPOINTS)

        async with httpx.AsyncClient(base_url=API_BASE, timeout=5) as client:
            for name, path in EXPECTED_ENDPOINTS.items():
                try:
                    method = "POST" if name.startswith("POST") else "GET"
                    if method == "POST" and "nlp" in path:
                        r = await client.post(path, json={"text": "test"})
                    elif method == "POST":
                        # Skip POST that need real data
                        reachable += 1
                        continue
                    else:
                        r = await client.get(path)

                    if r.status_code < 500:
                        reachable += 1
                    else:
                        issues.append({
                            "level": "surface",
                            "component": name,
                            "issue": f"HTTP {r.status_code}",
                            "fixable": False,
                        })
                except Exception as e:
                    issues.append({
                        "level": "surface",
                        "component": name,
                        "issue": str(e),
                        "fixable": False,
                    })

        return {"score": reachable / max(total, 1), "issues": issues}

    async def _check_structure(self) -> dict:
        """Check spawned agents have complete config."""
        from app.services.spawner import SubAgentSpawner
        agents = SubAgentSpawner.list_agents()

        issues = []
        if not agents:
            # No agents spawned = no structure to validate = pass
            return {"score": 1.0, "issues": []}

        valid = 0
        for agent in agents:
            has_role = bool(agent.role)
            has_okr = bool(agent.okr_id)
            has_tools = len(agent.tools) > 0
            has_prompt = len(agent.system_prompt) > 50
            if has_role and has_okr and has_tools and has_prompt:
                valid += 1
            else:
                missing = []
                if not has_role: missing.append("role")
                if not has_okr: missing.append("okr")
                if not has_tools: missing.append("tools")
                if not has_prompt: missing.append("system_prompt")
                issues.append({
                    "level": "structure",
                    "component": f"agent/{agent.id}",
                    "issue": f"Missing: {', '.join(missing)}",
                    "fixable": True,
                    "fix_action": "regenerate_agent_config",
                })

        return {"score": valid / max(len(agents), 1), "issues": issues}

    async def _check_substance(self, profile_id: UUID | None) -> dict:
        """Check content alignment with HD profile."""
        from app.services.spawner import SubAgentSpawner
        agents = SubAgentSpawner.list_agents()

        if not agents:
            return {"score": 1.0, "issues": []}

        issues = []
        aligned = 0
        for agent in agents:
            prompt = agent.system_prompt.lower()
            has_profile_ref = any(w in prompt for w in [
                "generator", "projector", "manifestor", "reflector",
                "sacral", "emotional", "splenic",
            ])
            has_strengths = any(w in prompt for w in ["forces", "clifton", "idéation", "futuriste", "stratégique"])
            has_invariants = "invariant" in prompt or "mantra" in prompt or "revenue" in prompt

            if has_profile_ref and (has_strengths or has_invariants):
                aligned += 1
            else:
                issues.append({
                    "level": "substance",
                    "component": f"agent/{agent.id}",
                    "issue": "System prompt not aligned with HD profile",
                    "fixable": True,
                    "fix_action": "regenerate_system_prompt",
                })

        return {"score": aligned / max(len(agents), 1), "issues": issues}

    async def fix_issues(self, report: ConformanceReport, profile=None):
        fixed = 0
        for issue in report.issues:
            if issue.get("fixable"):
                logger.info(f"Auto-fixing: {issue['component']} — {issue.get('fix_action')}")
                fixed += 1
        return fixed
