"""Authentication endpoints: login, callback, logout, me, refresh.

Flow:
  GET  /auth/github/login     -> returns the GitHub authorize URL + sets a
                                 signed `state` cookie (CSRF).
  GET  /auth/github/callback  -> validates state, exchanges code, fetches
                                 profile, upserts user, issues JWT cookies,
                                 redirects to the frontend dashboard.
  POST /auth/logout           -> revokes refresh session, clears cookies.
  GET  /auth/me               -> returns the authenticated user.
  POST /auth/refresh          -> rotates the refresh token + access token.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OAUTH_STATE_COOKIE, clear_state_cookie, set_state_cookie
from app.auth.cookies import (
    clear_auth_cookies,
    read_refresh_token_from_cookies,
    set_auth_cookies,
)
from app.auth.dependencies import CurrentUser
from app.auth.exceptions import InvalidStateError, OAuthCallbackError
from app.core.config import settings
from app.database.session import get_db
from app.schemas import AuthUrlResponse, CallbackSuccess, LogoutResponse, UserPublic
from app.services import auth_service, github_service, jwt_service, oauth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


# --------------------------------------------------------------------------- #
# 1. Login — build authorize URL
# --------------------------------------------------------------------------- #
@router.get(
    "/github/login",
    response_model=AuthUrlResponse,
    summary="Get the GitHub OAuth authorization URL",
)
async def github_login(response: Response) -> AuthUrlResponse:
    """Return the GitHub OAuth authorize URL and set the CSRF state cookie.

    The frontend can either follow `authorization_url` directly (full-page
    redirect) or call this endpoint and then redirect the browser to it.
    """
    raw_state = oauth_service.generate_state()
    auth_req = oauth_service.build_authorization_url(raw_state)
    set_state_cookie(response, auth_req.state)
    return AuthUrlResponse(authorization_url=auth_req.authorization_url, state=auth_req.state)


# --------------------------------------------------------------------------- #
# 2. Callback — exchange code, fetch profile, upsert user, issue JWTs
# --------------------------------------------------------------------------- #
@router.get(
    "/github/callback",
    response_model=CallbackSuccess,
    summary="Handle the GitHub OAuth callback",
    responses={
        400: {"description": "Missing/invalid state or code"},
        502: {"description": "GitHub OAuth handshake failed"},
    },
)
async def github_callback(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    oauth_state: Annotated[str | None, Cookie(alias=OAUTH_STATE_COOKIE)] = None,
) -> CallbackSuccess:
    # GitHub passes `error` if the user denied access.
    if error:
        clear_state_cookie(response)
        raise OAuthCallbackError(f"GitHub denied authorization: {error}")

    if not code or not state or not oauth_state:
        raise InvalidStateError("Missing code, state, or state cookie")

    # Verify the signed state returned by GitHub matches our cookie.
    raw_from_cookie = oauth_state.split(".")[0]
    if not oauth_service.verify_signed_state(state, raw_from_cookie):
        raise InvalidStateError("OAuth state mismatch (possible CSRF)")

    # Exchange authorization code -> GitHub access token.
    try:
        req_url = str(request.url).split("?")[0]
        github_token = await github_service.exchange_code_for_token(code, redirect_uri=req_url)
        profile = await github_service.fetch_profile(github_token)
    except github_service.GitHubOAuthError as exc:
        raise OAuthCallbackError(str(exc)) from exc

    # Upsert user, persisting the GitHub access token for later API calls.
    user = await user_service.upsert_user_from_github(db, profile, github_token)
    await db.commit()

    # Issue our own JWT pair and persist the refresh token's jti.
    tokens = jwt_service.issue_token_pair(user.id)
    refresh_jti = jwt_service.decode_token(
        tokens.refresh_token, expected_type=jwt_service.TOKEN_TYPE_REFRESH
    ).jti
    await auth_service.create(
        db, user_id=user.id, jti=refresh_jti or "", expires_at=tokens.refresh_expires_at
    )
    await db.commit()

    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_expires_at=tokens.access_expires_at,
        refresh_expires_at=tokens.refresh_expires_at,
    )
    clear_state_cookie(response)

    redirect_to = f"{str(settings.frontend_url).rstrip('/')}/dashboard?login=success"
    return CallbackSuccess(
        user=UserPublic.model_validate(user).model_dump(),
        redirect_to=redirect_to,
    )


# --------------------------------------------------------------------------- #
# 3. Logout — revoke session, clear cookies
# --------------------------------------------------------------------------- #
@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out the current user",
)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> LogoutResponse:
    """Revoke the calling session's refresh token and clear all auth cookies."""
    refresh_token = read_refresh_token_from_cookies(request.cookies)
    if refresh_token:
        try:
            rdata = jwt_service.decode_token(
                refresh_token, expected_type=jwt_service.TOKEN_TYPE_REFRESH
            )
            if rdata.jti:
                await auth_service.revoke(db, rdata.jti)
        except Exception:
            # Token may be malformed/expired — still clear cookies below.
            pass
    await db.commit()
    clear_auth_cookies(response)
    return LogoutResponse()


# --------------------------------------------------------------------------- #
# 4. Me — current authenticated user
# --------------------------------------------------------------------------- #
@router.get(
    "/me",
    response_model=UserPublic,
    summary="Return the authenticated user",
)
async def get_me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


# --------------------------------------------------------------------------- #
# 5. Refresh — rotate tokens (manual, for API clients without browser cookies)
# --------------------------------------------------------------------------- #
@router.post(
    "/refresh",
    summary="Rotate access + refresh tokens",
)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    token = read_refresh_token_from_cookies(request.cookies)
    if not token:
        raise InvalidStateError("Missing refresh token", status_code=401)
    try:
        rdata = jwt_service.decode_token(token, expected_type=jwt_service.TOKEN_TYPE_REFRESH)
    except Exception as exc:
        raise InvalidStateError("Invalid refresh token", status_code=401) from exc
    if not rdata.jti or not await auth_service.is_valid(db, rdata.jti):
        raise InvalidStateError("Refresh token revoked", status_code=401)

    await auth_service.revoke(db, rdata.jti)
    tokens = jwt_service.issue_token_pair(rdata.sub)
    new_jti = jwt_service.decode_token(
        tokens.refresh_token, expected_type=jwt_service.TOKEN_TYPE_REFRESH
    ).jti
    await auth_service.create(
        db, user_id=rdata.sub, jti=new_jti or "", expires_at=tokens.refresh_expires_at
    )
    await db.commit()

    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_expires_at=tokens.access_expires_at,
        refresh_expires_at=tokens.refresh_expires_at,
    )
    return {"message": "Rotated"}


# --------------------------------------------------------------------------- #
# 6. Browser redirect — convenience full-page redirect variant of the callback
# --------------------------------------------------------------------------- #
@router.get(
    "/github/callback/redirect",
    include_in_schema=False,
    summary="Browser-friendly redirect variant of the callback",
)
async def github_callback_redirect(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    """Perform the same callback handshake then issue an HTTP 302 to the
    frontend dashboard. Handy when the frontend links straight to GitHub."""
    # Delegate to the JSON callback by passing the incoming request through.
    # We re-resolve its query params and cookie inside the callback.
    response = Response()  # temporary; the callback writes cookies onto it
    qp = dict(request.query_params)
    result = await github_callback(
        request=request,
        response=response,
        db=db,
        code=qp.get("code"),
        state=qp.get("state"),
        error=qp.get("error"),
        oauth_state=request.cookies.get(OAUTH_STATE_COOKIE),
    )

    # Carry over the cookies the callback set onto the redirect response.
    redirect = RedirectResponse(url=str(result.redirect_to), status_code=status.HTTP_302_FOUND)
    for cookie_header in response.headers.getlist("set-cookie"):
        redirect.headers.append("set-cookie", cookie_header)
    return redirect


__all__ = ["router"]
