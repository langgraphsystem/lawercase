#!/bin/bash
# Start script for Railway deployment
# Uses PORT environment variable if available, defaults to 8000

PORT=${PORT:-8000}
WORKERS=${WORKERS:-4}

echo "Starting MegaAgent Pro API on port $PORT with $WORKERS workers..."

exec uvicorn api.main_production:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips '*'
