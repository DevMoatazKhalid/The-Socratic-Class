# AI Coach — Integration Spec

Scope: this document covers only the **AI Coach** (`ai/agents/coach/`), the
component responsible for diagnosing a student's learning state and
generating adaptive tutoring guidance. It does not cover the frontend,
main backend/API, database, or analytics/dashboard layers.

## 1. What the Coach owns vs. what it doesn't

The Coach owns: diagnosis, intervention selection, response generation,
response validation, and structured event/interaction output.

The Coach explicitly does **not** own: persistence, authentication, the
RAG ingestion pipeline (`ai/rag/` — only a retrieval interface is
consumed), analytics (mastery/dependency scores), or the external-AI
risk-assessment component. Those are separate, downstream systems that
consume the Coach's output.

## 2. Calling the Coach

```python
from ai.agents.coach import Coach, TaskContext
from ai.models.schemas import AssistancePolicy

coach = Coach()  # or Coach(course_tool=..., history_tool=...) with real tools wired in

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
- Loading/constructing `TaskContext` for the assignment.
- Tracking `session_id` and passing a reasonably-windowed `conversation`
  (the Coach does not load full history itself — see section 10 of the
  original spec).
- Incrementing `turn_index` each time the student revises and resubmits.
- Persisting `result.learning_event` (and, in future, evidence candidates)
  and displaying `result.response` to the student.

## 3. Output contract — `CoachResult`

```text
CoachResult
├── response: str                      # the message shown to the student
├── intervention: Intervention         # {type, assistance_level, rationale}
├── diagnosis_summary: Diagnosis       # {category, concept, explanation, evidence, confidence}
├── referenced_concepts: list[str]
├── tools_used: list[str]              # e.g. ["course_retriever"]
├── learning_event: LearningEvent      # event_type=AI_INTERACTION, payload = AIInteraction
├── evidence_candidates: list[...]     # reserved; currently empty, see section 6
├── risk_signals: list[...]            # reserved; currently empty, see section 6
└── metadata: dict                     # turn_index, internal errors (if any), validation notes
```

No internal chain-of-thought or hidden reasoning is exposed — only the
structured `diagnosis_summary` fields above.

## 4. Tool contracts

All tools are injectable (constructor argument to `Coach(...)`) so the real
RAG/history backends can be wired in without touching the graph.

- **`CourseRetrievalTool`** (`ai/tools/course_retrieval.py`)
  `.retrieve(course_id, query, top_k=4) -> list[RetrievedContext]`.
  Filters out any result tagged with a different `course_id` as a defense-
  in-depth measure. Raises `CourseRetrievalError` on underlying failure,
  which the graph catches and continues without course material.

- **`StudentHistoryTool`** (`ai/tools/student_history.py`)
  `.retrieve(student_id, assignment_id, concept=None, limit=3) -> list[RetrievedContext]`.
  Must return only *relevant*, bounded history — never the full profile.

- **`AssignmentContextTool`** (`ai/tools/assignment_context.py`)
  `.get(assignment_id) -> Optional[TaskContext]`. Typically unused in the
  request path since the backend already has and passes `TaskContext`
  directly; provided for callers that need to fetch it themselves.

- **`CodeAnalysisTool`** (`ai/tools/code_analysis.py`)
  `.analyze(code, language="python") -> CodeAnalysisResult`. Static AST
  analysis only (syntax validity, defined functions/variables, loop count).
  Does not execute student code.

## 5. Configuration

All model configuration is environment-driven (`ai/models/llm.py`):

| Variable | Purpose |
|---|---|
| `AI_PROVIDER` | `openai` \| `openai_compatible` \| `nvidia` \| `anthropic` |
| `AI_API_KEY` | provider API key |
| `AI_BASE_URL` | required for `openai_compatible`/NVIDIA NIM endpoints |
| `AI_MODEL_DEFAULT` | fallback model name for any role |
| `AI_MODEL_<ROLE>` | per-role override, `ROLE` ∈ `COACH, REASONING, LIGHTWEIGHT, VERIFICATION` |
| `AI_TEMPERATURE_DEFAULT` / `AI_TEMPERATURE_<ROLE>` | sampling temperature |

No API keys are hard-coded anywhere in `ai/`.

## 6. Learning events & evidence

The Coach emits one `LearningEvent` (`event_type=AI_INTERACTION`) per turn,
whose `payload` is the full `AIInteraction` record (diagnosis, intervention,
response, referenced concepts, tools used). This is the only durable output
the Coach produces today.

`LearningEvidenceCandidate` and `ExternalAIRiskSignal` models exist in
`ai/models/schemas.py` as the agreed contract for future work, but the
Coach graph does not currently populate them — evidence extraction and risk
scoring are downstream-analytics responsibilities, kept deliberately out of
this MVP's scope (see project boundaries, sections 19–21 of the original
task brief).

## 7. Example: one full turn (GUIDED policy)

**Input**
```text
assignment: "Implement Linear Regression using Gradient Descent"
policy: GUIDED
attempt: "theta = theta - prediction"
```

**Graph execution**
```text
understand_context -> diagnose -> choose_intervention
  -> (no retrieval needed) -> generate_response -> validate -> emit_interaction
```

**Output**
```json
{
  "response": "What quantity should scale how much you adjust theta at each step?",
  "intervention": {"type": "QUESTION", "assistance_level": "GUIDED", "rationale": "..."},
  "diagnosis_summary": {
    "category": "MISCONCEPTION",
    "concept": "learning_rate",
    "explanation": "Student updates theta by the prediction instead of the gradient.",
    "evidence": "theta = theta - prediction",
    "confidence": 0.8
  },
  "referenced_concepts": ["gradient_descent", "learning_rate"],
  "tools_used": [],
  "learning_event": {"event_type": "AI_INTERACTION", "...": "..."}
}
```

## 8. Running tests

```bash
pip install -r requirements-ai.txt
pytest ai/tests -q
```

All 31 tests run against mocked LLM calls — no live API key or network
access is required.
