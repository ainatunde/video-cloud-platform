#!/bin/bash
set -euo pipefail

echo "──────────────────────────────────────────────"
echo "  SRS (Simple Realtime Server) starting up"
echo "──────────────────────────────────────────────"

# Substitute environment variables in srs.conf if needed
# (SRS does not natively support env-var substitution, so we pre-process)
CONF=/etc/srs/srs.conf

if [ -n "${CANDIDATE:-}" ]; then
    echo "INFO: Setting RTC candidate to ${CANDIDATE}"
    sed -i "s|\\\$CANDIDATE|${CANDIDATE}|g" "${CONF}"
else
    # Default to wildcard if no candidate IP provided
    sed -i "s|\\\$CANDIDATE|*|g" "${CONF}"
fi

echo "INFO: Starting SRS with config ${CONF}"
exec /usr/local/srs/objs/srs -c "${CONF}"
