# The Socratic Class - AI Coach

An agentic, multi-role Socratic tutoring system built on LangGraph and LangChain. The AI Coach diagnoses student learning states (misconceptions, conceptual gaps, logical errors), selects pedagogical interventions (guiding questions, hints, clarifications), generates level-appropriate responses, and enforces pedagogical guardrails.

---

## LLM Configuration

All LLM and provider configurations are driven through environment variables. The application automatically reads `.env` on startup.

### Quick Setup

1. **Copy `.env.example` to `.env` if necessary:**
   ```bash
   cp .env.example .env
   ```

2. **Select the provider (`AI_PROVIDER`):**
   Choose one of:
   - `openai`
   - `openai_compatible`
   - `nvidia` (or `nvidia_nim`)
   - `anthropic`

3. **Add the API key (`AI_API_KEY`):**
   Provide your API key for the chosen provider.

4. **Add the model (`AI_MODEL_DEFAULT`):**
   Specify the model name for your provider (e.g. `gpt-4o-mini`, `claude-3-5-haiku-20241022`, or `meta/llama-3.1-8b-instruct`).

5. **Add the base URL only when required (`AI_BASE_URL`):**
   Required when using `openai_compatible` or `nvidia` / `nvidia_nim` (e.g. `https://integrate.api.nvidia.com/v1` or `http://localhost:8000/v1`).

6. **Run the smoke test:**
   ```bash
   python scripts/test_llm.py
   ```

---

### Provider Configuration Examples

#### OpenAI
```env
AI_PROVIDER=openai
AI_API_KEY=your_openai_key_here
AI_MODEL_DEFAULT=gpt-4o-mini
```

#### NVIDIA NIM
```env
AI_PROVIDER=nvidia
AI_API_KEY=your_nvidia_api_key_here
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MODEL_DEFAULT=meta/llama-3.1-8b-instruct
```

#### OpenAI-Compatible (Local vLLM / Ollama / Self-Hosted)
```env
AI_PROVIDER=openai_compatible
AI_API_KEY=your_api_key_or_placeholder
AI_BASE_URL=http://localhost:8000/v1
AI_MODEL_DEFAULT=your-model-name
```

#### Anthropic
```env
AI_PROVIDER=anthropic
AI_API_KEY=your_anthropic_key_here
AI_MODEL_DEFAULT=claude-3-5-haiku-20241022
```

---

### Role-Specific Models (Optional)

The AI Coach defines four logical roles. Each role can be configured with a distinct model suited for its task:

```env
AI_MODEL_COACH=gpt-4o-mini
AI_MODEL_REASONING=gpt-4o
AI_MODEL_LIGHTWEIGHT=gpt-4o-mini
AI_MODEL_VERIFICATION=gpt-4o-mini
```

If a role-specific model is left blank, it automatically falls back to `AI_MODEL_DEFAULT`.

---

## Running Tests

### Automated Test Suite
Run all unit and graph tests (mocked, runs offline without calling external APIs):
```bash
pytest -q
```

### LLM Smoke Test
Verify credentials and connectivity to your configured LLM:
```bash
python scripts/test_llm.py
```

### Coach Integration Smoke Test
Verify the full end-to-end Coach pipeline (`diagnose` -> `choose_intervention` -> `generate_response` -> `validate`) with your configured LLM:
```bash
python scripts/test_coach.py
```

---

## Course-Scoped RAG Subsystem

The Socratic Class includes an end-to-end course-isolated RAG subsystem to ground the AI Coach in syllabus knowledge without revealing answers.

### Architecture Highlights
- **Trusted 5-Tuple Scope**: Strict pre-ranking filtering by `university_id`, `course_id`, `classroom_id`, `assignment_id`, and `allowed_document_ids` whitelist.
- **Canonical Input Normalization**: `normalize_file_input` converts paths, bytes, or file-like streams into immutable bytes, eliminating stream consumption bugs across storage and parser.
- **PDF Parser**: `PyMuPDF4LLM` structure-preserving markdown extractor with OCR fallback.
- **Cleaner**: Deterministic header/footer/page-number removal and artifact stripping.
- **Chunker**: Structure-aware chunking (500–900 tokens) with semantic content-type classification (`DEFINITION`, `EXPLANATION`, `CODE`, `TABLE`, `FORMULA`).
- **True Hybrid Concept Extraction**: Combines deterministic regex/definitions with LLM semantic extraction, canonical normalization (`normalize_concept`), and domain aliasing.
- **Embeddings**: NVIDIA Multilingual Embeddings (`nvidia/nv-embedqa-e5-v5`, 1024-dim) with hash/mock providers for offline testing.
- **Storage**: PostgreSQL with `pgvector` and Full-Text Search (FTS) indexes, with memory storage for zero-dependency execution.
- **Hybrid Retrieval**: Dense cosine similarity + PostgreSQL FTS merged via **Reciprocal Rank Fusion (RRF)**.
- **Reranking**: NVIDIA Reranker (`nvidia/llama-3.2-nv-rerankqa-1b-v2`) with fallback scoring.
- **Pedagogical Query Formulation**: `build_retrieval_query` synthesizes assignment instructions, normalized concepts, student misconceptions, and attempts.
- **Isolation Guarantee**: Strict multi-tenant isolation enforced in SQL and storage before ranking, not merely in prompt instructions.
- **Verifiable Citations**: Guaranteed source references (`document_title`, `document_id`, `chunk_id`, `page_number`, `section`).

For comprehensive architecture details, see [`docs/RAG.md`](docs/RAG.md).

### Benchmark & Test Verification
- **209 Unit & Integration Tests**: 100% passing across prompt-injection security, multi-tenant isolation, chunking, retrieval, Docling fallback, ingestion idempotency, LangSmith tracing, invariants, and guardrails.
- **35-Case Offline Evaluation Benchmark** (`ai/evaluation/evaluate_rag.py`):
  - **Retrieval Performance**:
    - **Recall@1**: 91.4%
    - **Recall@3**: 100.0%
    - **Recall@5**: 100.0%
    - **Mean Reciprocal Rank (MRR)**: 95.7%
    - **Source Citation Correctness**: 100.0%
    - **Course & Tenant Isolation Guarantee**: 100.0%
  - **Generation-Side Pedagogical Quality (§31)**:
    - **Groundedness Rate**: 100.0%
    - **Hallucination Rate**: 0.0%
    - **Policy Compliance (No Giveaway)**: 100.0%
    - **Attempt-First Enforcement**: 100.0%
    - **Intervention Appropriateness**: 100.0%

### RAG Commands

#### 1. Run Complete Test Suite (Unit, Invariants, RAG)
```bash
pytest -v
```

#### 2. Run RAG End-to-End Smoke Test
```bash
python scripts/test_rag_smoke.py
```

#### 3. Run RAG 35-Case Offline Evaluation Benchmark
```bash
python ai/evaluation/evaluate_rag.py
```

#### 4. Run Database Migrations (PostgreSQL + pgvector)
```bash
python database/run_migrations.py
```

