"""Conditional routing functions for the Coach graph (section 9)."""
from __future__ import annotations

import ast
import re

from ai.agents.coach.state import CoachState

MAX_VALIDATION_RETRIES = 1

_CODE_KEYWORD_PATTERN = re.compile(
    r"\b(def|class|import|from|return|for|while|if|elif|else|try|except|finally|with|lambda|yield)\b"
)
_ASSIGNMENT_PATTERN = re.compile(r"\b\w+\s*=[^=]")


def is_code_attempt(attempt: str) -> bool:
    """Check if the student's submission contains code constructs."""
    if not attempt or not attempt.strip():
        return False

    # Explicit markdown code fences
    if "```" in attempt:
        return True

    # Common programming keywords
    if _CODE_KEYWORD_PATTERN.search(attempt):
        return True

    # Variable assignment (e.g. theta = theta - lr * grad)
    if _ASSIGNMENT_PATTERN.search(attempt):
        return True

    # Try parsing as Python AST and check for substantive code nodes
    try:
        tree = ast.parse(attempt)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                    ast.Assign,
                    ast.AugAssign,
                    ast.For,
                    ast.While,
                    ast.If,
                    ast.Call,
                ),
            ):
                return True
    except SyntaxError:
        # If syntax error but has code-like symbols and operators
        if re.search(r"[:\(\)\[\]\{\}]", attempt) and any(c in attempt for c in "=+-*/"):
            return True

    return False


def should_analyze_code(state: CoachState) -> bool:
    """Determine whether static code analysis should be executed for this turn."""
    task = state.get("task_context")
    if not task or not task.is_programming:
        return False

    attempt = state.get("current_attempt") or ""
    return is_code_attempt(attempt)


def route_after_understand_context(state: CoachState) -> str:
    """Route to code analysis if programming task with code attempt, else straight to diagnose."""
    if should_analyze_code(state):
        return "analyze_code"
    return "diagnose"


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
