"""`POST /api/ai/verify/challenge` and `/api/ai/verify/evaluate`.

Learning Verification is intentionally decoupled from the Coach graph (see
section 5 / docs/AI_SPEC.md) -- this router calls `VerificationService`
directly rather than routing through `Coach.invoke`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ai.verification.models import VerificationChallengeRequest, VerificationRequest
from ai.verification.service import VerificationService, get_default_verification_service
from backend.app.schemas.verification import (
    VerificationChallengeApiRequest,
    VerificationChallengeApiResponse,
    VerificationEvaluateApiRequest,
    VerificationEvaluateApiResponse,
)
from backend.app.services.auth import AuthContext, get_auth_context

router = APIRouter(prefix="/api/ai/verify", tags=["verification"])


def _get_service() -> VerificationService:
    return get_default_verification_service()


@router.post("/challenge", response_model=VerificationChallengeApiResponse)
def generate_challenge(
    payload: VerificationChallengeApiRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: VerificationService = Depends(_get_service),
) -> VerificationChallengeApiResponse:
    request = VerificationChallengeRequest(
        assignment_id=payload.assignment_id,
        concept=payload.concept,
        verification_type=payload.verification_type,
        student_work=payload.student_work,
        course_context=payload.course_context,
    )
    challenge = service.generate_challenge(request)
    return VerificationChallengeApiResponse(
        challenge_id=challenge.challenge_id,
        verification_type=challenge.verification_type.value,
        concept=challenge.concept,
        question=challenge.question,
        criteria=challenge.criteria,
    )


@router.post("/evaluate", response_model=VerificationEvaluateApiResponse)
def evaluate_verification(
    payload: VerificationEvaluateApiRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: VerificationService = Depends(_get_service),
) -> VerificationEvaluateApiResponse:
    if payload.student_id != auth.student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="student_id in request body does not match the authenticated session.",
        )
    request = VerificationRequest(
        student_id=payload.student_id,
        assignment_id=payload.assignment_id,
        concept=payload.concept,
        verification_type=payload.verification_type,
        challenge_question=payload.challenge_question,
        student_response=payload.student_response,
        criteria=payload.criteria,
        original_attempt=payload.original_attempt,
    )
    result = service.verify(request)
    return VerificationEvaluateApiResponse(
        verification_id=result.verification_id,
        student_id=result.student_id,
        assignment_id=result.assignment_id,
        concept=result.concept,
        verification_type=result.verification_type.value,
        outcome=result.outcome.value,
        score=result.score,
        confidence=result.confidence,
        feedback=result.feedback,
        criteria_evaluations=[c.model_dump(mode="json") for c in result.criteria_evaluations],
        evidence_candidate=(
            result.evidence_candidate.model_dump(mode="json") if result.evidence_candidate else None
        ),
    )
