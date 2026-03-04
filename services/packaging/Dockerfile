FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends wget curl \
    && wget -q https://github.com/google/shaka-packager/releases/download/v3.2.0/packager-linux-x64 \
         -O /usr/local/bin/packager \
    && chmod +x /usr/local/bin/packager \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8003/health || exit 1

CMD ["uvicorn", "shaka_packager:app", "--host", "0.0.0.0", "--port", "8003", \
     "--workers", "2", "--log-level", "info"]
