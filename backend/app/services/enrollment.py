"""
Trusted enrollment resolution.

Section 9 / section 17 of the integration spec are explicit that
university_id, course_id, classroom_id, assignment_id, and the allowed
document whitelist must never come from client-provided request fields --
they must come from trusted server-side context.

This module is the smallest safe mechanism for that: given the
authenticated `student_id` (from `backend/app/services/auth.py`) and the
`course_id` the client asked about, it looks up the *trusted* classroom_id
and allowed_document_ids for that enrollment. `course_id` itself is treated
as client-supplied per docs/API.md's `CoachApiRequest.course_id`, but
everything scope-sensitive beyond it comes from this resolver, not the
request body.

The lookup here is an in-memory fixture (optionally overridden by a JSON
file via `ENROLLMENT_FIXTURE_PATH`) seeded to match `data/documents/` in
this repo. This is explicitly a placeholder for a real enrollments table --
swapping `EnrollmentResolver._lookup` for a real DB query is the intended
upgrade path and does not require changing any caller of
`resolve_enrollment`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status

from backend.app.config import get_backend_config


@dataclass(frozen=True)
class Enrollment:
    university_id: str
    classroom_id: Optional[str]
    allowed_document_ids: tuple[str, ...] = ()


class EnrollmentError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=message)


# Seed fixture matching data/documents/ in this repo, so a fresh checkout
# can exercise the full backend -> Coach -> RAG path end-to-end without any
# extra setup. Keyed by (student_id, course_id); "*" matches any student_id
# for demo/smoke courses.
_DEFAULT_ENROLLMENTS: dict[tuple[str, str], Enrollment] = {
    ("*", "course_cs101"): Enrollment(university_id="stanford_univ", classroom_id="classroom_alpha"),
    ("*", "course_econ201"): Enrollment(university_id="stanford_univ", classroom_id="classroom_beta"),
    ("*", "smoke_course"): Enrollment(university_id="smoke_univ", classroom_id="smoke_room"),
}


class EnrollmentResolver:
    def __init__(self, fixture_path: Optional[str] = None) -> None:
        self._enrollments: dict[tuple[str, str], Enrollment] = dict(_DEFAULT_ENROLLMENTS)
        if fixture_path:
            self._load_fixture(fixture_path)

    def _load_fixture(self, path: str) -> None:
        data = json.loads(Path(path).read_text())
        for entry in data:
            key = (entry.get("student_id", "*"), entry["course_id"])
            self._enrollments[key] = Enrollment(
                university_id=entry["university_id"],
                classroom_id=entry.get("classroom_id"),
                allowed_document_ids=tuple(entry.get("allowed_document_ids", ())),
            )

    def resolve(self, *, student_id: str, university_id_hint: Optional[str], course_id: str) -> Enrollment:
        """Resolve the trusted enrollment for `student_id` in `course_id`.

        `university_id_hint` (from the auth token, if present) is used only
        to disambiguate/validate -- the authoritative university_id
        returned always comes from the enrollment record itself, never
        purely from client/token-supplied text alone without a matching
        enrollment.
        """
        enrollment = self._enrollments.get((student_id, course_id)) or self._enrollments.get(("*", course_id))
        if enrollment is None:
            raise EnrollmentError(
                f"No trusted enrollment found for course_id={course_id!r}. "
                "The student is not authorized for this course."
            )
        if university_id_hint and university_id_hint != enrollment.university_id:
            raise EnrollmentError(
                "university_id from the authenticated session does not match "
                "the trusted enrollment record for this course."
            )
        return enrollment


_resolver: Optional[EnrollmentResolver] = None


def get_enrollment_resolver() -> EnrollmentResolver:
    global _resolver
    if _resolver is None:
        cfg = get_backend_config()
        _resolver = EnrollmentResolver(fixture_path=cfg.enrollment_fixture_path)
    return _resolver
