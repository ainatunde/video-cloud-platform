# Configuration Reference

## Environment Variables

### Global / Platform-Wide

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `warn` | Log verbosity: `debug`, `info`, `warn`, `error` |
| `TZ` | `UTC` | Container timezone |
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL (event bus) |

---

### SRS Ingest Server

| Variable | Default | Description |
|----------|---------|-------------|
| `SRS_RTMP_PORT` | `1935` | RTMP ingest port |
| `SRS_HTTP_PORT` | `8080` | HTTP server port for HLS delivery |
| `SRS_API_PORT` | `1985` | HTTP API port |
| `SRS_SRT_PORT` | `8890` | SRT ingest port |
| `CANDIDATE` | _(empty)_ | WebRTC ICE candidate IP/STUN URL |
| `MAX_CONNECTIONS` | `1000` | Maximum simultaneous connections |

### SRS Configuration Options (`srs.conf`)

| Option | Default | Description |
|--------|---------|-------------|
| `hls_fragment` | `6` | HLS segment duration in seconds |
| `hls_window` | `60` | HLS playlist window (seconds; divide by fragment = segment count) |
| `hls_cleanup` | `on` | Delete old HLS segments automatically |
| `max_connections` | `1000` | Max concurrent client connections |
| `srs_log_level` | `warn` | SRS log level: `trace/info/warn/error/off` |

---

### YOLO AI Analyzer

| Variable | Default | Description |
|----------|---------|-------------|
| `YOLO_MODEL` | `yolov8n.pt` | YOLO model file to use (`yolov8n`, `yolov8s`, `yolov8m`, `yolov8l`, `yolov8x`) |
| `GPU_ENABLED` | `false` | Enable CUDA GPU inference (`true`/`false`) |
| `MODEL_PATH` | `/models` | Directory where YOLO model files are stored |
| `SCENE_CHANGE_THRESHOLD` | `0.5` | Cosine similarity threshold for scene change detection (0.0–1.0; lower = more sensitive) |
| `FRAME_SKIP` | `5` | Process every Nth frame (higher = faster, less accurate) |
| `BATCH_SIZE` | `1` | Number of frames per inference batch (GPU: increase to 4–8) |
| `CONFIDENCE_THRESHOLD` | `0.25` | Minimum detection confidence to include in results |
| `YOLO_PORT` | `8000` | HTTP API listening port |

---

### SCTE-35 Processor

| Variable | Default | Description |
|----------|---------|-------------|
| `YOLO_URL` | `http://yolo-analyzer:8000` | YOLO analyzer service URL |
| `SRS_URL` | `http://srs:1985` | SRS API URL |
| `SCTE35_PORT` | `8001` | HTTP API listening port |
| `PTS_TOLERANCE_MS` | `100` | Acceptable PTS deviation for validation (milliseconds) |
| `DEFAULT_SPLICE_TYPE` | `splice_insert` | Default SCTE-35 command: `splice_insert` or `time_signal` |
| `DEFAULT_DURATION_S` | `30` | Default ad break duration in seconds |
| `AUTO_INJECT_ENABLED` | `true` | Enable automatic injection on scene change events |

---

### FFmpeg Transcoder

| Variable | Default | Description |
|----------|---------|-------------|
| `HARDWARE_ACCEL` | `false` | Enable hardware acceleration: `false`, `nvenc`, `vaapi`, `videotoolbox` |
| `SRS_URL` | `http://srs:1985` | SRS API for stream discovery |
| `SCTE35_URL` | `http://scte35-processor:8001` | SCTE-35 processor URL |
| `PRESETS_DIR` | `./presets` | Directory containing JSON preset files |
| `TRANSCODER_PORT` | `8002` | HTTP API listening port |
| `MAX_PARALLEL_JOBS` | `4` | Maximum concurrent transcoding jobs |
| `SEGMENT_DURATION` | `6` | Output HLS segment duration (seconds) |
| `GOP_SIZE` | `60` | Key frame interval in frames |

### FFmpeg Preset Parameters

Each preset JSON file (`services/transcoding/presets/`) supports:

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Profile name (e.g., `"1080p"`) |
| `width` | int | Output video width (pixels) |
| `height` | int | Output video height (pixels) |
| `video_bitrate` | string | Video bitrate (e.g., `"5000k"`) |
| `audio_bitrate` | string | Audio bitrate (e.g., `"192k"`) |
| `codec` | string | Video codec: `libx264`, `h264_nvenc`, `libx265`, `hevc_nvenc` |
| `preset` | string | Encoder speed preset: `ultrafast`/`fast`/`medium`/`slow` |
| `profile` | string | H.264 profile: `baseline`/`main`/`high` |
| `level` | string | H.264 level: `3.0`, `3.1`, `4.0`, `4.1` |
| `fps` | int | Output frame rate (0 = same as input) |
| `keyframe_interval` | int | Key frame interval in frames |

---

### Shaka Packager

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCODER_URL` | `http://ffmpeg-transcoder:8002` | FFmpeg transcoder URL |
| `OUTPUT_DIR` | `/var/www/streams` | Root directory for HLS/DASH output |
| `SEGMENT_DURATION` | `6` | Segment duration in seconds |
| `PACKAGER_PORT` | `8003` | HTTP API listening port |
| `ENABLE_DASH` | `true` | Generate MPEG-DASH manifests in addition to HLS |
| `ENCRYPTION_ENABLED` | `false` | Enable AES-128 segment encryption |

---

### Ad Server

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | `production` | Node.js environment |
| `PORT` | `3000` | HTTP server port |
| `REDIS_URL` | `redis://redis:6379` | Redis URL for event publishing |
| `DATABASE_URL` | _(required)_ | PostgreSQL connection string |
| `AD_DECISION_TIMEOUT_MS` | `200` | Maximum ad decision latency before fallback |
| `DEFAULT_AD_DURATION_S` | `30` | Default ad break duration |
| `FALLBACK_AD_URL` | _(empty)_ | VAST URL to use if primary ad servers time out |
| `GAM_NETWORK_CODE` | _(empty)_ | Google Ad Manager network code |

### Ad Server Configuration (`services/ad-insertion/config/ad-servers.json`)

```json
{
  "servers": [
    {
      "id": "gam",
      "name": "Google Ad Manager",
      "type": "GAM",
      "enabled": true,
      "vast_url": "https://pubads.g.doubleclick.net/gampad/ads?...",
      "timeout_ms": 150,
      "priority": 1
    }
  ]
}
```

---

### Analytics Collectors

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:changeme@timescaledb:5432/platform` | TimescaleDB connection string |
| `SRS_API_URL` | `http://srs:1985` | SRS API for stream metrics polling |
| `COLLECT_INTERVAL` | `10` | Stream metrics polling interval (seconds) |
| `AD_BATCH_SIZE` | `50` | Maximum ad events to flush per batch |
| `AD_FLUSH_INTERVAL` | `5` | Seconds to wait between Redis polls when queue is empty |

---

### Grafana

| Variable | Default | Description |
|----------|---------|-------------|
| `GF_SECURITY_ADMIN_PASSWORD` | _(required)_ | Grafana admin password |
| `GF_SERVER_ROOT_URL` | `http://localhost:3001` | External URL for Grafana |
| `GF_SERVER_SERVE_FROM_SUB_PATH` | `false` | Set to `true` when deploying at `/grafana` subpath |
| `GF_AUTH_ANONYMOUS_ENABLED` | `false` | Allow unauthenticated dashboard viewing |
| `GF_USERS_ALLOW_SIGN_UP` | `false` | Disable self-registration |

### Prometheus Configuration (`configs/prometheus.yml`)

| Option | Description |
|--------|-------------|
| `scrape_interval` | How frequently to scrape metrics (default: `15s`) |
| `evaluation_interval` | How frequently to evaluate alerting rules |
| `scrape_configs[].job_name` | Logical name for the scrape target |
| `scrape_configs[].static_configs[].targets` | `host:port` pairs to scrape |
| `scrape_configs[].metrics_path` | Path to the metrics endpoint (default: `/metrics`) |

---

### Dashboard Server

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | HTTP server port |
| `SRS_API_URL` | `http://srs:1985` | SRS proxy target |
| `TRANSCODER_URL` | `http://ffmpeg-transcoder:8002` | Transcoder proxy target |
| `AD_SERVER_URL` | `http://ad-server:3000` | Ad server proxy target |
| `SCTE35_URL` | `http://scte35-processor:8001` | SCTE-35 processor proxy target |
| `DATABASE_URL` | _(optional)_ | Direct TimescaleDB access for server-side queries |

---

## TimescaleDB Schema Configuration

### Hypertable Chunk Intervals

Default chunk interval is 7 days. Adjust for higher write volumes:

```sql
-- Smaller chunks for high-volume deployments (1-day chunks)
SELECT set_chunk_time_interval('stream_metrics', INTERVAL '1 day');
SELECT set_chunk_time_interval('ad_analytics', INTERVAL '1 day');
```

### Compression Policy

Enable automatic compression for chunks older than 7 days:

```sql
ALTER TABLE stream_metrics SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'stream_id'
);
SELECT add_compression_policy('stream_metrics', INTERVAL '7 days');
```

### Retention Policy

Automatically drop chunks older than 90 days:

```sql
SELECT add_retention_policy('stream_metrics', INTERVAL '90 days');
SELECT add_retention_policy('ad_analytics', INTERVAL '365 days');
```
