"""Session validation middleware.

Attaches a lightweight `request.state.user_id` when a valid access token is
present, and refreshes an about-to-expire access token transparently using
the refresh cookie (sliding session). This is *non-blocking*: it never
rejects a request — endpoint-level `get_current_user` is the gatekeeper.
Keeping it non-blocking means public routes (login, callback) keep working.
"""
from __future__ import annotations

import time

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth.cookies import (
    read_access_token_from_cookies,
    read_refresh_token_from_cookies,
    set_auth_cookies,
)
from app.database.session import async_session_factory
from app.services import auth_service, jwt_service
from app.services.jwt_service import IssuedTokens

# When the access token has less than this many minutes left, silently rotate.
_REFRESH_SLACK_MINUTES = 5


class SessionValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user_id = None
        rotated: IssuedTokens | None = None

        access_token = read_access_token_from_cookies(request.cookies)
        if access_token:
            try:
                data = jwt_service.decode_token(
                    access_token, expected_type=jwt_service.TOKEN_TYPE_ACCESS
                )
                request.state.user_id = data.sub
                # Sliding refresh: if the access token is about to expire and
                # we have a valid refresh token, mint a fresh pair.
                remaining = (data.exp.timestamp() - time.time()) / 60
                if remaining < _REFRESH_SLACK_MINUTES:
                    rotated = await self._maybe_rotate(request)
            except jwt.InvalidTokenError:
                request.state.user_id = None

        response = await call_next(request)

        # If we rotated the session, set the new cookies on the way out so the
        # browser keeps a valid session without any client-side logic.
        if rotated is not None:
            set_auth_cookies(
                response,
                access_token=rotated.access_token,
                refresh_token=rotated.refresh_token,
                access_expires_at=rotated.access_expires_at,
                refresh_expires_at=rotated.refresh_expires_at,
            )

        return response

    async def _maybe_rotate(self, request: Request) -> IssuedTokens | None:
        refresh_token = read_refresh_token_from_cookies(request.cookies)
        if not refresh_token:
            return None
        try:
            rdata = jwt_service.decode_token(
                refresh_token, expected_type=jwt_service.TOKEN_TYPE_REFRESH
            )
        except jwt.InvalidTokenError:
            return None
        async with async_session_factory() as db:
            if not rdata.jti or not await auth_service.is_valid(db, rdata.jti):
                return None
            # Revoke the consumed refresh token (rotation defends reuse).
            await auth_service.revoke(db, rdata.jti)
            tokens = jwt_service.issue_token_pair(rdata.sub)
            new_jti = jwt_service.decode_token(
                tokens.refresh_token, expected_type=jwt_service.TOKEN_TYPE_REFRESH
            ).jti
            await auth_service.create(
                db,
                user_id=rdata.sub,
                jti=new_jti or "",
                expires_at=tokens.refresh_expires_at,
            )
            await db.commit()
        return tokens


__all__ = ["SessionValidationMiddleware"]
