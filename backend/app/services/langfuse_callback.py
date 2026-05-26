"""Langfuse tracing for all LLM calls via LiteLLM callback."""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def init_langfuse():
    """Initialize Langfuse callbacks for LiteLLM. Call once at startup."""
    global _initialized
    if _initialized:
        return

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.info("Langfuse not configured (no keys). Skipping tracing.")
        return

    try:
        import litellm
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]

        import os
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
        os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

        _initialized = True
        logger.info(f"Langfuse tracing enabled → {settings.LANGFUSE_HOST}")
    except Exception as e:
        logger.warning(f"Langfuse init failed: {e}")
