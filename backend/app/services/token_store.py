"""Token store — persistance + auto-refresh des OAuth tokens."""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, delete

from app.core.database import async_session
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)


class TokenStore:
    """CRUD + auto-refresh for OAuth tokens in PostgreSQL."""

    async def save(self, tool_key: str, token_data: dict) -> None:
        async with async_session() as db:
            existing = await db.execute(
                select(OAuthToken).where(OAuthToken.tool_key == tool_key)
            )
            token = existing.scalar_one_or_none()

            if token:
                token.access_token = token_data["access_token"]
                token.refresh_token = token_data.get("refresh_token") or token.refresh_token
                token.token_type = token_data.get("token_type", "Bearer")
                token.expires_in = token_data.get("expires_in")
                token.client_id = token_data.get("client_id") or token.client_id
                token.client_secret = token_data.get("client_secret") or token.client_secret
                token.token_endpoint = token_data.get("token_endpoint") or token.token_endpoint
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
        """Get token, auto-refresh if expired."""
        async with async_session() as db:
            result = await db.execute(
                select(OAuthToken).where(OAuthToken.tool_key == tool_key)
            )
            token = result.scalar_one_or_none()
            if not token:
                return None

            # Check if expired
            if token.expires_in and token.updated_at:
                elapsed = (datetime.now(timezone.utc) - token.updated_at.replace(tzinfo=timezone.utc)).total_seconds()
                if elapsed > (token.expires_in - 60):  # refresh 60s before expiry
                    refreshed = await self._refresh(token)
                    if refreshed:
                        return refreshed
                    # Refresh failed — return stale token, let the caller handle 401
                    logger.warning(f"Token refresh failed for {tool_key}, returning stale token")

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

    async def _refresh(self, token: OAuthToken) -> dict | None:
        """Refresh an expired token using the refresh_token."""
        if not token.refresh_token or not token.token_endpoint or not token.client_id:
            logger.warning(f"Cannot refresh {token.tool_key}: missing refresh_token/endpoint/client_id")
            return None

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    token.token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": token.refresh_token,
                        "client_id": token.client_id,
                        "client_secret": token.client_secret or "",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if r.status_code != 200:
                    logger.warning(f"Token refresh failed for {token.tool_key}: {r.status_code} {r.text[:200]}")
                    return None

                data = r.json()
                new_token = {
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token", token.refresh_token),
                    "token_type": data.get("token_type", "Bearer"),
                    "expires_in": data.get("expires_in"),
                    "client_id": token.client_id,
                    "client_secret": token.client_secret,
                    "token_endpoint": token.token_endpoint,
                    "tool_key": token.tool_key,
                }

                # Save refreshed token
                await self.save(token.tool_key, new_token)
                logger.info(f"Token refreshed for {token.tool_key}")
                return new_token

        except Exception as e:
            logger.error(f"Token refresh error for {token.tool_key}: {e}")
            return None

    async def list_connected(self) -> list[str]:
        async with async_session() as db:
            result = await db.execute(select(OAuthToken.tool_key))
            return [row[0] for row in result.all()]

    async def remove(self, tool_key: str) -> None:
        async with async_session() as db:
            await db.execute(delete(OAuthToken).where(OAuthToken.tool_key == tool_key))
            await db.commit()


token_store = TokenStore()
