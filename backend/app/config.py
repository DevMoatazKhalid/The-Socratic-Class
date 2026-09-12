"""
Backend configuration.

Thin, deliberately small: the backend is an integration/API layer over the
existing `ai/` package, not a new platform. See docs/AI_SPEC.md and
docs/API.md for the contract this backend implements.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.is_file():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()


def _clean(name: str) -> Optional[str]:
    val = os.getenv(name)
    if val is None:
        return None
    val = val.strip()
    return val if val else None


class BackendConfig:
    def __init__(self) -> None:
        self.environment: str = (_clean("ENVIRONMENT") or "development").lower()

        # Minimal MVP auth (section 9: "smallest safe trusted-context
        # mechanism consistent with the existing project rather than
        # inventing a complete identity platform"). See
        # backend/app/services/auth.py for how this is used.
        self.jwt_secret: Optional[str] = _clean("BACKEND_JWT_SECRET")
        # Only honored outside production -- lets local/dev/CI callers
        # authenticate as a given student without standing up a full JWT
        # issuer. Never available when environment == "production".
        self.allow_dev_header_auth: bool = (self.environment != "production")

        # Trusted enrollment fixture (student/course -> university/classroom/
        # allowed_document_ids). See backend/app/services/enrollment.py.
        self.enrollment_fixture_path: Optional[str] = _clean("ENROLLMENT_FIXTURE_PATH")


_config: Optional[BackendConfig] = None


def get_backend_config() -> BackendConfig:
    global _config
    if _config is None:
        _config = BackendConfig()
    return _config
