# Troubleshooting Guide

## SRS Not Accepting RTMP Streams

### Symptom
OBS or FFmpeg shows "Connection refused" or "Connect failed" when streaming to `rtmp://host:1935/live/key`.

### Diagnosis
```bash
# Check if SRS is running
docker compose ps srs
curl http://localhost:1985/api/v1/versions

# Check SRS logs
docker compose logs srs | tail -50
```

### Solutions

1. **Port not exposed**: Ensure port 1935 is mapped in `docker-compose.yml`:
   ```yaml
   ports:
     - "1935:1935"
   ```

2. **Firewall blocking port**: Open RTMP port:
   ```bash
   ufw allow 1935/tcp
   # AWS Security Groups: add inbound rule TCP 1935
   ```

3. **SRS config syntax error**: Validate config:
   ```bash
   docker exec srs_container srs -t -c /etc/srs/srs.conf
   ```

4. **Max connections reached**: Increase `max_connections` in `srs.conf`.

---

## YOLO Model Not Loading

### Symptom
`yolo-analyzer` container starts but `/health` returns `{"status": "error"}` or the container restarts.

### Diagnosis
```bash
docker compose logs yolo-analyzer | grep -i error
```

### Solutions

1. **Model file not found**: Ensure the model file exists:
   ```bash
   docker exec yolo_container ls -la /models/
   # If empty, download the model:
   docker exec yolo_container python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
   ```

2. **Insufficient memory**: YOLOv8x requires ~4GB RAM. Use `yolov8n` for limited memory:
   ```bash
   YOLO_MODEL=yolov8n.pt docker compose up -d yolo-analyzer
   ```

3. **CUDA version mismatch**: Ensure CUDA toolkit matches PyTorch version:
   ```bash
   docker exec yolo_container python -c "import torch; print(torch.version.cuda)"
   ```

4. **Python package missing**: Reinstall dependencies:
   ```bash
   docker compose build yolo-analyzer --no-cache
   ```

---

## SCTE-35 Markers Not Appearing in Stream

### Symptom
Ad breaks are expected but no SCTE-35 markers appear in the HLS stream or TS output.

### Diagnosis
```bash
# Check SCTE-35 processor logs
docker compose logs scte35-processor | tail -100

# Verify Redis events are being published
docker exec redis_container redis-cli subscribe scene_changes

# Check injection endpoint directly
curl -X POST http://localhost:8001/inject \
  -H 'Content-Type: application/json' \
  -d '{"stream_id":"live/test","pts":30.0,"duration":30.0,"splice_type":"splice_insert"}'
```

### Solutions

1. **TSDuck not installed in container**:
   ```bash
   docker exec scte35_container which tsp
   # If not found: rebuild the image
   docker compose build scte35-processor --no-cache
   ```

2. **PTS calculation error**: The target PTS may be in the past. Add lead time:
   - Check `tsduck_injector.py` and ensure `pts_from_timestamp()` adds at least 5 seconds lead.

3. **Wrong PID**: Default injection PID is 500. If this conflicts, change in `tsduck_injector.py`.

4. **AUTO_INJECT_ENABLED=false**: Check environment variable and set to `true`.

5. **YOLO not detecting scene changes**: Lower `SCENE_CHANGE_THRESHOLD` (e.g., from 0.5 to 0.3).

---

## FFmpeg Transcoding Errors

### Symptom
`ffmpeg-transcoder` logs show errors; no ABR output streams are produced.

### Common Errors and Fixes

**"Connection refused" to input stream**:
```bash
# Verify SRS is publishing
curl http://localhost:1985/api/v1/streams
# Wait for stream to appear before starting transcoder
```

**"Conversion failed" / codec error**:
```bash
# Check FFmpeg codec support
docker exec ffmpeg_container ffmpeg -codecs 2>&1 | grep libx264
# If missing: rebuild with --enable-libx264
```

**Out of memory (OOM kill)**:
```bash
# Reduce parallel jobs
MAX_PARALLEL_JOBS=2 docker compose up -d ffmpeg-transcoder
# Or increase container memory limit in docker-compose.yml
```

**Hardware acceleration not available**:
```bash
# Disable NVENC and fall back to CPU
HARDWARE_ACCEL=false docker compose up -d ffmpeg-transcoder

# For NVENC debugging
docker exec ffmpeg_container nvidia-smi
docker exec ffmpeg_container ffmpeg -encoders 2>&1 | grep nvenc
```

---

## Grafana Datasource Connection Issues

### Symptom
Grafana dashboards show "No data" or "datasource connection error".

### Diagnosis
```bash
# Test TimescaleDB from Grafana container
docker exec grafana_container nc -zv timescaledb 5432
```

### Solutions

1. **Wrong hostname**: Ensure `url` in `datasources/timescaledb.yaml` is `timescaledb:5432`.

2. **Wrong password**: Check `POSTGRES_PASSWORD` env var matches `secureJsonData.password`.

3. **TimescaleDB not initialized**: Run init SQL:
   ```bash
   docker exec timescaledb_container psql -U postgres -d platform \
     -f /docker-entrypoint-initdb.d/init.sql
   ```

4. **Extension not installed**:
   ```bash
   docker exec timescaledb_container psql -U postgres -d platform \
     -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
   ```

5. **SSL mode mismatch**: Set `sslmode: disable` in datasource config for local deployments.

---

## Ad Server Timeouts

### Symptom
Ad decisions time out; logs show "Ad decision timeout after 200ms".

### Diagnosis
```bash
# Test ad server response time
time curl -s -X POST http://localhost:3000/ads/decision \
  -H 'Content-Type: application/json' \
  -d '{"stream_id":"test","duration_s":30}'
```

### Solutions

1. **External ad server slow**: Increase `AD_DECISION_TIMEOUT_MS`:
   ```bash
   AD_DECISION_TIMEOUT_MS=500 docker compose up -d ad-server
   ```

2. **Redis not available**: Check Redis connectivity:
   ```bash
   docker exec ad_server_container node -e "
   const r = require('redis').createClient({url:'redis://redis:6379'});
   r.connect().then(() => console.log('Redis OK')).catch(console.error);
   "
   ```

3. **Database connection pool exhausted**: Increase pool size in `DATABASE_URL` or adjust `pg.Pool` settings.

4. **VAST URL unreachable**: Test the ad network URL directly:
   ```bash
   curl -v "https://pubads.g.doubleclick.net/gampad/ads?..." | head -50
   ```

---

## TimescaleDB Performance Issues

### Symptom
Slow queries; high CPU on TimescaleDB container; insert backlog growing.

### Diagnosis
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check chunk count
SELECT count(*) FROM timescaledb_information.chunks WHERE hypertable_name = 'stream_metrics';

-- Check table sizes
SELECT hypertable_name, pg_size_pretty(total_bytes)
FROM timescaledb_information.hypertable_size WHERE hypertable_name = 'stream_metrics';
```

### Solutions

1. **Too many small chunks**: Increase chunk interval:
   ```sql
   SELECT set_chunk_time_interval('stream_metrics', INTERVAL '1 day');
   ```

2. **Missing indexes**: Ensure indexes exist:
   ```sql
   \d stream_metrics
   -- Check idx_stream_metrics_stream exists
   ```

3. **Old chunks not compressed**: Enable compression:
   ```sql
   SELECT add_compression_policy('stream_metrics', INTERVAL '7 days');
   ```

4. **Continuous aggregate not refreshing**: Manually refresh:
   ```sql
   CALL refresh_continuous_aggregate('stream_metrics_hourly', NULL, NULL);
   ```

5. **Connection pool exhausted**: Check `max_connections` in PostgreSQL:
   ```bash
   docker exec timescaledb_container psql -U postgres -c "SHOW max_connections;"
   # Increase in postgresql.conf: max_connections = 200
   ```
