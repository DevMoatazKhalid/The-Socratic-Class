"""
Response validation / guardrails for the AI Coach (section 22).

Two layers, cheapest first:
1. Fast, deterministic rule checks (no LLM call) that catch the clearest
   policy violations.
2. An LLM-based reviewer for the more nuanced checks (relevance, whether the
   answer was effectively given away, unsupported claims about the student,
   confidence-calibration, etc).

Keep this focused -- it is not a general content-moderation framework.
"""
from __future__ import annotations

import logging

from ai.agents.coach.schemas import ValidationResult
from ai.models.llm import ModelRole, get_structured_llm
from ai.models.schemas import AssistancePolicy
from ai.prompts.verification.validation_prompt import build_validation_messages

logger = logging.getLogger(__name__)

# Fixed phrases in GUIDED mode that overwhelmingly signal the AI is just
# handing over the answer rather than guiding. Not exhaustive -- backstopped
# by the LLM reviewer below.
_GUIDED_RED_FLAG_PHRASES = (
    "the answer is",
    "the correct answer is",
    "here is the solution",
    "here's the solution",
    "the final answer is",
)


def rule_based_check(*, policy: AssistancePolicy, draft_response: str) -> list[str]:
    violations: list[str] = []
    if not draft_response or not draft_response.strip():
        violations.append("Response is empty.")
        return violations

    if policy == AssistancePolicy.GUIDED:
        lowered = draft_response.lower()
        for phrase in _GUIDED_RED_FLAG_PHRASES:
            if phrase in lowered:
                violations.append(
                    f"GUIDED policy violation: response contains answer-revealing phrase '{phrase}'."
                )
    return violations


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
    """Full validation pass. Rule violations are collected first (cheap);
    the LLM check still runs (unless disabled) to catch what rules can't."""

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
    return ValidationResult(passes=passes, violations=all_violations, revised_response=revised)
