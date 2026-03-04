# Build from the official FFmpeg Alpine image
FROM jrottenberg/ffmpeg:7.1-alpine AS base

RUN apk add --no-cache python3 py3-pip curl

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

COPY . .

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

CMD ["python3", "-m", "uvicorn", "transcoding_manager:app", \
     "--host", "0.0.0.0", "--port", "8002", "--log-level", "info"]
