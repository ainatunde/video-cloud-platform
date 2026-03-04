# VOD Processing Workflow

This guide covers processing a video-on-demand (VOD) file through the platform pipeline.

## Overview

VOD workflow: Source file → FFmpeg transcoding → Shaka packaging → HLS/DASH output → CDN delivery

---

## Step 1: Prepare Source File

```bash
# Recommended source: H.264, 1080p, high bitrate (10-30 Mbps)
# Analyze source file
ffprobe -v quiet -print_format json -show_streams /path/to/source.mp4 | \
  python3 -m json.tool | grep -E '"codec_name|width|height|bit_rate|r_frame_rate"'
```

---

## Step 2: Transcode to ABR Ladder

```bash
# Submit VOD transcoding job
curl -X POST http://localhost:8002/transcode/vod \
  -H 'Content-Type: application/json' \
  -d '{
    "input_url": "http://storage/vod/source.mp4",
    "output_dir": "/var/www/vod/movie123",
    "profiles": ["360p", "480p", "720p", "1080p"],
    "hardware_accel": false
  }'

# Response: {"job_id": "job_abc123", "status": "queued"}
```

Monitor job progress:
```bash
# Poll job status
JOB_ID="job_abc123"
while true; do
  STATUS=$(curl -s http://localhost:8002/jobs/${JOB_ID} | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], d.get('progress', 0))")
  echo "Status: $STATUS"
  if [[ "$STATUS" == *"completed"* ]]; then break; fi
  sleep 5
done
```

---

## Step 3: Package with Shaka

```bash
# Package into HLS
curl -X POST http://localhost:8003/package/hls \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "vod/movie123",
    "inputs": [
      {"url": "file:///var/www/vod/movie123/360p.mp4", "bitrate": 800, "resolution": "640x360"},
      {"url": "file:///var/www/vod/movie123/480p.mp4", "bitrate": 1400, "resolution": "854x480"},
      {"url": "file:///var/www/vod/movie123/720p.mp4", "bitrate": 2800, "resolution": "1280x720"},
      {"url": "file:///var/www/vod/movie123/1080p.mp4", "bitrate": 5000, "resolution": "1920x1080"}
    ],
    "segment_duration": 6,
    "output_dir": "/var/www/streams/vod/movie123"
  }'
```

---

## Step 4: Run AI Analysis on VOD

```bash
# Analyze VOD for scene changes and content categories
curl -X POST http://localhost:8000/analyze/video \
  -H 'Content-Type: application/json' \
  -d '{
    "stream_id": "vod/movie123",
    "video_url": "http://storage/vod/source.mp4",
    "frame_skip": 30,
    "threshold": 0.5
  }'

# Response includes scene change timestamps
```

---

## Step 5: Inject SCTE-35 Markers at Scene Changes

```bash
# After AI analysis, inject markers at identified ad break points
SCENE_CHANGES='[30.5, 125.0, 287.3, 420.8]'

echo "$SCENE_CHANGES" | python3 -c "
import sys, json, subprocess

timestamps = json.load(sys.stdin)
for ts in timestamps:
    subprocess.run([
        'curl', '-s', '-X', 'POST', 'http://localhost:8001/inject',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            'stream_id': 'vod/movie123',
            'pts': ts,
            'duration': 30.0,
            'splice_type': 'splice_insert'
        })
    ])
    print(f'Injected marker at {ts}s')
"
```

---

## Step 6: Verify Output

```bash
# Check master playlist
curl -s http://localhost:8080/vod/movie123/master.m3u8

# Expected output:
# #EXTM3U
# #EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
# 360p/stream.m3u8
# #EXT-X-STREAM-INF:BANDWIDTH=2800000,RESOLUTION=1280x720
# 720p/stream.m3u8
# ...

# Validate with ffprobe
ffprobe -v quiet http://localhost:8080/vod/movie123/master.m3u8
```

---

## Step 7: Upload to CDN / S3

```bash
# Sync output to S3
aws s3 sync /var/www/streams/vod/movie123/ \
  s3://your-cdn-bucket/vod/movie123/ \
  --acl public-read \
  --content-type application/x-mpegURL \
  --cache-control "max-age=31536000" \
  --exclude "*.m3u8" \
  --include "*.ts"

# Upload playlists with shorter cache
aws s3 sync /var/www/streams/vod/movie123/ \
  s3://your-cdn-bucket/vod/movie123/ \
  --include "*.m3u8" \
  --cache-control "max-age=300"
```

---

## Automated VOD Pipeline Script

```bash
#!/bin/bash
# Usage: ./vod-pipeline.sh <input-file> <stream-id>
set -e

INPUT="$1"
STREAM_ID="${2:-vod/$(basename $INPUT .mp4)}"

echo "Processing: $INPUT → $STREAM_ID"

# 1. Transcode
JOB=$(curl -s -X POST http://localhost:8002/transcode/vod \
  -H 'Content-Type: application/json' \
  -d "{\"input_url\":\"file://${INPUT}\",\"output_dir\":\"/var/www/vod/${STREAM_ID}\",\"profiles\":[\"360p\",\"720p\",\"1080p\"]}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

echo "Transcoding job: $JOB"

# 2. Wait for completion
while [[ "$(curl -s http://localhost:8002/jobs/$JOB | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")" != "completed" ]]; do
  sleep 5
done

echo "Transcoding complete!"

# 3. Package
curl -s -X POST http://localhost:8003/package/hls \
  -H 'Content-Type: application/json' \
  -d "{\"stream_id\":\"${STREAM_ID}\",\"output_dir\":\"/var/www/streams/${STREAM_ID}\"}"

echo "Packaging complete!"
echo "Playback URL: http://localhost:8080/${STREAM_ID}/master.m3u8"
```
