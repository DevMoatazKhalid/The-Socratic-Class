"""
Coach working state.

This represents the *current learning interaction*, not the student's full
persistent profile. Long-term analytics fields (mastery/dependency scores,
etc.) must never live here -- see docs/AI_SPEC.md section on boundaries.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from ai.models.schemas import (
    AssistancePolicy,
    Diagnosis,
    ExternalAIRiskSignal,
    Intervention,
    LearningEvidenceCandidate,
    RetrievedContext,
)
from ai.tools.code_analysis import CodeAnalysisResult


class TaskContext(BaseModel):
    """Static context about the assignment the student is working on.

    Tenant scoping fields (university_id, classroom_id, allowed_document_ids)
    are populated exclusively by trusted backend session authorization.
    """

    assignment_id: str
    course_id: str
    title: str
    instructions: str
    subject_area: Optional[str] = None
    is_programming: bool = False
    # Supplied by trusted backend/session authorization, never student text.
    university_id: Optional[str] = None
    classroom_id: Optional[str] = None
    allowed_document_ids: list[str] = Field(default_factory=list)


class InteractionMetadata(BaseModel):
    student_id: str
    assignment_id: str
    session_id: str
    turn_index: int = 0


class CoachState(TypedDict, total=False):
    """LangGraph state dict for a single Coach graph execution."""

    # --- input / static context ---
    task_context: TaskContext
    policy: AssistancePolicy
    metadata: InteractionMetadata

    # --- conversation ---
    messages: Annotated[list[BaseMessage], add_messages]
    current_attempt: str

    # --- working products of the graph ---
    code_analysis: Optional[CodeAnalysisResult]
    diagnosis: Optional[Diagnosis]
    intervention: Optional[Intervention]
    retrieved_context: list[RetrievedContext]
    tools_used: list[str]
    needs_course_material: bool
    needs_student_history: bool
    response: Optional[str]
    referenced_concepts: list[str]
    evidence_candidates: list[LearningEvidenceCandidate]
    risk_signals: list[ExternalAIRiskSignal]

    # --- validation / control flow ---
    validation_passed: Optional[bool]
    validation_violations: list[str]
    retry_count: int
    errors: list[str]
