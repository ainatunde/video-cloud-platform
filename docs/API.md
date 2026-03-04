# API Reference

## AI Analysis Service (port 8000)

### POST /analyze/frame

Analyze a single video frame for object detection and scene classification.

**Request:**
```http
POST /analyze/frame
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "frame_data": "<base64-encoded JPEG>",
  "timestamp": 1234567890.123
}
```

**Response:**
```json
{
  "stream_id": "live/stream1",
  "timestamp": 1234567890.123,
  "objects": [
    {"label": "person", "confidence": 0.94, "bbox": [100, 50, 300, 400]},
    {"label": "car", "confidence": 0.87, "bbox": [400, 200, 600, 350]}
  ],
  "scene_changed": true,
  "scene_id": "scene_abc123",
  "content_category": "IAB-17",
  "iab_tier1": "Sports",
  "iab_tier2": "Motor Racing",
  "processing_ms": 12
}
```

---

### POST /analyze/video

Batch process a VOD file for scene detection and content analysis.

**Request:**
```http
POST /analyze/video
Content-Type: application/json

{
  "stream_id": "vod/movie123",
  "video_url": "http://storage/vod/movie123.mp4",
  "frame_skip": 5,
  "threshold": 0.5
}
```

**Response:**
```json
{
  "stream_id": "vod/movie123",
  "total_frames_analyzed": 2400,
  "scene_changes": [
    {
      "timestamp": 12.5,
      "confidence": 0.82,
      "objects_before": ["person", "desk"],
      "objects_after": ["car", "road"]
    }
  ],
  "processing_time_s": 34.2
}
```

---

### GET /health

Health check endpoint.

**Response:**
```json
{"status": "ok", "model": "yolov8n", "gpu": false, "uptime_s": 3600}
```

---

### WebSocket /ws/stream

Real-time frame analysis for live streams.

**Connect:** `ws://yolo-analyzer:8000/ws/stream?stream_id=live/stream1`

**Send frames (JSON):**
```json
{"frame_data": "<base64 JPEG>", "pts": 1234567890}
```

**Receive events:**
```json
{"type": "scene_change", "stream_id": "live/stream1", "pts": 1234567890, "confidence": 0.78}
```

---

## SCTE-35 Processor Service (port 8001)

### POST /inject

Inject a SCTE-35 marker into a live stream.

**Request:**
```http
POST /inject
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "pts": 30.0,
  "duration": 30.0,
  "splice_type": "splice_insert",
  "event_id": 12345,
  "out_of_network": true
}
```

**Response:**
```json
{
  "success": true,
  "event_id": 12345,
  "pts_ticks": 2700000,
  "duration_ticks": 2700000,
  "injected_at": "2024-01-15T10:30:00Z"
}
```

---

### POST /validate

Validate SCTE-35 markers in a TS file or stream.

**Request:**
```http
POST /validate
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "event_id": 12345
}
```

**Response:**
```json
{
  "valid": true,
  "event_id": 12345,
  "pts_accuracy_ms": 12,
  "crc_valid": true,
  "section_syntax": "short"
}
```

---

### GET /health

```json
{"status": "ok", "tsduck_version": "3.38", "uptime_s": 7200}
```

---

## Transcoding Service (port 8002)

### POST /transcode/live

Start live transcoding for an incoming stream.

**Request:**
```http
POST /transcode/live
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "input_url": "rtmp://srs:1935/live/stream1",
  "profiles": ["360p", "480p", "720p", "1080p"],
  "hardware_accel": false
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "stream_id": "live/stream1",
  "status": "running",
  "output_urls": {
    "360p": "rtmp://localhost:1935/abr/stream1_360p",
    "480p": "rtmp://localhost:1935/abr/stream1_480p",
    "720p": "rtmp://localhost:1935/abr/stream1_720p",
    "1080p": "rtmp://localhost:1935/abr/stream1_1080p"
  },
  "started_at": "2024-01-15T10:30:00Z"
}
```

---

### POST /transcode/vod

Transcode a VOD file to multiple quality levels.

**Request:**
```http
POST /transcode/vod
Content-Type: application/json

{
  "input_url": "http://storage/vod/source.mp4",
  "output_dir": "/var/www/vod/movie123",
  "profiles": ["360p", "720p", "1080p"],
  "hardware_accel": false
}
```

**Response:**
```json
{
  "job_id": "job_xyz789",
  "status": "queued",
  "estimated_duration_s": 120
}
```

---

### GET /jobs/{id}

Get transcoding job status.

**Response:**
```json
{
  "job_id": "job_xyz789",
  "status": "running",
  "progress": 0.45,
  "fps": 28.3,
  "elapsed_s": 54,
  "eta_s": 66
}
```

---

### DELETE /jobs/{id}

Cancel and remove a transcoding job.

**Response:**
```json
{"job_id": "job_xyz789", "stopped": true}
```

---

## Packaging Service (port 8003)

### POST /package/hls

Package multi-bitrate streams into an HLS master playlist.

**Request:**
```http
POST /package/hls
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "inputs": [
    {"url": "rtmp://ffmpeg:1935/abr/stream1_360p", "bitrate": 800, "resolution": "640x360"},
    {"url": "rtmp://ffmpeg:1935/abr/stream1_720p", "bitrate": 2800, "resolution": "1280x720"},
    {"url": "rtmp://ffmpeg:1935/abr/stream1_1080p", "bitrate": 5000, "resolution": "1920x1080"}
  ],
  "segment_duration": 6,
  "output_dir": "/var/www/streams/live/stream1"
}
```

**Response:**
```json
{
  "master_playlist": "http://nginx:80/live/stream1/master.m3u8",
  "status": "packaging"
}
```

---

### POST /package/dash

Package streams into an MPEG-DASH MPD manifest.

**Request/Response**: Same structure as `/package/hls` but returns an `.mpd` URL.

---

## Ad Server (port 3000)

### POST /ads/decision

Request an ad decision for a SCTE-35 event.

**Request:**
```http
POST /ads/decision
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "event_id": 12345,
  "duration_s": 30,
  "content_category": "IAB-17",
  "viewer_id": "viewer_abc",
  "geo_country": "US"
}
```

**Response:**
```json
{
  "ad_id": "ad_def456",
  "ad_server": "gam",
  "vast_url": "https://pubads.g.doubleclick.net/...",
  "creative_url": "https://cdn.example.com/ads/ad_def456.mp4",
  "duration_s": 30,
  "decision_ms": 45
}
```

---

### GET /ads/vast/{id}

Retrieve the VAST XML for a specific ad.

**Response:** VAST 3.0 XML document.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<VAST version="3.0">
  <Ad id="ad_def456">
    <InLine>
      <AdSystem>Video Cloud Platform</AdSystem>
      <AdTitle>Sample Ad</AdTitle>
      <Impression><![CDATA[http://ad-server:3000/ads/impression/ad_def456]]></Impression>
      <Creatives>
        <Creative>
          <Linear>
            <Duration>00:00:30</Duration>
            <MediaFiles>
              <MediaFile type="video/mp4" bitrate="1500" width="1280" height="720">
                <![CDATA[https://cdn.example.com/ads/ad_def456.mp4]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>
```

---

### POST /ads/impression/{id}

Record an ad impression event.

**Request:**
```http
POST /ads/impression/ad_def456
Content-Type: application/json

{
  "stream_id": "live/stream1",
  "viewer_id": "viewer_abc",
  "event_type": "impression"
}
```

**Response:**
```json
{"recorded": true, "event_id": "evt_789"}
```

---

## Dashboard Server API (port 3002)

The dashboard server proxies requests to underlying services:

| Dashboard Path | Proxied To |
|---------------|------------|
| `GET /api/streams` | `http://srs:1985/api/v1/streams` |
| `POST /api/transcode/*` | `http://ffmpeg-transcoder:8002/*` |
| `GET /api/ads/*` | `http://ad-server:3000/*` |
| `POST /api/scte35/*` | `http://scte35-processor:8001/*` |
| `GET /health` | Local health check |

All dashboard API endpoints accept and return JSON. Errors follow:
```json
{"error": "description", "code": 400}
```
