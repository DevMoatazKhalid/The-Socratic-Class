-- Migration 001: RAG Documents and pgvector Chunks Schema
-- The Socratic Class AI Coach

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Documents table
CREATE TABLE IF NOT EXISTS documents (
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

CREATE INDEX IF NOT EXISTS idx_documents_course ON documents(course_id);
CREATE INDEX IF NOT EXISTS idx_documents_course_classroom ON documents(course_id, classroom_id);
CREATE INDEX IF NOT EXISTS idx_documents_university_course ON documents(university_id, course_id);

-- 3. Document chunks table
CREATE TABLE IF NOT EXISTS document_chunks (
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

-- Fast lookup and strict multi-tenant course isolation indexes
CREATE INDEX IF NOT EXISTS idx_chunks_course ON document_chunks(course_id);
CREATE INDEX IF NOT EXISTS idx_chunks_course_classroom ON document_chunks(course_id, classroom_id);
CREATE INDEX IF NOT EXISTS idx_chunks_university_course ON document_chunks(university_id, course_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(document_id);

-- Full-Text Search GIN index
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON document_chunks USING gin(tsv_content);

-- Vector Cosine Similarity Index (HNSW)
-- Note: if HNSW is unsupported on older pgvector versions, fallback to ivfflat
DO $$
BEGIN
    CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);
EXCEPTION WHEN OTHERS THEN
    BEGIN
        CREATE INDEX idx_chunks_embedding_ivfflat ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    EXCEPTION WHEN OTHERS THEN
        NULL; -- Keep sequential scan as last resort
    END;
END $$;
