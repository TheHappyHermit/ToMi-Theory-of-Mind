-- ============================================================================
-- HERMES BRAIN: EXTENDED COGNITIVE CORTEX SCHEMA
-- Dual-Engine Compatible: PostgreSQL + pgvector & SQLite
-- ============================================================================

-- 1. Epistemic Belief & Defeater Lattice
CREATE TABLE IF NOT EXISTS cognitive_beliefs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    statement       TEXT NOT NULL,
    credence        REAL DEFAULT 1.0 CHECK (credence >= 0.0 AND credence <= 1.0),
    provenance      TEXT NOT NULL, -- 'user', 'tool', 'inference', 'wiki'
    -- WHERE the belief came from, not just who said it: file path, wiki page
    -- slug, or message id. Required. 'user' tells you the category of the
    -- source; it does not tell you which of several hundred pages to re-read
    -- when the belief turns out to be wrong, and a belief you cannot re-check
    -- is indistinguishable from one you should never have stored.
    --
    -- The column is DEFAULT '' rather than bare NOT NULL because SQLite cannot
    -- add a NOT NULL column to an existing table without a rebuild, and this
    -- schema is additive-only. The requirement is therefore enforced where it
    -- can actually hold: at the writer. DefeaterGraph.add_belief refuses an
    -- empty or whitespace-only location, so no row is written without one.
    -- There is deliberately no CHECK constraint here -- a constraint that always
    -- passes is worse than none, because it reads like enforcement.
    source_location TEXT NOT NULL DEFAULT '',
    epistemic_state TEXT NOT NULL CHECK (epistemic_state IN ('grounded', 'disputed', 'undercut', 'superseded')),
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_cog_beliefs_topic ON cognitive_beliefs(topic);
CREATE INDEX IF NOT EXISTS idx_cog_beliefs_state ON cognitive_beliefs(epistemic_state);

CREATE TABLE IF NOT EXISTS cognitive_defeaters (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    target_belief_id    INTEGER REFERENCES cognitive_beliefs(id) ON DELETE CASCADE,
    defeater_belief_id  INTEGER REFERENCES cognitive_beliefs(id) ON DELETE CASCADE,
    defeater_type       TEXT NOT NULL CHECK (defeater_type IN ('rebutting', 'undercutting')),
    rational_justification TEXT NOT NULL,
    created_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_defeaters_target ON cognitive_defeaters(target_belief_id);

-- 2. Somatic Markers & Operational Risk Memory (Limbic Engine)
CREATE TABLE IF NOT EXISTS somatic_markers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_pattern  TEXT NOT NULL,
    target_pattern  TEXT NOT NULL,
    valence_bias    REAL NOT NULL CHECK (valence_bias >= -1.0 AND valence_bias <= 1.0),
    sample_count    INTEGER NOT NULL DEFAULT 1,
    last_experienced TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (action_pattern, target_pattern)
);

CREATE INDEX IF NOT EXISTS idx_somatic_action ON somatic_markers(action_pattern);

-- 3. Theory of Mind User State (Social Cognition)
CREATE TABLE IF NOT EXISTS user_mental_models (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain          TEXT NOT NULL,
    attributed_belief TEXT NOT NULL,  -- What the agent attributes to the user
    ground_truth    TEXT NOT NULL,    -- What is empirically or factually grounded
    discrepancy     BOOLEAN NOT NULL DEFAULT 0,
    last_verified   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_mental_models_domain ON user_mental_models(domain);

-- 4. Counterfactual & Chronesthetic Rollouts (Default Mode Network)
CREATE TABLE IF NOT EXISTS counterfactual_rollouts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_event       TEXT NOT NULL,
    actual_path         TEXT NOT NULL,
    counterfactual_path TEXT NOT NULL,
    predicted_advantage TEXT NOT NULL,
    lesson_extracted    TEXT NOT NULL,
    created_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- 5. Working Memory Snapshots (Dorsolateral Prefrontal Cortex)
CREATE TABLE IF NOT EXISTS working_memory_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    active_goal     TEXT NOT NULL,
    sub_goals_json  TEXT NOT NULL DEFAULT '[]',
    hypotheses_json TEXT NOT NULL DEFAULT '[]',
    focus_slots_json TEXT NOT NULL DEFAULT '[]',
    updated_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_wm_session ON working_memory_snapshots(session_id);

-- 6. Retrieval Log — append-only record of every retrieval the retriever performs.
-- Four components are blocked on this: metacognition (calibrate on own history),
-- scheduling (tag + recall history), the benchmark (was the retriever correct?),
-- and the shortcut library (fire on high confidence, escalate when low).
--
-- This is instrumentation, not a performance measurement. Logging what happened
-- is permitted and required; producing quality numbers from it is not.
--
-- Append-only. Never UPDATE or DELETE a row here. The calibration signal is the
-- value of the history, and a corrected row is indistinguishable from a real one.
CREATE TABLE IF NOT EXISTS retrieval_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at     TEXT NOT NULL,          -- RFC 3339 UTC: YYYY-MM-DDTHH:MM:SSZ
    session_id      TEXT NOT NULL,
    query           TEXT NOT NULL,
    strategy        TEXT NOT NULL,          -- keyword | dense | graph | fused | reranked
    doc_id          TEXT NOT NULL,
    source_path     TEXT,                   -- absolute path; provenance is mandatory
    rank_position   INTEGER,
    score           REAL,
    was_selected    INTEGER NOT NULL DEFAULT 0,  -- did this survive to the final answer?
    latency_ms      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_retrieval_log_observed ON retrieval_log(observed_at);
CREATE INDEX IF NOT EXISTS idx_retrieval_log_doc      ON retrieval_log(doc_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_log_session  ON retrieval_log(session_id);

-- 7. Confidence Log — append-only record of how sure the system was of each claim.
--
-- A confidence with no evidence_ids is not a confidence, it is a vibe. The column
-- is nullable so a claim can be logged before its evidence is resolved, but
-- was_correct stays null until an outcome actually fills it in. Never back-fill
-- it from the claim's own text: that manufactures the calibration signal this
-- table exists to measure.
CREATE TABLE IF NOT EXISTS confidence_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at     TEXT NOT NULL,          -- RFC 3339 UTC: YYYY-MM-DDTHH:MM:SSZ
    session_id      TEXT NOT NULL,
    claim           TEXT NOT NULL,
    confidence      REAL NOT NULL,          -- 0.0-1.0
    evidence_ids    TEXT,                   -- JSON array of retrieval_log.id
    mechanism       TEXT NOT NULL,          -- which subsystem emitted it
    was_correct     INTEGER                 -- filled in later by outcome, nullable now
);

CREATE INDEX IF NOT EXISTS idx_confidence_log_observed ON confidence_log(observed_at);
CREATE INDEX IF NOT EXISTS idx_confidence_log_session ON confidence_log(session_id);
