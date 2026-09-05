# AI Coach & Learning Verification — Integration Spec

Scope: this document covers the **AI Coach** (`ai/agents/coach/`) and **Learning Verification** (`ai/verification/`) subsystems. It details the runtime contracts, tools, policies, events, and integration surface exposed to the FastAPI backend.

---

## 1. Subsystem Boundaries

The AI package owns:
- **Diagnosis & Interventions**: Classifying student learning states and choosing appropriate pedagogical actions.
- **Socratic Tutoring**: Generating policy-governed conversational guidance without revealing answers.
- **Response Validation**: Guardrail checking to prevent answer leakage or policy breaches.
- **Observable Evidence & Risk Signals**: Emitting calibrated indicators linked to specific learning moments.
- **Learning Verification**: Generating and evaluating conceptual challenges across Explain, Modify, and Transfer modes.

The AI package explicitly does **not** own:
- Database persistence or direct SQL/ORM connections.
- Student authentication and session lifecycle management.
- The RAG ingestion/chunking pipeline (only a bounded retrieval interface is consumed).
- Longitudinal analytics (computing cumulative mastery scores or cheating verdicts).

---

## 2. Calling the Coach

```python
from ai.agents.coach import Coach, TaskContext
from ai.models.schemas import AssistancePolicy

coach = Coach()  # or Coach(course_tool=..., history_tool=..., code_tool=...)

task_context = TaskContext(
    assignment_id="asg_123",
    course_id="course_ml_101",
    title="Implement Linear Regression using Gradient Descent",
    instructions="Implement gradient descent to fit a linear regression model...",
    is_programming=True,
)

result = coach.invoke(
    student_id="student_42",
    assignment_id="asg_123",
    session_id="sess_abc",
    task_context=task_context,
    attempt="theta = theta - prediction",       # the student's current work
    message="is this right?",                    # optional accompanying message
    policy=AssistancePolicy.GUIDED,
    conversation=[],                              # prior turns, already windowed by the caller
    turn_index=0,                                 # 0 for the first turn in a session
)
```

The backend is responsible for:
- Constructing `TaskContext` from the assignment store.
- Tracking `session_id` and passing a reasonably-windowed `conversation` (recent 6-8 messages).
- Incrementing `turn_index` with each attempt/revision.
- Persisting `result.learning_event`, `result.evidence_candidates`, and displaying `result.response`.

---

## 3. Output Contract — `CoachResult`

```text
CoachResult
├── response: str                      # the message shown to the student
├── intervention: Intervention         # {type, assistance_level, rationale}
├── diagnosis_summary: Diagnosis       # {category, concept, explanation, evidence, confidence}
├── referenced_concepts: list[str]
├── tools_used: list[str]              # e.g. ["code_analysis", "course_retriever"]
├── learning_event: LearningEvent      # event_type=AI_INTERACTION, payload = AIInteraction
├── evidence_candidates: list[...]     # observable learning moments linked to learning_event.id
├── risk_signals: list[...]            # observable structural anomalies across attempts
└── metadata: dict                     # turn_index, internal errors (if any), validation notes
```

No internal chain-of-thought or hidden prompt reasoning is exposed to the student.

---

## 4. Tool Contracts

All tools are injectable constructor arguments to `Coach(...)`:

- **`CourseRetrievalTool`** (`ai/tools/course_retrieval.py`):
  `.retrieve(course_id, query, top_k=4) -> list[RetrievedContext]`.
  Enforces **strict course isolation** (`strict_isolation=True`): discards any chunks whose `course_id` does not match the requested course. Malformed or missing metadata is safely ignored.
- **`StudentHistoryTool`** (`ai/tools/student_history.py`):
  `.retrieve(student_id, assignment_id, concept=None, limit=3) -> list[RetrievedContext]`.
  Returns bounded prior learning events. Never loads full longitudinal profiles into state.
- **`AssignmentContextTool`** (`ai/tools/assignment_context.py`):
  `.get(assignment_id) -> Optional[TaskContext]`.
  Fallback interface for fetching assignment context when not passed in the request path.
- **`CodeAnalysisTool`** (`ai/tools/code_analysis.py`):
  `.analyze(code, language="python") -> CodeAnalysisResult`.
  Static Python AST analysis only (syntax validity, defined functions, variables, loop count). Does **not** execute student code. Explicitly sets `is_supported_language=False` for non-Python attempts.

---

## 5. Configuration & Environment Variables

All model configuration is managed through `ai/config.py` and `ai/models/llm.py`:

| Variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `openai` | `openai` \| `openai_compatible` \| `nvidia` \| `nvidia_nim` \| `anthropic` |
| `AI_API_KEY` | None | Provider API key (fail-fast validation) |
| `AI_BASE_URL` | None | Required for `openai_compatible`, `nvidia`, `nvidia_nim` |
| `AI_MODEL_DEFAULT` | `gpt-4o-mini` | Fallback model name across all roles |
| `AI_MODEL_<ROLE>` | None | Per-role model override (`COACH`, `REASONING`, `LIGHTWEIGHT`, `VERIFICATION`) |
| `AI_TEMPERATURE_DEFAULT` | `0.5` | Fallback sampling temperature |
| `AI_TEMPERATURE_REASONING`| `0.2` | Lower temperature for deterministic diagnosis |
| `AI_TIMEOUT` | `60.0` | Request timeout in seconds |
| `AI_MAX_RETRIES` | `2` | Maximum retry attempts on network error |

API keys are never printed in logs, representations, or error traces.

---

## 6. Learning Evidence Candidates & Risk Signals

- **Evidence Candidates** (`LearningEvidenceCandidate`):
  Emitted per turn with types `UNDERSTANDING`, `MISCONCEPTION`, `REVISION`, `INDEPENDENCE`, `EXPLANATION`, `TRANSFER`. Each candidate is traceable to `source_event_ids=[learning_event.id]` and calibrated by model confidence (`STRONG`, `MODERATE`, `WEAK`).
- **External AI Risk Signals** (`ExternalAIRiskSignal`):
  Emitted only upon observable anomalies (e.g. `unusually_large_attempt_jump` from <60 chars to >350 chars without intermediate turns). The system never asserts cheating or external AI usage.

---

## 7. Learning Verification Module

The Learning Verification module (`ai/verification/`) operates independently of the LangGraph Coach:

```python
from ai.verification import (
    VerificationChallengeRequest,
    VerificationRequest,
    VerificationService,
    VerificationType,
)

service = VerificationService()

# 1. Generate challenge question
challenge = service.generate_challenge(
    VerificationChallengeRequest(
        assignment_id="asg_gd",
        concept="gradient_descent",
        verification_type=VerificationType.EXPLAIN,
        student_work="theta = theta - lr * gradient",
    )
)

# 2. Evaluate student response
result = service.verify(
    VerificationRequest(
        student_id="student_42",
        assignment_id="asg_gd",
        concept="gradient_descent",
        verification_type=VerificationType.EXPLAIN,
        challenge_question=challenge.question,
        student_response="The gradient indicates steepest ascent; subtracting moves toward the minimum.",
        criteria=challenge.criteria,
    )
)
# result.outcome in (PASS, PARTIAL, NEEDS_RETRY, INSUFFICIENT_EVIDENCE)
```

Passing verification outcomes automatically emit a traceable `LearningEvidenceCandidate`.

---

## 8. HTTP Contracts Adapter Layer

The `ai/contracts/` module defines ready-to-use Pydantic DTOs for the FastAPI backend:

- `CoachApiRequest` & `CoachApiResponse` for `POST /api/ai/coach`.
- `run_coach_turn(request: CoachApiRequest)` adapter function.
- `VerificationChallengeApiRequest` & `VerificationChallengeApiResponse` for `POST /api/ai/verify/challenge`.
- `VerificationEvaluateApiRequest` & `VerificationEvaluateApiResponse` for `POST /api/ai/verify/evaluate`.

---

## 9. Running Tests

```bash
pip install -r requirements-ai.txt
pytest -v
```

All tests run against mock pipelines — no live API keys or external network connections are required.
