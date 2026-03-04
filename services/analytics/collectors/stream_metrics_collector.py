"""Stream metrics collector - polls SRS API and pushes to TimescaleDB."""
import asyncio
import os
import logging
from datetime import datetime, timezone
import aiohttp
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:changeme@timescaledb:5432/platform")
SRS_API_URL = os.getenv("SRS_API_URL", "http://srs:1985")
COLLECT_INTERVAL = int(os.getenv("COLLECT_INTERVAL", "10"))


async def collect_srs_metrics(session: aiohttp.ClientSession) -> list[dict]:
    """Fetch stream metrics from SRS HTTP API."""
    try:
        async with session.get(f"{SRS_API_URL}/api/v1/streams") as resp:
            data = await resp.json()
            return data.get("streams", [])
    except Exception as e:
        logger.error(f"Failed to collect SRS metrics: {e}")
        return []


async def insert_metrics(conn: asyncpg.Connection, metrics: list[dict]):
    """Insert metrics into TimescaleDB."""
    now = datetime.now(timezone.utc)
    rows = []
    for stream in metrics:
        rows.append((
            now,
            stream.get("id", "unknown"),
            stream.get("kbps", {}).get("recv_30s", 0) * 1000,
            stream.get("video", {}).get("fps", 0.0),
            0.0,   # buffer_ratio from player
            0,     # startup_time from player
            0,     # latency
            0.0,   # packet loss
            0.0,   # jitter
            stream.get("clients", 0),
            None, None,
        ))
    if rows:
        await conn.executemany(
            """INSERT INTO stream_metrics
               (time, stream_id, bitrate, fps, buffer_ratio, startup_time_ms,
                latency_ms, packet_loss, jitter_ms, viewer_count, geo_country, geo_city)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
            rows,
        )
        logger.info(f"Inserted {len(rows)} stream metric rows")


async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                metrics = await collect_srs_metrics(session)
                if metrics:
                    await insert_metrics(conn, metrics)
                await asyncio.sleep(COLLECT_INTERVAL)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
