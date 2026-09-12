"""HTTP request/response schemas for `/api/ai/verify/*`, mirroring docs/API.md."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ai.verification.models import VerificationType


class VerificationChallengeApiRequest(BaseModel):
    assignment_id: str
    concept: str
    verification_type: VerificationType
    student_work: str
    course_context: Optional[str] = None


class VerificationChallengeApiResponse(BaseModel):
    challenge_id: str
    verification_type: str
    concept: str
    question: str
    criteria: list[str]


class VerificationEvaluateApiRequest(BaseModel):
    student_id: str
    assignment_id: str
    concept: str
    verification_type: VerificationType
    challenge_question: str
    student_response: str
    criteria: list[str] = []
    original_attempt: Optional[str] = None


class VerificationEvaluateApiResponse(BaseModel):
    verification_id: str
    student_id: str
    assignment_id: str
    concept: str
    verification_type: str
    outcome: str
    score: float
    confidence: float
    feedback: str
    criteria_evaluations: list[dict]
    evidence_candidate: Optional[dict] = None
