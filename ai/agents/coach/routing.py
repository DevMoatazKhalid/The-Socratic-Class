"""Conditional routing functions for the Coach graph (section 9)."""
from __future__ import annotations

from ai.agents.coach.state import CoachState

MAX_VALIDATION_RETRIES = 1


def route_after_intervention(state: CoachState) -> str:
    if state.get("needs_course_material") or state.get("needs_student_history"):
        return "retrieve_context"
    return "generate_response"


def route_after_validation(state: CoachState) -> str:
    if state.get("validation_passed"):
        return "emit_interaction"
    if state.get("retry_count", 0) > MAX_VALIDATION_RETRIES:
        return "safe_fallback"
    return "generate_response"
