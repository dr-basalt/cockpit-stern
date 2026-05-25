import uuid
import logging

from app.agents.state import AgentState
from app.services.inversion import HITL_TRIGGERS

logger = logging.getLogger(__name__)

# Patterns indicating initiation without sacral response
INITIATION_PATTERNS = [
    "je veux lancer", "j'ai décidé de", "je vais commencer",
    "je vais faire", "j'ai choisi de", "je lance",
    "je décide de", "je me lance",
]

NOT_SELF_KEYWORDS = {
    "Generator": ["frustré", "frustration", "bloqué", "marre", "ras le bol"],
    "Manifesting Generator": ["frustré", "frustration", "bloqué", "marre", "ras le bol"],
    "Projector": ["amer", "amertume", "pas reconnu", "ignoré", "invisible"],
    "Manifestor": ["colère", "furieux", "en colère", "révolté"],
    "Reflector": ["déçu", "déception", "pas à la hauteur"],
}


async def filter_sp_node(state: AgentState) -> dict:
    """
    VRAI_SP — entry point unique.
    1. Detect not_self signal
    2. Detect initiation without sacral
    3. Detect HITL triggers
    4. Classify task_type
    """
    messages = state["messages"]
    profile = state["profile"]
    last_message = messages[-1].content if messages else ""
    msg_lower = last_message.lower()

    hd_type = profile.get("hd_type", "Generator")
    not_self_signal = profile.get("hd_not_self", "Frustration")

    updates: dict = {
        "active_agent": "sp",
        "not_self_detected": False,
        "requires_hitl": False,
        "hitl_token": None,
        "task_type": "production",
    }

    # 1. Detect not-self
    keywords = NOT_SELF_KEYWORDS.get(hd_type, NOT_SELF_KEYWORDS["Generator"])
    if any(kw in msg_lower for kw in keywords):
        updates["not_self_detected"] = True
        updates["task_type"] = "sacral_stimulus"
        logger.info(f"Not-self detected for {hd_type}: {not_self_signal}")

    # 2. Detect initiation without sacral (Generator/MG only)
    if hd_type in ("Generator", "Manifesting Generator"):
        if any(pattern in msg_lower for pattern in INITIATION_PATTERNS):
            if not updates["not_self_detected"]:
                updates["task_type"] = "sacral_stimulus"
                logger.info("Initiation without sacral detected")

    # 3. Detect HITL triggers
    if any(trigger in msg_lower for trigger in HITL_TRIGGERS):
        updates["requires_hitl"] = True
        updates["hitl_token"] = str(uuid.uuid4())
        updates["task_type"] = "irreversible_decision"
        logger.info(f"HITL trigger detected, token: {updates['hitl_token']}")

    # 4. Classify task_type if not already set by above
    if updates["task_type"] == "production" and not updates["not_self_detected"]:
        routing_keywords = state.get("inversion_config", {}).get("routing_keywords", {})

        clone_kw = routing_keywords.get("clone", [])
        anti_kw = routing_keywords.get("anti", [])
        sp_kw = routing_keywords.get("sp", [])

        clone_score = sum(1 for kw in clone_kw if kw in msg_lower)
        anti_score = sum(1 for kw in anti_kw if kw in msg_lower)
        sp_score = sum(1 for kw in sp_kw if kw in msg_lower)

        if sp_score > clone_score and sp_score > anti_score:
            updates["task_type"] = "flow"
        elif anti_score > clone_score:
            updates["task_type"] = "challenge"
        # else: stays "production" → Clone

    return updates
