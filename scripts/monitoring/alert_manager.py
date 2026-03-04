#!/usr/bin/env python3
"""Alert manager for video platform monitoring."""
import asyncio
import os
import logging
from datetime import datetime, timezone
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "60"))

ALERT_RULES = [
    {
        "name": "HighLatency",
        "query": "avg(stream_latency_ms) > 5000",
        "severity": "warning",
        "message": "Average stream latency exceeds 5 seconds",
    },
    {
        "name": "StreamDown",
        "query": "count(up{job='srs'}) == 0",
        "severity": "critical",
        "message": "SRS ingest server is unreachable",
    },
    {
        "name": "HighBufferRatio",
        "query": "avg(buffer_ratio) > 0.1",
        "severity": "warning",
        "message": "Average buffer ratio exceeds 10%",
    },
    {
        "name": "LowFillRate",
        "query": "avg(ad_fill_rate) < 0.5",
        "severity": "info",
        "message": "Ad fill rate below 50%",
    },
    {
        "name": "TranscoderDown",
        "query": "count(up{job='ffmpeg-transcoder'}) == 0",
        "severity": "critical",
        "message": "FFmpeg transcoder is unreachable",
    },
    {
        "name": "YOLODown",
        "query": "count(up{job='yolo-analyzer'}) == 0",
        "severity": "warning",
        "message": "YOLO analyzer is unreachable — auto ad insertion disabled",
    },
]


async def check_alert(client: httpx.AsyncClient, rule: dict) -> bool:
    """Query Prometheus and return True if the alert condition fires."""
    try:
        r = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": rule["query"]},
            timeout=5.0,
        )
        data = r.json()
        result = data.get("data", {}).get("result", [])
        return len(result) > 0
    except Exception as e:
        logger.error(f"Error checking alert '{rule['name']}': {e}")
        return False


async def send_alert(client: httpx.AsyncClient, rule: dict):
    """Fire alert: log and optionally POST to webhook."""
    now = datetime.now(timezone.utc).isoformat()

    if not ALERT_WEBHOOK_URL:
        logger.warning(
            f"ALERT [{rule['severity'].upper()}] {rule['name']}: {rule['message']} at {now}"
        )
        return

    payload = {
        "alert": rule["name"],
        "severity": rule["severity"],
        "message": rule["message"],
        "time": now,
    }
    try:
        resp = await client.post(ALERT_WEBHOOK_URL, json=payload, timeout=5.0)
        if resp.status_code not in (200, 201, 204):
            logger.error(f"Webhook returned {resp.status_code} for alert {rule['name']}")
        else:
            logger.info(f"Alert {rule['name']} sent to webhook")
    except Exception as e:
        logger.error(f"Failed to send alert {rule['name']} to webhook: {e}")


async def main():
    logger.info(f"Alert manager started. Prometheus: {PROMETHEUS_URL}")
    logger.info(f"Monitoring {len(ALERT_RULES)} alert rules, checking every {CHECK_INTERVAL}s")

    async with httpx.AsyncClient() as client:
        while True:
            for rule in ALERT_RULES:
                if await check_alert(client, rule):
                    await send_alert(client, rule)
            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
