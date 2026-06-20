"""Unit tests for the OAuth state / authorize-URL helpers."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.services import oauth_service


def test_generate_state_is_unique_and_urlsafe():
    a = oauth_service.generate_state()
    b = oauth_service.generate_state()
    assert a != b
    assert len(a) > 20


def test_signed_state_roundtrip():
    raw = oauth_service.generate_state()
    signed = oauth_service.build_signed_state(raw)
    assert oauth_service.verify_signed_state(signed, raw) is True


def test_verify_rejects_wrong_raw_state():
    raw = oauth_service.generate_state()
    signed = oauth_service.build_signed_state(raw)
    assert oauth_service.verify_signed_state(signed, "different") is False


def test_verify_rejects_tampered_signature():
    raw = oauth_service.generate_state()
    signed = oauth_service.build_signed_state(raw)
    parts = signed.split(".")
    tampered = f"{parts[0]}.{'0' * len(parts[1])}.{parts[2]}"
    assert oauth_service.verify_signed_state(tampered, raw) is False


def test_authorization_url_contains_required_params():
    req = oauth_service.build_authorization_url("rawstate")
    parsed = urlparse(req.authorization_url)
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert qs["client_id"] == ["test_client_id"]
    assert "read:user" in qs["scope"][0].split(" ")
    assert "user:email" in qs["scope"][0].split(" ")
    # state in URL is the SIGNED form (3 dot parts), not the raw value.
    assert req.state.count(".") == 2
    assert qs["state"] == [req.state]
