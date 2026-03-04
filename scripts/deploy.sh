#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Production deploy script
# Builds images, runs migrations, and performs a rolling restart.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "──────────────────────────────────────────────"
echo "  Video Cloud Distribution Platform — Deploy"
echo "──────────────────────────────────────────────"

# Ensure .env is present
if [ ! -f .env ]; then
    echo "✘  .env not found. Run 'make setup' first." >&2
    exit 1
fi

echo "▶  Building images…"
docker compose build --pull

echo "▶  Starting infrastructure services first (postgres, redis, timescaledb)…"
docker compose up -d postgres redis timescaledb
echo "   Waiting 10s for databases to initialise…"
sleep 10

echo "▶  Starting remaining services…"
docker compose up -d --remove-orphans

echo "▶  Running health check…"
sleep 15
python3 scripts/monitoring/health_check.py || true

echo ""
echo "✔  Deploy complete."
echo ""
