#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Generate a synthetic RTMP test stream using FFmpeg.
# Requires ffmpeg installed locally (not in Docker).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RTMP_PORT="${RTMP_PORT:-1935}"
RTMP_URL="rtmp://localhost:${RTMP_PORT}/live/test"
DURATION="${STREAM_DURATION:-120}"  # seconds

if ! command -v ffmpeg &>/dev/null; then
    echo "✘  ffmpeg not found in PATH. Install ffmpeg to run test streams." >&2
    exit 1
fi

echo "▶  Pushing test stream to ${RTMP_URL} for ${DURATION}s…"
echo "   Press Ctrl-C to stop early."

ffmpeg -re \
    -f lavfi -i "testsrc2=size=1280x720:rate=30" \
    -f lavfi -i "sine=frequency=1000:sample_rate=48000" \
    -c:v libx264 -preset veryfast -b:v 2500k -g 60 -keyint_min 60 \
    -c:a aac -b:a 128k -ar 48000 \
    -f flv \
    -t "${DURATION}" \
    "${RTMP_URL}"

echo "✔  Test stream complete."
