"""
LangGraph node implementations for the AI Coach.

Each node reads/writes ai.agents.coach.state.CoachState. LLM calls use the
model factory (ai.models.llm) and structured schemas
(ai.agents.coach.schemas); nothing here talks to a concrete provider SDK.
"""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ai.agents.coach.evidence import extract_evidence_candidates, extract_risk_signals
from ai.agents.coach.schemas import DiagnosisResult, GeneratedResponse, InterventionDecision
from ai.agents.coach.state import CoachState
from ai.guardrails.coach_validator import validate_response
from ai.models.llm import ModelRole, get_structured_llm
from ai.models.schemas import (
    AssistancePolicy,
    Diagnosis,
    DiagnosisCategory,
    Intervention,
    InterventionType,
    RetrievedContext,
)
from ai.prompts.coach.intervention_prompt import build_intervention_messages
from ai.prompts.coach.response_prompt import build_response_messages
from ai.prompts.diagnosis.diagnosis_prompt import build_diagnosis_messages
from ai.tools.code_analysis import CodeAnalysisResult, CodeAnalysisTool
from ai.tools.course_retrieval import CourseRetrievalTool
from ai.tools.student_history import StudentHistoryTool

logger = logging.getLogger(__name__)

MAX_CONVERSATION_MESSAGES = 8


def _conversation_summary(messages: list[BaseMessage]) -> str:
    recent = messages[-MAX_CONVERSATION_MESSAGES:]
    lines = []
    for m in recent:
        role = "Student" if isinstance(m, HumanMessage) else "Coach"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)


def _format_course_material(chunks: list[RetrievedContext]) -> str:
    if not chunks:
        return ""
    return "\n\n".join(f"[{c.source}] {c.content}" for c in chunks)


def _format_code_analysis(result: Optional[CodeAnalysisResult]) -> str:
    if not result:
        return ""
    if not result.is_supported_language:
        return f"Code analysis ({result.language}): {result.syntax_error}"
    lines = [f"Valid Python syntax: {result.is_valid_syntax}"]
    if not result.is_valid_syntax and result.syntax_error:
        lines.append(f"Syntax error: {result.syntax_error}")
    if result.defined_functions:
        lines.append(f"Defined functions: {', '.join(result.defined_functions)}")
    if result.defined_variables:
        lines.append(f"Defined variables: {', '.join(result.defined_variables)}")
    if result.loops > 0:
        lines.append(f"Loop constructs count: {result.loops}")
    lines.append(f"Line count: {result.line_count}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node: understand_context
# ---------------------------------------------------------------------------

def understand_context(state: CoachState) -> dict:
    """Normalizes incoming state, resets per-turn working fields, and
    records the student's current attempt in the conversation history."""
    errors = list(state.get("errors") or [])
    metadata = state["metadata"]
    metadata.turn_index = (metadata.turn_index or 0) + 1
    attempt_message = HumanMessage(content=state["current_attempt"])

    return {
        "messages": [attempt_message],
        "metadata": metadata,
        "code_analysis": None,
        "evidence_candidates": [],
        "risk_signals": [],
        "retrieved_context": [],
        "tools_used": [],
        "needs_course_material": False,
        "needs_student_history": False,
        "validation_violations": [],
        "validation_passed": None,
        "retry_count": 0,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Node: analyze_code
# ---------------------------------------------------------------------------

def make_analyze_code_node(code_tool: CodeAnalysisTool):
    def analyze_code(state: CoachState) -> dict:
        attempt = state.get("current_attempt") or ""
        tools_used = list(state.get("tools_used") or [])
        errors = list(state.get("errors") or [])
        try:
            result = code_tool.analyze(attempt)
            tools_used.append(code_tool.name)
            return {"code_analysis": result, "tools_used": tools_used}
        except Exception as exc:
            logger.warning("Code analysis failed, continuing without it: %s", exc)
            errors.append(f"analyze_code: {exc}")
            return {"code_analysis": None, "tools_used": tools_used, "errors": errors}

    return analyze_code


# ---------------------------------------------------------------------------
# Node: diagnose
# ---------------------------------------------------------------------------

def diagnose(state: CoachState) -> dict:
    task = state["task_context"]
    policy = state["policy"]
    messages = state.get("messages") or []
    is_revision = state["metadata"].turn_index > 1
    prior = state.get("diagnosis")
    prior_summary = f"{prior.category.value} (concept: {prior.concept or 'n/a'})" if prior else ""
    code_summary = _format_code_analysis(state.get("code_analysis"))

    prompt_messages = build_diagnosis_messages(
        assignment_title=task.title,
        assignment_instructions=task.instructions,
        policy=policy.value,
        is_revision=is_revision,
        course_material=_format_course_material(state.get("retrieved_context") or []),
        prior_diagnosis_summary=prior_summary,
        conversation_summary=_conversation_summary(messages),
        current_attempt=state["current_attempt"],
        code_analysis_summary=code_summary,
    )

    try:
        llm = get_structured_llm(ModelRole.REASONING, DiagnosisResult)
        result: DiagnosisResult = llm.invoke(prompt_messages)
        diagnosis = Diagnosis(
            category=result.category,
            concept=result.concept,
            explanation=result.explanation,
            evidence=result.evidence,
            confidence=result.confidence,
        )
        return {"diagnosis": diagnosis}
    except Exception as exc:
        logger.exception("Diagnosis LLM call failed.")
        diagnosis = Diagnosis(
            category=DiagnosisCategory.UNCERTAIN,
            concept=None,
            explanation="Diagnosis could not be completed due to an internal error.",
            evidence="",
            confidence=0.0,
        )
        errors = list(state.get("errors") or [])
        errors.append(f"diagnose: {exc}")
        return {"diagnosis": diagnosis, "errors": errors}


# ---------------------------------------------------------------------------
# Node: choose_intervention
# ---------------------------------------------------------------------------

def choose_intervention(state: CoachState) -> dict:
    diagnosis = state["diagnosis"]
    policy = state["policy"]
    prior_intervention = state.get("intervention")
    is_revision = state["metadata"].turn_index > 1

    prompt_messages = build_intervention_messages(
        policy=policy.value,
        diagnosis_category=diagnosis.category.value,
        diagnosis_concept=diagnosis.concept or "",
        diagnosis_explanation=diagnosis.explanation,
        is_revision=is_revision,
        previous_intervention=prior_intervention.type.value if prior_intervention else "",
        turn_index=state["metadata"].turn_index,
    )

    try:
        llm = get_structured_llm(ModelRole.LIGHTWEIGHT, InterventionDecision)
        decision: InterventionDecision = llm.invoke(prompt_messages)
        intervention_type = decision.intervention_type
        rationale = decision.rationale
        needs_course_material = decision.needs_course_material
        needs_student_history = decision.needs_student_history
    except Exception as exc:
        logger.exception("Intervention-selection LLM call failed.")
        # Safe deterministic fallback: encouragement for correct reasoning,
        # otherwise a guiding question.
        intervention_type = (
            InterventionType.ENCOURAGEMENT
            if diagnosis.category == DiagnosisCategory.CORRECT_REASONING
            else InterventionType.QUESTION
        )
        rationale = "Fallback selection after an internal error."
        needs_course_material = False
        needs_student_history = False
        errors = list(state.get("errors") or [])
        errors.append(f"choose_intervention: {exc}")
        intervention = Intervention(type=intervention_type, assistance_level=policy, rationale=rationale)
        return {
            "intervention": intervention,
            "needs_course_material": needs_course_material,
            "needs_student_history": needs_student_history,
            "errors": errors,
        }

    # Code-level enforcement of the policy (section 23): critical constraints
    # are enforced here, not left to the prompt alone. On a first attempt
    # under GUIDED, an EXPLANATION is too close to just giving the answer --
    # downgrade to a guiding QUESTION unless reasoning is already correct.
    if (
        policy == AssistancePolicy.GUIDED
        and intervention_type == InterventionType.EXPLANATION
        and diagnosis.category != DiagnosisCategory.CORRECT_REASONING
        and not is_revision
    ):
        intervention_type = InterventionType.QUESTION
        rationale += (
            " (downgraded from EXPLANATION to QUESTION to respect GUIDED policy on a first attempt.)"
        )

    intervention = Intervention(type=intervention_type, assistance_level=policy, rationale=rationale)
    return {
        "intervention": intervention,
        "needs_course_material": needs_course_material,
        "needs_student_history": needs_student_history,
    }


# ---------------------------------------------------------------------------
# Node: retrieve_context
# ---------------------------------------------------------------------------

def make_retrieve_context_node(course_tool: CourseRetrievalTool, history_tool: StudentHistoryTool):
    def retrieve_context(state: CoachState) -> dict:
        task = state["task_context"]
        metadata = state["metadata"]
        diagnosis = state["diagnosis"]
        retrieved: list[RetrievedContext] = []
        tools_used = list(state.get("tools_used") or [])
        errors = list(state.get("errors") or [])

        if state.get("needs_course_material"):
            try:
                query = diagnosis.concept or state["current_attempt"][:200]
                retrieved.extend(course_tool.retrieve(task.course_id, query))
                tools_used.append(course_tool.name)
            except Exception as exc:
                logger.warning("Course retrieval failed, continuing without it: %s", exc)
                errors.append(f"retrieve_context/course: {exc}")

        if state.get("needs_student_history"):
            try:
                retrieved.extend(
                    history_tool.retrieve(metadata.student_id, metadata.assignment_id, diagnosis.concept)
                )
                tools_used.append(history_tool.name)
            except Exception as exc:
                logger.warning("Student history retrieval failed, continuing without it: %s", exc)
                errors.append(f"retrieve_context/history: {exc}")

        return {"retrieved_context": retrieved, "tools_used": tools_used, "errors": errors}

    return retrieve_context


# ---------------------------------------------------------------------------
# Node: generate_response
# ---------------------------------------------------------------------------

def generate_response(state: CoachState) -> dict:
    policy = state["policy"]
    diagnosis = state["diagnosis"]
    intervention = state["intervention"]
    messages = state.get("messages") or []

    prompt_messages = build_response_messages(
        policy=policy.value,
        intervention_type=intervention.type.value,
        diagnosis_category=diagnosis.category.value,
        diagnosis_concept=diagnosis.concept,
        course_material=_format_course_material(state.get("retrieved_context") or []),
        conversation_summary=_conversation_summary(messages),
        current_attempt=state["current_attempt"],
    )

    try:
        llm = get_structured_llm(ModelRole.COACH, GeneratedResponse)
        result: GeneratedResponse = llm.invoke(prompt_messages)
        return {"response": result.response, "referenced_concepts": result.referenced_concepts}
    except Exception as exc:
        logger.exception("Response-generation LLM call failed.")
        errors = list(state.get("errors") or [])
        errors.append(f"generate_response: {exc}")
        fallback = (
            "I ran into an issue putting together a response. Could you try rephrasing your "
            "question, or ask again in a moment?"
        )
        return {"response": fallback, "referenced_concepts": [], "errors": errors}


# ---------------------------------------------------------------------------
# Node: validate
# ---------------------------------------------------------------------------

def validate(state: CoachState) -> dict:
    policy = state["policy"]
    diagnosis = state["diagnosis"]
    intervention = state["intervention"]
    draft = state.get("response") or ""
    course_material = _format_course_material(state.get("retrieved_context") or [])

    result = validate_response(
        policy=policy,
        diagnosis_category=diagnosis.category.value,
        diagnosis_confidence=diagnosis.confidence,
        intervention_type=intervention.type.value,
        course_material=course_material,
        draft_response=draft,
    )

    update: dict = {"validation_passed": result.passes, "validation_violations": list(result.violations)}
    if not result.passes and result.revised_response:
        # A safe, minimal fix was available -- use it instead of burning a
        # regeneration retry.
        update["response"] = result.revised_response
        update["validation_passed"] = True
    elif not result.passes:
        update["retry_count"] = state.get("retry_count", 0) + 1
    return update


def safe_fallback_response(state: CoachState) -> dict:
    """Used when validation fails repeatedly -- respond safely instead of
    looping forever or shipping a bad response."""
    policy = state["policy"]
    if policy == AssistancePolicy.GUIDED:
        fallback = (
            "Let's slow down for a second. Can you walk me through how you got to your current "
            "answer, step by step? That'll help me point you in the right direction."
        )
    else:
        fallback = (
            "I want to make sure I give you accurate guidance here -- could you share a bit more "
            "detail about where you're stuck?"
        )
    return {
        "response": fallback,
        "referenced_concepts": [],
        "validation_passed": True,
        "intervention": Intervention(
            type=InterventionType.CLARIFICATION,
            assistance_level=policy,
            rationale="Safe fallback after repeated validation failures.",
        ),
    }


# ---------------------------------------------------------------------------
# Node: emit_interaction
# ---------------------------------------------------------------------------

def emit_interaction(state: CoachState) -> dict:
    response = state.get("response") or ""
    evidence_candidates = extract_evidence_candidates(state)
    risk_signals = extract_risk_signals(state)
    return {
        "messages": [AIMessage(content=response)],
        "evidence_candidates": evidence_candidates,
        "risk_signals": risk_signals,
    }
