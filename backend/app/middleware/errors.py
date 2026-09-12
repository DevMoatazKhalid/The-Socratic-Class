"""Standard HTTP error envelope, per docs/API.md section 3."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _envelope(code: str, message: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or []}}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = {
        status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    }.get(exc.status_code, "ERROR")
    return JSONResponse(status_code=exc.status_code, content=_envelope(code, str(exc.detail)))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_envelope("VALIDATION_ERROR", "Request validation failed.", exc.errors()),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # The Coach graph already degrades gracefully internally (see
    # ai/agents/coach/nodes.py fallbacks); this handler is the last resort
    # for anything that still escapes -- e.g. a bug in the HTTP layer
    # itself -- and must never leak internal details to the client.
    logger.exception("Unhandled exception in request %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_envelope("INTERNAL_ERROR", "An unexpected error occurred. Please try again."),
    )
