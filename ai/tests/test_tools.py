"""Unit tests for the Coach's tool interfaces."""
from __future__ import annotations

import pytest

from ai.models.schemas import RetrievedContext
from ai.tools.code_analysis import CodeAnalysisTool
from ai.tools.course_retrieval import CourseRetrievalError, CourseRetrievalTool
from ai.tools.student_history import StudentHistoryError, StudentHistoryTool


def test_course_retrieval_filters_out_other_courses():
    def fake_retriever(course_id, query, top_k=4):
        return [
            RetrievedContext(source="lecture1", content="gradient descent", metadata={"course_id": "course_a"}),
            RetrievedContext(source="lecture2", content="unrelated", metadata={"course_id": "course_b"}),
            RetrievedContext(source="lecture3", content="no course tag"),
        ]

    tool = CourseRetrievalTool(retriever=fake_retriever)
    results = tool.retrieve("course_a", "gradient descent")
    sources = {r.source for r in results}
    assert sources == {"lecture1", "lecture3"}


def test_course_retrieval_requires_course_id():
    tool = CourseRetrievalTool()
    with pytest.raises(ValueError):
        tool.retrieve("", "query")


def test_course_retrieval_wraps_underlying_errors():
    def broken_retriever(course_id, query, top_k=4):
        raise RuntimeError("vector db down")

    tool = CourseRetrievalTool(retriever=broken_retriever)
    with pytest.raises(CourseRetrievalError):
        tool.retrieve("course_a", "query")


def test_student_history_wraps_underlying_errors():
    def broken_provider(student_id, assignment_id, concept=None, limit=3):
        raise RuntimeError("db timeout")

    tool = StudentHistoryTool(provider=broken_provider)
    with pytest.raises(StudentHistoryError):
        tool.retrieve("s1", "a1")


def test_student_history_default_provider_returns_empty():
    tool = StudentHistoryTool()
    assert tool.retrieve("s1", "a1") == []


def test_code_analysis_valid_syntax():
    tool = CodeAnalysisTool()
    code = "def f(x):\n    for i in range(10):\n        x = x + i\n    return x\n"
    result = tool.analyze(code)
    assert result.is_valid_syntax
    assert "f" in result.defined_functions
    assert result.loops == 1


def test_code_analysis_invalid_syntax():
    tool = CodeAnalysisTool()
    result = tool.analyze("def f(x:\n    return x")
    assert not result.is_valid_syntax
    assert result.syntax_error
