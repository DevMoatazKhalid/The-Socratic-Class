"""
Coach LangGraph assembly + public entry point.

Backend integration should only need `Coach.invoke(...)` (or the module-
level `get_default_coach()` helper) -- it does not need to know about
LangGraph internals. See docs/AI_SPEC.md for the full integration contract.
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

from ai.agents.coach.evidence import extract_evidence_candidates, extract_risk_signals
from ai.agents.coach.nodes import (
    choose_intervention,
    diagnose,
    emit_interaction,
    generate_response,
    make_analyze_code_node,
    make_retrieve_context_node,
    safe_fallback_response,
    understand_context,
    validate,
)
from ai.agents.coach.routing import (
    route_after_intervention,
    route_after_understand_context,
    route_after_validation,
)
from ai.agents.coach.state import CoachState, InteractionMetadata, TaskContext
from ai.models.schemas import (
    AIInteraction,
    AssistancePolicy,
    CoachResult,
    LearningEvent,
    LearningEventType,
)
from ai.tools.code_analysis import CodeAnalysisTool
from ai.tools.course_retrieval import CourseRetrievalTool
from ai.tools.student_history import StudentHistoryTool

logger = logging.getLogger(__name__)


def build_coach_graph(
    course_tool: Optional[CourseRetrievalTool] = None,
    history_tool: Optional[StudentHistoryTool] = None,
    code_tool: Optional[CodeAnalysisTool] = None,
) -> StateGraph:
    """Builds (but does not compile) the Coach StateGraph. Split out from
    `Coach` so tests can inspect/compile it with injected tools."""

    course_tool = course_tool or CourseRetrievalTool()
    history_tool = history_tool or StudentHistoryTool()
    code_tool = code_tool or CodeAnalysisTool()

    retrieve_context = make_retrieve_context_node(course_tool, history_tool)
    analyze_code = make_analyze_code_node(code_tool)

    graph = StateGraph(CoachState)
    graph.add_node("understand_context", understand_context)
    graph.add_node("analyze_code", analyze_code)
    graph.add_node("diagnose", diagnose)
    graph.add_node("choose_intervention", choose_intervention)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_response", generate_response)
    graph.add_node("validate", validate)
    graph.add_node("safe_fallback", safe_fallback_response)
    graph.add_node("emit_interaction", emit_interaction)

    graph.set_entry_point("understand_context")
    graph.add_conditional_edges(
        "understand_context",
        route_after_understand_context,
        {"analyze_code": "analyze_code", "diagnose": "diagnose"},
    )
    graph.add_edge("analyze_code", "diagnose")
    graph.add_edge("diagnose", "choose_intervention")
    graph.add_conditional_edges(
        "choose_intervention",
        route_after_intervention,
        {"retrieve_context": "retrieve_context", "generate_response": "generate_response"},
    )
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("generate_response", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "emit_interaction": "emit_interaction",
            "generate_response": "generate_response",
            "safe_fallback": "safe_fallback",
        },
    )
    graph.add_edge("safe_fallback", "emit_interaction")
    graph.add_edge("emit_interaction", END)

    return graph


class Coach:
    """Public entry point the backend integrates against."""

    def __init__(
        self,
        course_tool: Optional[CourseRetrievalTool] = None,
        history_tool: Optional[StudentHistoryTool] = None,
        code_tool: Optional[CodeAnalysisTool] = None,
    ):
        self._graph = build_coach_graph(course_tool, history_tool, code_tool).compile()

    def invoke(
        self,
        *,
        student_id: str,
        assignment_id: str,
        session_id: str,
        task_context: TaskContext,
        attempt: str,
        policy: AssistancePolicy,
        message: Optional[str] = None,
        conversation: Optional[list[BaseMessage]] = None,
        turn_index: int = 0,
    ) -> CoachResult:
        """Run one Coach turn.

        `attempt` is the student's current work (code/answer/explanation).
        `message` is an optional free-text message alongside the attempt
        (e.g. "can you check this?"); if provided it's appended to the
        attempt text so diagnosis/response see the full picture.
        `conversation` is prior turns for this session, already trimmed by
        the caller to a reasonable window -- the Coach does not load full
        history itself (section 10).
        """
        current_attempt = attempt if not message else f"{attempt}\n\nStudent message: {message}"

        initial_state: CoachState = {
            "task_context": task_context,
            "policy": policy,
            "metadata": InteractionMetadata(
                student_id=student_id,
                assignment_id=assignment_id,
                session_id=session_id,
                turn_index=turn_index,
            ),
            "messages": list(conversation or []),
            "current_attempt": current_attempt,
            "code_analysis": None,
            "diagnosis": None,
            "intervention": None,
            "evidence_candidates": [],
            "risk_signals": [],
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

        final_state = self._graph.invoke(initial_state)
        return self._to_result(final_state)

    @staticmethod
    def _to_result(state: CoachState) -> CoachResult:
        diagnosis = state["diagnosis"]
        intervention = state["intervention"]
        metadata = state["metadata"]

        interaction = AIInteraction(
            session_id=metadata.session_id,
            student_id=metadata.student_id,
            assignment_id=metadata.assignment_id,
            intervention_type=intervention.type,
            assistance_level=intervention.assistance_level,
            diagnosis=diagnosis,
            response=state.get("response") or "",
            referenced_concepts=state.get("referenced_concepts") or [],
            tools_used=state.get("tools_used") or [],
        )
        learning_event = LearningEvent(
            student_id=metadata.student_id,
            assignment_id=metadata.assignment_id,
            session_id=metadata.session_id,
            event_type=LearningEventType.AI_INTERACTION,
            payload=interaction.model_dump(mode="json"),
        )

        # Extract evidence candidates linked to the durable learning_event ID
        evidence_candidates = extract_evidence_candidates(state, source_event_id=learning_event.id)
        risk_signals = extract_risk_signals(state)

        # Enrich learning event payload with serialized evidence candidates and risk signals
        payload = dict(learning_event.payload)
        payload["evidence_candidates"] = [c.model_dump(mode="json") for c in evidence_candidates]
        payload["risk_signals"] = [s.model_dump(mode="json") for s in risk_signals]
        learning_event.payload = payload

        return CoachResult(
            response=state.get("response") or "",
            intervention=intervention,
            diagnosis_summary=diagnosis,
            referenced_concepts=state.get("referenced_concepts") or [],
            tools_used=state.get("tools_used") or [],
            learning_event=learning_event,
            evidence_candidates=evidence_candidates,
            risk_signals=risk_signals,
            metadata={
                "turn_index": metadata.turn_index,
                "errors": state.get("errors") or [],
                "validation_violations": state.get("validation_violations") or [],
            },
        )


_default_coach: Optional[Coach] = None


def get_default_coach() -> Coach:
    """Lazily-built shared Coach instance using default (no-op) tools --
    convenient for the backend to import without constructing one itself."""
    global _default_coach
    if _default_coach is None:
        _default_coach = Coach()
    return _default_coach
