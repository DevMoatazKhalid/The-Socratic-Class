"""
HTTP request/response schemas for `POST /api/ai/coach`.

Mirrors docs/API.md exactly. Kept separate from `ai.models.schemas` /
`ai.agents.coach.state` (the internal Coach contracts) so the HTTP layer can
evolve (versioning, additive fields) without touching the AI package -- the
API router is responsible for translating between the two.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ai.models.schemas import AssistancePolicy


class ConversationTurn(BaseModel):
    role: str = Field(description="'student' or 'coach'")
    content: str


class CoachApiRequest(BaseModel):
    student_id: str
    assignment_id: str
    session_id: str
    course_id: str
    attempt: str
    policy: AssistancePolicy = AssistancePolicy.GUIDED
    message: Optional[str] = None
    assignment_title: Optional[str] = None
    assignment_instructions: Optional[str] = None
    is_programming: bool = False
    turn_index: int = 0
    conversation: list[ConversationTurn] = Field(default_factory=list)

    # Deliberately NOT accepted here, per section 17 of the integration
    # spec: university_id, classroom_id, allowed_document_ids. Those are
    # resolved server-side from the authenticated student_id + course_id
    # (see backend/app/services/enrollment.py) and must never be
    # client-overridable scope. If a client includes them, Pydantic simply
    # ignores unknown fields (default model config) -- they are never read.


class CoachApiResponse(BaseModel):
    """Mirrors `ai.models.schemas.CoachResult` field-for-field; kept as an
    explicit HTTP schema (rather than returning CoachResult directly) so the
    HTTP contract in docs/API.md doesn't silently drift if the internal
    schema changes."""

    response: str
    intervention: dict
    diagnosis: dict
    referenced_concepts: list[str]
    tools_used: list[str]
    learning_event: dict
    evidence_candidates: list[dict]
    risk_signals: list[dict]
    sources: list[dict]
    metadata: dict
