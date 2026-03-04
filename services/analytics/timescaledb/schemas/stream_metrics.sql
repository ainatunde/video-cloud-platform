-- Extended stream metrics schema
ALTER TABLE stream_metrics ADD COLUMN IF NOT EXISTS resolution TEXT;
ALTER TABLE stream_metrics ADD COLUMN IF NOT EXISTS codec TEXT;
ALTER TABLE stream_metrics ADD COLUMN IF NOT EXISTS segment_duration_ms INTEGER;
