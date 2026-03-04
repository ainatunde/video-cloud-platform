# Live Streaming Workflow

This guide walks through a complete live streaming session using the Video Cloud Platform.

## Prerequisites

- Platform running: `docker compose up -d`
- OBS Studio or FFmpeg installed on the streaming machine
- A test video file (or webcam) for content

---

## Step 1: Start the Platform

```bash
cd /path/to/video-cloud-platform

# Start all services
docker compose up -d

# Wait for all services to be healthy (about 30 seconds)
docker compose ps

# Expected output: all services showing "Up" or "healthy"
```

Verify core services are up:
```bash
curl http://localhost:1985/api/v1/versions   # SRS
curl http://localhost:8000/health             # YOLO Analyzer
curl http://localhost:8001/health             # SCTE-35 Processor
curl http://localhost:8002/health             # FFmpeg Transcoder
curl http://localhost:3000/health             # Ad Server
curl http://localhost:3002/health             # Dashboard
```

---

## Step 2: Configure Your Encoder (OBS or FFmpeg)

### OBS Studio

1. Open OBS → **Settings** → **Stream**
2. Set:
   - **Service**: Custom
   - **Server**: `rtmp://localhost:1935/live`
   - **Stream Key**: `mystream` (or any identifier)
3. Click **Start Streaming**

### FFmpeg (test stream from file)

```bash
# Stream a test video file on loop
ffmpeg -re \
  -stream_loop -1 \
  -i /path/to/test-video.mp4 \
  -c:v libx264 -preset fast -b:v 3000k -maxrate 3500k -bufsize 6000k \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv \
  rtmp://localhost:1935/live/mystream

# Or generate a synthetic test pattern
ffmpeg -re \
  -f lavfi -i "testsrc2=size=1280x720:rate=30" \
  -f lavfi -i "sine=frequency=440:sample_rate=44100" \
  -c:v libx264 -preset ultrafast -b:v 2000k \
  -c:a aac -b:a 64k \
  -f flv \
  rtmp://localhost:1935/live/mystream
```

### SRT Ingest (lower latency)

```bash
ffmpeg -re \
  -i /path/to/test-video.mp4 \
  -c:v libx264 -preset fast -b:v 3000k \
  -c:a aac -b:a 128k \
  -f mpegts \
  "srt://localhost:8890?streamid=live/mystream&latency=200000"
```

---

## Step 3: YOLO Auto-Detects Scenes

Once the stream is live, YOLO begins analyzing frames automatically:

```bash
# Monitor YOLO activity
docker compose logs -f yolo-analyzer

# Expected log output:
# INFO: Scene change detected: stream_id=live/mystream pts=90000 confidence=0.72
# INFO: Content category: IAB-17 (Sports)
```

Check the AI analysis endpoint directly:
```bash
# Get current scene info
curl http://localhost:8000/health
```

---

## Step 4: SCTE-35 Markers Injected

Scene changes trigger automatic SCTE-35 injection (if `AUTO_INJECT_ENABLED=true`):

```bash
# Monitor SCTE-35 processor
docker compose logs -f scte35-processor

# Expected log output:
# INFO: Injecting splice_insert: stream=live/mystream pts=2700000 duration=2700000
# INFO: Validation passed: event_id=1 pts_accuracy=12ms
```

Inject a manual marker via API:
```bash
curl -X POST http://localhost:8001/inject \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "live/mystream",
    "pts": 30.0,
    "duration": 30.0,
    "splice_type": "splice_insert"
  }'
```

---

## Step 5: ABR Transcoding Kicks In

The FFmpeg transcoder creates the multi-bitrate ladder:

```bash
# Monitor transcoding
docker compose logs -f ffmpeg-transcoder

# Verify all quality levels are producing output
curl http://localhost:8002/jobs
```

---

## Step 6: HLS Output Available for Viewers

The stream is now available for playback:

```bash
# Master playlist (all quality levels)
curl http://localhost:8080/live/mystream.m3u8

# Individual quality levels
curl http://localhost:8080/live/mystream_360p.m3u8
curl http://localhost:8080/live/mystream_720p.m3u8
curl http://localhost:8080/live/mystream_1080p.m3u8
```

Play in browser with the web player:
```
http://localhost:8888/src/index.html?url=http://localhost:8080/live/mystream.m3u8
```

Play with VLC or mpv:
```bash
vlc http://localhost:8080/live/mystream.m3u8
mpv http://localhost:8080/live/mystream.m3u8
```

---

## Step 7: Monitor in Dashboard

Open the management dashboard:
```
http://localhost:3002
```

- **Streams** tab: See live viewer count, bitrate, uptime
- **Analytics** tab: View Grafana dashboards at `http://localhost:3001`
- **SCTE-35** tab: View injected markers and validation status

---

## Step 8: Stop the Stream

```bash
# Stop FFmpeg encoder (Ctrl+C in the FFmpeg terminal)

# Or stop OBS: Click "Stop Streaming"

# SRS will automatically detect the publisher disconnect
# HLS segments remain available for ~60 seconds (hls_window)
```

---

## Verifying the Full Pipeline

Run this script to check all components in sequence:

```bash
#!/bin/bash
STREAM_ID="live/mystream"

echo "1. Checking SRS for active stream..."
curl -s http://localhost:1985/api/v1/streams | python3 -m json.tool | grep -A5 "\"id\": \"${STREAM_ID}\""

echo "2. Checking HLS manifest..."
curl -s -I http://localhost:8080/${STREAM_ID}.m3u8 | head -5

echo "3. Checking SCTE-35 markers..."
curl -s http://localhost:8001/markers?stream_id=${STREAM_ID} | python3 -m json.tool

echo "4. Checking transcoder jobs..."
curl -s http://localhost:8002/jobs | python3 -m json.tool

echo "Done!"
```
