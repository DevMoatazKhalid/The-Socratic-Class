"""
`POST /api/ai/coach` -- the P0 integration.

Wires: HTTP request -> trusted auth/enrollment resolution -> Coach
(LangGraph) -> CourseRetrievalTool -> RAGService -> PostgreSQL/pgvector ->
validation/enforcement -> HTTP response.

This router is intentionally thin: it does authentication/authorization and
schema translation only. All pedagogical/retrieval/safety logic stays in
`ai/`, per section 9 ("Backend should be a thin integration/API layer...
Do NOT duplicate the Coach logic in backend.").
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ai.agents.coach.graph import Coach, get_default_coach
from ai.agents.coach.state import TaskContext
from backend.app.schemas.coach import CoachApiRequest, CoachApiResponse
from backend.app.services.auth import AuthContext, get_auth_context
from backend.app.services.enrollment import get_enrollment_resolver

router = APIRouter(prefix="/api/ai", tags=["coach"])


def _conversation_to_messages(turns) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for turn in turns:
        if turn.role == "student":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))
    return messages


def _get_coach() -> Coach:
    return get_default_coach()


@router.post("/coach", response_model=CoachApiResponse)
def coach_turn(
    payload: CoachApiRequest,
    auth: AuthContext = Depends(get_auth_context),
    coach: Coach = Depends(_get_coach),
) -> CoachApiResponse:
    # The request body's student_id is client-supplied and used only for
    # convenience/logging correlation -- authorization is always driven by
    # the authenticated identity. Reject any mismatch outright rather than
    # silently preferring one over the other.
    if payload.student_id != auth.student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="student_id in request body does not match the authenticated session.",
        )

    # Trusted scope resolution: university_id / classroom_id /
    # allowed_document_ids NEVER come from the request body (section 17) --
    # only from server-side enrollment lookup keyed by the authenticated
    # student_id and the (client-supplied, but course-scoped-only)
    # course_id.
    enrollment = get_enrollment_resolver().resolve(
        student_id=auth.student_id,
        university_id_hint=auth.university_id,
        course_id=payload.course_id,
    )

    task_context = TaskContext(
        assignment_id=payload.assignment_id,
        course_id=payload.course_id,
        title=payload.assignment_title or "",
        instructions=payload.assignment_instructions or "",
        is_programming=payload.is_programming,
        university_id=enrollment.university_id,
        classroom_id=enrollment.classroom_id,
        allowed_document_ids=list(enrollment.allowed_document_ids),
    )

    result = coach.invoke(
        student_id=auth.student_id,
        assignment_id=payload.assignment_id,
        session_id=payload.session_id,
        task_context=task_context,
        attempt=payload.attempt,
        policy=payload.policy,
        message=payload.message,
        conversation=_conversation_to_messages(payload.conversation),
        turn_index=payload.turn_index,
    )

    return CoachApiResponse(
        response=result.response,
        intervention=result.intervention.model_dump(mode="json"),
        diagnosis=result.diagnosis_summary.model_dump(mode="json"),
        referenced_concepts=result.referenced_concepts,
        tools_used=result.tools_used,
        learning_event=result.learning_event.model_dump(mode="json"),
        evidence_candidates=[c.model_dump(mode="json") for c in result.evidence_candidates],
        risk_signals=[s.model_dump(mode="json") for s in result.risk_signals],
        sources=[s.model_dump(mode="json") for s in result.sources],
        metadata=result.metadata,
    )
