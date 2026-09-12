"""
Minimal trusted-identity extraction for the backend.

This is explicitly an MVP mechanism (section 9 of the integration spec):
"If the hackathon MVP lacks full auth, implement the smallest safe
trusted-context mechanism consistent with the existing project rather than
inventing a complete identity platform."

What this provides:
- Decodes an HS256 JWT bearer token (stdlib `hmac`/`hashlib` only -- no new
  dependency) to recover a trusted `student_id` (the `sub` claim) and an
  optional trusted `university_id` claim, set by whatever issues the token.
- In non-production environments only, falls back to trusting an
  `X-Student-Id` / `X-University-Id` header pair directly, so the backend is
  usable in local dev/CI without a running token issuer.

What this deliberately does NOT do:
- It does not implement token issuance, refresh, revocation, or any of the
  rest of a real identity platform. A production deployment should replace
  `decode_bearer_token` with real verification against the institution's
  actual auth provider; the important invariant to preserve is that
  `AuthContext.student_id` / `university_id` always come from a source the
  *backend* trusts, never from request-body fields the client can set
  directly (see `backend/app/services/enrollment.py` for how classroom_id/
  allowed_document_ids are then resolved from student_id + course_id).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, status

from backend.app.config import get_backend_config


class AuthError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


@dataclass(frozen=True)
class AuthContext:
    """Trusted identity for the current request. Never built from
    client-supplied request-body fields -- only from the bearer token (or,
    outside production, the dev header bypass)."""

    student_id: str
    university_id: Optional[str] = None


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def decode_bearer_token(token: str, secret: str) -> dict:
    """Verify and decode an HS256 JWT. Raises AuthError on any failure
    (bad signature, malformed token, expired `exp`)."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise AuthError("Malformed bearer token.")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        raise AuthError("Malformed bearer token signature.")

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise AuthError("Invalid bearer token signature.")

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise AuthError("Malformed bearer token payload.")

    if header.get("alg") != "HS256":
        raise AuthError("Unsupported token algorithm.")

    exp = payload.get("exp")
    if exp is not None and time.time() > float(exp):
        raise AuthError("Bearer token has expired.")

    return payload


def get_auth_context(
    authorization: Optional[str] = Header(default=None),
    x_student_id: Optional[str] = Header(default=None, alias="X-Student-Id"),
    x_university_id: Optional[str] = Header(default=None, alias="X-University-Id"),
) -> AuthContext:
    """FastAPI dependency resolving the trusted identity for this request."""
    cfg = get_backend_config()

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[len("bearer "):].strip()
        if not cfg.jwt_secret:
            raise AuthError(
                "Bearer token provided but no BACKEND_JWT_SECRET is configured on the server."
            )
        payload = decode_bearer_token(token, cfg.jwt_secret)
        student_id = payload.get("sub")
        if not student_id:
            raise AuthError("Bearer token missing required 'sub' (student_id) claim.")
        return AuthContext(student_id=student_id, university_id=payload.get("university_id"))

    if cfg.allow_dev_header_auth and x_student_id:
        # Dev/CI-only bypass -- never available when ENVIRONMENT=production
        # (see BackendConfig.allow_dev_header_auth).
        return AuthContext(student_id=x_student_id, university_id=x_university_id)

    raise AuthError(
        "Missing or invalid Authorization bearer token "
        "(and no dev X-Student-Id header fallback available)."
    )
