#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Platform setup script
# Run once before `make up` to prepare the environment.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "──────────────────────────────────────────────"
echo "  Video Cloud Distribution Platform — Setup"
echo "──────────────────────────────────────────────"

# 1. Copy .env.example to .env if not already present
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✔  Created .env from .env.example (please edit before production use)"
else
    echo "✔  .env already exists"
fi

# 2. Create required directories
mkdir -p models config/nginx/ssl

# 3. Create .gitkeep so models/ is tracked without model files
touch models/.gitkeep

# 4. Pull Docker images (optional — speeds up first `make up`)
if command -v docker &>/dev/null; then
    echo "▶  Pulling base images…"
    docker pull ossrs/srs:5 &
    docker pull python:3.11-slim &
    docker pull node:20-alpine &
    docker pull timescale/timescaledb:latest-pg14 &
    docker pull grafana/grafana:latest &
    docker pull prom/prometheus:latest &
    docker pull postgres:14-alpine &
    docker pull redis:7-alpine &
    docker pull nginx:alpine &
    wait
    echo "✔  Base images pulled"
fi

echo ""
echo "✔  Setup complete.  Run 'make up' to start the platform."
echo ""
