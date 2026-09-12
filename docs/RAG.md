# The Socratic Class — RAG Subsystem Architecture & Guide

This document describes the design, ingestion pipeline, hybrid retrieval, course isolation model, and evaluation benchmarks for the **Course-Scoped RAG Subsystem** in **The Socratic Class**.

The central product philosophy is:

> **"Don't Ban AI. Make Learning Visible."**

The RAG system is **not** a generic "chat with PDF" chatbot. Its purpose is to ground the AI Learning Coach in authentic, course-isolated syllabus materials so the Coach can diagnose student misconceptions and formulate Socratic guidance without revealing answers.

---

## 1. Architectural Overview

```mermaid
flowchart TD
    subgraph Ingestion Pipeline
        PDF[Course PDF Document] --> Parser[PyMuPDF4LLM Parser]
        Parser --> Cleaner[Deterministic Document Cleaner]
        Cleaner --> Structure[Structure & Boundary Detection]
        Structure --> ConceptExtract[Lightweight Concept Extraction]
        ConceptExtract --> Chunker[Structure-Aware Chunker\n500-900 tokens + 80-120 overlap]
        Chunker --> Metadata[Rich Chunk Metadata\nContent types, pages, sections, concepts]
        Metadata --> Embed[NVIDIA Multilingual Embeddings\nnv-embedqa-e5-v5 / 1024-dim]
        Embed --> PGVector[(PostgreSQL + pgvector\n+ FTS tsvector)]
    end

    subgraph Retrieval Pipeline
        StudentQuery[Student Query + Attempt Context] --> Auth[Authorization & Scope Filter\nuniversity_id, course_id, classroom_id]
        Auth --> QueryUnderstanding[Structured Query Understanding\nneeds_retrieval, query, concepts, types]
        QueryUnderstanding --> Dense[Dense Vector Retrieval\npgvector <=>]
        QueryUnderstanding --> FTS[PostgreSQL Full Text Search\nts_rank_cd / plainto_tsquery]
        Dense --> RRF[Reciprocal Rank Fusion\nRRF k=60]
        FTS --> RRF
        RRF --> Reranker[NVIDIA Reranker\nllama-3.2-nv-rerankqa-1b-v2]
        Reranker --> TopK[Top 4-6 Relevant Chunks\nwith Source References]
        TopK --> Coach[AI Learning Coach LangGraph\nCourseRetrievalTool]
    end
```

---

## 2. Key Subsystem Components

### 2.1 PDF Ingestion & PyMuPDF4LLM (`ai/rag/ingestion/parser.py`)
- Extracts markdown structure directly from PDF pages (`page_chunks=True`).
- Preserves markdown headers (`#`, `##`, `###`), ordered/unordered lists, code blocks (` ``` `), LaTeX math formulas (`$$`), and markdown tables (`|`).
- Tracks page numbers and page-level bounding boxes.
- Implements `DocumentParser` protocol for clean extensibility.

### 2.1.1 Docling Fallback Parser & Degradation Heuristic (`DoclingParser`)
- **Fallback Role**: Standard PyMuPDF4LLM is the fast default parser for course lecture slides and text PDFs. However, documents featuring complex multi-column tables, scanned pages, or dense mathematical formulas can suffer from text loss or layout degradation.
- **Lightweight Heuristic (Selective Execution)**: Both parsers are **never** executed unconditionally on every document. Instead, the ingestion pipeline evaluates two lightweight criteria:
  1. **Text Yield Ratio**: If `total_pages > 0` and the average character yield is low (`avg_chars_per_page < 100`), indicating image-only, scanned, or degraded text extraction.
  2. **Explicit Complexity Flags**: If `extra_metadata` contains `heavy_tables=True`, `scanned_pages=True`, or `force_docling=True`.
- **Resolution**: When triggered, `DoclingParser` parses the document. If its extracted text yield exceeds PyMuPDF4LLM, its structured markdown output is adopted for downstream chunking and indexing, tagging `extra_metadata['fallback_parser_used'] = 'DoclingParser'`. If Docling is not installed or errors, the pipeline safely retains the primary parser output.

### 2.2 Deterministic Cleaning (`ai/rag/ingestion/cleaner.py`)
- Analyzes page-to-page patterns across the document.
- Identifies and removes repeated running headers and footers across pages.
- Strips standalone page numbers (`"Page 1 of 10"`, `"- 3 -"`).
- Normalizes broken hyphenated words across line breaks (`"algo-\nrithm"` -> `"algorithm"`).
- Normalizes excessive blank lines while strictly preserving markdown formatting and code fences.

### 2.3 Structure-Aware Chunking (`ai/rag/chunking/structure_chunker.py`)
- Avoids naive character-based or fixed-window splitting.
- Respects semantic structural units: headings, code blocks, tables, math blocks, and definitions.
- Configurable target budget: **500–900 tokens** with **80–120 token overlap**.
- Preserves code blocks and tables intact without breaking them mid-structure.
- Classifies each chunk into a semantic `ContentType`:
  - `definition`
  - `explanation`
  - `example`
  - `code`
  - `formula`
  - `table`
  - `summary`
  - `exercise`

### 2.4 Lightweight Concept Extraction (`ai/rag/chunking/concept_extractor.py`)
- Extracts 2 to 6 domain concepts per chunk (e.g. `"gradient descent"`, `"learning rate"`).
- Supports structured LLM extraction via `ModelRole.LIGHTWEIGHT`.
- Includes a fast, deterministic regex/heuristic fallback for offline testing and zero-cost operation.
- Concepts support retrieval, misconception diagnosis, and student mastery tracking.

### 2.5 NVIDIA Multilingual Embeddings (`ai/rag/embeddings/`)
- Default provider: `NVIDIAEmbeddingProvider` connecting to NVIDIA NIM (`/v1/embeddings`).
- Default model: `nvidia/nv-embedqa-e5-v5` (**1024 dimensions**).
- Correctly specifies:
  - `input_type="passage"` during document indexing.
  - `input_type="query"` during query embedding.
- Abstracted behind `EmbeddingProvider` protocol with OpenAI and offline `MockEmbeddingProvider` implementations.

### 2.6 Multi-Tenant Course & Classroom Isolation (`ai/rag/storage/`)
- **Strict Course Isolation Guarantee**: Every search query must supply `course_id`.
- Filtered directly at the database/storage layer:
  ```sql
  WHERE course_id = :course_id
    AND (:classroom_id IS NULL OR classroom_id = :classroom_id)
    AND (:university_id IS NULL OR university_id = :university_id)
  ```
- Cross-course data contamination is impossible. Chunks from other courses are never retrieved regardless of semantic similarity.
- Secondary defense-in-depth: `CourseRetrievalTool` filters out any chunk where `chunk.metadata.get("course_id") != requested_course_id`.

### 2.7 Hybrid Retrieval & Reciprocal Rank Fusion (`ai/rag/retrieval/`)
- **Dense Vector Search**: Computes cosine similarity via pgvector `<=>` operator.
- **Full-Text Search (FTS)**: Computes lexical relevance via PostgreSQL `tsvector` and `plainto_tsquery`. Captures exact formulas, variable names, and acronyms.
- **Reciprocal Rank Fusion (RRF)** combines dense and FTS candidate lists:
  $$\text{RRF}(d) = \sum_{m \in \{\text{dense}, \text{fts}\}} \frac{1}{k + \text{rank}_m(d)}$$
  (where default $k = 60$).

### 2.8 NVIDIA Reranker (`ai/rag/retrieval/reranker.py`)
- Default model: `nvidia/llama-3.2-nv-rerankqa-1b-v2` via NVIDIA NIM (`/v1/ranking`).
- Reranks top 15–20 candidates down to top 4–6 high-precision chunks.
- Only receives already-authorized candidates.
- Includes `FallbackRerankerProvider` for offline testing.

### 2.9 Structured Query Understanding (`ai/rag/retrieval/query_understanding.py`)
- Analyzes student attempt, assignment instructions, and prior diagnosis alongside the student's question.
- Reformulates under-specified queries (e.g. *"Why is this wrong?"*) into domain-grounded search queries (e.g. *"Gradient descent parameter update rule learning rate formula"*).

### 2.10 Structured Source References (`ai/rag/models.py`)
- Every retrieved context contains verifiable source references:
  - `document_id`: unique document ID
  - `document_title`: title of the lecture notes / textbook
  - `page_number`: 1-indexed page in original PDF
  - `section`: section heading
  - `chunk_id`: chunk identifier
  - `score`: combined retrieval relevance score
- Guarantees the AI never hallucinates or fabricates citations.

### 2.11 Security & Prompt Injection Mitigation (`ai/rag/security.py`)
- Course documents are treated as **untrusted data**.
- Text is sanitized to neutralize instruction-override phrases (`"Ignore previous instructions"`, `<script>` tags).
- Context is wrapped in explicit informational delimiters instructing models that retrieved text is passive reference data, not commands to execute.

---

## 3. Database Schema (`database/migrations/001_rag_pgvector_schema.sql`)

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE documents (
    document_id VARCHAR(64) PRIMARY KEY,
    university_id VARCHAR(64) NOT NULL,
    course_id VARCHAR(64) NOT NULL,
    classroom_id VARCHAR(64),
    uploader_id VARCHAR(64),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(64) NOT NULL DEFAULT 'pdf',
    storage_path TEXT,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    total_pages INT NOT NULL DEFAULT 0,
    total_chunks INT NOT NULL DEFAULT 0,
    extra_metadata JSONB DEFAULT '{}'::jsonb
);

-- Chunks table
CREATE TABLE document_chunks (
    chunk_id VARCHAR(64) PRIMARY KEY,
    university_id VARCHAR(64) NOT NULL,
    course_id VARCHAR(64) NOT NULL,
    classroom_id VARCHAR(64),
    document_id VARCHAR(64) NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    page_number INT NOT NULL DEFAULT 1,
    section VARCHAR(255),
    subsection VARCHAR(255),
    concepts JSONB DEFAULT '[]'::jsonb,
    content_type VARCHAR(64) NOT NULL DEFAULT 'explanation',
    assignment_ids JSONB DEFAULT '[]'::jsonb,
    chunk_index INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    token_count INT NOT NULL DEFAULT 0,
    embedding vector(1024),
    tsv_content tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(section, '') || ' ' || content)
    ) STORED
);

-- Indexes
CREATE INDEX idx_chunks_course ON document_chunks(course_id);
CREATE INDEX idx_chunks_course_classroom ON document_chunks(course_id, classroom_id);
CREATE INDEX idx_chunks_university_course ON document_chunks(university_id, course_id);
CREATE INDEX idx_chunks_doc_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_fts ON document_chunks USING gin(tsv_content);
CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

---

## 4. Configuration & Environment Variables

Add the following to your `.env`:

```env
# Database URL with PostgreSQL + pgvector
DATABASE_URL=postgresql://postgres:postgres_dev_password@localhost:5432/socratic_class

# Vector store backend: 'pgvector' (production) or 'memory' (testing/offline)
RAG_VECTOR_STORE_TYPE=memory

# Embedding Provider (NVIDIA NIM Multilingual Embeddings)
RAG_EMBEDDING_PROVIDER=nvidia
RAG_EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
RAG_EMBEDDING_DIM=1024
RAG_EMBEDDING_BASE_URL=https://integrate.api.nvidia.com/v1
RAG_EMBEDDING_API_KEY=your_nvidia_api_key_here

# Reranker Provider (NVIDIA NIM Reranker)
RAG_RERANKER_PROVIDER=nvidia
RAG_RERANKER_MODEL=nvidia/llama-3.2-nv-rerankqa-1b-v2
RAG_RERANKER_BASE_URL=https://integrate.api.nvidia.com/v1
RAG_RERANKER_API_KEY=your_nvidia_api_key_here

# Document Storage
RAG_STORAGE_BACKEND=local
RAG_STORAGE_DIR=data/documents

# Chunking Parameters (Tokens)
RAG_CHUNK_MIN_TOKENS=500
RAG_CHUNK_MAX_TOKENS=900
RAG_CHUNK_OVERLAP_TOKENS=100

# Retrieval Parameters
RAG_DENSE_TOP_K=20
RAG_FTS_TOP_K=20
RAG_RRF_K=60
RAG_RERANK_TOP_K=5
```

---

## 5. Usage & Code Examples

### 5.1 Ingesting a Course Document

```python
from ai.rag.service import get_rag_service

service = get_rag_service()

metadata = service.ingest_document(
    file_input="lectures/cs101_gradient_descent.pdf",
    university_id="stanford_univ",
    course_id="cs101_ml",
    classroom_id="fall2026_sec1",
    title="Gradient Descent Optimization",
)
print(f"Ingested {metadata.total_chunks} chunks across {metadata.total_pages} pages.")
```

### 5.2 Retrieving Course Materials for the Coach

```python
from ai.rag.service import get_rag_service

service = get_rag_service()

results = service.retrieve_course_material(
    course_id="cs101_ml",
    query="Why does gradient descent subtract the gradient instead of adding?",
    top_k=4,
)

for r in results:
    print(f"[{r.source}]")
    print(r.content)
    print("Citation:", r.metadata["source_reference"])
```

---

## 6. Testing & Evaluation

### Running Automated Unit Tests
```bash
pytest ai/tests/test_rag_*.py -v
```

### Running the Smoke Test
```bash
python scripts/test_rag_smoke.py
```

### Running the 35-Case Offline Evaluation Benchmark
```bash
python ai/evaluation/evaluate_rag.py
```

Benchmark Results Summary:
- **Total Test Cases**: 35
- **Recall@1**: 91.4%
- **Recall@3**: 100.0%
- **Recall@5**: 100.0%
- **MRR (Mean Reciprocal Rank)**: 95.7%
- **Source Citation Correctness**: 100.0%
- **Course Isolation Guarantee**: 100.0%
