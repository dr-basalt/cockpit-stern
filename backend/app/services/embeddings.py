"""L4 — pgvector semantic embeddings via LiteLLM."""
import json
import logging
from uuid import UUID

import litellm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "openrouter/openai/text-embedding-3-small"
EMBEDDING_DIM = 1536


async def create_embedding(text_content: str) -> list[float] | None:
    """Generate embedding vector via LiteLLM."""
    try:
        response = await litellm.aembedding(model=EMBEDDING_MODEL, input=[text_content])
        return response.data[0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None


async def store_embedding(db: AsyncSession, profile_id: UUID, content: str, metadata: dict | None = None):
    """Store content + embedding in memory_embeddings table."""
    embedding = await create_embedding(content)
    if not embedding:
        return None

    meta_json = json.dumps(metadata or {})
    await db.execute(
        text("""
            INSERT INTO memory_embeddings (id, profile_id, content, embedding, metadata, created_at)
            VALUES (gen_random_uuid(), :pid, :content, :embedding, :meta, NOW())
        """),
        {"pid": str(profile_id), "content": content, "embedding": str(embedding), "meta": meta_json},
    )
    await db.commit()
    return True


async def search_similar(db: AsyncSession, profile_id: UUID, query: str, limit: int = 5) -> list[dict]:
    """Search for semantically similar content in profile's embeddings."""
    query_embedding = await create_embedding(query)
    if not query_embedding:
        return []

    try:
        result = await db.execute(
            text("""
                SELECT content, metadata, 1 - (embedding <=> :qemb::vector) as similarity
                FROM memory_embeddings
                WHERE profile_id = :pid
                ORDER BY embedding <=> :qemb::vector
                LIMIT :lim
            """),
            {"pid": str(profile_id), "qemb": str(query_embedding), "lim": limit},
        )
        rows = result.fetchall()
        return [{"content": r[0], "metadata": r[1], "similarity": float(r[2])} for r in rows]
    except Exception as e:
        logger.warning(f"Embedding search failed: {e}")
        return []
