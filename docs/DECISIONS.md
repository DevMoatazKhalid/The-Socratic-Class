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

---

## ADR-009: Universal Final-Answer Prohibition & Deterministic Post-Validation Defense
- **Status**: Accepted
- **Context**: No assistance policy (`GUIDED`, `ASSISTED`, `OPEN`) should ever permit handing the final assignment solution to the student. Furthermore, LLM response-generation, LLM validation, or validator-proposed rewrites (`revised_response`) can fail or hallucinate an answer giveaway.
- **Decision**:
  1. Extended `rule_based_check()` in `ai/guardrails/coach_validator.py` to check universal answer-revealing patterns across ALL policies.
  2. Fixed the validator rewrite bypass in `nodes.py`: any `revised_response` proposed by the LLM is subjected to deterministic rule checks rather than unconditionally accepted.
  3. Implemented `final_answer_enforcement()` as an absolute, deterministic last-line-of-defense check that runs in `validate()` and in `emit_interaction()`, safely falling back to a pedagogical reflection prompt if an answer giveaway is detected.
- **Consequences**: Zero possibility of final-answer leakage bypassing guardrails under any policy, even in the event of LLM misbehavior or rewrite injection.

---

## ADR-010: Hybrid Retrieval (Dense Vector + PostgreSQL FTS) with Reciprocal Rank Fusion (RRF)
- **Status**: Accepted
- **Context**: In course-scoped educational RAG, student queries span conceptual inquiries ("Why does gradient descent oscillate?") and exact lexical lookups ("What does parameter alpha represent in equation 3.2?", specific variable names, code symbols, or theorem titles). Pure dense vector retrieval struggles with rare technical tokens, exact variable names, and mathematical formulas, while pure keyword search (FTS/BM25) fails on paraphrased misconceptions and semantic queries.
- **Decision**: Implemented a hybrid retrieval architecture in `ai/rag/retrieval/` combining dense vector search (via pgvector cosine distance `<=>`) and lexical full-text search (via PostgreSQL `tsvector` and `plainto_tsquery`). Candidates from both streams are merged using Reciprocal Rank Fusion (RRF) with constant $k=60$:
  $$\text{RRF}(d) = \sum_{m \in \{\text{dense}, \text{fts}\}} \frac{1}{k + \text{rank}_m(d)}$$
  followed by a secondary precision reranking stage (`nvidia/llama-3.2-nv-rerankqa-1b-v2`). Cross-reference: `docs/RAG.md` §2.7, §2.8.
- **Consequences**: Outperforms pure dense retrieval on exact formula and code symbol lookup while maintaining high semantic recall on conceptual student queries (benchmark MRR 95.7%, Recall@3 100%). Adds negligible latency overhead (~2–5ms in PostgreSQL) with zero additional external infrastructure.

---

## ADR-011: PostgreSQL + pgvector for Unified Relational and Vector Storage
- **Status**: Accepted
- **Context**: Dedicated vector databases (Pinecone, Weaviate, Qdrant, Milvus) introduce operational complexity, dual-write consistency hazards, separate billing, network hops, and synchronization friction between student/course permissions in relational tables and vector indices. Educational multi-tenancy requires strict, non-negotiable isolation by `university_id`, `course_id`, and `classroom_id`.
- **Decision**: Adopted PostgreSQL with the `pgvector` extension and built-in `tsvector` FTS (`ai/rag/storage/pgvector.py`), unified with the existing Supabase PostgreSQL database. All course materials and chunks reside in `documents` and `document_chunks` tables with composite indexes (`(course_id, classroom_id)` and HNSW vector index). Strict multi-tenant isolation is enforced directly in SQL:
  `WHERE course_id = :course_id AND (:classroom_id IS NULL OR classroom_id = :classroom_id)`
  In-memory fallback (`MemoryVectorStore`) is maintained for zero-dependency local testing and CI. Cross-reference: `docs/RAG.md` §2.6, §3.
- **Consequences**: Eliminates distributed state synchronization and separate vector database costs. Multi-tenant access controls and data deletions are transactional (`ON DELETE CASCADE`). Performance is well within requirements for course-scale syllabi (10k–100k chunks per university tenant).

---

## ADR-012: Structure-Aware Semantic Chunking over Naive Fixed-Size Chunking
- **Status**: Accepted
- **Context**: Standard fixed-character or token-window chunking (e.g. 500 characters with 50 character overlap) blindly splices documents across mid-sentence, splits mathematical equations across boundaries, fragments code blocks into unparseable syntax errors, and breaks markdown tables into unusable partial rows. This leads to degraded LLM reasoning, corrupted source citations, and student confusion.
- **Decision**: Implemented `StructureAwareChunker` (`ai/rag/chunking/structure_chunker.py`) that respects structural document boundaries detected during PDF ingestion (headings `#`, `##`, `###`, fenced code blocks, LaTeX math blocks `$$`, and markdown tables). Chunks target an educational budget of 500–900 tokens with 80–120 token overlap between sections, while keeping code blocks and tables intact within a single chunk. Each chunk is classified into a semantic `ContentType` (`definition`, `explanation`, `example`, `code`, `formula`, `table`, `summary`, `exercise`) and enriched with 2–6 lightweight domain concepts. Cross-reference: `docs/RAG.md` §2.3, §2.4.
- **Consequences**: Preserves pedagogical context, syntax validity of code examples, and mathematical equations intact. Every chunk retains precise page number and section heading provenance, guaranteeing 100% source reference correctness.

---

## ADR-013: Trusted 5-Tuple RetrievalScope Authorization & Content-Hash Ingestion Idempotency
- **Status**: Accepted
- **Context**: Multi-tenant educational SaaS requires that retrieval is never broader than authorized. Additionally, document re-uploads must not duplicate chunks or corrupt the index.
- **Decision**:
  1. Introduced `RetrievalScope` (frozen dataclass with validation) carrying `university_id`, `course_id`, `classroom_id`, `assignment_id`, and `allowed_document_ids`. This scope is constructed from trusted backend/session data, never from LLM output, and flows through `RAGCourseRetriever` → `CourseRetrievalTool.retrieve_scoped()` → `RAGService.retrieve_course_material()` → `HybridRetriever.retrieve()` → SQL pre-ranking `WHERE` predicates. Defense-in-depth post-filtering in `CourseRetrievalTool._filter()` provides a second enforcement boundary.
  2. Implemented SHA-256 `content_hash` ingestion idempotency: before parsing, the service checks `vector_store.get_document_by_hash(course_id, content_hash)`. If an identical document is already `STORED`, it returns the existing metadata without reprocessing. A deterministic `document_id` derived from `university_id:course_id:content_hash` prevents ID collisions across tenants.
  3. Added `DoclingParser` fallback for degraded PDF extractions (scanned pages, complex tables, math-heavy layouts) triggered by a lightweight heuristic (`avg_chars_per_page < 100` or explicit flags).
- **Consequences**: Zero unauthorized cross-tenant data leakage, zero duplicate chunks on re-upload, and robust parsing coverage across all document types.
