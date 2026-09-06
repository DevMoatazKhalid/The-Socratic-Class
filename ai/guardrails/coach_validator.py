"""
Response validation / guardrails for the AI Coach (section 22).

Three layers, cheapest first:
1. Fast, deterministic rule checks (no LLM call) that catch the clearest
   policy violations — applied to ALL policies (GUIDED, ASSISTED, OPEN).
2. An LLM-based reviewer for the more nuanced checks (relevance, whether the
   answer was effectively given away, unsupported claims about the student,
   confidence-calibration, etc).
3. A deterministic final-answer enforcement pass that runs AFTER validation
   and AFTER any LLM rewrites — the absolute last line of defense.

Keep this focused -- it is not a general content-moderation framework.
"""
from __future__ import annotations

import logging
import re

from ai.agents.coach.schemas import ValidationResult
from ai.models.llm import ModelRole, get_structured_llm
from ai.models.schemas import AssistancePolicy
from ai.prompts.verification.validation_prompt import build_validation_messages

logger = logging.getLogger(__name__)

# ── Universal answer-revealing phrases (apply to ALL policies) ────────────
# The Coach MUST NEVER give the student the final answer, regardless of policy.
_UNIVERSAL_RED_FLAG_PHRASES = (
    "the answer is",
    "the correct answer is",
    "here is the solution",
    "here's the solution",
    "the final answer is",
    "the solution is",
    "here is the complete solution",
    "here's the complete solution",
    "here is the full solution",
    "here's the full solution",
    "the correct solution is",
)

# Additional phrases only flagged under GUIDED (where even partial answers
# are dangerous).
_GUIDED_EXTRA_PHRASES = (
    "you should write",
    "the code should be",
    "the code is",
    "the formula is",
    "just use",
    "simply use",
)


def rule_based_check(*, policy: AssistancePolicy, draft_response: str) -> list[str]:
    """Deterministic rule check applied to ALL policies.

    The final-answer prohibition is universal across GUIDED, ASSISTED, and
    OPEN.  GUIDED additionally flags partial-answer phrases.
    """
    violations: list[str] = []
    if not draft_response or not draft_response.strip():
        violations.append("Response is empty.")
        return violations

    lowered = draft_response.lower()

    # Universal: answer-revealing phrases forbidden under every policy.
    for phrase in _UNIVERSAL_RED_FLAG_PHRASES:
        if phrase in lowered:
            violations.append(
                f"{policy.value} policy violation: response contains "
                f"answer-revealing phrase '{phrase}'."
            )

    # GUIDED-only: additional phrases that are too close to giving the answer.
    if policy == AssistancePolicy.GUIDED:
        for phrase in _GUIDED_EXTRA_PHRASES:
            if phrase in lowered:
                violations.append(
                    f"GUIDED policy violation: response contains "
                    f"direct-answer phrase '{phrase}'."
                )

    return violations


# ── Deterministic final-answer enforcement (absolute last line) ───────────

# Compiled pattern that catches "the answer/solution is …" and similar.
_ANSWER_REVEAL_PATTERN = re.compile(
    r"\b(?:the\s+)?(?:correct\s+|final\s+|complete\s+|full\s+)?"
    r"(?:answer|solution)\s+(?:is|would be|equals?|=)\s",
    re.IGNORECASE,
)


def final_answer_enforcement(response: str) -> tuple[bool, str]:
    """Deterministic last-line-of-defense check.

    Returns (is_safe, cleaned_response).  If the response is unsafe,
    ``cleaned_response`` is a safe Socratic fallback.

    This function MUST run after every path that produces a student-facing
    response — after generation, after LLM validation, and after any
    revised_response substitution.
    """
    if not response or not response.strip():
        return False, _SAFE_SOCRATIC_FALLBACK

    lowered = response.lower()

    # Check universal phrases
    for phrase in _UNIVERSAL_RED_FLAG_PHRASES:
        if phrase in lowered:
            logger.warning(
                "final_answer_enforcement blocked response containing '%s'",
                phrase,
            )
            return False, _SAFE_SOCRATIC_FALLBACK

    # Check regex pattern
    if _ANSWER_REVEAL_PATTERN.search(response):
        logger.warning(
            "final_answer_enforcement blocked response matching answer-reveal pattern."
        )
        return False, _SAFE_SOCRATIC_FALLBACK

    return True, response


_SAFE_SOCRATIC_FALLBACK = (
    "Let me ask you a different way — can you walk me through your "
    "reasoning step by step? That will help me understand where to guide you."
)


def llm_check(
    *,
    policy: AssistancePolicy,
    diagnosis_category: str,
    diagnosis_confidence: float,
    intervention_type: str,
    course_material: str,
    draft_response: str,
) -> ValidationResult:
    messages = build_validation_messages(
        policy=policy.value,
        diagnosis_category=diagnosis_category,
        diagnosis_confidence=diagnosis_confidence,
        intervention_type=intervention_type,
        course_material=course_material,
        draft_response=draft_response,
    )
    llm = get_structured_llm(ModelRole.LIGHTWEIGHT, ValidationResult)
    return llm.invoke(messages)


def validate_response(
    *,
    policy: AssistancePolicy,
    diagnosis_category: str,
    diagnosis_confidence: float,
    intervention_type: str,
    course_material: str,
    draft_response: str,
    use_llm: bool = True,
) -> ValidationResult:
    """Full validation pass.

    1. Deterministic rule check (all policies).
    2. LLM check (unless disabled).
    3. Final deterministic enforcement on the result (including any
       revised_response from the LLM).
    """

    violations = rule_based_check(policy=policy, draft_response=draft_response)

    if not use_llm:
        return ValidationResult(passes=not violations, violations=violations)

    try:
        llm_result = llm_check(
            policy=policy,
            diagnosis_category=diagnosis_category,
            diagnosis_confidence=diagnosis_confidence,
            intervention_type=intervention_type,
            course_material=course_material,
            draft_response=draft_response,
        )
    except Exception:
        logger.exception("LLM validation call failed; falling back to rule-based result only.")
        return ValidationResult(passes=not violations, violations=violations)

    all_violations = violations + list(llm_result.violations)
    passes = not all_violations
    revised = llm_result.revised_response if not passes else None

    # If the LLM proposed a revised response, enforce rules on it too.
    if revised:
        revised_violations = rule_based_check(policy=policy, draft_response=revised)
        if revised_violations:
            # The LLM's rewrite itself violates rules — reject it.
            logger.warning(
                "LLM revised_response also violates rules; discarding rewrite."
            )
            all_violations.extend(revised_violations)
            revised = None

    return ValidationResult(
        passes=passes, violations=all_violations, revised_response=revised
    )
