"""
End-to-end backend API tests for `POST /api/ai/coach`.

These are the P0 regression tests required by section 15 ("Backend: API
reaches Coach, Coach reaches RAG, response reaches API, scope is
preserved"). The Coach itself is stubbed here (its own retrieval/diagnosis
behavior is covered by ai/tests/*) -- what's under test is purely the HTTP
integration: auth -> trusted enrollment resolution -> Coach.invoke call
shape -> response mapping.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai.agents.coach.state import TaskContext
from ai.models.schemas import (
    AssistancePolicy,
    CoachResult,
    Diagnosis,
    DiagnosisCategory,
    Intervention,
    InterventionType,
    LearningEvent,
    LearningEventType,
)
from backend.app.api.coach import _get_coach
from backend.app.main import app
from backend.app.services.auth import get_auth_context, AuthContext


class FakeCoach:
    """Records every `invoke(...)` call so tests can assert on exactly what
    the HTTP layer forwarded to the Coach -- especially the trusted
    TaskContext scope fields."""

    def __init__(self):
        self.calls: list[dict] = []

    def invoke(self, **kwargs) -> CoachResult:
        self.calls.append(kwargs)
        return CoachResult(
            response="Have you checked what happens when the learning rate is too large?",
            intervention=Intervention(
                type=InterventionType.QUESTION,
                assistance_level=kwargs["policy"],
                rationale="Probing for understanding of the learning-rate role.",
            ),
            diagnosis_summary=Diagnosis(
                category=DiagnosisCategory.MISCONCEPTION,
                concept="learning_rate",
                explanation="Forgot to scale by the learning rate.",
                evidence=kwargs["attempt"],
                confidence=0.8,
            ),
            referenced_concepts=["learning_rate"],
            tools_used=["course_retriever"],
            learning_event=LearningEvent(
                student_id=kwargs["student_id"],
                assignment_id=kwargs["assignment_id"],
                session_id=kwargs["session_id"],
                event_type=LearningEventType.AI_INTERACTION,
                payload={},
            ),
            evidence_candidates=[],
            risk_signals=[],
            sources=[],
            metadata={"turn_index": kwargs.get("turn_index", 0)},
        )


@pytest.fixture()
def fake_coach():
    return FakeCoach()


@pytest.fixture()
def client(fake_coach):
    app.dependency_overrides[_get_coach] = lambda: fake_coach
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        student_id="student_1", university_id="stanford_univ"
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _valid_payload(**overrides) -> dict:
    payload = {
        "student_id": "student_1",
        "assignment_id": "asg_1",
        "session_id": "sess_1",
        "course_id": "course_cs101",
        "attempt": "theta = theta - grad",
        "policy": "GUIDED",
        "message": "why is my update wrong?",
        "assignment_title": "Gradient Descent",
        "assignment_instructions": "Implement the update rule.",
        "is_programming": True,
        "turn_index": 1,
        "conversation": [],
    }
    payload.update(overrides)
    return payload


def test_coach_endpoint_reaches_coach_and_returns_mapped_response(client, fake_coach):
    resp = client.post("/api/ai/coach", json=_valid_payload())

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"].startswith("Have you checked")
    assert body["diagnosis"]["concept"] == "learning_rate"
    assert body["tools_used"] == ["course_retriever"]
    assert len(fake_coach.calls) == 1


def test_coach_endpoint_resolves_trusted_scope_not_from_request_body(client, fake_coach):
    """The client cannot supply university_id/classroom_id/allowed_document_ids
    -- they must come from the trusted enrollment resolver (section 17)."""
    payload = _valid_payload(course_id="course_cs101")
    resp = client.post("/api/ai/coach", json=payload)

    assert resp.status_code == 200
    task_context: TaskContext = fake_coach.calls[0]["task_context"]
    assert task_context.university_id == "stanford_univ"
    assert task_context.classroom_id == "classroom_alpha"
    assert task_context.course_id == "course_cs101"


def test_coach_endpoint_ignores_client_supplied_scope_override_attempt(client, fake_coach):
    """Even if a client stuffs extra scope-looking fields into the request
    body, they must never reach TaskContext -- only the enrollment-resolved
    values do."""
    payload = _valid_payload(course_id="course_cs101")
    payload["university_id"] = "attacker_university"
    payload["classroom_id"] = "attacker_room"
    payload["allowed_document_ids"] = ["secret_doc"]

    resp = client.post("/api/ai/coach", json=payload)

    assert resp.status_code == 200
    task_context: TaskContext = fake_coach.calls[0]["task_context"]
    assert task_context.university_id == "stanford_univ"
    assert task_context.classroom_id == "classroom_alpha"
    assert task_context.allowed_document_ids == []


def test_coach_endpoint_rejects_student_id_mismatch(client, fake_coach):
    payload = _valid_payload(student_id="someone_else")
    resp = client.post("/api/ai/coach", json=payload)

    assert resp.status_code == 403
    assert fake_coach.calls == []


def test_coach_endpoint_rejects_unenrolled_course(client, fake_coach):
    payload = _valid_payload(course_id="no_such_course")
    resp = client.post("/api/ai/coach", json=payload)

    assert resp.status_code == 403
    assert fake_coach.calls == []


def test_coach_endpoint_requires_authentication():
    # No dependency override for auth here -- exercise the real dependency.
    app.dependency_overrides[_get_coach] = lambda: FakeCoach()
    try:
        with TestClient(app) as c:
            resp = c.post("/api/ai/coach", json=_valid_payload())
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
