"""Regression tests for the Final Hardening invariants (A–P).

These tests verify that the critical safety invariants hold after the
hardening pass, covering:
- Final-answer leakage blocked under ALL policies (GUIDED, ASSISTED, OPEN)
- Validator rewrite bypass fixed
- Deterministic final-answer enforcement
- Safe fallback content safety
- First-turn GUIDED explanation downgrade
- Risk signal extraction and observable reporting
"""
from __future__ import annotations

import pytest

from ai.agents.coach import nodes as nodes_mod
from ai.agents.coach.schemas import ValidationResult
from ai.agents.coach.state import CoachState
from ai.guardrails import coach_validator
from ai.guardrails.coach_validator import final_answer_enforcement, rule_based_check
from ai.models.schemas import (
    AssistancePolicy,
    Diagnosis,
    DiagnosisCategory,
    Intervention,
    InterventionType,
)
from ai.tests.conftest import FakeStructuredLLM


# ── Helper ────────────────────────────────────────────────────────────────

def _base_state(task_context, metadata, policy=AssistancePolicy.GUIDED, **overrides) -> CoachState:
    state: CoachState = {
        "task_context": task_context,
        "policy": policy,
        "metadata": metadata,
        "messages": [],
        "current_attempt": "theta = theta - prediction",
        "diagnosis": Diagnosis(
            category=DiagnosisCategory.MISCONCEPTION,
            concept="learning_rate",
            explanation="Wrong update rule.",
            evidence="theta = theta - prediction",
            confidence=0.7,
        ),
        "intervention": Intervention(
            type=InterventionType.QUESTION,
            assistance_level=policy,
            rationale="probe",
        ),
        "retrieved_context": [],
        "tools_used": [],
        "needs_course_material": False,
        "needs_student_history": False,
        "response": None,
        "referenced_concepts": [],
        "validation_passed": None,
        "validation_violations": [],
        "retry_count": 0,
        "errors": [],
        "code_analysis": None,
        "evidence_candidates": [],
        "risk_signals": [],
    }
    state.update(overrides)
    return state


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT A: GUIDED blocks answer-revealing phrases
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantA_GuidedBlocksAnswers:
    @pytest.mark.parametrize("phrase", [
        "The answer is 42",
        "The correct answer is theta - lr * grad",
        "Here is the solution: x = 5",
        "The final answer is 3.14",
        "The solution is straightforward: use recursion",
    ])
    def test_guided_blocks_answer_phrase(self, phrase):
        violations = rule_based_check(
            policy=AssistancePolicy.GUIDED, draft_response=phrase
        )
        assert violations, f"Expected violation for GUIDED + '{phrase}'"


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT B: ASSISTED blocks answer-revealing phrases
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantB_AssistedBlocksAnswers:
    @pytest.mark.parametrize("phrase", [
        "The answer is 42",
        "The correct answer is theta - lr * grad",
        "Here is the solution: x = 5",
        "The final answer is 3.14",
    ])
    def test_assisted_blocks_answer_phrase(self, phrase):
        violations = rule_based_check(
            policy=AssistancePolicy.ASSISTED, draft_response=phrase
        )
        assert violations, f"Expected violation for ASSISTED + '{phrase}'"


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT C: OPEN blocks answer-revealing phrases
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantC_OpenBlocksAnswers:
    @pytest.mark.parametrize("phrase", [
        "The answer is 42",
        "The correct answer is theta - lr * grad",
        "Here is the solution: x = 5",
        "The final answer is 3.14",
    ])
    def test_open_blocks_answer_phrase(self, phrase):
        violations = rule_based_check(
            policy=AssistancePolicy.OPEN, draft_response=phrase
        )
        assert violations, f"Expected violation for OPEN + '{phrase}'"


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT D: Safe pedagogical responses pass all policies
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantD_SafeResponsesPass:
    @pytest.mark.parametrize("policy", list(AssistancePolicy))
    def test_safe_question_passes(self, policy):
        violations = rule_based_check(
            policy=policy,
            draft_response="What do you think happens when the learning rate is too large?",
        )
        assert not violations

    @pytest.mark.parametrize("policy", list(AssistancePolicy))
    def test_safe_hint_passes(self, policy):
        violations = rule_based_check(
            policy=policy,
            draft_response="Think about how the gradient relates to the direction of steepest descent.",
        )
        assert not violations


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT E: Deterministic final_answer_enforcement works
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantE_FinalAnswerEnforcement:
    def test_blocks_answer_phrase(self):
        is_safe, result = final_answer_enforcement("The answer is 42.")
        assert not is_safe
        assert "walk me through" in result.lower()

    def test_blocks_regex_pattern(self):
        is_safe, result = final_answer_enforcement(
            "The correct solution would be to use a recursive approach."
        )
        assert not is_safe

    def test_passes_safe_response(self):
        safe = "What happens when you multiply theta by the learning rate?"
        is_safe, result = final_answer_enforcement(safe)
        assert is_safe
        assert result == safe

    def test_blocks_empty_response(self):
        is_safe, _ = final_answer_enforcement("")
        assert not is_safe

    def test_blocks_whitespace_only(self):
        is_safe, _ = final_answer_enforcement("   ")
        assert not is_safe


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT F: Validator rewrite bypass is fixed
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantF_ValidatorRewriteBypass:
    def test_unsafe_revised_response_is_rejected(self, monkeypatch, task_context, metadata):
        """If the LLM validator proposes a revised_response that contains
        an answer-revealing phrase, it MUST be rejected (not passed through)."""
        def fake_validate(**kwargs):
            return ValidationResult(
                passes=False,
                violations=["original was off-topic"],
                revised_response="The answer is 42. Does that help?",
            )

        monkeypatch.setattr(nodes_mod, "validate_response", fake_validate)

        state = _base_state(task_context, metadata, response="some draft")
        update = nodes_mod.validate(state)

        # The unsafe rewrite should NOT be accepted directly as an answer.
        assert update.get("validation_passed") is not True or \
               update.get("response") != "The answer is 42. Does that help?"

    def test_safe_revised_response_is_accepted(self, monkeypatch, task_context, metadata):
        """A safe revised_response should be accepted after enforcement."""
        safe_rewrite = "What part of the gradient calculation are you unsure about?"

        def fake_validate(**kwargs):
            return ValidationResult(
                passes=False,
                violations=["original was too direct"],
                revised_response=safe_rewrite,
            )

        monkeypatch.setattr(nodes_mod, "validate_response", fake_validate)

        state = _base_state(task_context, metadata, response="some draft")
        update = nodes_mod.validate(state)

        assert update["validation_passed"] is True
        assert update["response"] == safe_rewrite


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT G: Safe fallback content is actually safe
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantG_SafeFallbackContent:
    @pytest.mark.parametrize("policy", list(AssistancePolicy))
    def test_safe_fallback_passes_enforcement(self, policy, task_context, metadata):
        state = _base_state(task_context, metadata, policy=policy)
        update = nodes_mod.safe_fallback_response(state)
        fallback = update["response"]
        is_safe, _ = final_answer_enforcement(fallback)
        assert is_safe, f"Safe fallback for {policy.value} failed enforcement: {fallback}"

    @pytest.mark.parametrize("policy", list(AssistancePolicy))
    def test_safe_fallback_has_no_rule_violations(self, policy, task_context, metadata):
        state = _base_state(task_context, metadata, policy=policy)
        update = nodes_mod.safe_fallback_response(state)
        violations = rule_based_check(policy=policy, draft_response=update["response"])
        assert not violations


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT H: First-attempt GUIDED explanation downgrade
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantH_GuidedDowngradeFirstAttempt:
    def test_explanation_downgraded_on_first_attempt(self, monkeypatch, task_context, metadata):
        from ai.agents.coach.schemas import InterventionDecision

        decision = InterventionDecision(
            intervention_type=InterventionType.EXPLANATION,
            rationale="explain",
            needs_course_material=False,
            needs_student_history=False,
        )
        monkeypatch.setattr(
            nodes_mod, "get_structured_llm",
            lambda role, schema: FakeStructuredLLM(result=decision),
        )
        metadata.turn_index = 1
        state = _base_state(task_context, metadata)
        update = nodes_mod.choose_intervention(state)
        assert update["intervention"].type == InterventionType.QUESTION


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT I: GUIDED allows EXPLANATION for CORRECT_REASONING
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantI_GuidedAllowsExplanationForCorrect:
    def test_correct_reasoning_keeps_explanation(self, monkeypatch, task_context, metadata):
        from ai.agents.coach.schemas import InterventionDecision

        decision = InterventionDecision(
            intervention_type=InterventionType.EXPLANATION,
            rationale="student is correct, explain further",
        )
        monkeypatch.setattr(
            nodes_mod, "get_structured_llm",
            lambda role, schema: FakeStructuredLLM(result=decision),
        )
        state = _base_state(
            task_context, metadata,
            diagnosis=Diagnosis(
                category=DiagnosisCategory.CORRECT_REASONING,
                concept=None,
                explanation="Correct!",
                evidence="good code",
                confidence=0.9,
            ),
        )
        update = nodes_mod.choose_intervention(state)
        assert update["intervention"].type == InterventionType.EXPLANATION


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT J: Deterministic enforcement catches post-LLM violations
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantJ_PostLLMEnforcement:
    def test_enforcement_catches_passed_but_unsafe_response(self, monkeypatch, task_context, metadata):
        """If LLM validation passes but the response contains an answer-revealing
        phrase, deterministic enforcement should replace it."""
        def fake_validate(**kwargs):
            return ValidationResult(passes=True, violations=[])

        monkeypatch.setattr(nodes_mod, "validate_response", fake_validate)

        state = _base_state(
            task_context, metadata,
            response="The answer is theta = theta - lr * gradient.",
        )
        update = nodes_mod.validate(state)

        # Should still be marked as passed (with safe replacement)
        assert update["validation_passed"] is True
        # But the response must NOT contain the original answer
        assert "the answer is" not in update.get("response", "").lower()


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT K: emit_interaction enforces final answer check
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantK_EmitInteractionEnforcement:
    def test_emit_replaces_unsafe_response(self, task_context, metadata):
        state = _base_state(
            task_context, metadata,
            response="The answer is 42.",
        )
        update = nodes_mod.emit_interaction(state)
        # The emitted message must NOT contain the original answer
        assert "the answer is" not in update["messages"][0].content.lower()

    def test_emit_passes_safe_response(self, task_context, metadata):
        safe = "What do you think would happen if you used a different learning rate?"
        state = _base_state(task_context, metadata, response=safe)
        update = nodes_mod.emit_interaction(state)
        assert update["messages"][0].content == safe


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT L: validate_response re-checks LLM revised_response
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantL_RevalidateRevisedResponse:
    def test_unsafe_llm_rewrite_discarded_at_validate_response_level(self, monkeypatch):
        """If LLM produces a revised_response that itself violates rules,
        validate_response() should discard it."""
        def fake_llm_check(**kwargs):
            return ValidationResult(
                passes=False,
                violations=["off-topic"],
                revised_response="The answer is definitely x = 5.",
            )

        monkeypatch.setattr(coach_validator, "llm_check", fake_llm_check)

        result = coach_validator.validate_response(
            policy=AssistancePolicy.GUIDED,
            diagnosis_category="MISCONCEPTION",
            diagnosis_confidence=0.7,
            intervention_type="QUESTION",
            course_material="",
            draft_response="Something off-topic.",
            use_llm=True,
        )
        # The revised_response should have been discarded
        assert result.revised_response is None


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT M: GUIDED extra phrases only flagged under GUIDED
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantM_GuidedExtraPhrasesOnlyGuided:
    def test_guided_extra_phrase_flagged(self):
        violations = rule_based_check(
            policy=AssistancePolicy.GUIDED,
            draft_response="The formula is F = ma, just use it directly.",
        )
        assert any("direct-answer" in v for v in violations)

    def test_open_does_not_flag_guided_extra_phrases(self):
        violations = rule_based_check(
            policy=AssistancePolicy.OPEN,
            draft_response="The formula is F = ma, try applying it.",
        )
        # OPEN should NOT flag GUIDED-extra phrases
        assert not any("direct-answer" in v for v in violations)


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT N: Empty response is always flagged
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantN_EmptyResponse:
    @pytest.mark.parametrize("policy", list(AssistancePolicy))
    def test_empty_response_flagged(self, policy):
        violations = rule_based_check(policy=policy, draft_response="")
        assert violations == ["Response is empty."]

    @pytest.mark.parametrize("policy", list(AssistancePolicy))
    def test_whitespace_response_flagged(self, policy):
        violations = rule_based_check(policy=policy, draft_response="   \n  ")
        assert violations == ["Response is empty."]


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT O: Risk signals are deterministic and observable
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantO_RiskSignals:
    def test_style_shift_signal_detected(self, task_context, metadata):
        from langchain_core.messages import HumanMessage
        from ai.agents.coach.evidence import extract_risk_signals

        metadata.turn_index = 2
        state = _base_state(
            task_context, metadata,
            messages=[
                HumanMessage(content="i dont know how to do this"),
                HumanMessage(content=(
                    '```python\ndef gradient_descent(X, y, lr=0.01):\n'
                    '    """Performs gradient descent."""\n'
                    '    # Initialize weights\n'
                    '    w = np.zeros(X.shape[1])\n'
                    '    for i in range(1000):\n'
                    '        grad = compute_gradient(X, y, w)\n'
                    '        w = w - lr * grad\n'
                    '    return w\n```'
                )),
            ],
        )
        signals = extract_risk_signals(state)
        signal_names = [s.signal for s in signals]
        assert "style_shift_between_attempts" in signal_names


# ═══════════════════════════════════════════════════════════════════════════
# INVARIANT P: Coach never claims student used external AI
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariantP_NoCheatingClaims:
    def test_risk_signals_use_observable_language(self, task_context, metadata):
        """Risk signals must use 'observable' language, never 'cheating' or 'AI-generated'."""
        from langchain_core.messages import HumanMessage
        from ai.agents.coach.evidence import extract_risk_signals

        metadata.turn_index = 2
        state = _base_state(
            task_context, metadata,
            messages=[
                HumanMessage(content="x"),
                HumanMessage(content="a" * 400),
            ],
        )
        signals = extract_risk_signals(state)
        for signal in signals:
            assert "cheat" not in signal.observation.lower()
            assert "ai-generated" not in signal.observation.lower()
            assert "used chatgpt" not in signal.observation.lower()
