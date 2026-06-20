"""FastAPI dependencies for authentication.

`get_current_user`  — required auth; raises 401 if no valid session.
`get_optional_user` — best-effort auth; returns None when unauthenticated.

Both read the access JWT from the httpOnly cookie (session-first) and fall
back to an `Authorization: Bearer <token>` header so the API is also
usable from non-browser clients / tests.
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import read_access_token_from_cookies
from app.auth.exceptions import InvalidSessionError
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User
from app.services import jwt_service
from app.services.user_service import get_user_by_id


def _extract_token(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    # 1) Session cookie (browser flow)
    token = read_access_token_from_cookies(request.cookies)
    if token:
        return token
    # 2) Bearer header (API clients / tests)
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def _resolve_user(token: str | None, db: AsyncSession) -> User | None:
    if not token:
        return None
    try:
        data = jwt_service.decode_token(token, expected_type=jwt_service.TOKEN_TYPE_ACCESS)
    except jwt.InvalidTokenError:
        return None
    user = await get_user_by_id(db, data.sub)
    if user is None:
        return None
    return user


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Require a valid access token. Raises InvalidSessionError (-> 401) otherwise."""
    token = _extract_token(request, authorization)
    user = await _resolve_user(token, db)
    if user is None:
        raise InvalidSessionError("Not authenticated")
    return user


async def get_optional_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Like get_current_user but returns None instead of raising."""
    token = _extract_token(request, authorization)
    return await _resolve_user(token, db)


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


__all__ = ["CurrentUser", "OptionalUser", "get_current_user", "get_optional_user"]
