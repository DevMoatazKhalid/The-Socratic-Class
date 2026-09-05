# AI Coach — Implementation Decisions & Assumptions

The repository scaffold (`ai/`, `docs/`) existed with empty placeholder
files only — no backend, frontend, database, or prior AI code to integrate
against. The decisions below were made autonomously per the "Analyze →
Decide → Implement" rule, since none rose to a genuine product/architecture
conflict requiring escalation.

- **Model provider default**: `AI_PROVIDER=openai` with `gpt-4o-mini` as the
  default model for every role. NVIDIA NIM and other OpenAI-compatible
  endpoints are supported by pointing `AI_PROVIDER=nvidia` (or
  `openai_compatible`) and `AI_BASE_URL` at the endpoint — no code change
  needed, per the multi-provider requirement.
- **Prompt directory mapping**: the scaffold shipped `ai/prompts/{diagnosis,
  coach,verification}/` rather than the `{diagnosis,intervention,response,
  validation}` layout sketched in the brief. Mapped as: `diagnosis/` → the
  diagnosis prompt, `coach/` → intervention-selection + response-generation
  prompts (both are coach-facing), `verification/` → the response-
  validation guardrail prompt (it verifies a draft response, not to be
  confused with the separate "Learning Verification" student-facing feature,
  which is out of scope for this MVP).
- **New tool file**: `ai/tools/assignment_context.py` was added (not in the
  original scaffold) since the brief explicitly requires an assignment-
  context interface. In practice the backend already holds `TaskContext`
  and passes it directly into `Coach.invoke(...)`; this tool exists for
  callers that need to fetch it themselves.
- **Tests location**: `ai/tests/` was created (not in the original tree) as
  the natural home for Coach-specific unit/integration tests, run with
  `pytest ai/tests`. `ai/evaluation/` was left for future LLM-quality
  evaluation harnesses, which is a different concern from correctness
  tests.
- **GUIDED-mode enforcement**: rather than relying solely on the prompt, the
  code deterministically downgrades an `EXPLANATION` intervention to
  `QUESTION` when the policy is GUIDED, the diagnosis isn't
  `CORRECT_REASONING`, and it's the student's first attempt (not a
  revision) — an explicit example of "critical constraints enforced in
  code" per section 23 of the brief.
- **Validation retry budget**: one regeneration retry on a failed
  validation pass before the graph routes to a fixed, policy-appropriate
  safe-fallback response, to guarantee the graph always terminates with a
  usable response rather than looping.
- **Evidence/risk-signal emission**: `LearningEvidenceCandidate` and
  `ExternalAIRiskSignal` schemas are defined (per sections 19 and 21) but
  the graph does not populate them yet — turning diagnoses into evidence
  and risk signals is explicitly downstream-analytics scope per the brief's
  boundaries (section 20), and adding it now would be scope creep beyond
  "the AI Coach core."
- **Code analysis tool**: static AST analysis only (syntax validity,
  defined names, loop count) — no code execution, per the brief's explicit
  prohibition on unrestricted tool execution ("Potentially execute code in
  a safe environment if the infrastructure supports it" was treated as
  out of scope since no sandboxed execution infrastructure exists yet).
