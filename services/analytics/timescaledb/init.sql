-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Stream metrics table
CREATE TABLE IF NOT EXISTS stream_metrics (
    time        TIMESTAMPTZ NOT NULL,
    stream_id   TEXT NOT NULL,
    bitrate     BIGINT,
    fps         FLOAT,
    buffer_ratio FLOAT,
    startup_time_ms INTEGER,
    latency_ms  INTEGER,
    packet_loss FLOAT,
    jitter_ms   FLOAT,
    viewer_count INTEGER,
    geo_country TEXT,
    geo_city    TEXT
);
SELECT create_hypertable('stream_metrics', 'time', if_not_exists => TRUE);

-- AI content analysis table
CREATE TABLE IF NOT EXISTS content_analysis (
    time        TIMESTAMPTZ NOT NULL,
    stream_id   TEXT NOT NULL,
    scene_id    TEXT,
    confidence  FLOAT,
    objects     JSONB,
    content_category TEXT,
    iab_tier1   TEXT,
    iab_tier2   TEXT
);
SELECT create_hypertable('content_analysis', 'time', if_not_exists => TRUE);

-- SCTE-35 markers table
CREATE TABLE IF NOT EXISTS scte35_markers (
    time        TIMESTAMPTZ NOT NULL,
    stream_id   TEXT NOT NULL,
    event_id    BIGINT,
    splice_type TEXT,
    pts         BIGINT,
    duration_pts BIGINT,
    out_of_network BOOLEAN,
    validated   BOOLEAN DEFAULT FALSE
);
SELECT create_hypertable('scte35_markers', 'time', if_not_exists => TRUE);

-- Ad analytics table
CREATE TABLE IF NOT EXISTS ad_analytics (
    time        TIMESTAMPTZ NOT NULL,
    stream_id   TEXT NOT NULL,
    ad_id       TEXT NOT NULL,
    event_type  TEXT NOT NULL, -- impression, click, complete, skip
    ad_server   TEXT,
    creative_url TEXT,
    duration_s  INTEGER,
    viewer_id   TEXT,
    geo_country TEXT
);
SELECT create_hypertable('ad_analytics', 'time', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_stream_metrics_stream ON stream_metrics (stream_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_content_analysis_stream ON content_analysis (stream_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_scte35_markers_stream ON scte35_markers (stream_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_ad_analytics_stream ON ad_analytics (stream_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_ad_analytics_event ON ad_analytics (event_type, time DESC);

-- Continuous aggregates for hourly stream metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS stream_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    stream_id,
    AVG(bitrate) AS avg_bitrate,
    AVG(fps) AS avg_fps,
    AVG(buffer_ratio) AS avg_buffer_ratio,
    AVG(latency_ms) AS avg_latency_ms,
    AVG(packet_loss) AS avg_packet_loss,
    MAX(viewer_count) AS peak_viewers
FROM stream_metrics
GROUP BY bucket, stream_id
WITH NO DATA;

-- Ad fill rate view
CREATE VIEW IF NOT EXISTS ad_fill_rate AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    stream_id,
    COUNT(*) FILTER (WHERE event_type = 'impression') AS impressions,
    COUNT(*) FILTER (WHERE event_type = 'complete') AS completions,
    COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
    ROUND(100.0 * COUNT(*) FILTER (WHERE event_type = 'complete') / NULLIF(COUNT(*) FILTER (WHERE event_type = 'impression'), 0), 2) AS completion_rate
FROM ad_analytics
GROUP BY bucket, stream_id;
