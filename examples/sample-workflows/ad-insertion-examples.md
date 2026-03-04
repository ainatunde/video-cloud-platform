# Ad Insertion Examples

This guide demonstrates various methods of injecting ads into live and VOD streams.

---

## Manual SCTE-35 Injection via API

### Basic splice_insert

```bash
# Inject a 30-second ad break starting at t=30s in stream "live/stream1"
curl -X POST http://localhost:8001/inject \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/stream1",
    "pts": 30.0,
    "duration": 30.0,
    "splice_type": "splice_insert",
    "event_id": 1001,
    "out_of_network": true
  }'
```

Expected response:
```json
{
  "success": true,
  "event_id": 1001,
  "pts_ticks": 2700000,
  "duration_ticks": 2700000,
  "injected_at": "2024-01-15T10:30:00Z"
}
```

### time_signal with segmentation descriptor

```bash
curl -X POST http://localhost:8001/inject \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/stream1",
    "pts": 60.0,
    "duration": 15.0,
    "splice_type": "time_signal",
    "event_id": 1002
  }'
```

### Validate an injected marker

```bash
curl -X POST http://localhost:8001/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/stream1",
    "event_id": 1001
  }'
```

Response:
```json
{
  "valid": true,
  "event_id": 1001,
  "pts_accuracy_ms": 8,
  "crc_valid": true,
  "section_syntax": "short"
}
```

---

## Automatic YOLO-Based Insertion

The platform detects scene changes automatically and injects markers without manual intervention.

### Enable auto-injection

```bash
# Ensure environment variable is set (default: true)
AUTO_INJECT_ENABLED=true docker compose up -d scte35-processor
```

### Monitor auto-injection events

```bash
# Subscribe to Redis channel to see events in real-time
docker exec redis_container redis-cli subscribe scene_changes
```

Example event:
```json
{
  "type": "scene_change",
  "stream_id": "live/stream1",
  "pts": 1234.5,
  "confidence": 0.74,
  "content_category": "IAB-17",
  "auto_inject": true
}
```

### Tune sensitivity

Lower the threshold to inject more frequently:
```bash
SCENE_CHANGE_THRESHOLD=0.3 docker compose up -d yolo-analyzer
```

---

## VAST Integration Example

### Request an ad decision from the ad server

```bash
curl -X POST http://localhost:3000/ads/decision \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/stream1",
    "event_id": 1001,
    "duration_s": 30,
    "content_category": "IAB-17",
    "viewer_id": "viewer_abc123",
    "geo_country": "US"
  }'
```

Response:
```json
{
  "ad_id": "ad_gam_789",
  "ad_server": "gam",
  "vast_url": "https://pubads.g.doubleclick.net/gampad/ads?...",
  "creative_url": "https://storage.googleapis.com/gcdn/ads/sample.mp4",
  "duration_s": 30,
  "decision_ms": 42
}
```

### Retrieve VAST XML

```bash
curl http://localhost:3000/ads/vast/ad_gam_789
```

### Record an impression

```bash
curl -X POST http://localhost:3000/ads/impression/ad_gam_789 \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/stream1",
    "viewer_id": "viewer_abc123",
    "event_type": "impression"
  }'
```

### Record ad completion

```bash
curl -X POST http://localhost:3000/ads/impression/ad_gam_789 \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/stream1",
    "viewer_id": "viewer_abc123",
    "event_type": "complete"
  }'
```

---

## Testing Full Ad Pipeline with curl

The following script tests the complete ad insertion flow:

```bash
#!/bin/bash
set -e

STREAM_ID="live/stream1"
BASE_URL="http://localhost"

echo "=== Testing Ad Insertion Pipeline ==="

echo "1. Injecting SCTE-35 marker..."
INJECT_RESULT=$(curl -s -X POST "${BASE_URL}:8001/inject" \
  -H 'Content-Type: application/json' \
  -d "{\"stream_id\":\"${STREAM_ID}\",\"pts\":30.0,\"duration\":30.0,\"splice_type\":\"splice_insert\"}")
EVENT_ID=$(echo $INJECT_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['event_id'])")
echo "   Event ID: $EVENT_ID"

echo "2. Requesting ad decision..."
AD_RESULT=$(curl -s -X POST "${BASE_URL}:3000/ads/decision" \
  -H 'Content-Type: application/json' \
  -d "{\"stream_id\":\"${STREAM_ID}\",\"event_id\":${EVENT_ID},\"duration_s\":30,\"geo_country\":\"US\"}")
AD_ID=$(echo $AD_RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ad_id','none'))")
echo "   Ad ID: $AD_ID"

echo "3. Fetching VAST..."
curl -s "${BASE_URL}:3000/ads/vast/${AD_ID}" | head -5

echo "4. Recording impression..."
curl -s -X POST "${BASE_URL}:3000/ads/impression/${AD_ID}" \
  -H 'Content-Type: application/json' \
  -d "{\"stream_id\":\"${STREAM_ID}\",\"event_type\":\"impression\"}"

echo "5. Validating SCTE-35 marker..."
curl -s -X POST "${BASE_URL}:8001/validate" \
  -H 'Content-Type: application/json' \
  -d "{\"stream_id\":\"${STREAM_ID}\",\"event_id\":${EVENT_ID}}" | python3 -m json.tool

echo "=== Pipeline test complete ==="
```

---

## Monitoring Ad Analytics in TimescaleDB

```sql
-- Connect to TimescaleDB
psql postgresql://postgres:changeme@localhost:5432/platform

-- Recent ad events
SELECT time, ad_id, event_type, stream_id, geo_country
FROM ad_analytics
ORDER BY time DESC
LIMIT 20;

-- Fill rate last hour
SELECT
  stream_id,
  COUNT(*) FILTER (WHERE event_type = 'impression') AS impressions,
  COUNT(*) FILTER (WHERE event_type = 'complete') AS completions,
  ROUND(100.0 * COUNT(*) FILTER (WHERE event_type = 'complete') /
    NULLIF(COUNT(*) FILTER (WHERE event_type = 'impression'), 0), 1) AS fill_rate
FROM ad_analytics
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY stream_id;
```
