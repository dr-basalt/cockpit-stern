from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cockpit:cockpit@localhost:5432/cockpit"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    ANTHROPIC_API_KEY: str = ""
    LITELLM_MASTER_KEY: str = ""

    # Observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Memory (optional)
    MEM0_API_KEY: str = ""
    GRAPHITI_NEO4J_URI: str = ""
    GRAPHITI_NEO4J_USER: str = ""
    GRAPHITI_NEO4J_PASSWORD: str = ""

    # MCP Gateway
    OBOT_URL: str = "http://obot:8080"
    NANGO_URL: str = "http://nango:3003"
    NANGO_SECRET_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # App
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
