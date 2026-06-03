"""Token store — persistance des OAuth tokens dans PostgreSQL."""
import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)


class TokenStore:
    """CRUD for OAuth tokens. Replaces the in-memory _oauth_tokens dict."""

    async def save(self, tool_key: str, token_data: dict) -> None:
        async with async_session() as db:
            existing = await db.execute(
                select(OAuthToken).where(OAuthToken.tool_key == tool_key)
            )
            token = existing.scalar_one_or_none()

            if token:
                token.access_token = token_data["access_token"]
                token.refresh_token = token_data.get("refresh_token")
                token.token_type = token_data.get("token_type", "Bearer")
                token.expires_in = token_data.get("expires_in")
                token.client_id = token_data.get("client_id")
                token.client_secret = token_data.get("client_secret")
                token.token_endpoint = token_data.get("token_endpoint")
                token.extra = token_data.get("extra")
            else:
                token = OAuthToken(
                    tool_key=tool_key,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    token_endpoint=token_data.get("token_endpoint"),
                    extra=token_data.get("extra"),
                )
                db.add(token)

            await db.commit()
            logger.info(f"Token saved for {tool_key}")

    async def get(self, tool_key: str) -> dict | None:
        async with async_session() as db:
            result = await db.execute(
                select(OAuthToken).where(OAuthToken.tool_key == tool_key)
            )
            token = result.scalar_one_or_none()
            if not token:
                return None
            return {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_type": token.token_type,
                "expires_in": token.expires_in,
                "client_id": token.client_id,
                "client_secret": token.client_secret,
                "token_endpoint": token.token_endpoint,
                "tool_key": token.tool_key,
            }

    async def list_connected(self) -> list[str]:
        async with async_session() as db:
            result = await db.execute(select(OAuthToken.tool_key))
            return [row[0] for row in result.all()]

    async def remove(self, tool_key: str) -> None:
        async with async_session() as db:
            await db.execute(delete(OAuthToken).where(OAuthToken.tool_key == tool_key))
            await db.commit()


token_store = TokenStore()
