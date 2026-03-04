FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg && \
    curl -o /tmp/install-tsduck.sh https://tsduck.io/install.sh && \
    bash /tmp/install-tsduck.sh && \
    rm -rf /var/lib/apt/lists/* /tmp/install-tsduck.sh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001", \
     "--workers", "2", "--log-level", "info"]
