import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime

from app.services.inversion import InversionRulesEngine

logger = logging.getLogger(__name__)

_agent_registry: dict[str, "SpawnedAgent"] = {}


@dataclass
class SubAgentTemplate:
    role: str
    profession: str
    ddd_context: str
    bpmn_xml: str = ""
    raci: dict = field(default_factory=lambda: {"responsible": "clone", "accountable": "real", "consulted": "anti", "informed": "sp"})
    tools: list[str] = field(default_factory=list)
    okr_parent_id: str = ""
    execution_mode: str = "mitl"
    model_tier: str = "pro"


@dataclass
class SpawnedAgent:
    id: str
    role: str
    profession: str
    system_prompt: str
    tools: list[str]
    okr_id: str
    execution_mode: str
    model_tier: str
    status: str = "ready"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


class SubAgentSpawner:
    def __init__(self):
        self.engine = InversionRulesEngine()

    async def spawn(self, template: SubAgentTemplate, profile, inversion_config=None) -> SpawnedAgent:
        agent_id = str(uuid.uuid4())
        system_prompt = (
            f"Tu es un {template.profession} spécialisé en {template.ddd_context}.\n"
            f"Rôle: {template.role}\n"
            f"Profil utilisateur: {profile.name} ({profile.hd_type}, {profile.hd_authority})\n"
            f"Forces: {', '.join(profile.clifton_top5)}\n"
            f"Mantra: {profile.mantra}\n"
            f"Invariants: {', '.join(profile.invariants)}\n\n"
            f"RACI: R={template.raci.get('responsible')}, A={template.raci.get('accountable')}, "
            f"C={template.raci.get('consulted')}, I={template.raci.get('informed')}\n"
            f"Mode d'exécution: {template.execution_mode}\n"
            f"OKR parent: {template.okr_parent_id}\n"
        )

        agent = SpawnedAgent(
            id=agent_id,
            role=template.role,
            profession=template.profession,
            system_prompt=system_prompt,
            tools=template.tools,
            okr_id=template.okr_parent_id,
            execution_mode=template.execution_mode,
            model_tier=template.model_tier,
        )

        _agent_registry[agent_id] = agent
        logger.info(f"Spawned sub-agent: {template.role} ({agent_id})")
        return agent

    async def spawn_agency_from_okr(self, root_okr, profile) -> list[SpawnedAgent]:
        """Generate agent team recursively from OKR tree."""
        agents = []
        role_map = {
            0: ("ceo_digital_twin", "CEO Digital Twin", "strategy"),
            1: ("product_lead", "Product Lead", "product"),
            2: ("sprint_lead", "Sprint Manager", "delivery"),
            3: ("task_executor", "Task Executor", "execution"),
        }

        level = getattr(root_okr, "level", 0)
        role, profession, context = role_map.get(level, role_map[3])

        template = SubAgentTemplate(
            role=role,
            profession=profession,
            ddd_context=context,
            tools=["notion", "github", "calendar"],
            okr_parent_id=str(root_okr.id),
            execution_mode="mitl" if level <= 1 else "yolo",
            model_tier="max" if level == 0 else "pro",
        )

        agent = await self.spawn(template, profile)
        agents.append(agent)
        return agents

    @staticmethod
    def list_agents() -> list[SpawnedAgent]:
        return list(_agent_registry.values())

    @staticmethod
    def get_agent(agent_id: str) -> SpawnedAgent | None:
        return _agent_registry.get(agent_id)
