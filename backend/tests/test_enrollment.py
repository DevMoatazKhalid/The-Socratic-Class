"""Unit tests for trusted enrollment resolution (backend/app/services/enrollment.py)."""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.app.services.enrollment import Enrollment, EnrollmentResolver


def test_resolve_known_seed_course():
    resolver = EnrollmentResolver()
    enrollment = resolver.resolve(student_id="s1", university_id_hint=None, course_id="course_cs101")
    assert enrollment.university_id == "stanford_univ"
    assert enrollment.classroom_id == "classroom_alpha"


def test_resolve_unknown_course_raises_forbidden():
    resolver = EnrollmentResolver()
    with pytest.raises(HTTPException) as exc_info:
        resolver.resolve(student_id="s1", university_id_hint=None, course_id="no_such_course")
    assert exc_info.value.status_code == 403


def test_resolve_rejects_university_mismatch():
    resolver = EnrollmentResolver()
    with pytest.raises(HTTPException) as exc_info:
        resolver.resolve(student_id="s1", university_id_hint="some_other_university", course_id="course_cs101")
    assert exc_info.value.status_code == 403


def test_resolve_loads_fixture_override(tmp_path):
    fixture = [
        {
            "student_id": "s_specific",
            "course_id": "course_x",
            "university_id": "uni_x",
            "classroom_id": "room_x",
            "allowed_document_ids": ["doc_1", "doc_2"],
        }
    ]
    fixture_path = tmp_path / "enrollments.json"
    fixture_path.write_text(json.dumps(fixture))

    resolver = EnrollmentResolver(fixture_path=str(fixture_path))
    enrollment = resolver.resolve(student_id="s_specific", university_id_hint=None, course_id="course_x")
    assert enrollment == Enrollment(
        university_id="uni_x", classroom_id="room_x", allowed_document_ids=("doc_1", "doc_2")
    )

    # A different, unenrolled student for the same course_id must not
    # inherit the specific-student record (no wildcard fallback defined for
    # this course in the fixture).
    with pytest.raises(HTTPException):
        resolver.resolve(student_id="someone_else", university_id_hint=None, course_id="course_x")
