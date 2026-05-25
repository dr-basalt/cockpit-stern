import json
import logging
from uuid import UUID

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Memory cascade L1→L2→L3→L4.
    L1: Redis (<1ms) — profile cache, session state, energy check-in
    L2: Mem0 (conversational mid-term) — optional
    L3: Graphiti (knowledge graph) — optional, skipped if no Neo4j
    L4: pgvector (semantic RAG) — via SQLAlchemy
    """

    def __init__(self):
        self._redis: redis.Redis | None = None
        self._mem0_client = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def _get_mem0(self):
        if self._mem0_client is None and settings.MEM0_API_KEY:
            try:
                from mem0 import MemoryClient
                self._mem0_client = MemoryClient(api_key=settings.MEM0_API_KEY)
            except Exception as e:
                logger.warning(f"Mem0 init failed: {e}")
        return self._mem0_client

    # --- L1: Redis ---

    async def cache_profile(self, profile_id: UUID, profile_data: dict, ttl: int = 900):
        r = await self._get_redis()
        await r.setex(f"profile:{profile_id}", ttl, json.dumps(profile_data, default=str))

    async def get_cached_profile(self, profile_id: UUID) -> dict | None:
        r = await self._get_redis()
        data = await r.get(f"profile:{profile_id}")
        return json.loads(data) if data else None

    async def set_energy(self, profile_id: UUID, level: int, ttl: int = 43200):
        r = await self._get_redis()
        await r.setex(f"energy:{profile_id}", ttl, str(level))

    async def get_energy(self, profile_id: UUID) -> int | None:
        r = await self._get_redis()
        val = await r.get(f"energy:{profile_id}")
        return int(val) if val else None

    # --- L2: Mem0 ---

    async def store_conversation(self, profile_id: UUID, messages: list[dict]):
        client = await self._get_mem0()
        if client:
            try:
                client.add(messages, user_id=str(profile_id))
            except Exception as e:
                logger.warning(f"Mem0 store failed: {e}")

    async def search_memory(self, profile_id: UUID, query: str) -> list[dict]:
        client = await self._get_mem0()
        if client:
            try:
                return client.search(query, user_id=str(profile_id))
            except Exception as e:
                logger.warning(f"Mem0 search failed: {e}")
        return []

    # --- L3: Graphiti (optional) ---

    async def _graphiti_available(self) -> bool:
        return bool(settings.GRAPHITI_NEO4J_URI)

    # --- Aggregated ---

    async def get_context(self, profile_id: UUID, query: str) -> str:
        parts = []

        # L1 — cached profile
        cached = await self.get_cached_profile(profile_id)
        if cached:
            parts.append(f"Profil en cache: {cached.get('name', 'inconnu')}")

        # L1 — energy
        energy = await self.get_energy(profile_id)
        if energy is not None:
            parts.append(f"Énergie actuelle: {energy}/10")

        # L2 — Mem0 search
        mem_results = await self.search_memory(profile_id, query)
        if mem_results:
            for r in mem_results[:3]:
                parts.append(f"Mémoire: {r.get('memory', r.get('text', ''))}")

        # L3 — Graphiti skipped if not available
        if not await self._graphiti_available():
            logger.debug("L3 skipped, no Neo4j configured")

        return "\n".join(parts) if parts else ""

    async def store_interaction(self, profile_id: UUID, interaction: dict):
        # L1 — update session cache
        r = await self._get_redis()
        await r.lpush(f"interactions:{profile_id}", json.dumps(interaction, default=str))
        await r.ltrim(f"interactions:{profile_id}", 0, 99)

        # L2 — store in Mem0
        if interaction.get("content"):
            await self.store_conversation(profile_id, [
                {"role": interaction.get("role", "user"), "content": interaction["content"]}
            ])

    async def get_decision_history(self, profile_id: UUID) -> list[dict]:
        r = await self._get_redis()
        raw = await r.lrange(f"decisions:{profile_id}", 0, -1)
        return [json.loads(item) for item in raw]

    async def store_decision(self, profile_id: UUID, decision: dict):
        r = await self._get_redis()
        await r.lpush(f"decisions:{profile_id}", json.dumps(decision, default=str))

    async def detect_not_self(self, profile_id: UUID, message: str, not_self_signal: str = "Frustration") -> bool:
        signal_lower = not_self_signal.lower()
        message_lower = message.lower()

        not_self_keywords = {
            "frustration": ["frustré", "frustration", "ras le bol", "marre", "bloqué", "coincé", "énervé"],
            "amertume": ["amer", "amertume", "pas reconnu", "ignoré", "invisible"],
            "colère": ["colère", "furieux", "révolté", "inacceptable"],
            "déception": ["déçu", "déception", "pas à la hauteur"],
        }

        keywords = not_self_keywords.get(signal_lower, [signal_lower])
        return any(kw in message_lower for kw in keywords)
