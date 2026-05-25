import logging
from uuid import UUID

from app.services.memory import MemoryService

logger = logging.getLogger(__name__)


class PatternDetector:
    """Background task — detects recurring patterns in user interactions."""

    def __init__(self, memory: MemoryService):
        self.memory = memory

    async def analyze(self, profile_id: UUID, message: str, profile: dict) -> dict | None:
        """
        Detect patterns:
        - Repeated not-self signals
        - Decision avoidance
        - Energy crashes
        """
        not_self = profile.get("hd_not_self", "Frustration")
        is_not_self = await self.memory.detect_not_self(profile_id, message, not_self)

        if is_not_self:
            return {
                "pattern": "not_self_recurring",
                "signal": not_self,
                "recommendation": f"Signal {not_self} détecté. Pattern récurrent possible.",
            }

        return None
