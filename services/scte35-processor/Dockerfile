FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget ca-certificates && \
    wget https://github.com/tsduck/tsduck/releases/download/v3.43-4549/tsduck_3.43-4549.ubuntu25_arm64.deb && \
    apt-get install -y ./tsduck_3.43-4549.ubuntu25_arm64.deb && \
    rm tsduck_3.43-4549.ubuntu25_arm64.deb
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001", \
     "--workers", "2", "--log-level", "info"]
