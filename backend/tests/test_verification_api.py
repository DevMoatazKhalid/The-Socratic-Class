"""End-to-end backend API tests for `/api/ai/verify/*`."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai.models.schemas import EvidenceStrength, EvidenceType, LearningEvidenceCandidate
from ai.verification.models import (
    VerificationChallenge,
    VerificationOutcome,
    VerificationResult,
    VerificationType,
)
from backend.app.api.verification import _get_service
from backend.app.main import app
from backend.app.services.auth import AuthContext, get_auth_context


class FakeVerificationService:
    def __init__(self):
        self.challenge_calls = []
        self.verify_calls = []

    def generate_challenge(self, request):
        self.challenge_calls.append(request)
        return VerificationChallenge(
            verification_type=request.verification_type,
            concept=request.concept,
            question="Why does scaling by the learning rate matter here?",
            criteria=["Mentions gradient magnitude", "Mentions convergence stability"],
        )

    def verify(self, request):
        self.verify_calls.append(request)
        return VerificationResult(
            student_id=request.student_id,
            assignment_id=request.assignment_id,
            concept=request.concept,
            verification_type=request.verification_type,
            outcome=VerificationOutcome.PASS,
            score=0.9,
            confidence=0.85,
            feedback="Solid explanation.",
            criteria_evaluations=[],
            evidence_candidate=LearningEvidenceCandidate(
                student_id=request.student_id,
                assignment_id=request.assignment_id,
                concept=request.concept,
                evidence_type=EvidenceType.EXPLANATION,
                strength=EvidenceStrength.STRONG,
                observation="Clear explanation of the learning-rate role.",
            ),
        )


@pytest.fixture()
def fake_service():
    return FakeVerificationService()


@pytest.fixture()
def client(fake_service):
    app.dependency_overrides[_get_service] = lambda: fake_service
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(student_id="student_1")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_generate_challenge_endpoint(client, fake_service):
    resp = client.post(
        "/api/ai/verify/challenge",
        json={
            "assignment_id": "asg_1",
            "concept": "learning_rate",
            "verification_type": "EXPLAIN",
            "student_work": "theta = theta - grad",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["concept"] == "learning_rate"
    assert "criteria" in body
    assert len(fake_service.challenge_calls) == 1


def test_evaluate_endpoint(client, fake_service):
    resp = client.post(
        "/api/ai/verify/evaluate",
        json={
            "student_id": "student_1",
            "assignment_id": "asg_1",
            "concept": "learning_rate",
            "verification_type": "EXPLAIN",
            "challenge_question": "Why does scaling by the learning rate matter?",
            "student_response": "It controls the step size taken during each update.",
            "criteria": ["Mentions step size"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "PASS"
    assert body["evidence_candidate"]["strength"] == "STRONG"
    assert len(fake_service.verify_calls) == 1


def test_evaluate_endpoint_rejects_student_id_mismatch(client, fake_service):
    resp = client.post(
        "/api/ai/verify/evaluate",
        json={
            "student_id": "someone_else",
            "assignment_id": "asg_1",
            "concept": "learning_rate",
            "verification_type": "EXPLAIN",
            "challenge_question": "Why does scaling by the learning rate matter?",
            "student_response": "It controls the step size.",
        },
    )
    assert resp.status_code == 403
    assert fake_service.verify_calls == []
