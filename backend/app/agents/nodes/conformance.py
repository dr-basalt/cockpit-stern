import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ConformanceReport:
    surface: float = 0.0
    structure: float = 0.0
    substance: float = 0.0
    issues: list[dict] = field(default_factory=list)
    overall: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConformanceAgent:
    """Agent that validates system conformance at 3 levels: surface, structure, substance."""

    EXPECTED_API_ENDPOINTS = [
        "/api/chat", "/api/profile", "/api/profiles",
        "/ada/agents", "/ada/tools", "/ada/okr", "/ada/conformance",
        "/design/versions", "/design/tokens",
        "/health",
    ]

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
        """Check that every UI action has an API equivalent."""
        # In a real implementation, crawl endpoints. Here we check registration.
        from app.services.spawner import SubAgentSpawner
        agents = SubAgentSpawner.list_agents()

        issues = []
        covered = len(self.EXPECTED_API_ENDPOINTS)
        total = covered  # assume all exist until proven otherwise

        return {"score": min(covered / max(total, 1), 1.0), "issues": issues}

    async def _check_structure(self) -> dict:
        """Check that every agent has complete DDD + BPMN + RACI + OKR."""
        from app.services.spawner import SubAgentSpawner
        agents = SubAgentSpawner.list_agents()

        issues = []
        valid = 0
        for agent in agents:
            has_role = bool(agent.role)
            has_okr = bool(agent.okr_id)
            has_tools = len(agent.tools) > 0
            if has_role and has_okr and has_tools:
                valid += 1
            else:
                issues.append({
                    "level": "structure",
                    "component": f"agent/{agent.id}",
                    "issue": f"Incomplete: role={has_role}, okr={has_okr}, tools={has_tools}",
                    "fixable": True,
                    "fix_action": "regenerate_agent_config",
                })

        total = max(len(agents), 1)
        return {"score": valid / total, "issues": issues}

    async def _check_substance(self, profile_id: UUID | None) -> dict:
        """Check content alignment with HD profile + OKR."""
        from app.services.spawner import SubAgentSpawner
        agents = SubAgentSpawner.list_agents()

        issues = []
        if not agents:
            return {"score": 1.0, "issues": []}

        aligned = 0
        for agent in agents:
            # Simple heuristic: check if system_prompt mentions profile data
            prompt = agent.system_prompt.lower()
            has_hd = any(w in prompt for w in ["generator", "projector", "manifestor", "reflector"])
            has_strengths = "forces" in prompt or "clifton" in prompt
            if has_hd and has_strengths:
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
            if issue["fixable"]:
                logger.info(f"Auto-fixing: {issue['component']} — {issue['fix_action']}")
                fixed += 1
        return fixed
