# Architecture Decision Records (ADRs)

This document captures the architectural decisions made for **The Socratic Class** AI Coach and Learning Verification subsystems, detailing the context, decisions, and consequences.

---

## ADR-001: Centralized Environment-Driven Model Abstraction
- **Status**: Accepted
- **Context**: The application must support multiple LLM backends (OpenAI, Anthropic, NVIDIA NIM, OpenAI-compatible local/hosted endpoints) without code changes or hardcoded keys.
- **Decision**: Implemented `ai/config.py` and `ai/models/llm.py` with `ModelRole` (`COACH`, `REASONING`, `LIGHTWEIGHT`, `VERIFICATION`), role-specific temperature/timeout/model overrides via `.env`, and secret masking.
- **Consequences**: Easy configuration via `.env` with fail-fast validation and zero risk of leaking keys in logs.

---

## ADR-002: Separation of Response Validation vs. Learning Verification
- **Status**: Accepted
- **Context**: "Validation" can refer to (a) an internal guardrail checking that the Coach's draft output doesn't leak answers, or (b) a student-facing assessment verifying authentic understanding.
- **Decision**:
  - **Response Validation** (`ai/guardrails/coach_validator.py`): A guardrail running inside the Coach LangGraph graph before messages reach the student. Uses `ModelRole.LIGHTWEIGHT`.
  - **Learning Verification** (`ai/verification/`): An independent student-facing assessment service outside the LangGraph graph with Explain, Modify, and Transfer tasks. Uses `ModelRole.VERIFICATION`.
- **Consequences**: Clean separation of concerns; no confusing prompt layout; independent scaling and evaluation.

---

## ADR-003: Observable Evidence Candidates vs. Mastery Scores
- **Status**: Accepted
- **Context**: Student analytics needs to track learning without the AI Coach making arbitrary claims of "mastery" or "cheating".
- **Decision**:
  - The Coach emits discrete, observable `LearningEvidenceCandidate` records (`UNDERSTANDING`, `MISCONCEPTION`, `REVISION`, `INDEPENDENCE`, `EXPLANATION`, `TRANSFER`) linked to `learning_event.id`.
  - The Coach detects cautious structural anomalies as `ExternalAIRiskSignal` (e.g. `unusually_large_attempt_jump`), never claiming the student cheated.
  - Final mastery scoring and risk assessment are downstream analytics responsibilities.
- **Consequences**: Pedagogical claims remain transparent, calibrated, and audit-traceable.

---

## ADR-004: AST-Only Non-Executing Code Analysis
- **Status**: Accepted
- **Context**: Programming assignments need code understanding, but executing untrusted student code inside the AI process poses severe security and resource risks.
- **Decision**: `CodeAnalysisTool` performs safe, static Python AST analysis only (syntax validity, defined functions, variables, loops). Student code is **never** executed. Non-Python code explicitly returns `is_supported_language=False` rather than falsely claiming valid syntax.
- **Consequences**: Zero remote code execution vulnerabilities; lightweight static signals inform diagnosis safely.

---

## ADR-005: Strict Multi-Tenant Course Isolation in RAG Retrieval
- **Status**: Accepted
- **Context**: Multiple courses share the platform. Misconfigured retrievers or untagged chunks could leak lecture notes or solution hints across courses.
- **Decision**: `CourseRetrievalTool` defaults to `strict_isolation=True`, dropping any retrieved context where `chunk.metadata.get("course_id") != requested_course_id`. Untagged chunks are rejected.
- **Consequences**: Complete defense-in-depth isolation preventing cross-course information leaks.

---

## ADR-006: Deterministic Policy Enforcement in Code
- **Status**: Accepted
- **Context**: LLMs can fail to follow prompt instructions, especially when prompted to explain concepts without revealing the answer under strict Socratic policies (`GUIDED`).
- **Decision**: Enforced critical pedagogical constraints in Python code (`ai/agents/coach/nodes.py`): on a student's first attempt under `GUIDED`, if the model selects `EXPLANATION`, the code deterministically downgrades the intervention to `QUESTION` unless the student's reasoning is already correct.
- **Consequences**: Guarantees Socratic scaffolding without relying solely on model compliance.

---

## ADR-007: Strategy Pattern for Independent Learning Verification
- **Status**: Accepted
- **Context**: Testing student understanding requires distinct conceptual dimensions: explaining mechanisms, modifying solutions for new constraints, and transferring concepts to novel domains.
- **Decision**: Implemented `ai/verification/strategies/` using the Strategy pattern (`ExplainStrategy`, `ModifyStrategy`, `TransferStrategy`) orchestrated by `VerificationService`.
- **Consequences**: New verification strategies can be added modularly; evaluation returns structured outcomes (`PASS`, `PARTIAL`, `NEEDS_RETRY`, `INSUFFICIENT_EVIDENCE`) and emits evidence candidates.

---

## ADR-008: HTTP DTO Contracts and Backend Decoupling
- **Status**: Accepted
- **Context**: The AI package must integrate smoothly into the FastAPI backend without exposing LangGraph internal state or creating circular dependencies.
- **Decision**: Defined `ai/contracts/coach_contract.py` containing Pydantic DTOs (`CoachApiRequest`, `CoachApiResponse`, `VerificationChallengeApiRequest`, etc.) and adapter functions (`run_coach_turn`).
- **Consequences**: The FastAPI backend can implement endpoints cleanly by simply importing the contract DTOs and adapter functions.
