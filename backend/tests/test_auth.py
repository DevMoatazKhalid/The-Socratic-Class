"""Unit tests for the minimal MVP auth mechanism (backend/app/services/auth.py)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException

from backend.app.services import auth as auth_mod
from backend.app.services.auth import AuthContext, decode_bearer_token, get_auth_context


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_hs256_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(sig)}"


def test_decode_bearer_token_valid():
    token = _make_hs256_jwt({"sub": "student_1", "university_id": "mit"}, "shhh")
    payload = decode_bearer_token(token, "shhh")
    assert payload["sub"] == "student_1"
    assert payload["university_id"] == "mit"


def test_decode_bearer_token_rejects_wrong_secret():
    token = _make_hs256_jwt({"sub": "student_1"}, "shhh")
    with pytest.raises(HTTPException):
        decode_bearer_token(token, "different-secret")


def test_decode_bearer_token_rejects_expired():
    token = _make_hs256_jwt({"sub": "student_1", "exp": time.time() - 10}, "shhh")
    with pytest.raises(HTTPException):
        decode_bearer_token(token, "shhh")


def test_decode_bearer_token_rejects_malformed():
    with pytest.raises(HTTPException):
        decode_bearer_token("not-a-jwt", "shhh")


def test_get_auth_context_with_valid_bearer_token(monkeypatch):
    cfg = auth_mod.get_backend_config()
    monkeypatch.setattr(cfg, "jwt_secret", "shhh")
    token = _make_hs256_jwt({"sub": "student_42", "university_id": "mit"}, "shhh")

    ctx = get_auth_context(authorization=f"Bearer {token}", x_student_id=None, x_university_id=None)
    assert ctx == AuthContext(student_id="student_42", university_id="mit")


def test_get_auth_context_dev_header_bypass_outside_production(monkeypatch):
    cfg = auth_mod.get_backend_config()
    monkeypatch.setattr(cfg, "environment", "development")
    monkeypatch.setattr(cfg, "allow_dev_header_auth", True)

    ctx = get_auth_context(authorization=None, x_student_id="student_9", x_university_id="mit")
    assert ctx == AuthContext(student_id="student_9", university_id="mit")


def test_get_auth_context_dev_header_bypass_disabled_in_production(monkeypatch):
    cfg = auth_mod.get_backend_config()
    monkeypatch.setattr(cfg, "environment", "production")
    monkeypatch.setattr(cfg, "allow_dev_header_auth", False)

    with pytest.raises(HTTPException):
        get_auth_context(authorization=None, x_student_id="student_9", x_university_id="mit")


def test_get_auth_context_rejects_missing_credentials(monkeypatch):
    cfg = auth_mod.get_backend_config()
    monkeypatch.setattr(cfg, "allow_dev_header_auth", False)

    with pytest.raises(HTTPException):
        get_auth_context(authorization=None, x_student_id=None, x_university_id=None)
