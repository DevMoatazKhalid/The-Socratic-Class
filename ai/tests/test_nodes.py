"""Unit tests for individual Coach graph nodes, with LLM calls mocked out."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from ai.agents.coach import nodes as nodes_mod
from ai.agents.coach.schemas import DiagnosisResult, GeneratedResponse, InterventionDecision
from ai.agents.coach.state import CoachState
from ai.models.schemas import (
    AssistancePolicy,
    Diagnosis,
    DiagnosisCategory,
    Intervention,
    InterventionType,
)
from ai.tools.course_retrieval import CourseRetrievalError, CourseRetrievalTool
from ai.tools.student_history import StudentHistoryTool
from ai.tests.conftest import FakeStructuredLLM


def _base_state(task_context, metadata, policy=AssistancePolicy.GUIDED, **overrides) -> CoachState:
    state: CoachState = {
        "task_context": task_context,
        "policy": policy,
        "metadata": metadata,
        "messages": [],
        "current_attempt": "theta = theta - prediction",
        "diagnosis": None,
        "intervention": None,
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
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# understand_context
# ---------------------------------------------------------------------------

def test_understand_context_records_attempt_and_increments_turn(task_context, metadata):
    state = _base_state(task_context, metadata)
    update = nodes_mod.understand_context(state)
    assert update["metadata"].turn_index == 1
    assert len(update["messages"]) == 1
    assert isinstance(update["messages"][0], HumanMessage)


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------

def test_diagnose_misconception(monkeypatch, task_context, metadata):
    fake_result = DiagnosisResult(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="learning_rate",
        explanation="Student updates theta directly by the prediction, not the gradient.",
        evidence="theta = theta - prediction",
        confidence=0.8,
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=fake_result)
    )

    state = _base_state(task_context, metadata)
    update = nodes_mod.diagnose(state)

    assert update["diagnosis"].category == DiagnosisCategory.MISCONCEPTION
    assert update["diagnosis"].concept == "learning_rate"


def test_diagnose_correct_reasoning_not_forced_into_misconception(monkeypatch, task_context, metadata):
    fake_result = DiagnosisResult(
        category=DiagnosisCategory.CORRECT_REASONING,
        concept=None,
        explanation="Gradient descent update is implemented correctly.",
        evidence="theta = theta - lr * gradient",
        confidence=0.9,
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=fake_result)
    )
    state = _base_state(task_context, metadata, current_attempt="theta = theta - lr * gradient")
    update = nodes_mod.diagnose(state)
    assert update["diagnosis"].category == DiagnosisCategory.CORRECT_REASONING


def test_diagnose_includes_prior_diagnosis_when_provided(monkeypatch, task_context, metadata):
    """Regression: diagnose() reads state["diagnosis"] to build a prior-turn
    summary for the prompt. If the caller supplies a prior diagnosis (via
    Coach.invoke(prior_diagnosis=...)), it must actually reach the prompt."""
    fake_result = DiagnosisResult(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="learning_rate",
        explanation="Still missing the learning-rate scaling.",
        evidence="theta = theta - gradient",
        confidence=0.75,
    )
    fake_llm = FakeStructuredLLM(result=fake_result)
    monkeypatch.setattr(nodes_mod, "get_structured_llm", lambda role, schema: fake_llm)

    prior_diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="gradient_descent",
        explanation="Updated theta directly by the prediction error.",
        evidence="theta = theta - prediction",
        confidence=0.8,
    )
    metadata.turn_index = 1  # about to become turn 2
    state = _base_state(
        task_context, metadata,
        current_attempt="theta = theta - gradient",
        diagnosis=prior_diagnosis,
    )
    nodes_mod.diagnose(state)

    assert len(fake_llm.calls) == 1
    prompt_text = "\n".join(m.content for m in fake_llm.calls[0])
    assert "gradient_descent" in prompt_text
    assert "MISCONCEPTION" in prompt_text


def test_diagnose_handles_llm_failure_gracefully(monkeypatch, task_context, metadata):
    monkeypatch.setattr(
        nodes_mod,
        "get_structured_llm",
        lambda role, schema: FakeStructuredLLM(raises=RuntimeError("provider down")),
    )
    state = _base_state(task_context, metadata)
    update = nodes_mod.diagnose(state)
    assert update["diagnosis"].category == DiagnosisCategory.UNCERTAIN
    assert update["errors"]


# ---------------------------------------------------------------------------
# choose_intervention
# ---------------------------------------------------------------------------

def test_choose_intervention_downgrades_explanation_under_guided_first_attempt(
    monkeypatch, task_context, metadata
):
    decision = InterventionDecision(
        intervention_type=InterventionType.EXPLANATION,
        rationale="Explaining directly seems efficient.",
        needs_course_material=False,
        needs_student_history=False,
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=decision)
    )
    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="learning_rate",
        explanation="...",
        evidence="...",
        confidence=0.7,
    )
    metadata.turn_index = 1  # first attempt
    state = _base_state(task_context, metadata, diagnosis=diagnosis)
    update = nodes_mod.choose_intervention(state)
    assert update["intervention"].type == InterventionType.QUESTION


def test_choose_intervention_allows_explanation_on_revision(monkeypatch, task_context, metadata):
    decision = InterventionDecision(
        intervention_type=InterventionType.EXPLANATION,
        rationale="Student is still stuck after a question; explain directly.",
        needs_course_material=False,
        needs_student_history=False,
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=decision)
    )
    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="learning_rate",
        explanation="...",
        evidence="...",
        confidence=0.7,
    )
    metadata.turn_index = 2  # this is a revision
    state = _base_state(task_context, metadata, diagnosis=diagnosis)
    update = nodes_mod.choose_intervention(state)
    assert update["intervention"].type == InterventionType.EXPLANATION


def test_choose_intervention_includes_previous_intervention_when_provided(
    monkeypatch, task_context, metadata
):
    """Regression: choose_intervention() reads state["intervention"] to tell
    the model what intervention was used last turn. If the caller supplies
    it (via Coach.invoke(prior_intervention=...)), it must reach the prompt
    instead of always rendering as "(none, first turn)"."""
    decision = InterventionDecision(
        intervention_type=InterventionType.HINT,
        rationale="Already asked a guiding question; escalate to a hint.",
        needs_course_material=False,
        needs_student_history=False,
    )
    fake_llm = FakeStructuredLLM(result=decision)
    monkeypatch.setattr(nodes_mod, "get_structured_llm", lambda role, schema: fake_llm)

    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="learning_rate",
        explanation="...",
        evidence="...",
        confidence=0.7,
    )
    prior_intervention = Intervention(
        type=InterventionType.QUESTION,
        assistance_level=AssistancePolicy.GUIDED,
        rationale="probed understanding last turn",
    )
    metadata.turn_index = 2
    state = _base_state(
        task_context, metadata,
        diagnosis=diagnosis,
        intervention=prior_intervention,
    )
    nodes_mod.choose_intervention(state)

    assert len(fake_llm.calls) == 1
    prompt_text = "\n".join(m.content for m in fake_llm.calls[0])
    assert "QUESTION" in prompt_text
    assert "(none, first turn)" not in prompt_text


def test_choose_intervention_adapts_after_revision_changes_diagnosis(monkeypatch, task_context, metadata):
    """Section 14: a changed diagnosis on revision should be able to produce
    a different intervention than the previous turn."""
    decisions = iter(
        [
            InterventionDecision(intervention_type=InterventionType.QUESTION, rationale="probe understanding"),
            InterventionDecision(intervention_type=InterventionType.GUIDED_DEBUGGING, rationale="still confused, debug together"),
        ]
    )
    monkeypatch.setattr(
        nodes_mod,
        "get_structured_llm",
        lambda role, schema: FakeStructuredLLM(side_effect=lambda messages: next(decisions)),
    )

    diagnosis1 = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION, concept="learning_rate",
        explanation="e1", evidence="ev1", confidence=0.6,
    )
    metadata.turn_index = 1
    state1 = _base_state(task_context, metadata, diagnosis=diagnosis1)
    result1 = nodes_mod.choose_intervention(state1)

    diagnosis2 = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION, concept="gradient_vs_learning_rate",
        explanation="e2", evidence="ev2", confidence=0.6,
    )
    metadata.turn_index = 2
    state2 = _base_state(
        task_context, metadata, diagnosis=diagnosis2, intervention=result1["intervention"]
    )
    result2 = nodes_mod.choose_intervention(state2)

    assert result1["intervention"].type != result2["intervention"].type


def test_choose_intervention_handles_llm_failure_gracefully(monkeypatch, task_context, metadata):
    monkeypatch.setattr(
        nodes_mod,
        "get_structured_llm",
        lambda role, schema: FakeStructuredLLM(raises=RuntimeError("provider down")),
    )
    diagnosis = Diagnosis(
        category=DiagnosisCategory.CORRECT_REASONING, concept=None,
        explanation="ok", evidence="ok", confidence=0.9,
    )
    state = _base_state(task_context, metadata, diagnosis=diagnosis)
    update = nodes_mod.choose_intervention(state)
    assert update["intervention"].type == InterventionType.ENCOURAGEMENT
    assert update["errors"]


def test_choose_intervention_forces_clarification_on_low_confidence(monkeypatch, task_context, metadata):
    """FIX 2: Low-confidence diagnosis (confidence < 0.4) forces CLARIFICATION
    when the LLM selects a more committal intervention like EXPLANATION."""
    decision = InterventionDecision(
        intervention_type=InterventionType.EXPLANATION,
        rationale="Explaining directly seems best.",
        needs_course_material=False,
        needs_student_history=False,
    )
    fake_llm = FakeStructuredLLM(result=decision)
    monkeypatch.setattr(nodes_mod, "get_structured_llm", lambda role, schema: fake_llm)

    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION,
        concept="learning_rate",
        explanation="Unclear if student understands step size.",
        evidence="theta = theta - prediction",
        confidence=0.3,
    )
    metadata.turn_index = 2  # Even on revision where EXPLANATION is normally allowed
    state = _base_state(task_context, metadata, diagnosis=diagnosis)
    update = nodes_mod.choose_intervention(state)

    # Must be forced to CLARIFICATION due to low confidence
    assert update["intervention"].type == InterventionType.CLARIFICATION
    assert "uncertainty threshold" in update["intervention"].rationale

    # Verify confidence was passed into the prompt
    assert len(fake_llm.calls) == 1
    prompt_text = "\n".join(m.content for m in fake_llm.calls[0])
    assert "0.30" in prompt_text

    # Verify existing response-generation flow remains valid
    state["intervention"] = update["intervention"]
    resp_result = GeneratedResponse(
        response="Could you clarify what you intended by subtracting prediction?",
        referenced_concepts=["learning_rate"],
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=resp_result)
    )
    gen_update = nodes_mod.generate_response(state)
    assert gen_update["response"] == resp_result.response


def test_choose_intervention_forces_clarification_for_uncertain_category(
    monkeypatch, task_context, metadata
):
    """FIX 3: DiagnosisCategory.UNCERTAIN deterministically forces CLARIFICATION
    regardless of what the LLM returns, even if confidence is reported as high."""
    decision = InterventionDecision(
        intervention_type=InterventionType.HINT,
        rationale="Give a small hint to nudge the student.",
        needs_course_material=False,
        needs_student_history=False,
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=decision)
    )

    diagnosis = Diagnosis(
        category=DiagnosisCategory.UNCERTAIN,
        concept=None,
        explanation="Attempt is completely ambiguous.",
        evidence="???",
        confidence=0.9,  # High confidence in being uncertain
    )
    state = _base_state(task_context, metadata, diagnosis=diagnosis)
    update = nodes_mod.choose_intervention(state)

    assert update["intervention"].type == InterventionType.CLARIFICATION
    assert "category is UNCERTAIN" in update["intervention"].rationale


# ---------------------------------------------------------------------------
# retrieve_context
# ---------------------------------------------------------------------------

def test_retrieve_context_handles_course_tool_failure_gracefully(task_context, metadata):
    def broken_retriever(course_id, query, top_k=4):
        raise RuntimeError("vector db unreachable")

    course_tool = CourseRetrievalTool(retriever=broken_retriever)
    history_tool = StudentHistoryTool()
    node = nodes_mod.make_retrieve_context_node(course_tool, history_tool)

    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION, concept="learning_rate",
        explanation="e", evidence="ev", confidence=0.7,
    )
    state = _base_state(task_context, metadata, diagnosis=diagnosis, needs_course_material=True)

    update = node(state)
    # Must not raise -- retrieval failure degrades gracefully.
    assert update["retrieved_context"] == []
    assert update["errors"]
    assert course_tool.name not in update["tools_used"]


# ---------------------------------------------------------------------------
# generate_response
# ---------------------------------------------------------------------------

def test_generate_response_success(monkeypatch, task_context, metadata):
    fake_result = GeneratedResponse(
        response="What does the learning rate control in each parameter update?",
        referenced_concepts=["learning_rate", "gradient_descent"],
    )
    monkeypatch.setattr(
        nodes_mod, "get_structured_llm", lambda role, schema: FakeStructuredLLM(result=fake_result)
    )
    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION, concept="learning_rate",
        explanation="e", evidence="ev", confidence=0.7,
    )
    from ai.models.schemas import Intervention

    intervention = Intervention(
        type=InterventionType.QUESTION, assistance_level=AssistancePolicy.GUIDED, rationale="probe"
    )
    state = _base_state(task_context, metadata, diagnosis=diagnosis, intervention=intervention)
    update = nodes_mod.generate_response(state)
    assert "learning rate" in update["response"].lower()
    assert "learning_rate" in update["referenced_concepts"]


def test_generate_response_handles_llm_failure_gracefully(monkeypatch, task_context, metadata):
    monkeypatch.setattr(
        nodes_mod,
        "get_structured_llm",
        lambda role, schema: FakeStructuredLLM(raises=RuntimeError("provider down")),
    )
    diagnosis = Diagnosis(
        category=DiagnosisCategory.MISCONCEPTION, concept="learning_rate",
        explanation="e", evidence="ev", confidence=0.7,
    )
    from ai.models.schemas import Intervention

    intervention = Intervention(
        type=InterventionType.QUESTION, assistance_level=AssistancePolicy.GUIDED, rationale="probe"
    )
    state = _base_state(task_context, metadata, diagnosis=diagnosis, intervention=intervention)
    update = nodes_mod.generate_response(state)
    assert update["response"]  # falls back to a safe message, doesn't crash
    assert update["errors"]


# ---------------------------------------------------------------------------
# emit_interaction
# ---------------------------------------------------------------------------

def test_emit_interaction_appends_ai_message(task_context, metadata):
    state = _base_state(task_context, metadata, response="Here's a question for you.")
    update = nodes_mod.emit_interaction(state)
    assert isinstance(update["messages"][0], AIMessage)
    assert update["messages"][0].content == "Here's a question for you."
