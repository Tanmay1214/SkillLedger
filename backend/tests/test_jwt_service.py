"""Unit tests for the JWT service."""
from __future__ import annotations

import time

import jwt
import pytest

from app.services import jwt_service


def test_access_token_roundtrip():
    token, exp = jwt_service.create_access_token(42)
    data = jwt_service.decode_token(token, expected_type=jwt_service.TOKEN_TYPE_ACCESS)
    assert data.sub == 42
    assert data.type == "access"
    assert data.exp == exp


def test_refresh_token_has_jti():
    token, exp, jti = jwt_service.create_refresh_token(7)
    assert jti  # non-empty
    data = jwt_service.decode_token(token, expected_type=jwt_service.TOKEN_TYPE_REFRESH)
    assert data.sub == 7
    assert data.jti == jti


def test_issue_pair_returns_both_tokens():
    pair = jwt_service.issue_token_pair(99)
    access = jwt_service.decode_token(pair.access_token, expected_type="access")
    refresh = jwt_service.decode_token(pair.refresh_token, expected_type="refresh")
    assert access.sub == refresh.sub == 99


def test_decode_rejects_wrong_type():
    token, _ = jwt_service.create_access_token(1)
    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.decode_token(token, expected_type="refresh")


def test_decode_rejects_tampered_token():
    token, _ = jwt_service.create_access_token(1)
    tampered = token[:-4] + "AAAA"
    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.decode_token(tampered)


def test_decode_rejects_expired_token():
    # Issue then rewind: we craft a token with exp in the past.
    import datetime as dt
    payload = {
        "sub": "1",
        "type": "access",
        "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1),
    }
    token = jwt.encode(payload, get_secret(), algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt_service.decode_token(token)


def get_secret():
    from app.core.config import settings
    return settings.jwt_secret
