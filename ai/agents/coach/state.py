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
from pydantic import BaseModel
from typing_extensions import TypedDict

from ai.models.schemas import AssistancePolicy, Diagnosis, Intervention, RetrievedContext


class TaskContext(BaseModel):
    """Static context about the assignment the student is working on."""

    assignment_id: str
    course_id: str
    title: str
    instructions: str
    subject_area: Optional[str] = None
    is_programming: bool = False


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
    diagnosis: Optional[Diagnosis]
    intervention: Optional[Intervention]
    retrieved_context: list[RetrievedContext]
    tools_used: list[str]
    needs_course_material: bool
    needs_student_history: bool
    response: Optional[str]
    referenced_concepts: list[str]

    # --- validation / control flow ---
    validation_passed: Optional[bool]
    validation_violations: list[str]
    retry_count: int
    errors: list[str]
