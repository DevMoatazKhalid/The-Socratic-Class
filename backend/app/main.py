"""
FastAPI application entry point.

Backend integration status (P0): this module + backend/app/api/coach.py +
backend/app/api/verification.py are the actual HTTP <-> Coach <-> RAG wiring
described in docs/AI_SPEC.md / docs/API.md. Run with:

    uvicorn backend.app.main:app --reload

(also the command docker-compose.yml already uses).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.coach import router as coach_router
from backend.app.api.verification import router as verification_router
from backend.app.middleware.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

app = FastAPI(title="The Socratic Class -- AI Coach API")

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(coach_router)
app.include_router(verification_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
