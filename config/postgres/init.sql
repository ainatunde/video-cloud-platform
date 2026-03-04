-- Video Cloud Platform — PostgreSQL schema initialisation
-- Runs automatically on first container startup.

-- ── Ad events ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ad_decisions (
    id              SERIAL PRIMARY KEY,
    decision_id     UUID NOT NULL,
    splice_event_id BIGINT,
    ad_id           TEXT,
    stream_id       TEXT,
    pts_seconds     DOUBLE PRECISION,
    duration        INTEGER,
    selected        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ad_impressions (
    id          SERIAL PRIMARY KEY,
    ad_id       TEXT NOT NULL,
    stream_id   TEXT,
    position_ms BIGINT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ad_clicks (
    id          SERIAL PRIMARY KEY,
    ad_id       TEXT NOT NULL,
    stream_id   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Stream sessions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stream_sessions (
    id          SERIAL PRIMARY KEY,
    stream_name TEXT NOT NULL,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    bytes_in    BIGINT DEFAULT 0,
    bytes_out   BIGINT DEFAULT 0
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ad_decisions_stream ON ad_decisions(stream_id);
CREATE INDEX IF NOT EXISTS idx_ad_impressions_ad   ON ad_impressions(ad_id);
CREATE INDEX IF NOT EXISTS idx_ad_impressions_time ON ad_impressions(created_at);
