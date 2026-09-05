# The Socratic Class — AI API Contracts

This document specifies the exact HTTP contracts for integrating the **AI Coach** and **Learning Verification** services with the FastAPI backend.

All endpoints adhere to standard JSON payloads and response envelopes.

---

## 1. AI Coach Endpoint

### `POST /api/ai/coach`
Executes a single pedagogical tutoring turn. Evaluates student work, diagnoses learning gaps, retrieves course materials (if necessary), and generates policy-compliant guidance.

#### Request Headers
| Header | Value | Required | Description |
|---|---|---|---|
| `Content-Type` | `application/json` | Yes | Request format |
| `Authorization` | `Bearer <token>` | Yes | JWT bearer token for authenticated student |

#### Request Body Schema (`CoachApiRequest`)
```json
{
  "student_id": "string",
  "assignment_id": "string",
  "session_id": "string",
  "course_id": "string",
  "attempt": "string",
  "policy": "GUIDED | ASSISTED | OPEN",
  "message": "string | null",
  "assignment_title": "string | null",
  "assignment_instructions": "string | null",
  "is_programming": false,
  "turn_index": 0,
  "conversation": [
    {
      "role": "student | coach",
      "content": "string"
    }
  ]
}
```

#### Field Specifications
- `student_id` *(string, required)*: Unique identifier of the student.
- `assignment_id` *(string, required)*: Unique identifier of the assignment.
- `session_id` *(string, required)*: Session/thread identifier for grouping related turns.
- `course_id` *(string, required)*: Course identifier used for strict RAG isolation. Chunks from other courses are strictly filtered out.
- `attempt` *(string, required)*: The student's code, math, or written response.
- `policy` *(string, optional, default: `"GUIDED"`)*: Pedagogical assistance level:
  - `GUIDED`: Strict Socratic mode. Explanations on first attempts are downgraded to questions; direct solutions are blocked.
  - `ASSISTED`: Scaffolding mode. Explanations and guided debugging are allowed when needed.
  - `OPEN`: Direct assistance mode. More direct explanations and formula hints are permitted.
- `message` *(string, optional)*: Accompanying student message (e.g. `"Why am I getting this error?"`).
- `assignment_title` *(string, optional)*: Human-readable title of the assignment.
- `assignment_instructions` *(string, optional)*: Full assignment instructions to ground diagnosis.
- `is_programming` *(boolean, optional, default: `false`)*: Enables conditional static AST code analysis when code is present. Student code is **never** executed.
- `turn_index` *(integer, optional, default: `0`)*: 0-indexed turn counter within this session.
- `conversation` *(array of objects, optional, default: `[]`)*: Recent prior dialogue turns for context windowing.

#### Response Schema (`CoachApiResponse`) — Status `200 OK`
```json
{
  "response": "What quantity should scale how much you adjust theta at each step?",
  "intervention": {
    "type": "QUESTION",
    "assistance_level": "GUIDED",
    "rationale": "Guide the student to reconsider what should scale the parameter update step."
  },
  "diagnosis": {
    "category": "MISCONCEPTION",
    "concept": "learning_rate",
    "explanation": "Student updates theta directly by the prediction instead of the gradient scaled by the learning rate.",
    "evidence": "theta = theta - prediction",
    "confidence": 0.85
  },
  "referenced_concepts": ["gradient_descent", "learning_rate"],
  "tools_used": ["code_analysis"],
  "learning_event": {
    "id": "evt_abc123456789",
    "student_id": "student_42",
    "assignment_id": "asg_gd",
    "session_id": "sess_100",
    "event_type": "AI_INTERACTION",
    "timestamp": "2026-09-05T20:00:00Z",
    "payload": {
      "interaction_id": "int_xyz987654321",
      "intervention_type": "QUESTION",
      "assistance_level": "GUIDED",
      "response": "What quantity should scale how much you adjust theta at each step?",
      "diagnosis": { "...": "..." },
      "evidence_candidates": [ "...serialized..." ],
      "risk_signals": [ "...serialized..." ]
    }
  },
  "evidence_candidates": [
    {
      "id": "ev_456def789abc",
      "student_id": "student_42",
      "assignment_id": "asg_gd",
      "concept": "learning_rate",
      "evidence_type": "MISCONCEPTION",
      "strength": "STRONG",
      "observation": "Observable misconception: Student updates theta directly by the prediction instead of the gradient scaled by the learning rate.",
      "source_event_ids": ["evt_abc123456789"],
      "created_at": "2026-09-05T20:00:00Z"
    }
  ],
  "risk_signals": [],
  "metadata": {
    "turn_index": 1,
    "errors": [],
    "validation_violations": []
  }
}
```

---

## 2. Learning Verification Endpoints

The Learning Verification module operates independently of the Coach graph. It generates and evaluates conceptual challenges across three modes: `EXPLAIN`, `MODIFY`, `TRANSFER`.

### `POST /api/ai/verify/challenge`
Generates a targeted verification challenge tailored to the student's recent work.

#### Request Body Schema (`VerificationChallengeApiRequest`)
```json
{
  "assignment_id": "asg_gd",
  "concept": "gradient_descent",
  "verification_type": "EXPLAIN",
  "student_work": "theta = theta - lr * gradient",
  "course_context": "Machine Learning 101 - Lecture 3"
}
```

#### Response Schema (`VerificationChallengeApiResponse`) — Status `200 OK`
```json
{
  "challenge_id": "vc_112233445566",
  "verification_type": "EXPLAIN",
  "concept": "gradient_descent",
  "question": "Why does gradient descent require subtracting the gradient rather than adding it?",
  "criteria": [
    "Explains that the gradient points in the direction of steepest ascent of the loss",
    "Identifies that subtraction moves parameters toward a local minimum of the objective function"
  ]
}
```

---

### `POST /api/ai/verify/evaluate`
Evaluates the student's response to a verification challenge.

#### Request Body Schema (`VerificationEvaluateApiRequest`)
```json
{
  "student_id": "student_42",
  "assignment_id": "asg_gd",
  "concept": "gradient_descent",
  "verification_type": "EXPLAIN",
  "challenge_question": "Why does gradient descent require subtracting the gradient rather than adding it?",
  "student_response": "The gradient points in the direction where the error increases fastest. We subtract it because we want to minimize error, moving downhill towards the minimum.",
  "criteria": [
    "Explains that the gradient points in the direction of steepest ascent of the loss",
    "Identifies that subtraction moves parameters toward a local minimum of the objective function"
  ],
  "original_attempt": "theta = theta - lr * gradient"
}
```

#### Response Schema (`VerificationEvaluateApiResponse`) — Status `200 OK`
```json
{
  "verification_id": "ver_778899001122",
  "student_id": "student_42",
  "assignment_id": "asg_gd",
  "concept": "gradient_descent",
  "verification_type": "EXPLAIN",
  "outcome": "PASS",
  "score": 0.95,
  "confidence": 0.90,
  "feedback": "Spot-on explanation! You clearly understand the geometric intuition of gradient ascent versus descent.",
  "criteria_evaluations": [
    {
      "criterion": "Explains that the gradient points in the direction of steepest ascent of the loss",
      "passed": true,
      "feedback": "Correctly identified that the gradient points in the direction of steepest increase."
    },
    {
      "criterion": "Identifies that subtraction moves parameters toward a local minimum of the objective function",
      "passed": true,
      "feedback": "Correctly connected subtraction with minimizing error."
    }
  ],
  "evidence_candidate": {
    "id": "ev_998877665544",
    "student_id": "student_42",
    "assignment_id": "asg_gd",
    "concept": "gradient_descent",
    "evidence_type": "EXPLANATION",
    "strength": "STRONG",
    "observation": "Student successfully completed explain verification for concept 'gradient_descent' with score 0.95.",
    "source_event_ids": ["ver_778899001122"],
    "created_at": "2026-09-05T20:05:00Z"
  }
}
```

---

## 3. Standard HTTP Error Envelopes

| Status Code | Reason | Description |
|---|---|---|
| `400 Bad Request` | Missing or malformed parameters | e.g. `course_id` missing, invalid JSON |
| `422 Unprocessable Entity` | Schema validation error | Pydantic validation failure on field types |
| `500 Internal Server Error` | Unhandled internal exception | Degrades gracefully; fallback message provided |

#### Standard Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'course_id' is required for course-scoped RAG retrieval.",
    "details": [
      {
        "loc": ["body", "course_id"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```
