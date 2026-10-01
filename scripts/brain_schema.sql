-- brain_schema.sql — Native Brain Search Schema
-- PostgreSQL + pgvector
-- Run: psql -h <host> -U <user> -d <db> -f brain_schema.sql
--
-- All timestamps are RFC 3339 UTC (YYYY-MM-DDTHH:MM:SSZ)
--
-- Configuration: EMBED_DIM must match the "dimensions" parameter passed to
-- Ollama /api/embed. pgvector HNSW supports up to 2000 dimensions.
-- If you change this, rebuild the HNSW index:
--   DROP INDEX IF EXISTS idx_embeddings_hnsw;
--   CREATE INDEX idx_embeddings_hnsw ON embeddings
--     USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── pages ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pages (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    slug            TEXT NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    file_hash       TEXT NOT NULL,
    embedding_model TEXT NOT NULL DEFAULT '',
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, slug)
);

CREATE INDEX IF NOT EXISTS idx_pages_source ON pages (source);
CREATE INDEX IF NOT EXISTS idx_pages_file_hash ON pages (file_hash);
CREATE INDEX IF NOT EXISTS idx_pages_updated_at ON pages (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_pages_metadata ON pages USING GIN (metadata);

-- ── embeddings ─────────────────────────────────────────────────────────
-- EMBED_DIM: must match the "dimensions" param passed to Ollama /api/embed
-- pgvector HNSW max = 2000. Ollama truncates server-side via "dimensions" param.
CREATE TABLE IF NOT EXISTS embeddings (
    id              BIGSERIAL PRIMARY KEY,
    page_id         BIGINT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    token_count     INTEGER NOT NULL DEFAULT 0,
    embedding       vector(2000),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (page_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_page_id ON embeddings (page_id);

-- HNSW index — created by sync script after dimension is confirmed
-- (cannot be created in raw SQL because the dimension must be applied to the column first)

-- ── conversation_history ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversation_history (
    id              BIGSERIAL PRIMARY KEY,
    query_text      TEXT NOT NULL,
    query_embedding vector(2000),
    results         JSONB NOT NULL DEFAULT '[]'::jsonb,
    result_count    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history (created_at DESC);

-- ── sync_state ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sync_state (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    last_run_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    files_synced    INTEGER NOT NULL DEFAULT 0,
    chunks_created  INTEGER NOT NULL DEFAULT 0,
    duration_ms     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'success',
    error_message   TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sync_state_source ON sync_state (source);
CREATE INDEX IF NOT EXISTS idx_sync_state_last_run ON sync_state (last_run_at DESC);

-- ── Helper: update updated_at automatically ────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_pages_updated_at ON pages;
CREATE TRIGGER update_pages_updated_at
    BEFORE UPDATE ON pages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── Helper: hybrid search with RRF ─────────────────────────────────────
CREATE OR REPLACE FUNCTION brain_search(
    query_embedding vector,
    query_text TEXT,
    match_count INTEGER DEFAULT 10,
    full_text_weight FLOAT DEFAULT 0.5,
    vector_weight FLOAT DEFAULT 0.5,
    source_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    page_id BIGINT,
    chunk_id BIGINT,
    source TEXT,
    slug TEXT,
    title TEXT,
    chunk_text TEXT,
    chunk_index INTEGER,
    full_text_rank FLOAT,
    vector_rank FLOAT,
    rrf_score FLOAT
) AS $$
DECLARE
    rrf_k CONSTANT FLOAT := 60.0;
BEGIN
    RETURN QUERY
    WITH fts AS (
        SELECT
            e.id AS e_id,
            p.id AS p_id,
            e.chunk_index AS ci,
            ts_rank(to_tsvector('english', e.chunk_text), plainto_tsquery('english', query_text)) AS rank
        FROM embeddings e
        JOIN pages p ON e.page_id = p.id
        WHERE
            to_tsvector('english', e.chunk_text) @@ plainto_tsquery('english', query_text)
            AND (source_filter IS NULL OR p.source = source_filter)
        ORDER BY rank DESC
        LIMIT match_count * 3
    ),
    vs AS (
        SELECT
            e.id AS e_id,
            p.id AS p_id,
            e.chunk_index AS ci,
            1 - (e.embedding <=> query_embedding) AS similarity
        FROM embeddings e
        JOIN pages p ON e.page_id = p.id
        WHERE (source_filter IS NULL OR p.source = source_filter)
        ORDER BY e.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    fts_ranked AS (
        SELECT e_id, p_id, ci, rank,
               ROW_NUMBER() OVER (ORDER BY rank DESC) AS rn
        FROM fts
    ),
    vs_ranked AS (
        SELECT e_id, p_id, ci, similarity,
               ROW_NUMBER() OVER (ORDER BY similarity DESC) AS rn
        FROM vs
    ),
    combined AS (
        SELECT
            COALESCE(f.e_id, v.e_id) AS e_id,
            COALESCE(f.p_id, v.p_id) AS p_id,
            COALESCE(f.ci, v.ci) AS ci,
            COALESCE(1.0 / (rrf_k + f.rn), 0.0) * full_text_weight AS fts_score,
            COALESCE(1.0 / (rrf_k + v.rn), 0.0) * vector_weight AS vs_score
        FROM fts_ranked f
        FULL OUTER JOIN vs_ranked v USING (e_id, p_id, ci)
    )
    SELECT
        c.p_id,
        c.e_id,
        p.source,
        p.slug,
        p.title,
        e.chunk_text,
        c.ci AS chunk_index,
        c.fts_score AS full_text_rank,
        c.vs_score AS vector_rank,
        (c.fts_score + c.vs_score) AS rrf_score
    FROM combined c
    JOIN pages p ON c.p_id = p.id
    JOIN embeddings e ON c.e_id = e.id
    ORDER BY (c.fts_score + c.vs_score) DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ── Helper: get page context around a chunk ────────────────────────────
CREATE OR REPLACE FUNCTION get_page_context(target_page_id BIGINT, target_chunk_index INTEGER)
RETURNS TABLE (
    chunk_index INTEGER,
    chunk_text TEXT,
    total_chunks INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.chunk_index,
        e.chunk_text,
        (SELECT chunk_count FROM pages WHERE id = target_page_id) AS total_chunks
    FROM embeddings e
    WHERE e.page_id = target_page_id
    ORDER BY abs(e.chunk_index - target_chunk_index), e.chunk_index
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- ── edges (HippoRAG 2 graph) ────────────────────────────────────────────
-- Associative graph backing brain/hippocampus/associative.py. Restored
-- 2026-09-24: this table and the graph's persistence layer were reverted out
-- during the Hermes Brain rebrand, which silently made the PPR graph
-- process-local (lost on every restart). See PROPOSED-BRAIN-ARCHITECTURE.md
-- §0.6. All statements are additive and idempotent.
CREATE TABLE IF NOT EXISTS edges (
    id              BIGSERIAL PRIMARY KEY,
    subject         TEXT NOT NULL,
    relation        TEXT NOT NULL,
    object          TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    heading         TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_by   BIGINT REFERENCES edges(id) ON DELETE SET NULL,
    superseded_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_edges_subject ON edges (subject);
CREATE INDEX IF NOT EXISTS idx_edges_object ON edges (object);
CREATE INDEX IF NOT EXISTS idx_edges_source_file ON edges (source_file);
CREATE INDEX IF NOT EXISTS idx_edges_superseded_by ON edges (superseded_by);
-- Must be UNIQUE and PARTIAL: this is the arbiter index for the writers' upsert.
-- brain/hippocampus/associative.py and scripts/run_swr_consolidation.py both
-- INSERT ... ON CONFLICT (subject, relation, object) WHERE superseded_by IS NULL
-- DO NOTHING. Postgres matches the arbiter by columns AND predicate, so both
-- the UNIQUE and the WHERE clause are load-bearing -- a plain non-unique index
-- (the original bug) or an ON CONFLICT without the predicate raises 42P10
-- "there is no unique or exclusion constraint matching the ON CONFLICT
-- specification", and every edge write fails silently behind a logged warning.
-- The partial predicate is also what makes C6/C7 supersession expressible:
-- multiple superseded rows may share a triple, but only one may be current.
CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_is_latest ON edges (subject, relation, object) WHERE superseded_by IS NULL;

-- ── roi_canary_probes (memory-ROI measurement) ──────────────────────────
-- Written by scripts/run_roi_canary.py. Measurement only: no deletions, no
-- curation policy. This is the instrumentation that makes a memory-ROI claim
-- checkable on a deployed system rather than asserted.
CREATE TABLE IF NOT EXISTS roi_canary_probes (
    id              BIGSERIAL PRIMARY KEY,
    domain          TEXT NOT NULL,
    question        TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    got_answer      TEXT,
    hit             BOOLEAN,
    precision_at_k  FLOAT,
    probed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_roi_canary_domain ON roi_canary_probes (domain, probed_at DESC);

-- ── scale_decay_diagnostic (monthly scale-sensitivity) ──────────────────
-- Written by scripts/run_scale_diagnostic.py. Tracks retrieval reliability as
-- the corpus grows, so degradation is detected before it is felt.
CREATE TABLE IF NOT EXISTS scale_decay_diagnostic (
    id              BIGSERIAL PRIMARY KEY,
    corpus_size     BIGINT NOT NULL,
    query           TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    got_answer      TEXT,
    correct         BOOLEAN,
    reliability     FLOAT,
    tested_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scale_decay_tested_at ON scale_decay_diagnostic (tested_at DESC);

-- ── decisions (append-only ledger) + decision_current (view) ────────────
-- Reconciled 2026-09-27: these two existed in the live database but were absent
-- from this file, which made the file misleading -- it read as the authority
-- for "what tables exist" while omitting a third of them. The same drift ran
-- the other way (edges/roi_canary_probes/scale_decay_diagnostic were defined
-- here but never applied). DDL below is the live pg_dump output, unmodified.
--
-- This table is C6/C7 groundwork: an append-only ledger where a new row
-- supersedes an old one via supersedes_id, and decision_current exposes only the
-- binding row per topic. That is the shape C7's deterministic newest-wins
-- resolution will operate on.
CREATE TABLE IF NOT EXISTS decisions (
    id            BIGSERIAL PRIMARY KEY,
    slug          TEXT NOT NULL,
    topic         TEXT NOT NULL,
    title         TEXT NOT NULL,
    decision_text TEXT NOT NULL,
    rationale     TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    supersedes_id BIGINT,
    superseded_by BIGINT,
    created_by    TEXT,
    source_session TEXT,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT decisions_status_check
        CHECK (status IN ('active', 'superseded', 'archived'))
);

COMMENT ON TABLE decisions IS
    'Append-only decision ledger. New row supersedes old via supersedes_id. '
    'The current binding decision for a topic is the active row with the '
    'latest created_at - see view decision_current.';

-- The binding decision per topic: active rows only, newest wins. DISTINCT ON
-- gives a deterministic winner, which is the same newest-wins rule C7 requires
-- of the memory layer -- deterministic code, never a model choosing.
CREATE OR REPLACE VIEW decision_current AS
    SELECT DISTINCT ON (topic)
        id, slug, topic, title, decision_text, rationale, status,
        supersedes_id, superseded_by, created_by, source_session,
        metadata, created_at
    FROM decisions
    WHERE status = 'active'
    ORDER BY topic, created_at DESC;
