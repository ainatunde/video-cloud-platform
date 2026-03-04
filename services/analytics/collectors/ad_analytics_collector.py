"""Ad analytics collector - reads ad events from Redis and writes to TimescaleDB."""
import asyncio
import os
import json
import logging
from datetime import datetime, timezone
import asyncpg
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tsdb:changeme@timescaledb:5432/metrics")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
AD_EVENTS_KEY = "ad_events"
BATCH_SIZE = int(os.getenv("AD_BATCH_SIZE", "50"))
FLUSH_INTERVAL = int(os.getenv("AD_FLUSH_INTERVAL", "5"))


async def read_ad_events_from_redis(redis_client: aioredis.Redis) -> list[dict]:
    """Read a batch of ad events from Redis using BLPOP."""
    events: list[dict] = []
    try:
        # Non-blocking drain up to BATCH_SIZE items
        for _ in range(BATCH_SIZE):
            raw = await redis_client.lpop(AD_EVENTS_KEY)
            if raw is None:
                break
            try:
                event = json.loads(raw)
                events.append(event)
            except json.JSONDecodeError as exc:
                logger.warning(f"Skipping malformed ad event: {exc}")
    except Exception as exc:
        logger.error(f"Redis read error: {exc}")
    return events


async def insert_ad_analytics(conn: asyncpg.Connection, events: list[dict]):
    """Insert ad events into TimescaleDB."""
    rows = []
    now = datetime.now(timezone.utc)
    for event in events:
        rows.append((
            event.get("time") or now,
            event.get("stream_id", "unknown"),
            event.get("ad_id", "unknown"),
            event.get("event_type", "impression"),
            event.get("ad_server"),
            event.get("creative_url"),
            event.get("duration_s"),
            event.get("viewer_id"),
            event.get("geo_country"),
        ))
    if rows:
        await conn.executemany(
            """INSERT INTO ad_analytics
               (time, stream_id, ad_id, event_type, ad_server,
                creative_url, duration_s, viewer_id, geo_country)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            rows,
        )
        logger.info(f"Inserted {len(rows)} ad analytics rows")


async def main():
    db_conn = await asyncpg.connect(DATABASE_URL)
    redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
    logger.info("Ad analytics collector started")
    try:
        while True:
            events = await read_ad_events_from_redis(redis_client)
            if events:
                await insert_ad_analytics(db_conn, events)
            else:
                # Wait before polling again when no events
                await asyncio.sleep(FLUSH_INTERVAL)
    finally:
        await redis_client.aclose()
        await db_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
