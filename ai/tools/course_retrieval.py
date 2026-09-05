"""
Course-material retrieval tool.

The AI Coach only depends on this thin interface; the actual RAG pipeline
(ingestion/chunking/embeddings/vector DB -- see ai/rag/) is owned and
implemented separately and plugged in here via the `retriever` callable.

Course isolation is critical: this tool must never return material tagged
with a different course_id than the one requested.
"""
from __future__ import annotations

from typing import Callable, Optional, Protocol

from ai.models.schemas import RetrievedContext


class CourseRetriever(Protocol):
    def __call__(self, course_id: str, query: str, top_k: int = 4) -> list[RetrievedContext]:
        ...


def _fallback_retriever(course_id: str, query: str, top_k: int = 4) -> list[RetrievedContext]:
    """Used when no real retriever is wired up yet (e.g. early dev/tests)."""
    return []


class CourseRetrievalError(RuntimeError):
    """Raised when the underlying retriever fails."""


class CourseRetrievalTool:
    """Injectable wrapper so tests/dev can supply a fake retriever, and the
    real RAG module can be plugged in without touching the Coach graph."""

    name = "course_retriever"

    def __init__(self, retriever: Optional[CourseRetriever] = None):
        self._retriever: CourseRetriever = retriever or _fallback_retriever

    def retrieve(self, course_id: str, query: str, top_k: int = 4) -> list[RetrievedContext]:
        if not course_id:
            raise ValueError("course_id is required for course-scoped retrieval.")
        try:
            results = self._retriever(course_id, query, top_k)
        except Exception as exc:  # tool failures must not crash the graph
            raise CourseRetrievalError(str(exc)) from exc

        # Defense in depth: drop anything not tagged for this course, in
        # case the underlying retriever is misconfigured.
        return [r for r in results if r.metadata.get("course_id") in (None, course_id)]
